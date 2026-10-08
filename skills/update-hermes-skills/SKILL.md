---
name: update-hermes-skills
description: Update skills already installed in Hermes, and work out which update path a given skill actually has. Use when a skill is out of date, when `hermes skills check` reports update_available / unavailable / orphaned, when an update was skipped for local edits, when a bundled (built-in) skill never updates, or before believing a `No updates available.` line. Routes by which kind of skill it is — hub-installed, bundled, local, or npx-installed — then gives the tested commands for that source. Installing and removing skills are the sibling skills.
---

# Update Hermes Skills

`hermes skills update` reaches **one** kind of skill. Three other kinds live in the same profile, look
identical in `hermes skills list`, and are invisible to it — and two of them answer
**`No updates available.`** and exit 0 rather than admitting they cannot see the skill at all. So the
first question is never "how do I update X"; it is **which kind of X is it**.

| Kind | How to recognise it | What updates it | Its silent failure mode |
|---|---|---|---|
| **hub-installed** | an entry in `skills/.hub/lock.json`; `list` shows a real `Source` (`skills.sh` / `github` / `clawhub` / `url` / `official`) | `hermes skills check` → `hermes skills update` | — |
| **bundled** (built-in) | tracked in `skills/.bundled_manifest`; `list --source builtin` | `hermes update` (re-seeds), `reset --restore` to revert | `0 new / 0 updated` can mean *no source* |
| **local** (a `cp -R` you made) | `list --source local`; `Source: local` | you, by hand | `check`/`update` answer `No … to check` / `No updates available.` |
| **npx-installed** (`npx skills add`) | `~/.agents/.skill-lock.json`, not the hub lock | `npx skills update -g -y` | `hermes skills check <name>` → `No hub-installed skills to check.` |

Measured on this machine (2026-09-30): `hermes skills update obsidian` — a local skill — prints
`No updates available.`, and `hermes skills check obsidian` prints `No hub-installed skills to check.`
Neither is evidence that `obsidian` is current.

## The one rule

`hermes skills check <name>` first (read-only), then read the **Status** column — `update` acts on
`update_available` rows and on nothing else.

| Status | What it means | What to do |
|---|---|---|
| `up_to_date` | installed bundle hash == upstream hash (a matching `source_revision` short-circuits before any download) | nothing |
| `update_available` | the upstream bundle now hashes differently | `hermes skills update <name>` |
| `unavailable` | the adapter matching the **recorded** source could not fetch it | fix that fetch path — for `url` entries see `references/update-hermes-url-skills.md` |
| `orphaned` | `install_path` is missing, or is not a directory | `hermes skills uninstall <name>` to clear the stale lock entry (no network is spent on these) |
| `invalid_install` | `install_path` cannot be resolved at all | read the lock entry; the name and the path disagree |

## Two hashes — why an update reports "available" and then does nothing

The two commands hash different things, and that is the trap this skill exists for:

- **`check` compares installed vs upstream** — the `content_hash` recorded at install time against the
  upstream bundle's hash. What you edited locally is not part of this comparison.
- **`update` compares on-disk vs installed** — `content_hash(<install_path>)` right now against the
  recorded hash. Any drift means the skill was edited, and an update `rmtree`-replaces the directory,
  so it is **skipped** unless `--force` is passed (`hermes_cli/skills_hub.py:887-897`, `:928-932`).

🔴 CHECKPOINT before `--force`: it `rmtree`-replaces the directory, so a copy holding content the clone
lacks loses exactly that content — run the copy-ahead check first, and stop if the copy is ahead.

**`update` is one-directional: a pushed revision → the profile.** It cannot publish a local edit outward,
so it is not the tool that reconciles a drifted copy — an installed copy that is *ahead* of its clone is a
job for `recruit-learning-in-session` (`references/recruit-learning-in-session-routing.md` § *Reconciling a drifted
installed copy*): judge the drift, backport what is worth keeping into the clone, push, and only then
update. Going straight to `--force` here is the one move that destroys the very edit that needed judging.

## Right after a push: `check` / `update` / `install` can disagree — read the GitHub quota first (measured 2026-10-04)

Same minute, same lock state: `check` reports `1 update(s) available` (installed = the previous revision,
upstream = the one just pushed) while `update` answers `No updates available.` and leaves the content on the
previous revision; minutes later, on the same host, `check` answers `unavailable` with 0 rows checked. A
further `install --force` prints the cause outright:

