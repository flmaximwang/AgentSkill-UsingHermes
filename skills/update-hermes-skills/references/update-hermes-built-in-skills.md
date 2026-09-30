# Updating bundled (built-in) skills

Bundled skills are the one kind whose update path has nothing to do with the skill hub. `hermes skills
update` never lists them, and `hermes skills check` never reports on them — the updater is `hermes
update`, and the bookkeeping is a hash manifest, not the lock file. The whole reference is one
diagnosis: **a bundled skill that "never updates" is usually a skill you edited, and the keeping is by
design.**

Evidence tiers below: *quoted from source* (with `file:line`), or *measured* (real output re-run
2026-09-30 on this machine, read-only). Nothing here ran `hermes update` itself.

## The mechanism, in one line

```
code root's skills/  ──►  sync_skills()  ──►  hash gate (.bundled_manifest)  ──►  <HERMES_HOME>/skills/
```

`sync_skills()` copies from the **current code root's** `skills/` into the **current profile's**
`HERMES_HOME/skills/`, tracking each skill's origin hash in `<HERMES_HOME>/skills/.bundled_manifest`.
Where that code root is — and therefore whether seeding has a source at all — is the sibling
`maintain-hermes-skills` skill's job: read its `maintain-hermes-bundled-skills.md` reference (installed
under `~/.hermes/skills/maintain-hermes-skills/references/`, in the repository under
`skills/maintain-hermes-skills/references/`). Follow that diagnostic when the sync reports zero work.
This reference covers only what the **update** does with what it finds.

## What `hermes update` prints about skills

`hermes_cli/update_cmd_maint.py:525-540` (quoted from source — the run itself was not executed here,
because it pulls git and restarts the gateway):

```python
def _print_bundled_skills_sync_report() -> None:
    """Run ``sync_skills`` (copies new, updates changed, respects user deletions) and print its summary."""
    result = sync_skills(quiet=True)
    if result["copied"]:
        print(f"  + {len(result['copied'])} new: {', '.join(result['copied'])}")
    if result.get("updated"):
        print(f"  ↑ {len(result['updated'])} updated: {', '.join(result['updated'])}")
    if result.get("user_modified"):
        print(f"  ~ {len(result['user_modified'])} user-modified (kept)")
        print("    → see them: hermes skills list-modified  (diff/reset to resume updates)")
    if result.get("cleaned"):
        print(f"  − {len(result['cleaned'])} removed from manifest")
    if result.get("relocated"):
        print(f"  → {len(result['relocated'])} moved to new upstream paths: {', '.join(result['relocated'])}")
```

Read the four symbols as four different states, because two of them look like success and are not:

| Line | Meaning |
|---|---|
| `+ N new` | a skill shipped upstream that this profile did not have |
| `↑ N updated` | your copy was pristine and the bundled copy changed → yours was replaced |
| `~ N user-modified (kept)` | **you edited it, so it was deliberately not updated** — the pointer line tells you where to go |
| `− N removed from manifest` | the manifest had an entry whose local copy is gone |
| `→ N moved to new upstream paths` | upstream re-filed the skill; the local copy followed |

## The hash gate — the four outcomes

From the `tools/skills_sync.py` module docstring (`:2-6`, quoted from source):

```
NEW skills are copied and recorded; EXISTING skills update only when bundled changed AND the user copy
still matches the origin hash (else user-customized -> SKIP); user-DELETED skills are not re-added; ...
```

So per skill, per sync:

1. **never seen** → copied in, hash recorded;
2. **bundled changed, your copy still matches the recorded hash** → updated;
3. **your copy no longer matches** → skipped with `  ~ <name> (user-modified, skipping)`
   (`tools/skills_sync.py:369`) — this is the deliberate protection, not a failure;
4. **you deleted it** → not re-added.

The same protection is what the hub's `update --force` mirrors for installed skills: destructive
replacement must be an explicit choice (`hermes_cli/skills_hub.py:905-910` says so outright).

Measured state on this machine (2026-09-30):

```
$ wc -l ~/.hermes/skills/.bundled_manifest
58 /Users/maxim/.hermes/skills/.bundled_manifest
$ find ~/.hermes/hermes-agent/skills -name SKILL.md | wc -l
58
$ ls ~/.hermes/.no-bundled-skills
ls: /Users/maxim/.hermes/.no-bundled-skills: No such file or directory
```

