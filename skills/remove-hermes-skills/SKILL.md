---
name: remove-hermes-skills
description: Remove skills from a Hermes profile, and tell a removal from a disable, an uninstall from an orphaned lock entry, and a bundled skill from a hub-installed one. Use when the user wants a skill uninstalled, deleted or muted, when `hermes skills uninstall` answers `'X' is not a hub-installed skill (may be a builtin)`, when a deleted skill still looks installed, when a deleted bundled skill refuses to come back — or keeps coming back — when a ClawHub slug and its frontmatter name disagree, or when the skill was installed by `npx skills` rather than the hub. Installing and updating skills are the sibling skills.
---

# Remove Hermes Skills

`hermes skills uninstall` reaches exactly **one** kind of skill, and that is the whole difficulty: three
other kinds live in the same profile, look identical in `hermes skills list`, and answer a removal
attempt with the *same* message — one that names the wrong kind.

```
$ hermes skills uninstall obsidian -y        # obsidian is a bundled skill here
Error: 'obsidian' is not a hub-installed skill (may be a builtin)

$ hermes skills uninstall book2skill -y      # right skill, wrong name — a ClawHub entry is keyed by its slug
Error: 'book2skill' is not a hub-installed skill (may be a builtin)
```

So the work is: **name the kind → find that kind's own key → run that kind's own command**. Every other
question ("does it come back?", "does the row disappear?", "what did I lose?") follows from the kind.

| Kind | Recognise it | Remove it with | Its own failure mode |
|---|---|---|---|
| **hub-installed** — the only kind `uninstall` reaches | a key in `<home>/skills/.hub/lock.json`; `list` shows a real `Source` (`skills.sh` / `github` / `clawhub` / `url` / `official`) | `hermes skills uninstall <lock key> -y` | the key is not always the name `list` prints |
| **bundled** (built-in) | a line in `<home>/skills/.bundled_manifest`; `list --source builtin` | `hermes skills opt-out --remove -y` (all of them) or `rm -rf <home>/skills/<cat>/<name>` (one) | no `uninstall` at all — and the two routes differ in whether it comes back |
| **local** (a `cp -R` you made) | `list --source local`, `Source: local`; no lock entry | `rm -rf` the directory | invisible to `check` / `update` / `uninstall` / `audit` |
| **npx-installed** (`npx skills add`) | `~/.agents/.skill-lock.json`, not the hub lock | `npx skills remove <name> -g -y` | the hub genuinely cannot see it |
| **not a removal** | `list` shows the row `disabled` | `hermes skills config`, or `skills.disabled` in `config.yaml` | `hermes-agent` is essential — no surface can disable it |

Measured on this machine (2026-09-30, throwaway `HERMES_HOME`): the two errors above are the same string,
so the message never tells you which case you are in. Never report it as "the skill does not exist".

## The one rule

**Resolve the name you were handed into the owning store's key before running anything**, then read that
store's entry. The key is the lock key for a hub skill (a ClawHub slug, not the frontmatter `name`), the
one in `.bundled_manifest` for a bundled skill, the CLI name for an npx install. `hermes skills check
<name>` is the cheap probe for a hub skill — but note the trap it shares with `uninstall`: it is
name-addressed too, and for a name the lock does not hold it answers `No hub-installed skills to check.`,
which reads as if every entry had vanished (measured 2026-09-30, session `20260930_164609_12e4ffd9`:
after `UNINSTALL paper2agent`, that sentence appeared while the lock still held 31 entries). Read
`skills/.hub/lock.json` itself before drawing a conclusion from any of it.

**And when the target is a bundle with nested `SKILL.md` children, read
`references/remove-hermes-skill-sh-skills.md` § Nested sub-skill trees *before* the first command** — one
entry removes them all, the children carry no lock entry of their own, and they are listed under the
**parent's** category.

## Disable is not removal

- `skills.disabled` in `config.yaml` hides a skill from the prompt. The files stay on disk, `check` and
  `update` still manage them, and `list` still counts them.
- `hermes skills config` is the interactive surface (global, or one platform through
  `skills.platform_disabled`); `hermes skills list --enabled-only [-p <profile>]` is what a profile will
  actually load.
- `ESSENTIAL_SKILLS = frozenset({"hermes-agent"})` is dropped from the disabled list on save and
  subtracted on read — it cannot be hidden, and (measured) it is not protected from *deletion* either:
  `opt-out --remove` deletes it like any other pristine bundled skill.
