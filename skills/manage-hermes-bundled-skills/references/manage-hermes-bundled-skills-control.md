# Turning bundled-skill seeding off and on

Seeding is controlled by **one file**, not by a config key:

```
<HERMES_HOME>/.no-bundled-skills
```

The CLI commands are just its writer and deleter. If you reason about "the switch" as the file, every
question resolves cleanly; if you reason about it as a flag, you will look for a config setting that
does not exist.

The source note's three semantics lines, preserved verbatim:

- `hermes skills opt-out`：写 `<HERMES_HOME>/.no-bundled-skills` 标记，让播种停止；默认**不动**盘上任何文件，加
  `--remove` 才额外删掉"未被你改过"的内置副本。
- `hermes skills opt-in`：删掉该标记恢复播种；加 `--sync` 立刻重灌，打印 `Re-seeded N bundled skill(s)`。
- `.no-bundled-skills` **存在** = 只再播种 essential 的 `hermes-agent`；**不存在** = 正常播种（判据在
  `tools/skills_sync.py:400`）。文件是开关本体，两条命令只是它的写/删器。

## The judgement site

```python
# tools/skills_sync.py:72-73
NO_BUNDLED_SKILLS_MARKER = ".no-bundled-skills"

# tools/skills_sync.py:400
essential_only = (_hermes_home() / NO_BUNDLED_SKILLS_MARKER).exists()
```

The marker's existence flips `essential_only`. Note the exact meaning: **it does not mean "seed
nothing"** — it means "seed only essential skills". The essential set is a singleton, the system-prompt
skill that every profile must have:

```python
# agent/skill_utils.py:295
ESSENTIAL_SKILLS: frozenset = frozenset({"hermes-agent"})
```

and `sync_skills()` filters the candidate list to it
(`bundled_skills = [(name, src) for name, src in bundled_skills if name in ESSENTIAL_SKILLS]`). The
same marker name is mirrored in `hermes_cli/profiles.py:92` (`NO_BUNDLED_SKILLS_MARKER`), written when a
profile is created with `--no-skills` and read at `:2443`.

## `opt-out` — default versus `--remove`

Measured `hermes skills opt-out --help` on this machine (2026-09-30):

```
usage: hermes skills opt-out [-h] [--remove] [--yes]

Write the .no-bundled-skills marker so the installer, `hermes update`, and any
direct sync stop seeding bundled skills into the active profile. By default
nothing already on disk is touched. Pass --remove to ALSO delete bundled
skills that are unmodified (user-edited and hub/local skills are never
removed).

options:
  -h, --help  show this help message and exit
  --remove    Also delete already-present unmodified bundled skills
  --yes, -y   Skip confirmation prompt when using --remove
```

So:

- plain `hermes skills opt-out` → writes the marker, **touches nothing on disk**. The skills already
  seeded stay usable; only future seeding stops (and the surviving set is still whatever was there).
- `hermes skills opt-out --remove` → writes the marker **and** deletes bundled copies that are
  "unmodified" (copy still matches its recorded `name:md5` hash). Skills you edited, plus hub-installed
  and manually-copied local skills, are **never** removed. It prompts unless `--yes` is passed.

## `opt-in` — restoring, and the re-seed

Measured `hermes skills opt-in --help` on this machine (2026-09-30):

```
usage: hermes skills opt-in [-h] [--sync]

Remove the .no-bundled-skills marker so bundled skills are seeded again on the
next `hermes update`. Pass --sync to re-seed now.

options:
  -h, --help  show this help message and exit
  --sync      Re-seed bundled skills immediately instead of waiting for update
```

- `hermes skills opt-in` → deletes the marker. Seeding returns on the next `hermes update`.
- `hermes skills opt-in --sync` → deletes the marker and re-seeds immediately, printing
  `Re-seeded {copied} bundled skill(s).` (`hermes_cli/skills_hub.py:1079`). This is the fastest way to
  confirm the chain's code root actually has a source — if it prints `Re-seeded 0 bundled skill(s).`,
  you are back to the early-return problem in the seeding reference, not to a marker problem.

## Making a PATH-installed `hermes` seed too

The `.no-bundled-skills` marker turns seeding off, but it cannot turn seeding *on* when the code root
has no `skills/` to seed from. On this machine the PATH CLI resolves to per-install `workspace/` code
roots that have no `skills/` (see the seeding reference's table). To make such an install seed, point
its source at a code root that does have one, by exporting:

```bash
export HERMES_BUNDLED_SKILLS=~/.hermes/hermes-agent/skills
```

(measured on this machine: neither the shell nor `.env` currently sets it). This is the **only**
situation the env var is for in a diagnostic conversation.

## The explicit warning

> `HERMES_BUNDLED_SKILLS` is a relocation hook for packagers (Homebrew / Nix), **not a switch**. It
> changes *where the source directory lives*; it does not stop or start seeding. To stop seeding set
> the `.no-bundled-skills` marker (`hermes skills opt-out`); to restart it remove the marker
> (`hermes skills opt-in [--sync]`).

Keep the two knobs apart when answering: the marker is a **profile** decision ("stop seeding here"),
the env var is a **packaging / chain** decision ("the source lives over there"). A user asking "how do
I stop bundled skills" wants the marker; a user asking "why does my `hermes` not seed" wants the env
var or a different launch chain.
