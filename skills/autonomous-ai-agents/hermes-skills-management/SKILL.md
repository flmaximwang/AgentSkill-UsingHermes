---
name: hermes-skills-management
description: Install, place, and troubleshoot Hermes skills.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, skills, install, category, troubleshooting]
    related_skills: [hermes-agent, hermes-source-hotfix, hermes-mcp-server-integration]
---

# Hermes Skills Management Skill

Installing, placing, moving and repairing skills in a Hermes profile: what the
installer accepts, why it refuses, and what a working skill directory looks
like. Covers `hermes skills install|list|uninstall` and the desktop-app install
action; does NOT cover authoring skill content (that is `hermes-agent`) or
wiring an MCP server into a profile (that is `hermes-mcp-server-integration`).

## When to Use

- "I can't install <skill>" / an install ends with `Installation blocked:`
- "I can't install <skill>" but nothing ever errors — the skill is probably
  already installed and you are judging by a UI row (step 3, pitfalls #7-#8)
- "Which skill in the hub does X? Install one" — vet the candidates first; do not
  install the first plausible search hit (step 3.7)
- Choosing a category, moving a skill, or a skill not showing up where expected
- After creating a hybrid `category/SKILL.md` layout and wondering what it breaks

## Prerequisites

`hermes` on PATH. Run the CLI as `env -u PYTHONPATH hermes ...` — a Hermes
session exports `PYTHONPATH` pointing at its own tree, which poisons an
external interpreter or install venv.

## Layout rules

- Skills live at `<skills>/<category>/<skill>/SKILL.md`, or at
  `<skills>/<skill>/SKILL.md` (flat). `<skills>` is `$HERMES_HOME/skills`, i.e.
  the PROFILE's dir when a profile is active — check `echo $HERMES_HOME` before
  installing, and pass `-p <profile>` if the target is not the active one.
- A **category bucket** is a directory whose children are skills. A directory
  that itself contains `SKILL.md` is a **skill**, and the installer will never
  nest into it (see Pitfalls #1).
- A directory can be BOTH (category bucket + umbrella/index `SKILL.md` listed
  as a top-level skill). The installer treats that as skill-only;
  `hermes skills list` is the tell — such a directory's skill shows a BLANK
  Category cell, while real buckets show their bucket name.
- Hub-installed skills are tracked in `<skills>/.hub/lock.json`
  (`identifier`, `install_path`, `content_hash`). `uninstall` refuses anything
  not in that file, so bundled/local skills are never deleted by it.

## Procedure

### 1. Install

```bash
env -u PYTHONPATH hermes skills install official/<category>/<skill> --yes [--category <bucket>]
```

- For `official/...` identifiers the category is DERIVED from the identifier
  (`hermes_cli/skills_hub.py::do_install`, the `bundle.source == "official"`
  branch) unless `--category` is passed. There is no flat install for official
  sources: passing an empty `--category` falls back to the derived value, so a
  blocked derived category must be redirected to another bucket.
- `--yes` is required for non-interactive/desktop-driven installs; `--force`
  reinstalls and is the ONLY way past a caution-class block. It cannot clear a
  `DANGEROUS` verdict — that tier is hard-blocked and the installer says so
  (`--force does not override a dangerous verdict`). Verdict tiers and what each
  one leaves you able to do: `references/candidate-vetting.md`.

### 2. Verify (all three, not just the exit code)

```bash
env -u PYTHONPATH hermes skills list | grep -i <skill>     # name | category | source | status
env -u PYTHONPATH hermes skills check | grep -i <skill>    # hub skills: up_to_date == installed
ls <skills>/<category>/<skill>/                            # files actually landed
```
Then load it with `skill_view(<skill>)` and confirm `readiness_status`.

### 3. Diagnose a refused OR a silent install

1. Read the action log — every UI/CLI install writes one:
   `read_file ~/.hermes/logs/action-skills-install-*.log` (newest match; repeat
   attempts append to the same file). It names the refusal verbatim. The
   desktop writes these into the DEFAULT home's `logs/` even when the install
   targets a named profile, so a profile's own `logs/` can be empty for it.
2. Get the exact path chain from source, don't paraphrase it:
   `tools/skills_hub_install.py::_check_install_target` (the refusal) and
   `hermes_cli/skills_hub.py::do_install` (where category comes from).
3. Probe the real guard function read-only instead of trial-installing:
   `scripts/probe_install_target.py <skill> <category> [...]` — prints
   OK/BLOCKED per category for the active profile and the default profile.
4. Redirect and retry: `--category <a bucket that has no SKILL.md>`. List the
   clean buckets with
   `for d in <skills>/*/; do [ -f "$d/SKILL.md" ] || echo "CLEAN: $d"; done`.
5. **A log ending at `Warning: '<name>' is already installed ... Use --force to
   reinstall.` is not a failure, and it leaves no other trace.** `do_install`
   looks the name up in the lock BEFORE quarantine/scan and returns there with
   exit 0, so nothing is fetched, scanned or written and no error reaches the
   caller. Confirm with the lock dump in
   `references/install-identifier-namespaces.md`, then decide: already installed
   (verify per step 2 and say so) or genuinely wanted a reinstall (`--force`).
6. **The identifier a caller installs with is usually NOT the identifier the
   lock records.** Recover what was actually asked for from the action-log
   FILENAME (`_hub_action_name` = `skills-install-<slug>-<sha1(identifier)[:8]>`),
   then compare with the resolved bundle identifier (`hermes skills inspect
   <identifier>`) and the lock's `identifier`. The four forms one skill wears,
   plus the recipes: `references/install-identifier-namespaces.md`.
7. **A row that lists is not a skill that installs.** The catalog feed and the
   hub search render metadata the fetch never needed, so a candidate can be
   visible, inspectable, and still unfetchable — `ClawHubSource.fetch` returns
   `None` when the platform API refuses the slug (`GET
   https://clawhub.ai/api/v1/skills/<slug>` → 409 Conflict, e.g. any slug four
   skills share a prefix with). The tell in `hermes skills inspect` is a metadata
   panel with NO `SKILL.md` preview. Probe the fetch before promising an install:
   `references/candidate-vetting.md`.

### 4. Move a skill

`hermes skills uninstall <name> --yes` then reinstall with the wanted
`--category`. Same command block as step 1; re-verify with step 2.

### 5. Clean a hybrid bucket (repair the layout, not the symptom)

A bucket holding its own `SKILL.md` blocks EVERY future install into it. Instead
of redirecting each install with `--category`, nest the umbrella: it stays
loadable and the bucket becomes a real category. Verified against the loader,
not assumed:

- `tools/skills_tool.py::_get_category_from_path` labels a skill with a category
  ONLY when its path under `<skills>` has >= 3 parts — that is why a root-level
  `SKILL.md` shows up as an uncategorized top-level skill.
- `_collect_skill_candidates` matches a bare name by directory name OR
  frontmatter `name:` anywhere under the root, so `skill_view('<umbrella>')`
  keeps resolving at `<skills>/<H>/<H>/SKILL.md` (no need to call it by path).
- `_skill_linked_files` reads `references|templates|assets|scripts` relative to
  the skill dir, so those move WITH the `SKILL.md` or its links go dead.

```bash
S="$HERMES_HOME/skills"          # echo $HERMES_HOME first: profile vs default
cd "$S" && tar czf "$HERMES_HOME/cache/scratch/hybrid_backup_$(date +%Y%m%d-%H%M%S).tgz" <H> [<H2> ...]
python3 <skill_dir>/scripts/clean_hybrid_dirs.py            # dry run: hybrids + planned moves
python3 <skill_dir>/scripts/clean_hybrid_dirs.py --apply    # move SKILL.md + support dirs into <H>/<H>/
```

Only the umbrella's own files move. Bucket-owned files stay put: a category
`README.md`, a nested `skills/` subcategory, `.DS_Store`.

Then prove it: the bulk-move checks under Verification, plus round-trip the
originally blocked install — `uninstall <parked> --yes` and reinstall it with NO
`--category`, which must land in the now-clean bucket.

The same tree is usually mirrored to a git distribution repo; apply the nesting
there too, or the next `sync.py pull` re-creates the hybrid. See
`references/profile-distribution-sync.md`.

## Pitfalls

1. **Never install into a category directory that has its own `SKILL.md`.**
   `_check_install_target` walks every ancestor of the target up to the skills
   root and raises `Refusing to install into '<dir>': it is an existing skill
   directory, not a category` when one holds `SKILL.md` — because a later
   update/uninstall of the outer skill would `rmtree` the nested one. Pick a
   different bucket, or clean the bucket itself (step 5); never hand-copy files
   into the blocked path.
2. **A hybrid directory blocks a whole CATALOG category, not one skill.** Any
   future skill whose catalog category equals the hybrid's name hits the same
   wall, so the workaround has to be repeated; record the hybrid dirs you keep
   (blank Category cell in `hermes skills list`) and pre-empt with `--category`
   — or clean the bucket once (step 5) and never need `--category` for it again.
3. **Don't verify by the installer's own success line.** It prints
   `Installed: <category>/<name>` before the lock entry and the file move are
   the whole story — confirm `install_path` in `.hub/lock.json` and a
   `skill_view` load.
4. **`--name` does not choose a directory for official sources**; the category
   still decides the parent. Use it only to rename.
5. **Bundled, hub-installed, pinned and user-owned skills are off-limits to
   the curator** — a skill that is wrong but bundled/hub-installed gets its fix
   in the source tree, not by editing it in place.
6. **`hermes skills uninstall <name>` silently cancels when stdin is not a
   TTY** (it prints `Confirm [y/N]: Cancelled.` and exits 0). A move done as
   uninstall+reinstall then looks like "the install refused, nothing changed",
   with the skill still in the old bucket. Pass `--yes`.
7. **Re-installing an already-installed skill is a success-shaped no-op.**
   Without `--force`, `do_install` prints a warning and returns before the scan,
   exiting 0 — so any caller that reads exit status (the desktop Catalog
   button) sees success, changes nothing, and the user clicks again. "Install
   did nothing" is diagnosed from `.hub/lock.json`, never from the absence of an
   error.
8. **Installed-ness is keyed on the lock's `identifier`, not on the skill name
   or the string the caller passed.** The catalog feed, hub search, CLI
   resolution and the lock each use a different form (see
   `references/install-identifier-namespaces.md`), so a UI row can keep
   offering "Install" for a skill that is installed and enabled. Trust
   `hermes skills list` / `skills check` / the lock, report the stale marker as
   the defect it is, and do not re-install blindly to "fix" it.
9. **A hub skill's factual content documents SOME version of a tool, not the
   installed one.** Tool tables, flag lists and command examples drift (a skill
   advertising eight MCP tools while the binary advertises one, by design; a
   `tree-sitter graph` subcommand that belongs to a different binary). Verify the
   load-bearing claim against the tool itself — `<tool> --help`, or a live
   protocol probe — before relying on it or repeating its numbers, and call the
   skill stale instead of propagating the claim.

## Verification

- [ ] `hermes skills list` shows the skill under the intended category
- [ ] `.hub/lock.json` entry's `install_path` matches the directory on disk
- [ ] `skill_view(<name>)` returns content and `readiness_status: available`
- [ ] No skills were silently dropped: the count of skill dirs under
      `<skills>` is unchanged apart from the new one.

### After a bulk move (step 5): prove nothing was lost or re-labelled wrong

```bash
S="$HERMES_HOME/skills"
find "$S" -name SKILL.md -not -path '*/.archive/*' -not -path '*/.hub/*' | wc -l  # identical before/after
find "$S" -type f    -not -path '*/.archive/*' -not -path '*/.hub/*' | wc -l  # identical before/after
env -u PYTHONPATH hermes skills list > after.txt    # diff vs before: ONLY the Category cell changes
```

- The summary line `N hub-installed, M builtin, K local — X enabled, Y disabled`
  must be identical (a diff here means a skill stopped being discovered).
- Check the loader's own enumeration: call
  `tools/skills_tool.py::_find_all_skills` with the CLI's interpreter and assert
  no skill has an empty `category` — that set WAS the hybrid list.
- Probe every cleaned bucket: `python3 <skill_dir>/scripts/probe_install_target.py new-skill <H> [<H2> ...]`
  → all `OK`.
- Layout changes reach the session's injected skill index only in the NEXT
  session: `skills_list` in the running session still shows the old tree.

Support files:
- `scripts/probe_install_target.py` — read-only install-target probe (step 3.3).
- `scripts/clean_hybrid_dirs.py` — dry-run-by-default nesting of a hybrid
  bucket's umbrella (step 5).
- `references/profile-distribution-sync.md` — the git payload repo that mirrors
  `<skills>`: owned vs excluded classification, `sync.py push|pull` semantics,
  and the order to run them after a layout change.
- `references/install-identifier-namespaces.md` — the four identifier forms one
  skill wears (catalog feed / hub search / CLI resolution / `.hub/lock.json`),
  how to recover the one a caller used from an action-log filename, the lock
  dump recipe, and the shape of the upstream fix (step 3.5-3.6, pitfalls #7-#8).
- `references/candidate-vetting.md` — whether a candidate will actually install:
  scan verdict tiers and exactly what `--force` clears, the
  listed-but-unfetchable row, the fetch probe that reads a bundle BEFORE
  installing it, and the survey recipe for "which hub skill does X" (step 3.7,
  pitfall #9).