- Ask which the user means. "Stop it firing" is a disable and is undone with one checkbox; a removal is
  undone by reinstalling, from an identifier the lock no longer holds.

## Before you remove

🔴 CHECKPOINT — a removal is the one operation here with no undo: the entry is read, the delta audited
and the backup taken *before* the first `uninstall`, and a missing step stops the run instead of being
worked around.

1. **Read the entry**, so the report can name what went: `source`, `identifier`, `install_path`, `files`,
   `metadata.source_revision` (`scripts/lock-provenance.py` in the sibling `install-hermes-skills` prints
   exactly this). For a ClawHub skill read the directory's `_meta.json` too — the lock stores no version.
2. **Back up hub entries** with `hermes skills snapshot export <file>`. It records lock entries only
   (name, source, identifier, category), so bundled, local and npx installs are outside it.
3. **`uninstall` has no local-edit guard.** Unlike `update`, it does not compare hashes: it `rmtree`s
   `install_path` as it stands. The only gate is the confirmation prompt, which `-y` skips — so if the
   copy holds edits you made, that is the moment they die. **Audit the delta before deleting anything**,
   and report it as part of the answer:

   ```bash
   curl -sL -o <home>/up.tgz "https://codeload.github.com/<owner>/<repo>/tar.gz/<pinned sha>"
   mkdir -p <home>/up && tar -xzf <home>/up.tgz -C <home>/up
   diff -r -x '.DS_Store' <home>/up/<repo>-<sha>/<path-in-repo> "<home>/skills/<install_path>"
   ```

   `.DS_Store` and `__pycache__/*.pyc` are noise; a directory carrying its own `SKILL.md` is content, and
   the reinstall returns only upstream's files. Measured (2026-09-30, session `20260930_164609_12e4ffd9`):
   the 69 upstream files were byte-identical and the entire delta was `.DS_Store`, three `__pycache__`
   entries and one self-authored child skill.
4. **A self-authored skill inside a hub bundle goes with the bundle.** It has no separate identity; the
   sibling `install-hermes-skills` calls the same fact out for updates.

## Commands

```bash
hermes skills uninstall <lock key> -y        # hub-installed — the only thing `uninstall` can remove
hermes skills opt-out [--remove] [-y]        # bundled — marker only / marker + delete pristine copies
hermes skills opt-in [--sync]                # undo the marker / re-seed the bundled set now
hermes skills reset <name> [--restore] [-y]  # bundled — re-baseline tracking / discard edits + re-copy stock
hermes skills list [--source all|hub|builtin|local] [--enabled-only]
hermes skills check <name>                   # an `orphaned` row is exactly what `uninstall` is for
hermes skills snapshot export <file>         # back up the hub set before a bulk removal
npx skills remove [<name>...] [-g] [-a <agent>] [-y] [--all]   # the npx-installed twin
```

Measured `hermes skills uninstall --help` on this machine (2026-09-30):

```
usage: hermes skills uninstall [-h] [--yes] name

positional arguments:
  name        Skill name to remove

options:
  -h, --help  show this help message and exit
  --yes, -y   Skip confirmation prompt
```

No `--force`, no `--source`, no `--category`: a removal has nothing to force and nowhere to file the
result.

## What a removal does not do

- **It does not reach another profile.** The lock, the manifest and the tree are all per `HERMES_HOME`.
  Use `hermes -p <profile> skills uninstall <key>`, or pin `HERMES_HOME=<profile dir>`. A gateway/agent
  session can be carrying a *different* profile's home, so print `${HERMES_HOME:-<unset>}` in the same
  command as the removal (sibling `maintain-hermes-skills` →
  `references/maintain-hermes-skills-inventory-and-availability.md`).
- **It leaves the scaffolding behind.** The category directory survives its last skill; `taps.json`,
  `.hub/scan-cache/`, `.hub/index-cache/` and `.usage.json` are untouched — the usage ledger keeps a name
  after its files are gone, so it is never evidence that a skill exists.
- **It leaves a dangling `skills.disabled` name.** Removing a skill that was *disabled* (a real case: an
  official optional skill parked in `disabled` after a `dangerous` scan verdict, e.g. `comfyui`) does not
  touch `config.yaml` — the name stays, the footer just goes `1 disabled` → `0 disabled`. Harmless now,
  but it silently re-disables the skill if it is ever reinstalled. Clean it with
  `hermes config set skills.disabled '[]'` (or the current list minus the name): the command prints
  `⚠ 'skills.disabled' is not a recognized config key` and *does* write it — read back with
  `hermes config get skills.disabled`. The agent's own `patch`/`write_file` tools **refuse** `config.yaml`
  (`Refusing to write to Hermes config file … Agent cannot modify security-sensitive configuration`), so
  the CLI is the only route.
