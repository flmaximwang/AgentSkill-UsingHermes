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

**A clean `inspect` is not proof the identifier installs** — an index entry (hermes-index, skills.sh)
resolves to metadata without its files, so the failure only surfaces at `install` (measured:
`alchaincyf/nuwa-skill/huashu-nuwa`; error table row 5 in the github reference).

## Non-negotiables (user rules)

- **🔴 No identifier in the request = ask, then stop. Never mine archaeology for a target.** "装 1 个 skill" /
  "install this skill" with no name, URL or path names a *count*, not a target, and which skill is meant
  exists only in the user's head. A 0-hit `search`, the session history, the repo's `git log` and the vault
  all answer "which skills exist", never "which one you want" — so running them buys nothing and a hit in
  any of them is a coincidence. Ask for one of **name / URL / local directory**; if that question is
  declined, or the answer comes back as a generic "continue", restate the gap in one line and stop. **Never
  promote a candidate found by archaeology to an install**, and if you did install on an inferred target,
  name the identifier you installed and say it was your assumption — do not present it as the requested
  one. The built-in "empty results → retry with a broader query" rule governs **retrievable facts**; a
  missing *selector* is not retrievable, so more searching cannot close it. Measured cost of getting this
  wrong: 5 archaeology calls, all 0-hit, ending in one installed skill the user never asked for.
- **Prove the install in a throwaway home before touching the real one.**
  `export HERMES_HOME=/Users/maxim/.hermes/cache/scratch/hh-<topic>` and install there; only
  reproduce it in `~/.hermes` once the route is known-good AND the user asked for it.
- **`HERMES_HOME` persists between shell calls and silently redirects the install.** A leftover
  export from an earlier test sends a "real" install into the sandbox (or the reverse). Print
  `echo "${HERMES_HOME:-<unset>}"` in the same command as the install, and `unset HERMES_HOME`
  when the target is the default profile.
- **A bare `HERMES_HOME` sandbox is not network-equivalent to the real home: copy `.env` *and*
  `config.yaml` into it before probing, or every fetch-based route fails with a message that blames
  the skill.** Measured: in an empty sandbox the raw-URL route answered `Error: Could not download
  '<url>'` and the clawhub identifier answered `'<id>' is listed in the clawhub index, but its files
  no longer exist upstream.` — while the *same* identifiers installed fine minutes later in a sandbox
  carrying the real home's `.env` **and** `config.yaml`, and again in the real home. `.env` alone was
  not enough. So a "dead" route in a fresh sandbox proves nothing until a mirrored home reproduces it;
  report the mirror, not the first sandbox.
- **An external installer may resolve its target from `HERMES_HOME`, not `HOME` — point both at the
  sandbox.** `npx skills` sets `hermesHome = process.env.HERMES_HOME || ~/.hermes` and copies into
  `<hermesHome>/skills`, so a probe with only `HOME` redirected leaves the **real** profile populated
  while the installer's own store/lock land in the scratch dir — a directory no side can update. Set
  `HOME` **and** `HERMES_HOME`, then confirm with `ls -ld <real-home>/skills/<name>`; undo a stray copy
  with `rm -rf` (no lock entry exists to uninstall). Route detail: `references/install-hermes-skills-from-npx.md` (part 2).
- **Reset a sandbox by picking a new name, not by deleting it.** `rm -rf "$HERMES_HOME"` is refused
  by the harness (a recursive delete of a variable path cannot be proven safe); `hh-<topic>2` costs
  nothing and keeps both runs comparable.
- **A sandbox name is single-use — an existing one silently turns the probe into a no-op.** Measured
  2026-09-30: a `hh-nuwa2` left over from a run 6 h earlier made the raw-URL probe answer `Warning:
  'huashu-nuwa' is already installed at nuwa/huashu-nuwa` and never execute, while the run read as if
  the route had been tried. Test the name first (`[ -e "$SB" ] && echo REUSED`), or pick a fresh
  ordinal, and look for the `already installed` line before crediting any sandbox result.
