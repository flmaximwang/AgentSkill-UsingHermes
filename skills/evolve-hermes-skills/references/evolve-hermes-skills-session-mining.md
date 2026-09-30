# Mining a finished session

The read half of `evolve-hermes-skills`: how to resolve which session to evolve, the four extractions the
subagent must run, the brief to paste into it, the report schema, and how the parent spot-checks the
result. Every command here was run against this machine's profile (`~/.hermes`, macOS, 2026-09-30) and the
outputs shown are real; where a claim is inferred rather than measured it says so.

Contents: §1 resolve the session · §2 the four extractions · §3 the subagent brief · §4 report schema ·
§5 gap classes · §6 parent-side verification · §7 what the transcript does not contain

## §1 Resolve the session

`$HERMES_HOME/state.db` is the canonical store (`sessions` + `messages`, SQLite). The session id has the
shape `20260930_163743_baa9e162` — date, time, short hash.

```bash
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
python3 -c "import sqlite3; c=sqlite3.connect('$HERMES_HOME/state.db'); [print(r) for r in c.execute(\"select id, datetime(started_at,'unixepoch','localtime'), chat_id, message_count, title from sessions order by last_activity_at desc limit 5\")]"
```

Measured while this file was being written:

```
('20260930_163743_baa9e162', '2026-09-30 16:37:43', '1554774220251332690', 35, '创建 evolve-hermes-skills 技能')
('20260930_162008_8587d70c', '2026-09-30 16:20:08', '1554769799991529472', 216, '安装 remove-hermes-skills skill')
('20260930_161657_430e707b', '2026-09-30 16:16:57', '1554768993779326989', 120, '迁移 hermes-skills 与 agent-evolution 重叠 skill')
```

Why this matters: three Discord threads were live at the same minute, and the *second* row's
`last_activity_at` (16:38:39) sat later than the first row's *start* (16:37:43). **"Newest session" alone
is wrong on a machine with concurrent sessions.**

Resolution, in order:

1. **By channel.** `chat_id` on this profile is the Discord channel/thread id (`sessions` also carries
   `thread_id` and `source`). Take the row whose `chat_id` equals the channel the evolve request arrived
   in. One row per thread is the normal case.
2. **By newest.** CLI sessions (`source` = `local`/`cli`) have no channel to match. Take the newest by
   `last_activity_at`, then **assert** it: the last few `user` messages must contain the evolve request.
3. **By asking.** If the assertion fails — the newest session's tail is about something else — print the
   three newest `id / title / started_at` triples and ask the user which session to evolve. Do not guess,
   and never union two sessions into one report: the receipts stop being receipts.

```sql
-- assertion form: the tail of the candidate must contain the invocation
select id, role, substr(content,1,120)
from messages where session_id = :sid order by id desc limit 12;
```

`sessions.title` is a usable handle when the user names the session ("evolve the one about X") — a LIKE
over `title`, or `session_search`, resolves it to an id, and the id is what everything downstream needs.

## §2 The four extractions

### 2.1 Which skills the session actually loaded

`messages.tool_calls` on the assistant rows is the request side (an array of
`{"function": {"name": …, "arguments": …}}`), and `json_each` walks it. This is the authoritative answer to
"which skills did you call in this session" — `hermes skills list` answers a different question (what is
installed).

```python
import sqlite3
c = sqlite3.connect(f"{HERMES_HOME}/state.db")
q = """select json_extract(tc.value,'$.function.name') as fn,
              json_extract(tc.value,'$.function.arguments') as args
       from messages m, json_each(m.tool_calls) tc
       where m.session_id=? and m.tool_calls is not null
         and json_extract(tc.value,'$.function.name')
             in ('skill_view','skill_manage','skills_list')
       order by m.id"""
for fn, args in c.execute(q, (sid,)): print(fn, '|', args)
```

Measured on session `20260930_162008_8587d70c` (the one that installed `remove-hermes-skills`):

```
skill_view   | {"name": "install-hermes-skills"}
skill_view   | {"name": "hermes-agent"}
skill_view   | {"name": "install-hermes-skills", "file_path": "references/install-hermes-skills-diagnosis.md"}
skill_manage | {"operations": [{"name": "install-hermes-skills", "action": "patch", "file_path": "references/install-hermes-s…
```

Three facts fall out of that one query, which is why it is the first extraction: which skills were opened,
which reference files were actually reached (a reference nobody opens is a routing bug — dim 6 territory),
and which skills the session **edited** (`skill_manage`), which are findings-in-waiting whether or not the
curator was involved.