```
Error: Could not download '<owner>/<repo>/skills/<name>'.
Hint: GitHub API rate limit exhausted (unauthenticated: 60 requests/hour).
Set GITHUB_TOKEN in your .env or install the gh CLI and run gh auth login to raise the limit to 5,000/hr.
```

**A headless host with no credential fetches through the unauthenticated GitHub API — 60 requests/hour** — and
one round of `inspect` + `install` + `update` + `check` spends it (exactly what happened here). In the same
window three sibling skills on a credentialed machine updated to the new revision without complaint, so this
is **not** index or cache lag — do not go looking there.

How to judge: ① read a `Could not download` / quota hint before blaming your own revision; ② the fix is a
credential on that host (`GITHUB_TOKEN` in the profile env, or `gh auth login`), or simply waiting out the
hourly reset (an unauthenticated host self-heals, just slowly); ③ a delivery's state is still decided by
**content comparison** plus the lock's `source_revision` — `No updates available.` and `update_available`
appearing together does not mean the content is current.

### 🔧 Never edit the installed copy — and the measured repair when you already did

**Rule: a hub-installed skill is edited in the clone, never in the installed tree.** An edit made in the
installed tree is a dead end three times over: `check` then reads `update_available` *even though the copy
is ahead*, `update` skips it with `kept your local edits`, and `--force` (the "obvious" fix) rmtree-replaces
the directory and deletes exactly the edit. Measured on this machine 2026-10-03 — the agent edited
`$HERMES_HOME/skills/git-annex/sync-and-share-content/SKILL.md` instead of the clone, and had to run this
sequence afterwards:

1. **Prove which copy you edited** — `diff -r <clone>/skills/<name> $HERMES_HOME/skills/<类目>/<name>`:
   the diff *is* your edit, and the clone path is where it has to land.
2. **Backport byte-identically into the clone** → `git add <pathspec>` → commit → `git push origin HEAD`
   → confirm `git ls-remote origin HEAD` equals your sha (that read-back is the delivery evidence, not the
   push's own output).
3. **Only now** `hermes skills update <name> --force`. It may *still* print `kept your local edits` — the
   skip verdict is the **recorded hash**, not whether the two trees currently agree — but it proceeds and
   re-records the lock. `--force` at this point destroys nothing: clone and installed copy are identical.
4. **Read back four things**: `diff -r` empty · `hermes skills check <name>` → `up_to_date` ·
   `metadata.source_revision` in `.hub/lock.json` == the pushed commit · the changed line greppable in the
   installed copy.

Measured before/after: the just-edited skill read `update_available` (copy ahead of its clone); after
backport + push + `--force` it read `up_to_date` with the lock's `source_revision` at the new commit
(`2887ff0` for `sync-and-share-content`, `00c823f` for `update-hermes-skills`).

**A `kept your local edits` line when you never edited anything is usually `__pycache__`.** Running a
skill's own bundled script generates `__pycache__/` inside the installed directory, and the on-disk
hash then differs from the recorded one — so `update` skips it. Fix: delete the installed copy's
`__pycache__/` first, then re-run `update` (measured to pass on the retry; nothing on disk was actually
changed). `hermes skills update <name>` takes **no `-y`** either (only `--force`; see Shared commands),
so a `kept your local edits` line is never cleared by `-y`.

Measured (sandbox, revision and hash both forged stale):

```
$ hermes skills check skill-creator
│ skill-creator │ github │ update_available │

$ hermes skills update skill-creator
Skipping: skill-creator — you have local edits (update would overwrite them).
1 skill(s) kept your local edits: skill-creator.
Overwrite with: hermes skills update <name> --force

$ hermes skills update skill-creator --force
Updated 1 skill(s).
```

So `update_available` plus a silent skip is a coherent pair rather than a bug, and **a skipped run
still exits 0**. A related measured fact: forging only `source_revision` back to an older commit
leaves `check` at `up_to_date` — the revision is a fast-path shortcut, **the hash is the decision**.

**A blocked delivery lies in its closing line.** `hermes skills update <name>` against a bundle the scan
refuses prints `Not installed: the security scan found 1 high-risk pattern(s) in … Hermes never installs
unverified skills with high-risk findings, even with --force.` and then *still* ends `Updated 1 skill(s).`
with exit 0 — measured twice (2026-09-30: session `20260930_162008_8587d70c` on `remove-hermes-skills`,
1 finding; sessions `20260930_152412_ccb1545a` and `20260930_154259_24a59f` on `install-hermes-skills`,
5 findings). So the summary line is not the outcome: read the whole output, and treat the *previous
revision still being installed* as the truth — a non-empty `diff -rq` against the clone, and a
`metadata.source_revision` older than the push.

**That contradiction has a ladder, and re-running with `--force` is not on it:** 1) read the pattern list
and fix the text the scanner reads — the same finding will come back otherwise
(`install-hermes-skills` → `references/install-hermes-skills-scan-gate.md`); 2) if the verdict is
`dangerous` on a `community` or `trusted` source, **no flag overrides it** and the delivery is `--force`-
proof at that revision; 3) if you cannot fix it, say the *previous* revision is what the profile still
loads, and name the offending pattern instead of reporting an update that did not happen.

