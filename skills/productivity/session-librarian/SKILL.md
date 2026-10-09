---
name: session-librarian
description: "Organize sessions by prompt: find, rename, archive, prune."
version: 1.0.0
author: Hermes Agent + Teknium
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Sessions, Organization, Cleanup, Library, Productivity]
    category: productivity
    related_skills: [weekly-review-planning]
---

# Session Librarian

Manage the user's session library conversationally: find past sessions about a
topic, summarize what they decided, rename them meaningfully, split work into
parallel sessions, and propose stale ones for archive or deletion — all from a
plain-language request like *"find my sessions about Q3 pricing, keep the
useful ones, and clean up the duplicates."*

Inspired by Perplexity Computer's prompt-driven session management (Aug 2026):
the agent starts, organizes, and cleans up the user's own session library, and
always shows the plan before touching anything.

## When to Use

- "What sessions do I have about X?" / "What did we decide about X?"
- "Rename these sessions to something meaningful."
- "Clean up my session library" / "archive the stale ones."
- "Fork that session into a follow-up focused on Y."
- "Split this into one session per ticket" (see Parallel workstreams below).

## The Two Surfaces

| Task | Surface |
|---|---|
| Find sessions by topic, read content, summarize decisions | `session_search` tool (FTS5 over the message store) |
| List/filter by metadata (age, source, cost, tokens, workspace) | `hermes sessions list` / `stats` via terminal |
| Rename | `hermes sessions rename <session_id> <title...>` |
| Bulk soft-hide (reversible) | `hermes sessions archive <filters>` |
| Delete (destructive) | `hermes sessions delete` / `hermes sessions prune <filters>` |
| Export before deleting anything valuable | `hermes sessions export --session-id <id> --format md` |
| Continue work in a new place | `/branch` (fork current session) or start a fresh session and cite the summary |

## Procedure

① **Discover.** Use `session_search(query=..., limit=5-10)` with topic
keywords; vary phrasing (feature name, symptom, project name). For metadata
sweeps ("sessions older than 60 days from telegram"), use
`hermes sessions list --source telegram --limit 50` instead.

② **Summarize per session.** The discovery result's `bookend_start` (goal),
match window, and `bookend_end` (resolution) usually suffice — only dump a
full session (`session_search(session_id=...)`) when the user asks for
decisions in depth. Report each as: link (`@session:` form) — one-line goal —
one-line outcome.

③ **Plan before acting (MANDATORY for anything that mutates).** Present a
plan table first: which sessions get renamed to what, which get archived,
which are proposed for deletion and why (duplicate of which keeper, stale,
empty). Wait for the user's go-ahead. Exception: a single rename the user
explicitly dictated can be done directly.

④ **Act with the safest primitive.**
- Prefer `archive` (reversible soft-hide) over `delete`/`prune`.
- Always run destructive commands with `--dry-run` first and show the output,
  then re-run with `--yes` after confirmation.
- Before deleting anything with meaningful content, offer
  `hermes sessions export --format md` as a backup.

⑤ **Report.** Renames applied, sessions archived (count + how to undo:
archived sessions remain in the DB and are listed with `--include-archived`),
anything exported, anything skipped and why.

## Parallel Workstreams

For "one session per ticket, investigate each, report back": do NOT try to
drive other live sessions. Use `delegate_task` with one task per workstream —
each subagent runs in its own session automatically — then synthesize their
summaries. Mention that each delegation's transcript is itself searchable
later via `session_search`.

## Bulk archiving by age ("archive everything older than N days")

`hermes sessions archive --older-than 30d --yes` looks like it covers the whole
library but silently misses two classes of rows, because bulk prune/archive
share `_PRUNE_FILTERS` / `_prune_filter_where` (`hermes_state_maintenance.py`):

1. `clauses = ["s.ended_at IS NOT NULL"]` — **unended (open) rows are never
   candidates**, and stale-open rows are exactly what accumulates (crashed
   backends, cli sessions that never closed).