Result-side fallback, if `tool_calls` is ever empty for a store: `skill_view` results carry the skill name
as JSON, so

```sql
select json_extract(content,'$.name') from messages
where session_id=? and tool_name='skill_view' and json_valid(content)
  and json_extract(content,'$.name') is not null
```

returns the same names (measured: the three rows above). Prefer the `tool_calls` form — it also carries the
arguments.

### 2.2 What the process actually did (tool census)

```sql
select tool_name, count(*) from messages
where session_id=? and tool_name is not null group by 1 order by 2 desc;
```

Measured, same session:

```
terminal 55 · read_file 25 · search_files 17 · write_file 11 · process_manage 7
skill_view 3 · tool_search 1 · skill_manage 1 · session_search 1 · patch 1
```

This is the raw material for the gaps **no** skill covers: a session that ran `terminal` 55 times against a
handful of skills did most of its work outside them. Read it as a prompt to the diff job in §5 — every one
of those tools is a place where a missing step in a routed skill costs the next session the same search.

### 2.3 Which skills appeared while the session ran

The curator's audit ledger is a JSONL file, one entry per mutation by any actor:

`$HERMES_HOME/skills/.curator_ledger.jsonl` — keys `id, ts, actor, action, skill, evidence, before, after`
(measured on 1023 lines).

```python
import json
for line in open(f"{HERMES_HOME}/skills/.curator_ledger.jsonl", encoding="utf-8"):
    e = json.loads(line)
    if (e.get("evidence") or {}).get("session_id") == sid:
        print(e["ts"], e["actor"], e["action"], e["skill"], e["id"])
```