58 manifest entries matching 58 `SKILL.md` files in the checkout, and no opt-out marker → this profile
is on the normal seeding path, and the app/gateway chain is the one that seeded it.

## Diagnosis — walk this ladder, drop a rung only on its signal

**Rung 1 — is it user-modified? (the overwhelmingly common answer).**
Signal to stop here: the skill appears in the list.

```
$ hermes skills list-modified
3 user-modified bundled skill(s) (kept as-is by `hermes update`):
  ~ computer-use
  ~ hermes-agent
  ~ obsidian

See changes:   hermes skills diff <name>
Resume updates: hermes skills reset <name>          (keep your copy, re-baseline)
Revert to stock: hermes skills reset <name> --restore

$ hermes skills list-modified --json
["computer-use", "hermes-agent", "obsidian"]
```

`--json` is the scriptable form (an array of names only — the human view carries the hints). Then pick
the intent:

- **keep your edits, resume receiving upstream changes** → `hermes skills reset <name>`. It clears the
  manifest entry so future syncs stop treating the copy as user-modified. Mechanism, inferred from the
  CLI's own wording: it re-baselines the tracking against your copy, it does not restore upstream
  content.
- **throw your edits away and go back to stock** → `hermes skills reset <name> --restore`. The
  confirmation prompt states it plainly — `This will DELETE your current copy and re-copy the bundled
  version.`
- **see the delta first** → `hermes skills diff <name>`. Measured, and note that it shows both file
  content and whole-file additions:

```
$ hermes skills diff hermes-agent
-### Let the user reply to a delivery
- …
- only in stock: references/windows-quirks.md
- only in stock: templates/clock.mjs
- only in stock: templates/plugin.js
- only in stock: templates/skin.yaml

Revert with: hermes skills reset hermes-agent --restore
```

`+ only in your copy: <path>` marks files only you have; `- only in stock: <path>` marks stock files
your copy lost. When nothing differs, `diff` prints a green no-difference line and no `reset` hint.

**Rung 2 — did the sync even have work to do?**
Signal: `hermes update` printed `0 new / 0 updated`, or nothing at all, while the built-in skill is
still old. That is not "already current" — a sync with no source to copy from early-returns and renders
identically. Follow the sibling skill `maintain-hermes-skills`, whose own reference
`maintain-hermes-bundled-skills.md` covers it (which chains/interpreters have a `skills/`, and
`HERMES_BUNDLED_SKILLS` when one does not).

**Rung 3 — was this profile opted out?**
Signal: the marker file exists, or `hermes update` printed the `opted out of bundled skills … seeding
essential skills only` line. The marker means *essential only* (a singleton set,
`ESSENTIAL_SKILLS = frozenset({"hermes-agent"})`, `agent/skill_utils.py:295`), never "seed nothing".
Control and its two commands belong to `maintain-hermes-skills`; do not duplicate them here.

**Rung 4 — is it an official *optional* skill rather than a bundled one?**
Signal: `list --source builtin` does not show it, but it is meant to come from upstream. `hermes skills
repair-official <name> [--restore]` backfills or restores official optional skills from the repo
source (`hermes_cli/skills_hub.py:1119-1138`); `--restore` moves any existing matching copy to a backup
directory before copying the official source, and prints both `Restored` and `Backfilled provenance`
lists.

## Traps worth stating outright

- **`hermes update` is not a skills-only command.** It pulls the latest git changes and reinstalls
  dependencies; the bundled-skills sync is one step of it. Use `hermes update --check` or `hermes
  update --plan` to stay read-only (measured `--help`: both described as read-only, `--plan` also lists
  every running service per profile and how each will be restarted).
- **A bundled skill is never silently overwritten.** If you need an edit to survive, edit the copy in
  `HERMES_HOME` — the sync will keep it and list it, instead of fighting you.
- **`reset` and the hub's `update --force` are opposite controls.** `reset` restores *tracking* for a
  bundled skill you edited (your content stays); `update --force` *discards* local edits for a
  hub-installed skill. Reaching for the wrong one either loses your work or leaves you stuck on
  `up_to_date` forever.
- **`list-modified` is the lookup, not a grep over `list`.** It reads the manifest via
  `list_user_modified_bundled_skills()`, so it is the only view that names exactly the set `hermes
  update` will skip.
