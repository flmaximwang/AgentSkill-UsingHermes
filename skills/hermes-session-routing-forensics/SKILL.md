---
name: hermes-session-routing-forensics
description: "Use when a Hermes chat's messages reach the wrong agent."
---

# Hermes conversation-routing forensics

## When to Use

- A session suddenly answers as a sub-agent — "am I in the main agent?"
- A delegated batch never reported back to the conversation that dispatched it.
- A channel sprouts a thread whose name is a subagent task string.
- You must know which session a chat/thread resolves to before /new-ing, archiving, or re-running
  work on that line.

## Procedure overview

Answer "which agent am I actually talking to?" — and "where did the delegated work go?" — from the
session store and the gateway log, **read-only**. No code tracing until the cheap evidence conflicts.

## The model in one paragraph

A messaging chat maps to a **routing key**
(`agent:<profile>:<platform>:<chat_type>:<chat_id>[:<thread_id>]`) and that key maps to exactly **one
session row** at a time. Every inbound message — including *synthetic* ones the gateway injects
itself — is delivered to whatever session the key currently resolves to. So "which agent is answering
me" is never a UI question: it is "which `session_id` does this key hold, and what is that row's
lineage?"

## Step 1 — Find the routing key and its current owner

```bash
sqlite3 -header -column ~/.hermes/state.db "
SELECT r.session_key,
       json_extract(r.entry_json,'$.session_id')   AS owner_session,
       json_extract(r.entry_json,'$.display_name') AS display_name,
       datetime(r.updated_at,'unixepoch','localtime') AS entry_updated
FROM gateway_routing r
WHERE r.session_key LIKE '%<chat_or_thread_id>%';"
```

- `~/.hermes/state.db` is the **default profile**; another profile's chats live in
  `~/.hermes/profiles/<name>/state.db`. `gateway_routing.scope` is the sessions directory, so entries
  never mix across stores — query each profile's own file.
- `entry_updated` is when the entry was last written, **not** when the route moved: the `created_at`
  inside `entry_json` is the *session's* start time. Date a route change from the log line (Step 3).

## Step 2 — Check whether one key is held by two live rows

```bash
sqlite3 -header -column ~/.hermes/state.db "
SELECT substr(id,1,26) id, source, created_source, substr(parent_session_id,1,26) parent,
       end_reason, datetime(started_at,'unixepoch','localtime') started,
       datetime(ended_at,'unixepoch','localtime') ended, message_count, title
FROM sessions WHERE session_key = '<key>' ORDER BY started_at;"
```

Read it as: **one live row is normal; a second row carrying the chat's key is the takeover shape.**

- Classify by `created_source`, not `source`: `source` is live routing state and a child that grabbed
  the chat's key reads the *platform* there, while `created_source='subagent'` still records what it
  really is.
- `json_extract(model_config,'$._delegate_from')` / `'$._branched_from')` name the fork edge — a
  delegate child, or a branch. Walk `parent_session_id` upward to see whose chat key it took.
- `end_reason='session_switch'` on the original row is the fingerprint of that row's key being moved
  to another session while the row was still live.

## Step 3 — The trigger is in the log, one line per decision

```bash
grep -n -E "Pinned async-delegation completion|permanently-gone session|still live in sessions.json|Watch pattern notification|Invalidated run generation|STOP for session|slash '/(stop|new|branch)'" ~/.hermes/logs/gateway.log | tail -40
```

| Log line | What it means |
|---|---|
| `Pinned async-delegation completion to owning session <X> (was <Y>) for routing key <K>` | The key K just moved from Y to X. If X is a delegate/subagent row, the chat is now the subagent's. |
| `Watch pattern notification — injecting for <platform> chat=…` immediately before an `inbound message: … msg='[IMPORTANT: Background process <proc> exited…'` | A **subagent's background-process notice was injected into the parent chat** as a synthetic inbound message. This is the usual trigger — not anything the user typed. |
| `routing key '<K>' -> <X> is ended in state.db but still live in sessions.json; dropping stale entry and recovering/recreating the session` | The key's owner had already ended (or was ended by a fork); the next message recreates a session on that key. |
| `Async delegation <id> targets permanently-gone session <S>; terminally dropping delivery (result remains in the delegation records)` | The batch result never reached its parent. |
| `Invalidated run generation … (stop_command)` + `STOP for session <key> — agent interrupted` | A `/stop`. It also terminates the in-flight async delegations. |

Discord slash commands are logged by the adapter (`slash '/branch' invoked by user=…`), which is how
you date a fork or a stop to the second.

## Step 4 — Where the delegated work went