Measured: **all 200 most recent entries carry `evidence.session_id`**, so the session that caused a
mutation is recorded rather than inferred. `action` is one of `create / write_file / patch / delete`;
`actor` is `curator`, `agent` (the foreground session's own `skill_manage`), or `user`.

- `action: create` → **a skill that did not exist when the session began.** These are the
  "curator 产生的新 skill" the user asks about, and they have no lock entry and no repo by construction:
  Phase 2 rung 2, plus the promotion question.
- `write_file` / `patch` by `curator` → the background pass edited an existing skill mid-session. Its
  edits are as much a product of the session as the agent's, so diff those too; `evidence.session_id`
  names the causing session.
- Anything by `agent` → the session's own edits, i.e. the session already noticed a gap. Start there: an
  agent that patched a skill mid-session has usually left a note of what it found.

Ledger entries are appended live, so an entry created *after* the subagent ran is not in its report —
re-run this one query at the end of Phase 2 if the session is long, and reconcile before optimising.

### 2.4 Provenance per skill (input to Phase 2's ladder)

`.usage.json` is per-skill telemetry: `created_by, state, use_count, view_count, patch_count,
last_viewed_at, last_used_at, created_at, pinned, archived_at`. `created_by: "agent"` marks a skill the
agent made; `"installed"` a hub install; `null` a bundled/pre-marker skill. Measured, top `last_viewed_at`:

```
maintain-hermes-skills      created_by=installed  state=active
skill-library-consolidation created_by=agent      state=active   ← curator-created, no repo
hermes-agent                created_by=None       state=active
```

Cross-check the hub lock for a repo-maintained skill (exact commands in
`evolve-hermes-skills-routing.md` §1); `created_by` alone cannot see a repo.

## §3 The subagent brief

Paste this, filling the two placeholders. It is deliberately explicit that the child cannot ask questions.

```
You are mining ONE finished Hermes session, read-only, to find where the skills it loaded failed it.
Do not edit, create or delete any file, and do not patch any skill — your deliverable is a report.

Inputs
- HERMES_HOME: <...>
- session id: <...>
- The full extraction recipe (commands + measured receipts): <abs path to this file>
- Resolve nothing yourself: the session id above is the one to mine.

What to do
1. Run every query in §2 of the recipe and record the raw output. If a query returns no rows, say so
   explicitly — an empty result is a finding about the session, not a reason to stop.
2. Read, in full, every skill the session loaded (SKILL.md and, for each reference the session actually
   reached, that reference file), plus every skill the ledger shows was created or edited during the
   session.
3. Diff the session's real process against those skills: read the transcript (messages table, ordered by
   id) and find every place where (a) the user corrected the agent's approach or facts, (b) the agent
   improvised something a loaded skill should have stated, (c) a command or file path had to be
   discovered, retried or re-derived because a skill was silent or wrong, (d) a failure branch fired
   that the skill does not encode, (e) a skill was loaded but its reference was never reached although
   the session needed it.
4. For each such place, produce ONE finding. A finding without a receipt is deleted before you report:
   receipt = a messages.id plus the verbatim quote (<= 200 chars), or the real command output.
5. Rank findings by what they cost the session: a user correction > a wrong command > a re-derivation >
   a slow path > a cosmetic gap.

Report exactly this schema, nothing else:
- session: id, title, channel, message count, start time
- skills_loaded: [{name, loaded_via: skill_view|skill_manage, references_reached: [...], provenance:
  agent|installed|bundled|repo|unknown, path}]
- skills_appeared: [{name, actor, action, ts, ledger_id}]   (from §2.3; empty list is a valid answer)
- tool_census: [{tool, count}]
- findings: [{id, skill, evidence: {message_id, quote}, gap_class: missing-step|wrong-step|
  missing-failure-branch|missing-pointer|trigger-never-fired|no-skill-covered, cost: user-correction|
  wrong-command|re-derivation|slow-path|cosmetic, proposed_edit: one or two sentences, dimension_hint:
  dim2|dim3|dim4|dim5|dim6}]
- no_coverage: [ {what the session did, tools used, evidence} ]   (work no loaded skill covered)
- skipped: [ {what you did not examine, and why} ]
```

## §4 Report schema notes

- `dimension_hint` is the bridge to Phase 3: darwin's rubric wants the *dimension* to fix, and the gap
  class maps onto it — `missing-step`→dim2, `missing-failure-branch`→dim3, no checkpoint→dim4,
  `wrong-step`/vagueness→dim5, `missing-pointer`/`reference never reached`→dim6.
- `skipped` is compulsory and is the honesty valve: transcripts are long, and a child that silently
  sampled half of them produces a confident report over a partial read.
- Keep `proposed_edit` to one or two sentences. The actual edit belongs to Phase 3, where darwin's
  per-round single-dimension rule applies; a fully drafted rewrite smuggled in at Phase 1 defeats that.

## §5 Gap classes, and where each one goes

| Class | What it looks like in the transcript | Route |
|---|---|---|
| `missing-step` | the agent did a step no skill names | add the step; if it needs depth, a reference |
| `wrong-step` | an instruction in the skill that the session proved wrong for this machine | correct it, with the session's output as the receipt |
| `missing-failure-branch` | a retry, a fallback, a "that failed so then…" the skill does not encode | encode trigger / first fix / fallback (darwin dim3) |
| `missing-pointer` | the right reference existed but was never reached, or the body never routes to it | add or repair the route row (dim6) |
| `trigger-never-fired` | a skill that should have loaded and did not appear in §2.1 | fix the description's trigger condition, not the body |
| `no-skill-covered` | work in `tool_census` that no loaded skill touches | candidate new skill, or a new reference under an existing umbrella — check the umbrella first |

## §6 Parent-side verification

Two findings, minimum, re-queried directly. One command, using the ids the report returned:

```python
for mid in (findings[0]["evidence"]["message_id"], findings[1]["evidence"]["message_id"]):
    print(mid, c.execute("select role, tool_name, substr(content,1,300) from messages where id=?", (mid,)).fetchone())
```

The quote must exist and must mean what the report says it means. Two traps this catches are worth naming:
the child paraphrasing a message it read in a summary rather than in full, and the child attributing the
*agent's* words to the *user* (a correction and a proposal look alike in a transcript and route to
different edits). A finding that fails goes in the user-facing report as dropped, with the reason.

## §7 What the transcript does and does not contain

- **Compaction.** `messages.compacted` and `messages._compressed_summary` mark turns the context
  compressor folded into a summary. Measured 2026-09-30 across this profile's `state.db`: **zero
  `compacted=1` rows**, so every session's transcript is complete on this machine. Check it before
  trusting a report — `select count(*) from messages where session_id=? and compacted=1` — and when it is
  non-zero, say the session is partial and that pre-compaction detail is only recoverable from the
  compressed summaries, not from the full turns.
- **Full text survives compression in the FTS mirror.** `messages_fts` (measured: 54 113 rows) indexes
  message content, so a search for a phrase the agent used still lands on the row even when the live
  context no longer holds it.
- **The user's own words are the highest-value rows** and the easiest to lose: filter `role='user'` and
  read them in order before anything else — the corrections are the receipt class that outranks every
  other.
- **The transcript is not the session's whole state.** Memory writes, cron mutations and file edits happen
  outside it. Skill-relevant state has its own stores (`.usage.json`, `.curator_ledger.jsonl`, the hub
  lock), which is exactly why §2 reads them instead of the transcript.