2. Orphan-swept rows age from the sweep, not from activity:
   `(COALESCE(s.end_reason,'') != 'startup_orphan_reap' OR s.ended_at < ?)` —
   a deliberate *prune* safety rule (don't delete before recovery), which
   wrongly suppresses archive too.

**Two-pass procedure (verified, ~174/584 rows came from pass 2):**

```bash
# Pass 1 — ended sessions, the CLI path
hermes sessions archive --older-than 30d --dry-run   # show + count first
hermes sessions archive --older-than 30d --yes
```

```python
# Pass 2 — the leftovers; engine primitive, dry-run first
import sys, time; sys.path.insert(0, "<hermes repo>")
from hermes_state import SessionDB
from hermes_state_maintenance import _LAST_ACTIVE_SQL
db = SessionDB()  # db_path tells you which store you are touching
db.archive_stale_sessions(30, exclude_pinned=True)  # may archive unended rows
```

`archive_stale_sessions` is the sanctioned idle-archive sweep (`auto_archive`
uses it): it skips `end_reason='compression'` non-tips (archives whole lineage
via `set_session_archived`), the hidden canonical Bot Chat, and pinned rows.
Re-run **both** dry-runs afterwards and require zero leftovers before reporting.

## Enumerate EVERY session store first

One `hermes sessions ...` call touches exactly one profile's store, and the
desktop app lists all profiles at once — so a user with 6 profiles sees "lots of
old sessions" after a pass that fully cleaned `default`. Before touching
anything, enumerate and count:

```bash
hermes profile list                      # profile names (also: which gateways RUN)
find ~/.hermes -name state.db -not -path "*/venv/*"   # + ~/.hermes/profiles/*/state.db
```

Then per profile: `hermes -p <name> sessions archive --older-than 30d --dry-run`
for pass 1, and `HERMES_HOME=~/.hermes/profiles/<name> python -c "from hermes_state
import SessionDB; print(SessionDB().db_path)"` to prove pass 2 targets the right
store. Report per-profile counts — "the whole library" means every store.
`~/.hermes/state-snapshots/*/state.db` (pre-update backups) and
`shared-state.db` / `kanban.db` / `projects.db` are NOT session stores.

## Never archive an open row a live gateway route points at

`archive_stale_sessions` (and the built-in `sessions.auto_archive` sweep) will
archive **unended** rows — correct for dead cli/tui rows, wrong for a messaging
thread a running gateway will resume. Evidence, all source-verified:

- `gateway/session_lifecycle.py::_route_reset_reason` — *"Only explicit
  suspension replaces a routed conversation; time never does."* An idle-route
  entry is reused in place, so the next inbound message continues the SAME row.
- The repo has exactly **one** `set_session_archived(..., False)` call site
  (`hermes_state_sessions.py::unarchive_recoverable_session`) and it only fires
  for `ws_orphan_reap` / `agent_close` ends. Nothing un-archives on new
  activity → the resumed chat stays hidden from listings (`archived=exclude`).
- The engine's own orphan reaper spares rows a live gateway heartbeat could own
  (`respect_gateway_heartbeats`) — proof such rows are owned conversations, not
  debris.

Scan before/after every sweep (a route survives in `entry_json`, not a column):

```sql
select s.id, s.source, datetime(COALESCE(s.last_activity_at,s.started_at),'unixepoch','localtime'),
       r.session_key, datetime(r.updated_at,'unixepoch','localtime')
from sessions s join gateway_routing r on json_extract(r.entry_json,'$.session_id')=s.id
where s.archived=1 and s.ended_at is null;
```

Target = **zero rows**; restore each with `db.set_session_archived(sid, False)`
(never raw SQL — it must clear the whole compression lineage). Also note the
harm is visibility, not data loss: the archived flag gates listings/exports, not
`_check_transcript_write_guards`, so the resumed chat still writes fine.

## Pitfalls

- **`ORDER BY <flag> DESC` on a text label lies.** A `case when … then 'ROUTED'
  else 'no-route' end` sorts `'no-route'` FIRST (lowercase `n` > uppercase `R`
  in ASCII), so risky rows can fall outside a `LIMIT`. Sort numbers, or COUNT the
  risk set instead of eyeballing a list.
- **The age filter runs on `last_active` = freshest of `last_activity_at` /
  latest message / `started_at`** — a session created long ago but touched
  yesterday is correctly kept. Never reimplement the predicate in raw SQL with
  `strftime('%s', ...)`: it returns TEXT, so `numeric < text` is always true
  in SQLite and every row matches (silent over-match). Compare epoch numbers.
- **Pinned rows are never bulk-archived by either surface.** Report the
  remaining old-but-visible pinned sessions and let the user unpin
  deliberately; do not `--include-pinned` on your own initiative.
- **There is no `unarchive` CLI subcommand.** Restore via the desktop app
  (设置 → 会话 → 「已归档会话」→ 取消归档 / Settings → Sessions → Archived
  sessions → Unarchive) or `PATCH /api/sessions/{id}` with
  `{"archived": false}`; `set_session_archived` also un-hides the whole
  compression lineage, so raw `UPDATE sessions` on one row leaves ancestors
  archived.
- **Archive is a flag, not space.** `state.db` size barely moves; offer
  `hermes sessions optimize` (FTS merge + VACUUM) only if the user asked for
  disk back.
- **Never delete without a dry-run + explicit confirmation in this
  conversation.** A standing "clean things up" is authority to *propose*, not
  to prune.
- **`session_search` finds content, not metadata.** Age/cost/source filters
  live in the CLI; combine both when the request mixes them ("old sessions
  about pricing").
- **Titles are identity for `/resume <title>`.** When renaming, keep titles
  short, unique, and prefix-friendly; warn the user if a rename collides with
  an existing title.
- **Archived ≠ deleted.** Archive hides sessions from default listings only.
  Say which one you did.
- **Cross-profile session links** (`@session:<profile>/<id>`) are read-only
  from another profile; management commands act on the current profile's DB.

## Verification

After a cleanup pass, re-run the discovery query and `hermes sessions list`
to confirm the library reflects the plan (keepers present with new titles,
archived ones gone from the default listing).
