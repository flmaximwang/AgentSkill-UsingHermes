---
name: install-hermes-skills
description: Install Hermes skills from GitHub, skills.sh, ClawHub and the official catalogs. Use when installing a skill into Hermes, or when the user hands you a skill source — a github.com / raw.githubusercontent.com link, an `npx skills add` command, an `owner/repo/path` identifier, a bare skill name to look up, or a clawhub `@publisher/slug`. Also covers any `hermes skills` question — inspect, search, tap, `--category`, trust and scan verdicts, why an install was blocked, or how to update/uninstall what is already installed. Routes by source first, then gives the exact tested commands.
---

# Install Hermes Skills

Hermes installs skills from nine sources, and the **identifier's shape is what picks the source** —
not the other way round. So the work is: figure out what you were handed → convert it into the
identifier that shape accepts → `inspect` → install. Guessing a shape is what produces the failures
this skill documents, and their error text misleads the same way every time: an identifier no adapter
claims reports `Could not find '…' in any source.`, which reads as "this skill does not exist" when
the real problem is that no source accepts that shape.

Two facts prevent most of the confusion, so they come first:

1. **`Source:` is not necessarily where the content came from.** `Source: skills.sh` is a GitHub
   fetch wearing a relabelled badge; the truth lives in `metadata.source_url` in the lock.
2. **`Trust:` follows the source, and trust × scan verdict decides whether `--force` is needed** — so
   the same repo can install cleanly through one route and be blocked through another.

## The one rule

`hermes skills inspect <identifier>` is read-only and needs no `--force`. Run it before every install
and read two lines: `Source:` and `Trust:`. That pair predicts the outcome — and when one route is
blocked, it usually shows which other route to take instead.

## Trust × verdict — when an install is blocked

| trust \ 判决 | safe | caution | dangerous |
|---|---|---|---|
| builtin | allow | allow | allow |
| **trusted** | allow | **allow** | block |
| **community** | allow | **block** | block |
| agent-created | allow | allow | ask |

- `TRUSTED_REPOS = {openai/skills, anthropics/skills, huggingface/skills, NVIDIA/skills}`; everything
  else — custom taps included, and anything reached through `skills.sh` — is `community`.
- `--force` overrides a **caution** verdict and an "already installed" conflict. It **cannot**
  override `dangerous` (`--force does not override a dangerous verdict.`).
- The verdict depends on download scope, not just on content: the same skill scans `SAFE` through the
  URL route (3 files) and `CAUTION` through the tap route (which reaches `scripts/*.py` and `*.html`).
- **A block is often structural, not a sign of malice.** Measured `paper2agent`: 23 findings, the
  loudest being images (`oversized_file`: 995 KB jpg vs a 256 KB limit), `too_many_files` (69 > 50)
  and `oversized_skill` (6311 KB > 5120 KB). Adding only `--yes` wastes a round trip — `community` +
  `caution` is exactly the case `--force` is for.

## Route by what you were handed

| You were handed | Read |
|---|---|
| `github.com/…` or `raw.githubusercontent.com/…` (repo / `tree` / `blob` / raw link) | `references/install-hermes-skills-from-github.md` |
| `npx skills add <repo> --skill <name>` (a skills.sh page or README command) | `references/install-hermes-skills-from-npx.md` |
| `owner/repo/path`, or `skills.sh/<owner>/<repo>/<skill>` | `references/install-hermes-skills-from-skill-sh.md` |
| a bare name / keyword, "the official X", a bundled or optional skill | `references/install-hermes-skills-from-names.md` |
| `@publisher/slug` (clawhub.ai) | `references/install-hermes-skills-from-clawhub.md` |
| a lone `SKILL.md` with no repo behind it | the raw-URL route in the github reference |

Read the one file the shape points at — each is a complete, tested protocol for that source. When you
cannot tell what you have, work from the shape: the source router resolves in this order
(`tools/skills_hub_search.py:99-114`)

```
official → hermes-index → skills.sh → well-known → url → github(tap) → clawhub → lobehub → browse-sh
```

