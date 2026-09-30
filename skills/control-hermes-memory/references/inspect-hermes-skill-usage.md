# Was this skill actually invoked? — usage forensics and trigger tuning

Read this when the complaint is a **skill that never fires**: *"did you ever load X?"*, *"why doesn't
this skill trigger?"*, *"the description is broad, so why is it ignored?"*. The memory/skill **write**
side (the fork, the curator, the approval queues) is `control-hermes-memory-md.md` and
`control-hermes-skill-curator.md`; this reference is the **read** side — measuring what did or did
not load, finding what fired instead, and changing a description so it can fire.

Every number below was measured on this machine **2026-09-30**, default profile, `~/.hermes`
(`HERMES_HOME=/Users/maxim/.hermes`), source at `~/.hermes/hermes-agent/` (git install
`v0.21.5+4905.gf42f579`). Nothing here is inferred from the docs.

## The premise — why a broad description is not a trigger

- **No code matches a description.** The `<available_skills>` block is pure text rendered into the
  system prompt (`agent/prompt_builder.py:1442-1472`); a grep of the tree for
  `match_skill|embedding|relevance|auto_activate` finds only `tools/skill_usage.py:683`
  `_match_skill_dir`, which matches **file names**. So nothing in the runtime reads a description
  and decides to load. The only reader is the model, and the only caller of `skill_view` is the model.
- **Consequence:** a description is usable as a trigger **only if it names a condition that can be
  false on some turn**. `"Use when you receive any questions or challenges"` is true on every turn —
  a filter that returns `True` everywhere cannot select this turn, so it never produces a call.
  Measured: 91 `SKILL.md` files / **89 distinct names** on disk, **50 never loaded** (median load
  count 0, mean 2.19 over the ~466 `skill_view` events recorded at the time of writing — the total
  only grows, so re-run the appendix rather than quoting it later).
- **Two mechanisms bypass the model's judgement entirely** (see *Fixing it* below):
  `skills.auto_load` (config) and `channel_skill_bindings` (Discord/Slack channel or thread).

## Step 1 — Find the install record (what, from where, when)

```python
import json
d = json.load(open('/Users/maxim/.hermes/skills/.hub/lock.json'))['installed']
print(json.dumps({k: {x: v.get(x) for x in
      ('source','identifier','install_path','installed_at','content_hash')}
      for k, v in d.items() if 'KEYWORD' in k}, indent=1, ensure_ascii=False))
```

Measured for the two `respond-to-*` skills:

```json
{"source": "url", "trust_level": "community", "scan_verdict": "safe",
 "install_path": "secretary/respond-to-questions",
 "installed_at": "2026-09-30T00:35:09.266296+00:00",
 "content_hash": "sha256:712eb90365eb772a",
 "identifier": "https://raw.githubusercontent.com/flmaximwang/AgentSkill-StructuredResponse/main/skills/respond-to-questions/SKILL.md"}
```

Notes that matter later: `source: url` means **no commit pin**, so `update` refetches the floating
`/main/` ref and nothing can be rolled back; and a hand-edit of the installed `SKILL.md` breaks the
recorded `content_hash`. `.hub/audit.log` holds the one-line install/uninstall/blocked history
(UTC timestamps — `2026-09-30T00:35:09Z INSTALL respond-to-questions url:community safe …` is
08:35 CST).

## Step 2 — Was it ever loaded?

`state.db` (`~/.hermes/state.db`) stores every message; a skill load is a `role='tool'` row with
`tool_name='skill_view'` whose JSON `content` carries the skill's `name`.

```python
import sqlite3, json, collections
db = sqlite3.connect("/Users/maxim/.hermes/state.db"); db.row_factory = sqlite3.Row
cnt = collections.Counter()
for r in db.execute("SELECT content FROM messages WHERE tool_name='skill_view'"):
    try: cnt[json.loads(r["content"]).get("name", "?")] += 1
    except Exception: cnt["?"] += 1
print(len(cnt), "distinct skills loaded /", sum(cnt.values()), "load events")
print([kv for kv in cnt.most_common() if "respond-to" in kv[0]])
```

Measured: 466 load events; `respond-to-questions` **1**, `respond-to-requirements` **1** — both
`2026-09-30 14:46:02`, i.e. the turn the user asked the question, and **zero** before it. Beware the
`?` bucket (71 rows): those are loads whose payload was compacted, so it is evidence of a load but
not of *which* skill.

Repeat read-only across every other profile — the answer to "have you ever used X?" is usually
profile-scoped:

```python
import glob, sqlite3
for p in sorted(glob.glob("/Users/maxim/.hermes/profiles/*/state.db")):
    d = sqlite3.connect(f"file:{p}?mode=ro", uri=True)   # read-only URI, never write another profile
    print(p.split('/')[-2], d.execute(
        "SELECT count(*) FROM messages WHERE tool_name='skill_view'").fetchone()[0])
```

