# Removing skills.sh / GitHub-tap skills — and the `npx skills` installs next to them

The common case, and the one `hermes skills uninstall` was built for. A three-segment identifier
(`owner/repo/path`) normally resolves through the **skills.sh** adapter — a GitHub fetch wearing a
relabelled badge — and a custom **tap** install records source `github`. Both land in `GitHubSource`,
both write a normal lock entry, and both are keyed by the **skill directory name** (the last segment of
`install_path`). For the label-versus-truth distinction, see
`install-hermes-skills/references/install-hermes-skills-from-skill-sh.md`; for removal it does not matter
which of the two wrote the entry.

Measured on this machine (2026-09-30) — the removal of this pack's own skill, end to end:

```
$ hermes skills uninstall remove-hermes-skills -y
Uninstalled 'remove-hermes-skills' from hermes/remove-hermes-skills

$ python3 -c 'import json,os;print(list(json.load(open(os.path.expanduser("~/.hermes/skills/.hub/lock.json")))["installed"]))'
[]

$ ls -d ~/.hermes/skills/hermes/remove-hermes-skills
ls: …: No such file or directory

$ tail -1 ~/.hermes/skills/.hub/audit.log
2026-09-30T08:31:15Z UNINSTALL remove-hermes-skills skills.sh:community n/a user_request
```

Three facts from that run worth reusing: the printed location is the **lock-relative `install_path`**, the
whole directory goes (support files, `scripts/`, nested sub-skills), and the audit line is written even
though nothing was fetched.

## The command

```bash
hermes skills list --source hub                  # names + Source column; the key is the last path segment
hermes skills check <name>                       # read-only; `orphaned` means the entry is already a shell
hermes skills uninstall <name> -y                # rmtree(install_path) + lock entry dropped + audit line
```

**No network is spent.** `uninstall_skill` reads the lock, resolves `install_path`, `rmtree`s it and
writes the two records (`tools/skills_hub_install.py:205-223`). Consequences:

- a **private** repository uninstalls exactly like a public one, no token involved — and a `check` that
  reports `unavailable` (bad token / blocked URL) says nothing about whether removal will work;
- a skill can be removed while its upstream is gone, renamed or archived.

## Nested sub-skill trees: one entry removes them all

One install can bring several `SKILL.md` files if the fetched directory contains sub-directories with
their own. The hub identity stays single, the children show up in `list` as `local`, and removal is
whole-tree — measured earlier in this pack on `paper2agent` (4 rows in `list`, `uninstall paper2agent -y`
→ `list` empty, nothing left on disk). So: never try to remove a child by name (it has no lock entry →
`Error: '<child>' is not a hub-installed skill (may be a builtin)`), and warn before `uninstall <parent>`
that the children go too. Depth in the sibling `install-hermes-skills` →
`references/install-hermes-skills-from-skill-sh.md`.

## Two states that look like a failed removal

**An orphaned entry (the directory is gone, the lock entry is alive).** `check` names it and prints the
remedy itself (paths below are relative to the profile home — `<home>` is `~/.hermes` for the default
profile):

```
$ rm -rf <home>/skills/hermes/remove-hermes-skills
$ hermes skills check remove-hermes-skills
│ remove-hermes-skills │ skills.sh │ orphaned │
Orphaned: remove-hermes-skills — lock-file entries whose local directory is missing or replaced by a
non-directory. For missing directories, remove the stale entry with: hermes skills uninstall <name>
$ hermes skills uninstall remove-hermes-skills -y
Uninstalled 'remove-hermes-skills' from hermes/remove-hermes-skills        # nothing on disk to delete
```

Note what this is for: a lock entry is what makes every install surface say "already installed", so an
orphan both looks installed and blocks the reinstall that would fix it.

**A renamed or moved directory (the entry is alive, the files are elsewhere).** The removal addresses
`install_path` from the lock, so the files survive:

```
$ mv <home>/skills/hermes/remove-hermes-skills <home>/skills/hermes/renamed-by-hand
$ hermes skills uninstall remove-hermes-skills -y
Uninstalled 'remove-hermes-skills' from hermes/remove-hermes-skills
$ test -d <home>/skills/hermes/renamed-by-hand && echo YES
YES                                        # an orphan the hub no longer knows about
```

And when the *key* and the path's last segment disagree, the removal refuses instead of guessing:

```
$ hermes skills uninstall remove-hermes-skills -y     # lock: install_path = "hermes/wrong-name"
Error: Refusing to uninstall 'remove-hermes-skills': Unsafe install path: hermes/wrong-name
```

So: read `install_path` before believing a removal finished, and address the key that matches it (or
repair the entry — `install-hermes-skills` → `references/install-hermes-skills-diagnosis.md`).

## A `cp -R` copy is not a hub skill — and the hub cannot clean up after one

A directory copied in by hand has no lock entry, so `check` / `update` / `audit` / `uninstall` are all
blind to it (`No hub-installed skills to check.` / `Error: '<name>' is not a hub-installed skill …`) and
the only removal is `rm -rf`. Two related leftovers worth grepping for when a user says "it is still
there":

- **an old category directory** after a skill was reinstalled with a different `--category` — one row in
  `list`, two directories on disk, and the second one is invisible everywhere (the skill scan de-dupes by
  name);
- **a directory renamed out of the way** (see above), which is a local copy in all but name.

## The `npx skills` twin — same registry, a different remover

`npx skills add <owner>/<repo> --skill <name>` installs through the skills CLI, not the hub. Hermes is a
first-class target (the CLI's own agent table carries `skillsDir: ".hermes/skills"`), but the bookkeeping
is separate — canonical copy in `~/.agents/skills/<name>`, lock in `~/.agents/.skill-lock.json` — and the
hub genuinely cannot remove it (`hermes skills check <name>` → `No hub-installed skills to check.`).

Measured from the CLI installed on this machine (skills `1.5.23`, read from its own help text):

```
Usage: skills remove [skills...] [options]

Arguments:
  skills            Optional skill names to remove (space-separated)

Options:
  -g, --global       Remove from global scope (~/) instead of project scope
  -a, --agent        Remove from specific agents (omit to clean all agent links)
  -s, --skill        Specify skills to remove (use '*' for all skills)
  -y, --yes          Skip confirmation prompts
  --all              Remove every installed skill (-y implied). Do not combine with named skills.

  $ skills remove my-skill                   # remove specific skill
  $ skills remove skill1 skill2 -y           # remove multiple skills
  $ skills remove --global my-skill          # remove from global scope
  $ skills remove --all                      # remove all skills
```

Aliases `rm` / `r`. Three rules for using it on a Hermes profile:

- **`-g` for a profile-installed skill.** Without it the CLI works in project scope (the current working
  directory's agent dirs); a skill installed globally into `~/.hermes/skills` is the `-g` case;
- **`HERMES_HOME` decides which Hermes it cleans** — the CLI resolves
  `hermesHome = process.env.HERMES_HOME?.trim() || join(home, ".hermes")` and then
  `globalSkillsDir: join(hermesHome, "skills")`, so a removal aimed at one profile writes another
  profile's tree when the environment carries it. Set it explicitly, as with every other removal;
- **`--all` is not "all of Hermes".** The CLI scans its canonical directory plus every agent it detects
  and removes the selected names from **all** of them, so `--all` / `-s '*'` reaches other agents'
  skill directories (Claude Code, Cursor, Codex, …) on the same machine. Never answer "just remove the
  Hermes copies" with that flag.

## After a removal

- The skill comes back only by installing it again: `hermes skills install <owner>/<repo>/<path>
  --category <same category> -y`. The category is read at install time only — the removed entry cannot
  hand its path over.
- Verify as in `SKILL.md` § Prove it went (store, disk, `audit.log`), then check the *other* home if the
  user has more than one profile — a double install of one skill leaves two lock entries and one
  directory, so a removal in one home can leave a convincing-looking row in the other.