- **🔴 CHECKPOINT — `inspect` before `install`, always.** It is read-only and prints `Source:` / `Trust:`.
  Report both to the user before installing anything from a `community` source, and say what the scan
  flagged; a `--force` past a caution verdict is the user's call, not yours.
- **Two packages for the same display name = ask, do not overwrite.** A registry package is
  often a third-party fork of a different lineage than the upstream repo. Compare `SKILL.md`
  frontmatter (`name:`, version, author) and the file inventory, then let the user choose which
  one to keep — the ranking rule above says which one to *recommend*.
- **Report by route + verified numbers** (files installed, size, verdict, target home) — never
  "installed successfully". An install that succeeded into the wrong home is a failure.
- **The chat reply is ≤3 sentences by default — not an escalation after the user complains.** Lead with
  the answer to the question that was asked, then the commands you actually ran (name them: an install
  done by clone + `cp -R`, or by `npx skills`, must not be reported as an install command), then what it
  cost (files, size, verdict, target home, and anything the route dropped). The evidence chain (probe
  outputs, per-route verdicts, file inventories) belongs in the note, the commit or the lock, never in
  the message — a wall of sections is unreadable and the user will say so. Expand only when asked, then
  one question per turn, ≤3 sentences each.
- **A correction to this skill, or to any skill in this pack, is written in the pack clone — never in the
  installed copy.** Source of truth is `~/Repositories/AgentSkill-UsingHermes`; deliver with
  `scripts/auto-generate-skill-structure.py <name>` → `scripts/verify-skill-package.py skills/<name>` →
  `git add skills/<name>` → commit → push `main` → `hermes skills update <name>` (`--force` when the
  installed copy carries local edits). A `skill_manage`/editor patch under `$HERMES_HOME/skills/` looks
  applied, is invisible to the repo, and dies at the next update, which replaces the directory wholesale.
- **A bare name has several bloodlines: rank them before installing, then prove the winner installs.**
  The candidate the resolver picks is not necessarily the one worth having, and the best-maintained
  one may not be installable at all. Read both axes per source — skills.sh page `Installs` /
  `First Seen`, `gh api repos/<owner>/<repo> --jq '{stars,pushed_at,archived}'`, ClawHub
  `GET https://clawhub.ai/api/v1/skills/<slug>` → `.skill.stats.installs/.downloads/.stars/.versions`
  and `.skill.updatedAt` (signals per source: `references/install-hermes-skills-registry-routes.md` § Popularity and
  recency signals). Measured trap: the popular, actively-pushed upstream won both axes and could not
  be installed at all, while a stale one-version registry fork with 15 installs installed `safe` — so
  report the ranking **and** the installability of the winner, and never present a winner you have not
  tried.
- **Give one recommended route, never a menu of fallbacks.** When the supported route is blocked,
  the answer is the lever that makes *that* route work — a `.skillignore` in the skill directory for
  a scan block, a narrow in-repo directory layout, or an identifier rebuilt from the repo tree — not
  clone-and-copy plus a hand-rolled sync script. A hand-copied directory has no lock entry, so
  `check` / `update` / `uninstall` never see it again: state that cost instead of shipping the copy
  as the answer. When the fix belongs in the repo (layout change, ignore file), say so and ask
  whether to open it upstream rather than silently substituting a workaround.

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
| a GitHub repo or a tap — direct path vs tap vs bare URL, identifier grammar, what "keep it current" costs | `references/install-hermes-skills-github-sources.md` |
| a repo whose **structure** (not the link) decides the identifier: single-skill, root skill + `examples/`, monorepo, a registry id whose third segment is the skill's *name* | `references/install-hermes-skills-repo-structure-routing.md` |
| the full route list (A–F), the per-route maintenance matrix, the lock schema, what `skill_view` exposes, clearing a scan block with `.skillignore` | `references/install-hermes-skills-registry-routes.md` |
| a third-party skill/plugin pack (Codex `.codex-plugin`, Claude `.claude-plugin`, an Agent Plugins v1 package) | `references/install-hermes-skills-external-pack-adoption.md` |
| a package of your own that has to pass `skills_guard` — which documented commands trip it, how to predict the verdict before pushing, why `.skillignore` cannot clear a block on this route | `references/install-hermes-skills-scan-gate.md` |
| renaming a skill or the whole pack — the cascade, the substitution table, the verbatim-evidence exemptions, and re-installing wherever the old name is already known | `references/install-hermes-skills-renaming-a-skill-pack.md` |
| an error string to decode (`Could not download`, `Could not find … in any source`, `Invalid skill name: .`, `is not a hub-installed skill`, `is listed in the hermes-index index, but its files no longer exist upstream`), an install that shipped three files its body references, "how was this installed / why did it need `--force`", or you need to read/import a `tools/skills_hub_*.py` module (run it under `~/.hermes/hermes-agent/venv/bin/python` — the ambient and the vendored interpreters have no `httpx`) | `references/install-hermes-skills-diagnosis.md` + `scripts/lock-provenance.py` |

