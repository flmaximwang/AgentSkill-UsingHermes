---
name: maintain-hermes-skill-cards
description: "Use when a hub-installed skill shows 2 cards or Hub. Also for a card with a grey, ON, unclickable switch over a skill that is not installed, and for `Orphaned:` rows from `hermes skills check`. Fixed by editing data (`skills/.hub/lock.json`), never Hermes source."
---

# Skill-card maintenance (Skills & Tools page)

## When to Use

Any of these in the desktop's Skills & Tools page:

- an installed skill shows **two cards** (a registry card plus an extra "Hub" card)
- an installed skill's source label reads **"Hub"** instead of `ClawHub`/`skills.sh`
- a card shows a **grey, ON, unclickable switch** for a skill that isn't installed
- `hermes skills check` lists entries under **`Orphaned:`**

Fix by editing **data** (`skills/.hub/lock.json`) — never Hermes source.

| Symptom in UI | Cause |
|---|---|
| Installed skill shows **twice**: registry card + extra "Hub" card | lock key (→ payload `name`) ≠ the skill's `SKILL.md` name, so the frontend can't link them |
| Installed skill shows source **"Hub"** instead of `ClawHub` | the local row never merged; after merging, the card takes the registry row's fields |
| Card with a **grey, ON, unclickable switch** for a skill you don't have | lock entry whose directory is gone (orphan), or identifier present in `installedIdentifiers` |

## Data model (verified, not guessed)

- Lock per profile: `~/.hermes/skills/.hub/lock.json` (default),
  `~/.hermes/profiles/<name>/skills/.hub/lock.json` (others).
- `hermes_cli/web_server_profiles.py:461` `_installed_hub_identifiers()` returns
  `{entry["identifier"]: {name, trust_level, scan_verdict}}` — key is the
  **identifier field**, `name` is the **lock key**.
- `apps/desktop/src/app/capabilities/catalog/skill-catalog.tsx`: `:204`
  `isInstalled` first clause is `skillsByName.has(entry.name)` (case-sensitive);
  `:174` `matchInstalled` = `installedByIdentifier.get(entry.installIdentifier)`;
  `installedByIdentifier` is only filled when `installedByName.get(record.name)`
  resolves AND that skill's provenance is `hub`. `catalog-browser.tsx:76`
  `mergeInstalled` keeps the FIRST feed row per installed id.
- Identifier rule `apps/shared/src/catalog-install.ts:9`: row's `installIdentifier`
  wins; else prefix `clawhub/` when `source.toLowerCase() == 'clawhub'`; else
  `official/<name>` for `optional`.
- `tools/skills_tool.py:210` dedupes loaded skills by name — two same-named skills
  can never both load.

**Invariant (all three, one string each):**

```
lock key  ==  install_path last segment  ==  SKILL.md frontmatter `name:`
lock entry `identifier`  ==  the catalog row's computed installIdentifier
```

## Procedure

```bash
# ALWAYS pass HERMES_HOME: a desktop/gateway shell often points it at another profile
PROFILE=/Users/maxim/.hermes            # or .../profiles/<name>
<skill-dir>/scripts/align_skill_card.py "$PROFILE" <skill-name>            # dry run
<skill-dir>/scripts/align_skill_card.py "$PROFILE" <skill-name> --apply    # backup + fix
HERMES_HOME="$PROFILE" hermes skills check <skill-name>                    # expect up_to_date
```

The script backs the lock up, renames the skill directory when needed, and sets
key/`install_path`/`identifier`. Manual fallback: set the lock key to the
`SKILL.md` name, `install_path` to match the key, `identifier` to
`clawhub/<catalog row identifier>`.

The read-only counterpart of the fixer is `scripts/check-lock-alignment.py [skill ...]` — run it from the
hermes source tree with the install's venv python and `HERMES_HOME=<home>` (docstring has the exact line).
It audits **every** lock entry for the same three-string agreement and lists the entries that would fold
wrongly or report `invalid_install`, so reach for it when the question is "which installed skills are
affected" rather than "fix this one card". It writes nothing.

### Clear orphaned entries

```bash
HERMES_HOME="$PROFILE" hermes skills check              # names under "Orphaned:"
HERMES_HOME="$PROFILE" hermes skills uninstall <name>   # removes the stale entry
```

## Verification (all must hold)

```bash
HERMES_HOME="$PROFILE" hermes skills check <name>       # up_to_date, NOT invalid_install
```

```bash
# payload record name must equal a real skill name; empty output = every card links
HERMES_HOME="$PROFILE" <hermes-venv-python> -c "
from tools.skills_tool import _find_all_skills
from hermes_cli.web_server_profiles import _installed_hub_identifiers
n={s['name'] for s in _find_all_skills(skip_disabled=True)}
print({k:v['name'] for k,v in _installed_hub_identifiers(None).items() if v['name'] not in n})"
```

Then have the user switch away from the Skills page and back (the
`/api/skills/hub/sources` query has `staleTime: 60_000`).

## Pitfalls (each cost a round trip)

- **`install_path`'s last segment must equal the lock key**
  (`tools/skills_hub_models.py:248`) — otherwise `hermes skills check` returns
  `invalid_install` and updates silently stop. Renaming the key alone is not
  enough: rename the directory too and sync `install_path`.
- **Two cards can be legitimate**: two registries (e.g. `skillopt` on ClawHub plus
  a same-named `skills.sh` project) each contribute a catalog row. Read the source
  labels first; only the local-row duplicate is a bug.
- **A card can read `book2skill/local-local`, not the install name** — measured on
  `cangjie-skill` (ClawHub `@terrybenedict0515/cangjie-skill`, 21 files, `safe`): the
  installed `SKILL.md` carries `name: book2skill`, so `hermes skills list` renders it as
  `book2skill/local-local` (the SKILL.md name, not the install name), and the
  `ClawHub`→`hub` label collapse applies exactly as a name-key miss would predict. The
  same install was also **missing its 6 `templates/` files**, which is the payload-side
  symptom of the same class. Do not "fix" this by editing the skill's `SKILL.md` name
  (an update overwrites it) — align the lock key to the SKILL.md name only when the
  three-string invariant actually disagrees. Related dead end, reported rather than
  forced: the upstream GitHub `kangarooking/cangjie-skill` has **no usable install route**
  — the whole repo as a bundle is `dangerous` (permanently blocked; the `critical` finding
  sits in `tests/`) and the raw-URL route ships only a 4-file empty shell. So a missing
  `templates/` here is a publisher-entry gap, not a wrong card alignment.
- **Look catalog rows up case-insensitively** — the registry row is often
  `SkillOpt` while the local skill is `skillopt`, and the UI compares names
  case-sensitively. Snapshot: `https://nousresearch.github.io/hermes-agent/docs/api/skills.json`
  (~63 MB, 101k rows; the `hermes-agent.nousresearch.com` docs URL 302s to the same bytes).
- **`hermes skills update` can revert the alignment**: the installer names the
  install directory from the registry slug, so an updated skill may return as
  `<slug>/` with the old lock key. Re-run the script after updates.
- **Don't edit the skill's own `SKILL.md` name to match the lock** — an update
  overwrites `SKILL.md`; align the lock instead.
- Back up the lock before every edit and quote the restore command in the reply.

## Skill Structure

<!-- Generated by Scripts -->

```
maintain-hermes-skill-cards/
├── SKILL.md  (142 lines)
└── scripts/
    ├── align_skill_card.py  (133 lines)
    └── check-lock-alignment.py  (120 lines)
```

<!-- Generated by Scripts -->