Measured totals: investment-advisor 542, protein-design 147, personal-accountant 29,
profile-development 24, travel-guider 23, rdm-assistance 21, obsidian-maintenance 8,
software-development 1, game-research 0, job-hunter 0 — `respond-to-*` **0** in all of them.

## Step 3 — Was the behaviour happening anyway?

A skill can be absent from the load log and still be obeyed, because the same text lived somewhere
else that is *always* in context. Search the assistant turns for the skill's **literal strings**
(headings are the best marker — they survive paraphrase):

```python
rows = db.execute("""SELECT timestamp, session_id FROM messages
 WHERE role='assistant' AND content IS NOT NULL
   AND (content LIKE '%What I ask%' OR content LIKE '%What I want%'
        OR content LIKE '%Keypoints you offer%' OR content LIKE '%Effects of each change%')
 ORDER BY timestamp""")
```

Measured, per day: **09-27: 1, 09-28: 45, 09-29: 84, 09-30: 64**, last one `2026-09-30 13:50:07`.
So the *behaviour* ran for four days while the *skill* was never loaded — the load log alone would
have misled you into "it was never used".

## Step 4 — Where it came from instead (persona vs skill)

The system prompt of every session is stored by hash, so you can prove the source:

```python
# NOTE: the column is `prompt`, NOT `content` —
#   SELECT content FROM system_prompts  →  Error: no such column: content
rows = db.execute("""SELECT s.id, s.started_at FROM sessions s
 JOIN system_prompts p ON p.hash = s.system_prompt_hash
 WHERE p.prompt LIKE '%What I ask%' ORDER BY s.started_at""")
```

Measured: **59 sessions** had the 4-heading format inside their system prompt; the earliest is
`20260927_213040_5adc59` (2026-09-27 21:30) and the block sat between `## Responding to requirements`
and `## How we study` in `SOUL.md` — i.e. the persona carried the same text the two skills now carry.

The trim is a file event, so date it from the file system, not from memory:

```bash
stat -f '%Sm %z %N' ~/.hermes/SOUL.md       # 2026-09-30 14:01, 1048 bytes now
grep -n "unsure about the question\|multiple targets" ~/.hermes/SOUL.md   # empty after the trim
```

Measured: at `14:00:44` the grep still hit lines **29 / 34 / 74**; after the 14:01 edit the sections
are gone. Cross-check with step 3: the last 4-heading turn is 13:50:07, and the four sessions after
the trim (14:02 / 14:11 / 14:31 / 14:42) have none — the behaviour **stopped silently**, with no
error anywhere. That pairing (behaviour timestamp vs file mtime) is the whole diagnosis.

## Step 5 — How crowded the decision is

Pull the `<available_skills>` block out of the session's own system prompt and count what competes:

```python
import re
txt = db.execute("SELECT prompt FROM system_prompts WHERE hash=(SELECT system_prompt_hash FROM sessions WHERE id=?)",
                 (session_id,)).fetchone()[0]
block = re.search(r"<available_skills>(.*?)</available_skills>", txt, re.S).group(1)
print(len(block), "chars,", len(re.findall(r"^\s+- ([^:]+):", block, re.M)), "skills,",
      round(block.find("secretary") / len(block) * 100, 1), "% into the block")
```

Measured: **8,679 chars / 89 named skills**, `secretary` at **90.6 %** depth. Two consequences:
position is a real (if secondary) handicap, and any description that claims universal relevance is
indistinguishable from the ~88 other `Use when …` entries around it.

## Step 6 — The mechanism, with citations

| Question | Answer | Source |
|---|---|---|
| Who renders the skill list? | text only, into the stable prompt tier | `agent/prompt_builder.py:1442-1472` |
| Any description/keyword matcher? | none (only file-name matching) | `tools/skill_usage.py:683` |
| Force a load for every session? | `skills.auto_load: [name, …]` → full skill blocks injected at agent init | `agent/system_prompt.py:317-340`, `agent/skill_commands.py:692-706, 709-734` |
| Force a load per channel/thread? | `channel_skill_bindings: [{id: "<channel id>", skills: [name]}]`, threads inherit the parent id; applies **on new sessions only** | `gateway/platforms/base.py:1824-1851`, `gateway/run_turn.py:2078-2083`, `gateway/config_loader.py:221` (Discord/Slack only) |

Both config keys were **unset** on this machine (`grep -n "auto_load\|auto_skill" ~/.hermes/config.yaml`
→ nothing), which is why a load had to come from the model's own judgement. The gateway path prepends
the skill body to the user's message text (`run_turn.py:599`), so a long session keeps it in history
rather than re-injecting per turn.

## Step 7 — Which descriptions actually get loaded

Feature-score every on-disk description against the load counts (Step 2):

