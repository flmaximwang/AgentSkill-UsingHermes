# Removing ClawHub (`@publisher/slug`) skills

A ClawHub skill **is** a hub entry, so removal is one command — `hermes skills uninstall <slug> -y` — and
the work is entirely in choosing the name. A ClawHub package carries up to three names, and the two
commands that matter address different ones:

| Name | Where it lives | Who takes it |
|---|---|---|
| registry display name (`Cangjie Skill`) | the ClawHub page | nobody on the CLI |
| frontmatter `name:` (`book2skill`) | the installed `SKILL.md` | the agent's skill list, `skill_view` |
| **slug** (`cangjie-skill`) | the lock key, the install directory | **`check` / `update` / `audit` / `uninstall`** |

Measured on this machine (2026-09-30), for two installed ClawHub skills:

```json
"skillopt":       {"source": "clawhub", "identifier": "clawhub/skillopt",                    "install_path": "skillopt"}
"cangjie-skill":  {"source": "clawhub", "identifier": "@terrybenedict0515/cangjie-skill",   "install_path": "agent-evolution/cangjie-skill", "files": 21}
```

and the consequence, both commands run for real:

```
$ hermes skills check cangjie-skill
│ cangjie-skill │ clawhub │ up_to_date │

$ hermes skills uninstall book2skill -y              # the frontmatter name — not a lock key
Error: 'book2skill' is not a hub-installed skill (may be a builtin)
```

That error is the same string a bundled skill produces, so it never tells you the name was wrong.
Resolve the key from the store, not from `list` — `list` prints the frontmatter name and therefore shows
this skill as `book2skill | local | local | enabled`, i.e. as if the hub did not manage it.

## The command

```bash
hermes skills list | grep -i <name>          # read the DISPLAYED name, expect a mismatch
python3 - <<'PY'                             # the lock keys are the truth
import json, os; d = json.load(open(os.path.expanduser("~/.hermes/skills/.hub/lock.json")))
print([k for k, v in d["installed"].items() if v["source"] == "clawhub"])
PY
hermes skills check <slug>                   # read-only confirmation the slug is a key (clawhub | up_to_date)
hermes skills uninstall <slug> -y            # the removal
```

`uninstall` takes the **bare slug**, not the `@publisher/slug` identifier — the publisher segment is
load-bearing at *install* time (the registry answers `409 AMBIGUOUS_SKILL_SLUG` and the adapter
disambiguates with `?owner=`), while the entry's key is the slug alone. Pass what the lock shows.

## Before removing — the version is in the package, not in the lock

ClawHub entries store `metadata: {}` — no `source_revision`, no version. The install dropped its own
record next to the skill instead:

```
$ cat <home>/skills/agent-evolution/cangjie-skill/_meta.json
{"ownerId": "kn73v3qf2r4dbre319rz829p0d82msxd", "slug": "cangjie-skill",
 "version": "1.0.0", "publishedAt": 1781784343470}
```

So copy that file (or its `version`/`publishedAt`) into the report before deleting: after `uninstall`
there is no recorded version anywhere in the profile, and the registry can have moved on
(`GET https://clawhub.ai/api/v1/skills/<slug>` → `.skill.stats.versions`, `.updatedAt`).

The same read also settles the **lineage** question, which matters when removal is really "this is the
wrong skill": compare the frontmatter `name` and `version` against the intended upstream — a changed
`name` means a different bloodline, not a newer version. The measured case (ClawHub's
`@terrybenedict0515/cangjie-skill`, frontmatter `name: book2skill`, no `scripts/`) and its upstream
(`kangarooking/cangjie-skill`, `name: cangjie-skill`) are documented in the sibling
`install-hermes-skills` → `references/install-hermes-skills-from-clawhub.md`.

## Removing in order to replace — the swap workflow

A ClawHub skill is a repackaging layer, and `hermes skills update` can never cross to another bloodline
(it re-fetches the recorded source). A swap is therefore **uninstall + install**, and the category has to
be re-supplied because it is read at install time only:

```bash
hermes skills uninstall <installed slug> -y                                  # e.g. darwin-skill-qszf
hermes skills install "skills-sh/alchaincyf/darwin-skill/darwin-skill" --category agent-evolution -y
hermes skills check <new key>                                                # expect up_to_date
```

Measured for that pair: 37 files / 5.1 MB, verdict `SAFE`, and the new key (`darwin-skill`) matches the
display name, so the confusion above disappears with it. Order matters — installing first leaves two
copies and one of them invisible to `list`.

## Traps

- **Never rename the directory to match the frontmatter name.** Two measured outcomes, in one run:
  - the removal is **addressed from the lock**, so a renamed directory survives as an orphan while the
    entry is deleted: `mv <home>/skills/hermes/remove-hermes-skills <home>/skills/hermes/renamed-by-hand`
    then `hermes skills uninstall remove-hermes-skills -y` → `Uninstalled 'remove-hermes-skills' from
    hermes/remove-hermes-skills`, rename survived (`renamed dir still on disk? YES`), lock empty. The hub
    has now forgotten files that are still on disk — `rm -rf` them yourself;
  - an entry whose `install_path` no longer ends in the key is refused, not guessed:
    `Error: Refusing to uninstall 'remove-hermes-skills': Unsafe install path: hermes/wrong-name`
    (`_resolve_lock_install_path` → `_normalize_lock_install_path`, `tools/skills_hub_install.py:38`).
    Fix the entry's `install_path` (back up `lock.json` first) or address the key that matches it — never
    hand a "tidier" name to `uninstall`.
- **An entry with no directory is still removed cleanly.** `check` reports `orphaned` and prints the
  remedy; `uninstall <slug> -y` then clears the entry without touching the disk (measured: it prints
  `Uninstalled … from <install_path>` even though nothing is there, and the lock key disappears). This is
  also the fix for "the install fails because it thinks it is already installed".
- **`uninstall` has no `--force` and no local-edit guard.** It `rmtree`s the directory as it stands; the
  confirmation prompt (`-y` skips it) is the only gate. An edited ClawHub skill dies with the directory.
- **Two publishers can hold the same slug.** `hermes skills uninstall <slug>` removes *your* entry; it
  does not disambiguate the registry. If the user's complaint is "I installed the wrong publisher's
  copy", the removal is the same command and the answer is what you install next.
- **The registry copy is not yours to delete.** Removal touches this profile's home only; the ClawHub
  package and its stats are untouched, and the desktop catalog row will simply return to its
  "not installed" state after the page's 30-minute stale window.
- **Do not confuse a ClawHub install with an `npx skills` install of the same skill.** Both can show up
  as `local`/`local`; only the hub-installed one has a lock entry, and the npx one is removed by the CLI
  (`references/remove-hermes-skill-sh-skills.md`).
