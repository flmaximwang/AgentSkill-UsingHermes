---
name: manage-hermes-bundled-skills
description: Use when Hermes' bundled (built-in) skills are missing, not updating, or seem to seed nothing — also when someone asks where bundled skills come from, whether any config is needed for seeding, or how to stop / restore bundled-skill seeding in a profile. Explains that bundled skills are never downloaded — tools/skills_sync.py copies the code root's skills/ into HERMES_HOME/skills/ — and drives a three-step diagnostic plus the opt-out / opt-in commands.
---

# Manage Hermes Bundled Skills

Bundled (built-in) skills are **not downloaded**. `tools/skills_sync.py::sync_skills()` copies them
from the **current code root's `skills/`** into the **current profile's `HERMES_HOME/skills/`**. So
"can it seed" depends on exactly one thing — whether *that* code root has a `skills/` directory — and
not at all on how many skills already sit in HERMES_HOME.

The trap this skill exists for: when the code root has no `skills/`, `sync_skills()` early-returns on
`if not bundled_dir.exists(): return {...}` and reports `0 new / 0 updated`. That output reads like
"already up to date"; it actually means **there is no source**. A silent `0 new / 0 updated` is never
evidence of success.

## The causal chain

```
code root's skills/  ──►  _get_bundled_dir()  ──►  hash gate (.bundled_manifest)  ──►  <HERMES_HOME>/skills/
```

- **Source** = `_get_bundled_dir()` = `Path(tools/skills_sync.py).parent.parent / "skills"` — the code
  root's `skills/`. Overridable by `HERMES_BUNDLED_SKILLS` (`hermes_constants.py:388-395` `_packaged_dir`:
  env → checkout default → `HERMES_HOME/<subdir>`; `get_bundled_skills_dir` at `:408`).
- **Target** = `<HERMES_HOME>/skills/` — one set per profile, e.g. `~/.hermes/skills/`.
- **Gate** = `.bundled_manifest` lines of `name:md5`. The sync copies and records by hash; a copy you
  edited is **never overwritten** — it prints `user-modified, skipping`.

## Diagnostic — work it in this order

**1. Which interpreter / launch chain am I on?** The code root is decided by the chain, not by the
question. Two chains coexist on a normal machine: a PATH-installed editable install (its `tools` maps
to a per-install `workspace/`) versus the desktop app / gateway launch script
`~/.hermes/hermes-agent/.hermes/bin/hermes`, which inserts the git checkout
`/Users/maxim/.hermes/hermes-agent` onto `sys.path`.

Enumerate the chains before answering — packaged, checkout and launcher copies all coexist:

```bash
which -a hermes
```

Measured here, that prints the launcher first, then the two per-install venv scripts, then a
`~/.local/bin` copy. So "where do the bundled skills come from" is answered **per entry** in that
list, never once for the machine. The launcher wrapper is plain text; read it and note that it
`sys.path.insert(0, '/Users/maxim/.hermes/hermes-agent')` and pops `PYTHONPATH`/`PYTHONHOME` — that
insert is exactly why its `_get_bundled_dir()` lands on the checkout rather than a `workspace/`.

**2. Does that chain's code root have `skills/`?** Run the same `_get_bundled_dir()` call the sync
would make, on the interpreter in question:

```bash
env -u PYTHONPATH <venv>/bin/python3 -c \
  "from tools import skills_sync as s; p = s._get_bundled_dir(); print(p, p.exists())"
```

Two installs exist here, and both print `.../workspace/skills False`:

- `~/.hermes/installs/b200403c2b90970e/environments/52bc5256b3ca4a1bb91a06058efb2f54/workspace/skills False`
- `~/.hermes/installs/b200403c2b90970e/environments/d1c8e05cbd8b40dda7d9552a947e61ad/workspace/skills False`

while the app/gateway chain resolves `~/.hermes/hermes-agent/skills`, which exists and holds **58**
`SKILL.md` files. (PATH CLI code root provenance: the editable-install finder
`__editable___hermes_agent_0_0_0_finder.py:9` maps `tools` to `workspace/tools`.)

**3. Which knob applies?** Two different complaints, two different answers:

| Symptom | Cause | Knob |
|---|---|---|
| A PATH-installed `hermes` seeds nothing, while the app does | its code root has no `skills/` | point the chain at a real source — `HERMES_BUNDLED_SKILLS` (see control reference) |
| You want the app / install to *stop* seeding into a profile | opt-out is a profile decision | `.no-bundled-skills` marker via `hermes skills opt-out` |

`HERMES_BUNDLED_SKILLS` is a relocation hook for packagers (Homebrew / Nix), **not a switch**. To
turn seeding off use the marker.

## Commands

```bash
hermes skills opt-out           # write <HERMES_HOME>/.no-bundled-skills; touches nothing already on disk
hermes skills opt-out --remove  # marker + delete unmodified bundled copies (user-edited and hub/local kept)
hermes skills opt-in            # remove the marker; seeding resumes on the next `hermes update`
hermes skills opt-in --sync     # remove the marker and re-seed now → prints `Re-seeded N bundled skill(s)`
```

`opt-out` default leaves every file in place — the marker alone stops future seeding. Only `--remove`
deletes copies, and only "unmodified" ones. `opt-in` is the write/delete of that same marker; the
file, not the command, is the switch (`tools/skills_sync.py:400`).

## Read next

- `references/manage-hermes-bundled-skills-seeding.md` — the mechanism in full: `_get_bundled_dir()`,
  the `HERMES_BUNDLED_SKILLS` override, the target dir, the `name:md5` hash gate and
  `.bundled_manifest`, `user-modified, skipping`, the early return, the two workspace code roots
  versus the app/gateway launcher, and the measured closing loop (58-line manifest, mtimes, PIDs).
- `references/manage-hermes-bundled-skills-control.md` — turning seeding off and on:
  `.no-bundled-skills` as the switch itself, default `opt-out` versus `--remove`, what
  `opt-in --sync` prints, and how to make a PATH-installed `hermes` seed too.

## Skill Structure

<!-- Generated by Scripts -->

```
manage-hermes-bundled-skills/
├── SKILL.md  (116 lines)
├── references/
│   ├── manage-hermes-bundled-skills-control.md  (117 lines)
│   └── manage-hermes-bundled-skills-seeding.md  (138 lines)
└── scripts/
    └── auto-generate-skill-structure.py  (142 lines)
```

<!-- Generated by Scripts -->

