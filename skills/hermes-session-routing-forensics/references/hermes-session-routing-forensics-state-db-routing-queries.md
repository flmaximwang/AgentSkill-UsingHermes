# state.db routing queries — ready to paste

Read-only only. Default profile store: `~/.hermes/state.db`; per profile:
`~/.hermes/profiles/<name>/state.db`. Every query below is scoped to ONE store by design
(`gateway_routing.scope` is the sessions directory, so entries never mix across profiles).

Open read-only when poking around:

```bash
sqlite3 "file:$HOME/.hermes/state.db?mode=ro" "SELECT count(*) FROM sessions;"
```

## The three tables that answer everything

| Table | Columns that matter |
|---|---|
| `gateway_routing` | `session_key`, `entry_json` (JSON: `session_id`, `display_name`, `last_prompt_tokens`, `origin.*`), `updated_at`, `scope` |
| `sessions` | `id`, `source` (live), `created_source` (immutable provenance), `parent_session_id`, `session_key`, `chat_id`, `chat_type`, `thread_id`, `end_reason`, `started_at`, `ended_at`, `message_count`, `model_config` (`$._delegate_from`, `$._branched_from`), `display_name`, `archived`, `title` |
| `async_delegations` | `delegation_id`, `origin_session`, `origin_session_id`, `parent_session_id`, `state`, `delivery_state`, `dispatched_at`, `completed_at`, `task_json` (goals), `result_json` (per-task status/summary) |

## Routing key shape

`agent:<profile>:<platform>:<chat_type>:<chat_id>[:<thread_id>]` — e.g.
`agent:main:discord:thread:1554813966440603762:1554813966440603762`. Chat and thread id are often
identical for a Discord thread; search with `LIKE '%<id>%'` on the short form.

## Which columns are live vs provenance

- `source` = live routing state. A delegate child holding a chat key reads the *platform* there.
- `created_source` = stamped once at first creation and never overwritten. This is the column that
  says `subagent` for a child that later looks like a chat session.
- `end_reason` values worth recognizing: `session_switch` (the key was moved to another session),
  `compression` (a compression fork's parent), `session_reset`, `startup_orphan_reap`.

## Delegation lifecycle

- `state`: `running` → `completed` (the run itself finished).
- `delivery_state`: `pending` → `delivered` | `dropped`. `dropped` means the parent never received the
  result even though the run completed; the payload stays in `result_json`.
- A batch that a `/stop` interrupted comes back with per-task `status='interrupted'` — those tasks
  produced nothing usable and must be re-dispatched.

## Log greps (the cheap half)

```bash
grep -n "routing key" ~/.hermes/logs/gateway.log | tail -20
grep -n -E "Pinned async-delegation completion|permanently-gone session" ~/.hermes/logs/gateway.log | tail -20
grep -n -E "Watch pattern notification|Background process .* exited" ~/.hermes/logs/gateway.log | tail -20
grep -n -E "slash '/(stop|new|branch)'" ~/.hermes/logs/gateway.log | tail -20
```

The same lines mirror into `errors.log` and `gateway.error.log`. Timestamps there are local time and
are the authority for "when did the route change" (the DB columns are session start / entry write
update, not the switch instant).