and two shapes are accepted by **nothing** (`install` and `inspect` then report it two *different*
ways — see the github reference's "Known misjudgments"):

- a **two-segment** `owner/repo` → use `owner/repo/` (trailing slash) or a raw URL instead;
- a `blob` link, or a three-segment identifier ending in `/SKILL.md`.

## The commands

```bash
# install — the identifier shape carries the source; there is no --source flag
hermes skills install "<owner>/<repo>/<path>" --category <cat> -y
hermes skills install "<raw URL to SKILL.md>" --name <name> -y
hermes skills inspect <identifier>          # read-only preview: do this first

# verify
hermes skills list                          # Name | Category | Source | Trust | enabled
hermes skills list --source local|builtin|hub
hermes skills list --enabled-only -p <profile>

# maintain (hub-installed skills only)
hermes skills check <name>                  # up_to_date / update_available / unavailable / orphaned
hermes skills update <name> [--force]       # local edits are skipped unless --force
hermes skills audit [--deep] <name>         # re-scan
hermes skills uninstall <name> -y           # removes the whole installed tree
hermes skills snapshot export <file>        # back up / restore the installed set
```

Measured `hermes skills install --help` on this machine (2026-09-30):

```
usage: hermes skills install [-h] [--category CATEGORY] [--name NAME]
                             [--force] [--yes]
                             identifier
```

Two consequences worth stating plainly: **`--category` is the only lever on where files land**
(`skills/<cat>/<name>/`, layered values allowed), and **you cannot pin a source at install time** —
`do_install(source_id=…)` is used only inside `do_update`.

## Scope and when changes take effect

- **Per profile**: `hermes -p <profile> skills install …` writes into
  `~/.hermes/profiles/<profile>/skills/`. Profiles do not share skill directories — install again in
  the other profile, or copy across.
- **In session**: `/skills install <identifier-or-url> [--name] [--category] [--force] [--now]`.
  The default is "effective next session"; `--now` applies immediately but **invalidates the prompt
  cache**. `/reload-skills` rescans the skills directory.
- **Project-local skills** (a repo's `./.hermes/skills`, `./.agents/skills`) load only after
  `hermes skills trust`.

## Not in the hub? know the trade

A manual `cp -R` into `<HERMES_HOME>/skills/` is still discovered (discovery is directory-based,
nothing to register) but has **no lock entry**: `check`, `update`, `audit` and `uninstall` cannot see
it, and there is no version record. In exchange it is the only install `update` will never overwrite —
the right route for a skill you intend to keep editing, the wrong one for anything you want
maintained. Measured contrast:

```
$ hermes skills check
No hub-installed skills to check.
$ hermes skills uninstall obsidian -y
Error: 'obsidian' is not a hub-installed skill (may be a builtin)
```

## State files

| path (relative to `HERMES_HOME`, default `~/.hermes`) | contents |
|---|---|
| `skills/` | the skills themselves, **one set per profile** |
| `skills/.hub/lock.json` | install ledger: `source / identifier / trust_level / scan_verdict / content_hash / install_path / files / metadata / scan_provenance` |
| `skills/.hub/taps.json` | custom GitHub taps |
| `skills/.hub/quarantine/` | pre-scan holding area (emptied on install) |
| `skills/.hub/scan-cache/` | scan results, keyed by bundle hash |
| `skills/.hub/audit.log` | one line per install: `2026-09-29T15:09:19Z INSTALL skill-creator url:community safe sha256:47dbdef2599c902a` |
| `skills/.usage.json` | usage counts (curator) |

Reading the ledger is the fastest way to answer "where did this come from, and why is it stuck".
`check` vs `update` in two lines: `check` compares **installed content against upstream** by hash (a
matching `source_revision` short-circuits to `up_to_date` with no download at all), while `update`
separately judges **your local edits** by comparing the on-disk hash with the hash recorded at install
time — so a locally edited skill is skipped unless you pass `--force`. The revision is not the
deciding field; the content hash is.

## Skill Structure

<!-- Generated by Scripts -->

```
install-hermes-skills/
├── SKILL.md  (168 lines)
├── references/
│   ├── install-hermes-skills-from-clawhub.md  (72 lines)
│   ├── install-hermes-skills-from-github.md  (363 lines)
│   ├── install-hermes-skills-from-names.md  (132 lines)
│   ├── install-hermes-skills-from-npx.md  (66 lines)
│   └── install-hermes-skills-from-skill-sh.md  (193 lines)
└── scripts/
    └── auto-generate-skill-structure.py  (142 lines)
```

<!-- Generated by Scripts -->
