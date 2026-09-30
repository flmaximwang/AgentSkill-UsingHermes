# Session-store forensics — what did the agent actually do?

For questions of the shape "did you ever load skill X?", "have you been following rule Y?", "when did
behaviour Z stop?", "which prompt text was active then?". The session store is the record; the prompt text
you believe is loaded is not evidence, and neither is a skill's own body.

Use this whenever a claim would otherwise rest on the agent's self-report ("I have been applying that rule") or on the skill's text ("this skill's format appears in the replies"). Both are inferences; the store
holds the load record and the prompt text.

## The store

- One SQLite DB **per home**: `~/.hermes/state.db` (default profile) and
  `~/.hermes/profiles/<name>/state.db`. A skill loaded in one home says nothing about another — enumerate
  `~/.hermes/profiles/*/state.db` and report per home.
- `shared-state.db`, `kanban.db`, `projects.db` are **not** session stores. `~/.hermes/state-snapshots/*/state.db`
  are pre-update backups: usable for a *before* comparison, never as the current state.
- Open read-only — the live DB is WAL and can be hundreds of MB:
  `sqlite3 "file:<path>?mode=ro"` or `sqlite3.connect(f"file:{p}?mode=ro", uri=True)`.
- Tables that answer these questions:
  - `messages(id, session_id, role, content, tool_calls, tool_name, timestamp, ...)` — `role='assistant'`
    rows carry the requested calls in `tool_calls` (JSON), the result comes back as its own row with
    `role='tool'` + `tool_name` and the payload in `content`.
  - `sessions(id, started_at, source, title, system_prompt_hash, ...)` and `system_prompts(hash, prompt)` —
    join on `system_prompt_hash = hash` to recover the exact prompt text a session ran with
    (`sessions.system_prompt` also exists; the hash table is the deduped, reliable copy).

## Recipe A — was skill X ever loaded?

Parse, do not grep. A skill *name* appears in the `tool_calls` of unrelated work (a `grep` in a shell
command, a note write, a lock dump) and in the skill index that rides in **every** system prompt, so
`LIKE '%<name>%'` over the whole table over-counts badly. The load record is the `skill_view` tool *result*.

```python
import sqlite3, json, collections
db = sqlite3.connect("file:/Users/maxim/.hermes/state.db?mode=ro", uri=True)
per = collections.Counter()
for content, ts, sid in db.execute(
        "SELECT content, timestamp, session_id FROM messages WHERE tool_name='skill_view'"):
    try:
        per[json.loads(content).get("name", "?")] += 1
    except Exception:
        per["?"] += 1
```

Report count + earliest/latest timestamp + session id per skill, and the total number of `skill_view`
results as the denominator ("1 of 466 loads"). Zero loads of a skill the user believes is in force is the
finding — say "never loaded", not "probably applied via the persona".

## Recipe B — which prompt text was active when?

```sql
SELECT s.id, datetime(s.started_at,'unixepoch','localtime') AS started, p.prompt
FROM sessions s JOIN system_prompts p ON p.hash = s.system_prompt_hash
WHERE p.prompt LIKE '%<distinctive phrase from the rule>%'
ORDER BY s.started_at;
```

This dates a rule's presence in the persona (first / last session whose prompt carried it). It is how you
show a behaviour **predates** a skill's install — i.e. it was coming from `SOUL.md`, not from the skill
that was meant to replace it. When the rule lives only in a skill, no session prompt will match it: that
is the proof the index alone does not carry the body.

## Recipe C — was the behaviour applied?

Count the rule's **output shape**, not its intent:

```sql
SELECT date(timestamp,'unixepoch','localtime') AS day, count(*) FROM messages
WHERE role='assistant' AND content LIKE '%<required header>%'
GROUP BY day ORDER BY day;
```

Bracket the change: the last matching turn before it, and every session started after it. Zero matches
after the change, together with zero loads of the skill that was supposed to take over, is the finding —
state both numbers, and name the timestamp of the last matching turn.

## Recipe D — date the install that was supposed to carry the rule

- `<home>/skills/.hub/lock.json` → `installed.<name>.installed_at` (UTC) + `identifier` /
  `metadata.source_url`.
- `<home>/skills/.hub/audit.log` → the `<ISO-8601>Z INSTALL <name> <source>:<trust> <verdict> sha256:…` line.

Compare that timestamp with the first session that no longer carried the old prompt text (Recipe B). If the
install came **before** the prompt changed, the install is not what has been driving the behaviour — say so
instead of attributing the behaviour to the skill.

## Pitfalls

- **Install state and use state are different records.** `lock.json` / `hermes skills list` / `check` answer
  "is it installed, from where, at which revision" — none of them records a single load. An installed skill
  can sit at zero uses forever; `check` reporting `unavailable` is a fetch/network verdict and says nothing
  about usage.
- **`skill_view` results are JSON strings**; parse for `name`. Grepping the raw row for the skill name
  double-counts the skill index in system prompts and the user's own prose.
- **Epoch vs UTC.** `messages.timestamp` / `sessions.started_at` are epoch seconds (`datetime(t,'unixepoch','localtime')`);
  `audit.log` and `lock.json` carry UTC (`Z` / `+00:00`). Convert before comparing across the two.
- **A behaviour's text may exist twice** — verbatim in both `SOUL.md` and a skill body — when the persona was
  split into skills. Diff the skill body against the old prompt text from Recipe B before attributing the
  behaviour to either layer, and report the split as the cause.
- **Report the layer answer, not the archaeology.** The reply is: what the record shows (counts, first/last
  timestamps, session ids), which layer was actually in force, and what remains unproven. The SQL belongs in
  the note, not in the message.