```bash
sqlite3 -header -column ~/.hermes/state.db "
SELECT delegation_id, substr(origin_session,-38) origin_session, origin_session_id,
       parent_session_id, state, delivery_state,
       datetime(dispatched_at,'unixepoch','localtime') dispatched,
       datetime(completed_at,'unixepoch','localtime') completed
FROM async_delegations
WHERE origin_session LIKE '%<chat_id>%' OR parent_session_id IN
      (SELECT id FROM sessions WHERE session_key LIKE '%<chat_id>%')
ORDER BY dispatched_at;"
```

Then read the payload — **`delivery_state` decides whether the parent ever saw it, and per-task
`status` decides whether the work exists at all**:

```bash
sqlite3 ~/.hermes/state.db "SELECT result_json FROM async_delegations WHERE delegation_id='<id>';" \
  | python3 -c "import json,sys; r=json.load(sys.stdin); [print(x.get('status'),'|',(x.get('summary') or '')[:110]) for x in r.get('results',[])]"
```

- `delivery_state='delivered'` → it was injected; `'dropped'` → it was not, and the result exists
  only in this table.
- `status='interrupted'` tasks produced (at most) a truncated summary — they must be **re-dispatched**,
  not "recovered". Count them before telling the user how much survived.

## Step 5 — Confirm from the transcript

```bash
sqlite3 ~/.hermes/state.db "SELECT id, role, substr(replace(content,char(10),' / '),1,200), datetime(timestamp,'unixepoch','localtime') FROM messages WHERE session_id='<owner_session>' ORDER BY id DESC LIMIT 10;"
```

The user's own messages appearing under the *owner* session's id proves routing delivered them there —
no need to infer it from his description. For cross-profile recall use `session_search(profile=<name>)`;
`session_search` finds transcript content, the DB finds routing.

## Rules and pitfalls

- **A delegate/subagent child must never hold the chat's routing columns** (`session_key`, `chat_id`,
  `chat_type`, `thread_id`, `user_id`); only a compression fork may inherit them. The repo carries a
  guard test for exactly this (`tests/hermes_state/test_delegate_child_routing_inheritance.py`), so a
  child row carrying the chat's key IS the bug — verify with `created_source` +
  `parent_session_id` before blaming the platform layer.
- **The trigger is usually an injected synthetic inbound, not the user's message.** A subagent's
  background-process completion notice is addressed to the chat and arrives looking like a message
  from the user; the gateway's routing recovery then re-pins the key to the session that owns that
  delegation. So "why exactly then" answers as: a background process the child started exited.
- **"Ends the run" is not "restores the route".** `/stop` kills the run generation and the in-flight
  delegations (`interrupted`), but the key stays where it is; only `/new` (or a route recovery) moves
  it. Never tell the user the main session resumed after `/stop`.
- **`/branch` from a hijacked chat forks the wrong conversation.** The branch's parent is whatever row
  owns the key — if that is a subagent, the new thread and its title are built from the subagent
  session, which is why a channel sprouts a thread named after a subagent task.
- **A `session_switch`-ended row is not resumable.** The key is gone; the transcript stays in the DB,
  reachable through `session_search` / `@session:<profile>/<id>` only. Say that instead of promising a
  return to that conversation.
- **Read-only, always.** `gateway_routing`, `sessions` and `async_delegations` are gateway-owned: hand
  the chat-side command (`/new`) to the user rather than editing rows or switching keys yourself.
- **Order of evidence: routing table → owner row lineage → log decision lines → delegation records →
  transcript.** One log line usually names the decision (`Pinned …` / `dropped` / `Invalidated run
  generation`); grep that before opening any source file.

## Answer shape (this user)

1. **One-sentence conclusion** naming the trigger and the second it happened.
2. **The decision sequence** as short bullets, each carrying its own log line or DB read — the trigger
   (which command / input form / event) first, the branch that consumed it second.
3. **What it cost** — what was dropped or killed, and what is still recoverable (with where).
4. **What to do now** — one action.
5. State what was **ruled out** as well as what remains open. Do **not** answer with "which function
   writes that field" or a narrated call chain: the ask is the trigger and the judgment sequence.

## Files

- `references/hermes-session-routing-forensics-state-db-routing-queries.md` — the ready SQL/log greps, per-store notes, and how to read
  each column.
- `scripts/routing_owner.py` — one-shot read-only dump: routing key → owner, every row holding the
  key, parent chain, delegations with per-task status.

## Skill Structure

<!-- Generated by Scripts -->

```
hermes-session-routing-forensics/
├── SKILL.md  (179 lines)
├── test-prompts.json  (14 lines)
├── references/
│   └── hermes-session-routing-forensics-state-db-routing-queries.md  (54 lines)
└── scripts/
    └── routing_owner.py  (140 lines)
```

<!-- Generated by Scripts -->