## What `update` does per skill, in order (source-verified)

1. `check_for_skill_updates(name)` — keep only the `update_available` rows
   (`hermes_cli/skills_hub.py:916`).
2. `_has_local_edits(installed)` → skip, unless `--force` (`:928`).
3. `do_install(identifier, category=<parent of install_path>, force=True, source_id=<lock's source>)`
   (`:937-938`), which means:
   - **the category comes from `install_path`'s parent**, so an update keeps the skill exactly where it
     is and never re-files it;
   - **the source is pinned** to the lock's registry. The in-code reason: a bare identifier such as
     `reddit` would otherwise fuzzy-resolve inside `do_install` to a same-named skill in a *different*
     registry, overwriting the files and rewriting the lock's `source`;
   - **`force=True` is internal**, so an update does **not** re-ask the security gate the way a first
     install does — a `community` + `caution` skill that needed `--force` to install updates without it
     (the bundle is still scanned and the verdict re-recorded);
   - the install is a **whole-directory replacement**, so support files, scripts and any nested
     `SKILL.md` bundles all move together.
4. Prints `Updated N skill(s).`, or the kept-your-local-edits lines above.

## A source change is uninstall + install — never an update

`do_update` re-fetches the **recorded** `source` + `identifier` (`do_install(..., source_id=<lock's
source>)`, `hermes_cli/skills_hub.py:937`), so an update only ever moves a skill forward inside its own
bloodline; it cannot move it to a better one. Measured (2026-09-30): a ClawHub fork of `darwin-skill`
(7 installs) and the upstream `alchaincyf/darwin-skill` (`6132★`, skills.sh `Installs 10.7K`) are two
different lock entries, and no `update` on the fork produces the upstream one.

The move is four steps: rank the candidates (`install-hermes-skills` →
`references/install-hermes-skills-from-names.md`), prove the winner installs in a throwaway
`HERMES_HOME`, `hermes skills uninstall <lock key> -y` (the **lock key** — for ClawHub the slug, not the
name `list` prints), then `hermes skills install "<winner>" --category <same category> -y`, because the
category is only read at install time and is not inherited. Verify with `list`, the lock entry and
`check <new key>` → `up_to_date`; a same-name fork under the same name makes a failed move look
successful, so report the identifier you installed.

## What no update command can reach

- **Bundled skills** are not hub entries: `hermes skills update` never lists them. `hermes update`
  re-seeds them and *keeps* any copy you edited — `list-modified` / `diff` / `reset`
  (`references/update-hermes-built-in-skills.md`).
- **Local copies** have no lock entry: `check`, `update`, `audit` and `uninstall` cannot see them.
  Re-install through the hub if you want them maintained.
- **A local edit inside an installed skill.** No update command pushes content outward — an installed copy
  that has drifted ahead of its clone is reconciled through the clone first (`recruit-learning-in-session` →
  `references/recruit-learning-in-session-routing.md` § *Reconciling a drifted installed copy*). `--force` before
  that publishes nothing and deletes the edit; this command only ever carries a pushed revision home.
- **npx-installed skills** are managed by the skills CLI's own lock, not the hub one — same registry,
  different updater (`references/update-hermes-skill-sh-skills.md`).
- **Sub-skills inside an installed bundle**: `list` reports them as `local`, but they live in the
  parent's tree, so the parent's update and uninstall move all of them. They are not separately
  updatable.
- **Other profiles**: the lock is per profile. Run `hermes -p <profile> skills update <name>`, or the
  skill stays stale there.

## Cost — scope checks by name

`check` without a name walks **every** hub entry (20 on this machine) and each row costs a network round
trip. Only adapters that implement `current_revision` can answer without downloading
(`tools/skills_hub_github.py:300`; the base class returns `""`, `tools/skills_hub_models.py:154-157`),
and that shortcut also needs a `source_revision` in the lock. Measured per entry:

| Source | Lock records `source_revision`? | Measured `check` | Note |
|---|---|---|---|
| `github` (tap) | yes | 3.3 s | fast path |
| `skills.sh` | yes | 9.5–11.9 s | fast path, still a GitHub API call |
| `clawhub` | no (`metadata: {}`) | 8.9 s | full download on every check |
| `url` | no | 2.1 s | full download on every check (tiny bundle) |
| `official` | no (`metadata: {}`) | not timed | full download on every check |

Two consequences for scripts: check **by name** (never a bare `hermes skills check` on a timer), and
grep for `update_available` rather than the summary line — `0 update(s) available` also contains
`update(s) available`.

## Shared commands

```bash
hermes skills check [name]                 # read-only; scope it by name (see Cost)
hermes skills update [name] [--force]      # --force overwrites local edits (rmtree-replaces the tree)
hermes skills audit [name] [--deep]        # re-scan; verdicts follow the scanner version
hermes skills snapshot export <file>       # back up the installed set before a bulk update

hermes skills list --source hub|builtin|local
hermes skills list-modified [--json]       # bundled skills you edited (kept by `hermes update`)
hermes skills diff <name>                  # bundled: your copy vs the stock version
hermes skills reset <name> [--restore]     # bundled: re-baseline tracking / revert to stock
hermes -p <profile> skills check|update    # the lock is per profile
```

**Pass one name per command.** The CLI takes a single positional — `hermes skills update alpha beta` exits 2
with `hermes: error: unrecognized arguments: beta` and updates nothing (measured 2026-09-30), so a batch of
names is one invocation per name.

**`update` takes no `-y`** (unlike install/uninstall, which do): `hermes skills update <name> -y` exits 2
with `hermes: error: unrecognized arguments: -y` and updates nothing (measured 2026-10-03). `--force` is
the only flag this subcommand has, and it never prompts — so there is nothing for `-y` to answer.

Measured `hermes skills update --help` on this machine (2026-09-30):

```
usage: hermes skills update [-h] [--force] [name]

positional arguments:
  name        Specific skill to update (default: all outdated skills)

options:
  --force     Overwrite skills you have edited locally (they are skipped by
              default)
```

In a session the same work is `/skills update <name> [--force]`; `/skills check` is read-only.

## Route by what was asked

| The question is | Read |
|---|---|
| a bundled / built-in skill never changes, what `hermes update` printed, `list-modified`, `diff`, `reset`, `repair-official` | `references/update-hermes-built-in-skills.md` + `scripts/restore_builtin_skills.py` (the re-seed half) |
| a three-segment identifier or a tap skill (the common case), the revision fast path, nested sub-skill trees, an update skipped because of a self-authored skill inside the bundle | `references/update-hermes-skill-sh-skills.md` |
| an `npx skills add` install of the same registry | `references/update-hermes-skill-sh-skills.md` |
| a `@publisher/slug` ClawHub skill, version vs hash, same-slug-different-lineage risk, moving a ClawHub install to its upstream | `references/update-hermes-clawhub-skills.md` |
| a raw-URL skill, a `check` stuck on `unavailable`, floating refs | `references/update-hermes-url-skills.md` |
| installing, removing, seeding on/off, or a search that cannot find your skill | the siblings `install-hermes-skills`, `remove-hermes-skills`, `maintain-hermes-skills` |
| an error string from any `hermes skills` command, or "how was this installed / why did it need `--force`" | `install-hermes-skills` → `references/install-hermes-skills-diagnosis.md` |

## When the new content takes effect

- A CLI `hermes skills update <name>` clears the skill cache as it writes, so a CLI session sees it at
  once; a **running** session (gateway / desktop) picks the new files up on its next session — or
  immediately with `/reload-skills`.
- The update is per profile; `hermes skills list --enabled-only -p <profile>` shows what a profile
  will actually load.

## Skill Structure

<!-- Generated by Scripts -->

```
update-hermes-skills/
├── SKILL.md  (295 lines)
├── test-prompts.json  (12 lines)
├── references/
│   ├── update-hermes-built-in-skills.md  (174 lines)
│   ├── update-hermes-clawhub-skills.md  (121 lines)
│   ├── update-hermes-skill-sh-skills.md  (168 lines)
│   └── update-hermes-url-skills.md  (133 lines)
└── scripts/
    └── restore_builtin_skills.py  (128 lines)
```

<!-- Generated by Scripts -->