```python
import re
feat = lambda d: {
  "tool_or_system": bool(re.search(r"\b(git|gh|curl|docker|pytest|npm|hermes|obsidian|zotero|discord|snapgene|python|ffmpeg)\b", d, re.I)),
  "file_ext":       bool(re.search(r"\.[a-z]{2,4}\b", d)),
  "always_true":    bool(re.search(r"\bany\b|\bwhenever\b|\balways\b|every task|all tasks", d, re.I)),
  "quoted_or_caps": bool(re.search(r"\"[^\"]+\"|`[^`]+`|[A-Z]{2,}", d)),
}
```

Measured (89 distinct skills — 91 files, `docx` and `xlsx` exist twice — mean loads):

| Feature in the description | present | absent |
|---|---|---|
| names a tool / system | n=26, **mean 5.46** | n=63, mean 0.84 |
| names a file extension | n=8, mean 1.75 | n=81, mean 2.23 |
| `any / whenever / always` | n=5, mean 3.00 | n=84, mean 2.14 |
| quoted or CAPITALISED artifact | n=33, mean 1.45 | n=56, mean 2.62 |

Read it for **direction, not as a causal multiplier**: skills describing frequently recurring tasks
(obsidian 41 loads, hermes-agent 59) inflate the left column, so task frequency is confounded in. The
defensible rule is the one from the premise — *the description must name something that can be
recognised in the current turn*; a tool/system name is the cheapest such anchor, extensions and
quoted nouns are not (the last row even runs the other way).

## Fixing the description

Four rules, each aimed at how the previous failure actually happened:

1. **Replace a condition on *me* with a recognisable object.** `"when you receive any questions or
   challenges"` describes the agent and is true every turn. Name the artifact the skill produces.
2. **Convert "every turn applies" into a once-per-session action.** *"Load once at the FIRST message
   of a session …"* — that condition is evaluable (already loaded ⇒ false), so the entry can finally
   discriminate between this turn and the rest.
3. **Put the literal output strings in the description.** The four headings double as a checklist the
   model can check itself against; an abstract `"structured behavior and summary"` cannot be checked,
   so no deficit is ever felt and nothing is loaded.
4. **Add one counter-sentence against the "already covered" judgement** — the exact failure here was
   *"the format is already in my default behaviour"*. State that the load is required **even if** the
   format looks covered by the persona or another skill.

Working templates (frontmatter `description:`):

```yaml
# respond-to-questions
Load once at the FIRST message of a session whose rounds will end with a summary. It fixes the reply
format for the whole session: end EVERY round with the four headers — 1) What I ask 2) What you did
3) Keypoints you offer 4) Questions to dig in. Load it even if you believe the format is already
covered by the persona or another skill.

# respond-to-requirements
Load once at the FIRST message of a session where the user asks for work to be done. End EVERY round
with — 1) What I want 2) What you did 3) Effects of each change 4) Things left to do. Load it even if
you think your default summaries already match.
```

**Ceiling, stated plainly:** a description change can only raise the probability of being noticed.
It cannot reach 100 %, because the decision stays with the model. The only deterministic routes are
`skills.auto_load` (every session) and `channel_skill_bindings` (one channel/thread) — both remove the
judgement from the loop, and both are config edits in the user's profile.

## Landing a description change

1. Edit the frontmatter in the **source repo** (the raw URL target), not the installed copy.
2. Commit and push — for a `source: url` install with no commit pin, `update` refetches `/main/`, so
   an unpushed edit is invisible.
3. `hermes skills update <name>` (the recorded `content_hash` changes; if you had hand-edited the
   installed copy, it mismatches and the command reports local edits — that is the signal you edited
   the wrong place).
4. The new description enters the prompt only for a **new session** (or after `/reload-skills`); the
   block is built at agent init and cached with the stable prompt tier.

## One-shot appendix

`skill-usage-counts.py` — load counts for every on-disk skill in one read-only run:

```python
#!/usr/bin/env python3
import collections, glob, json, os, re, sqlite3
db = sqlite3.connect(os.path.expanduser("~/.hermes/state.db")); db.row_factory = sqlite3.Row
cnt = collections.Counter()
for r in db.execute("SELECT content FROM messages WHERE tool_name='skill_view'"):
    try: cnt[json.loads(r["content"]).get("name", "?")] += 1
    except Exception: cnt["?"] += 1
names = []
for p in glob.glob(os.path.expanduser("~/.hermes/skills/**/SKILL.md"), recursive=True):
    txt = open(p, encoding="utf-8", errors="replace").read()[:1500]
    m = re.search(r"^name:\s*(.+)$", txt, re.M)
    names.append(m.group(1).strip() if m else os.path.basename(os.path.dirname(p)))
for n in sorted(set(names), key=lambda x: -cnt.get(x, 0)):
    print(f"{cnt.get(n, 0):4d}  {n}")
print(f"-- {len(set(names))} skills, {sum(1 for n in set(names) if not cnt.get(n))} never loaded")
```