Read the one file the shape points at — each is a complete, tested protocol for that source. Where a
reference presents its routes as a **ladder** (the github one does), walk it from the top and step down
a rung **only** when the current one is impossible — each rung states its own drop signal, and the
lower rungs lose files or lose maintenance. When you cannot tell what you have, work from the shape:
the source router resolves in this order
(`tools/skills_hub_search.py:99-114`)

```
official → hermes-index → skills.sh → well-known → url → github(tap) → clawhub → lobehub → browse-sh
```

**Classify the repo before quoting an identifier form**: the same `github.com/<owner>/<repo>` link
needs a different identifier in each of the four tree types, and one of them has no usable identifier
at all (`references/install-hermes-skills-repo-structure-routing.md`).

and two shapes are accepted by **nothing** (`install` and `inspect` then report it two *different*
ways — see the github reference's "Error text → meaning" table):

- a **two-segment** `owner/repo` → use `owner/repo/` (trailing slash) or a raw URL instead;
- a `blob` link, or a three-segment identifier ending in `/SKILL.md`.

## Replacing an installed skill with a better bloodline

`hermes skills update` cannot do this: it re-fetches the **recorded** source + identifier, so it only
moves a skill forward inside its own bloodline. Replacing one is an install operation (mechanics in
`update-hermes-skills` → "A source change is uninstall + install"):

1. **Rank** the candidates on popularity × recency (`references/install-hermes-skills-from-names.md`) —
   a plain `search <name>` can list only the weaker registry copies and never the upstream repo.
2. **Prove the winner installs** in a throwaway `HERMES_HOME` (non-negotiables above); a winner you have
   not tried is not a recommendation.
3. `hermes skills uninstall <lock key> -y` — the **lock key**, which for ClawHub is the slug, not the
   name `hermes skills list` prints.
4. `hermes skills install "<winner identifier>" --category <same category> -y`. **Re-supply the
   category**: it is read at install time only, and the removed entry cannot hand its path over.

Then verify the new entry — `hermes skills list` (category + `Source`), the lock's `identifier` /
`install_path` / `content_hash`, and `check <new key>` → `up_to_date` — and name the identifier you
installed, because a same-name fork would make a failed move look like a successful one.

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
├── SKILL.md  (295 lines)
├── test-prompts.json  (12 lines)
├── references/
│   ├── install-hermes-skills-diagnosis.md  (219 lines)
│   ├── install-hermes-skills-external-pack-adoption.md  (105 lines)
│   ├── install-hermes-skills-from-clawhub.md  (87 lines)
│   ├── install-hermes-skills-from-github.md  (527 lines)
│   ├── install-hermes-skills-from-names.md  (202 lines)
│   ├── install-hermes-skills-from-npx.md  (166 lines)
│   ├── install-hermes-skills-from-skill-sh.md  (193 lines)
│   ├── install-hermes-skills-github-sources.md  (130 lines)
│   ├── install-hermes-skills-registry-routes.md  (451 lines)
│   ├── install-hermes-skills-renaming-a-skill-pack.md  (119 lines)
│   ├── install-hermes-skills-repo-structure-routing.md  (76 lines)
│   └── install-hermes-skills-scan-gate.md  (91 lines)
└── scripts/
    └── lock-provenance.py  (83 lines)
```

<!-- Generated by Scripts -->