- **It is not undone by `update`.** `hermes skills update` re-fetches the *recorded* source + identifier,
  and the entry is gone. Getting the skill back is an install, and `--category` must be passed again
  because the category is read at install time only.
- **A running session keeps it until it reloads.** The CLI clears the skills cache as it writes
  (`_finish_change` → `_clear_skills_cache`, `hermes_cli/skills_hub.py:122-131`); an already-running
  gateway or desktop session needs `/reload-skills` (or a new session) before the skill is gone from its
  list.

## When the removal refuses — trigger / first fix / fallback

| Trigger | First fix | If it still fails |
|---|---|---|
| `Error: '<name>' is not a hub-installed skill (may be a builtin)` | read `skills/.hub/lock.json` yourself — no entry means the copy is local or bundled, and that message names the wrong kind | local: delete the directory; bundled: `hermes skills opt-out --remove` |
| `hermes skills check <name>` → `orphaned` | `hermes skills uninstall <name> -y` clears the stale entry (no network is spent on those) | the missing directory is already gone — the entry was the last thing left |
| `hermes skills list` shows the name as `local` although only the parent was ever installed | it is a nested child: remove the **parent** by its lock key | confirm with `ls -d` and the `list` footer that the children went with it |
| the skill is back after a clean removal | something re-created it: check `.bundled_manifest`, then the lock, then `~/.agents/.skill-lock.json` | the re-creating route is the one to switch off, not the copy to delete again |

## Prove it went

Three cheap checks, in this order — the first one alone is not proof:

1. **The store.** The key must be absent from `skills/.hub/lock.json` (`installed`) — or from
   `.bundled_manifest` for a bundled skill, where the removal is "the copy is gone" instead.
2. **The disk.** `ls -d <home>/skills/<install_path>` — and look for the *other* copy: a removal that
   reports success while the files survive is the renamed-directory case, not a success.
3. **The log.** `skills/.hub/audit.log` writes one line per hub action; a removal looks like

```
2026-09-30T08:31:15Z UNINSTALL remove-hermes-skills skills.sh:community n/a user_request
```

measured alongside the command output `Uninstalled 'remove-hermes-skills' from
hermes/remove-hermes-skills` (the path printed is `install_path`, relative to `skills/`), an empty lock,
and a `list` footer that went `1 hub-installed` → `0 hub-installed`.

## Route by what was asked

| The question is | Read |
|---|---|
| a bundled / built-in skill — delete one, delete them all, "stop seeding them", `opt-out --remove` output, official *optional* skills that are not bundled | `references/remove-hermes-built-in-skills.md` |
| a `@publisher/slug` ClawHub skill, or `list` prints a name that is not the key | `references/remove-hermes-clawhub-skills.md` |
| a three-segment identifier or a tap skill (the common case), nested sub-skill trees, an orphaned lock entry, a renamed directory, or an `npx skills` install | `references/remove-hermes-skill-sh-skills.md` |
| a raw-URL skill (`Source: url`), a one-file install, a `check` stuck on `unavailable` | `references/remove-hermes-url-skills.md` |
| *how did it get here* — its source, identifier, `--force` history, why the lock looks odd | `install-hermes-skills` → `references/install-hermes-skills-diagnosis.md` |
| any `hermes skills` error string | `install-hermes-skills` → `references/install-hermes-skills-diagnosis.md` |
| installing it again, or moving it to a better bloodline instead of deleting it | `install-hermes-skills` → `references/install-hermes-skills-from-names.md` |
| updating rather than removing, `check` statuses, source changes | `update-hermes-skills` |
| why a skill exists at all, what seeded it, enabling and disabling, the curator's `.archive/` | `maintain-hermes-skills` |

## Skill Structure

<!-- Generated by Scripts -->

```
remove-hermes-skills/
├── SKILL.md  (204 lines)
├── test-prompts.json  (12 lines)
└── references/
    ├── remove-hermes-built-in-skills.md  (151 lines)
    ├── remove-hermes-clawhub-skills.md  (115 lines)
    ├── remove-hermes-skill-sh-skills.md  (156 lines)
    └── remove-hermes-url-skills.md  (87 lines)
```

<!-- Generated by Scripts -->
