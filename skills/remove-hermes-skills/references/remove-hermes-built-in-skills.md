# Removing bundled (built-in) skills

Bundled skills are the one kind with **no uninstall**: they are not hub entries, and
`hermes skills uninstall <name>` answers `Error: '<name>' is not a hub-installed skill (may be a builtin)`
for every one of them. Their bookkeeping is the hash manifest
`<home>/skills/.bundled_manifest` (`name:hash` lines), and removing them is a **filesystem** operation,
not a registry one.

Two independent levers hide behind "delete this bundled skill", and conflating them is what makes a
deletion look like it failed or like it keeps coming back:

- **should this profile receive them at all** — the marker file `<home>/.no-bundled-skills`
  (`hermes skills opt-out` / `opt-in`); while it exists every seeding path
  (CLI/TUI/dashboard start, `hermes gateway`, `hermes update`, profile create) seeds only
  `ESSENTIAL_SKILLS = frozenset({"hermes-agent"})`;
- **should these copies exist on disk** — deletion (`opt-out --remove`, or `rm -rf`).

The two deletion routes then differ in exactly one way, and it decides the route:

| Route | Deletes | Its manifest entry | Back after `hermes skills opt-in --sync`? |
|---|---|---|---|
| `hermes skills opt-out --remove -y` | every **pristine** bundled copy, in one shot | **dropped** | **yes** — re-enters as a new skill |
| `rm -rf <home>/skills/<category>/<name>` | that one directory | **kept** | **no** — a deleted skill is never re-added |

Both rows were measured on 2026-09-30 in a throwaway `HERMES_HOME` seeded with the code root's
58-skill set (`hermes skills opt-in --sync` → `Re-seeded 58 bundled skill(s)`).

## The removal ladder — walk it top-down, drop a rung only on its signal

Ranking criterion: **least maintenance and the most complete result** — "gone now" *and* "does not come
back by itself", without hand-editing the manifest.

**Rung 1 — `hermes skills opt-out --remove -y` for the whole set.** Use it when several or all bundled
skills should go, or when the profile should stop receiving them ever. You get the marker *and* the
deletion, in one command. Measured output (58 seeded, 1 edited by hand, 1 hand-copied local skill and
1 hub skill also present):

```
Opted out of bundled skills. Future install / update / sync runs will not seed bundled skills into this profile.
Marker: <home>/.no-bundled-skills

Will remove 57 unmodified bundled skill(s):
airtable, apple-notes, …, xurl, youtube-content
Keeping 1 (user-modified or non-bundled).
Removed 57 pristine bundled skill(s); kept 1.
Removed: airtable, apple-notes, …, xurl, youtube-content
```

What survived on disk: the **edited** bundled copy (`grounded-citations`), the **hand-copied** local
directory, and the **hub-installed** skill — 3 `SKILL.md` files left out of 61. So the blast radius is
exactly "pristine bundled copies". The first list block is a free dry run — read it before confirming.

Semantics, from `tools/skills_sync_bundled_ops.py:159-192` (quoted from source): it iterates the
**manifest**, and per name skips a copy that is `user-modified (kept)` or has
`no bundled source (removed upstream)`; a name whose directory is already gone has its stale entry
dropped silently and is counted in neither `removed` nor `skipped`; `--remove` also writes the manifest
back, so the removed names lose their entries and a later `opt-in` re-seed treats them as new.

Drop signal: you want **one** skill gone and the rest still seeded → rung 2. Or the copy is edited and
the edits must survive *and* the skill must not be re-seedable → see the trap list below.

Two things to say out loud before running it:

- it deletes `hermes-agent` too (measured: it is in the `Removed:` list). `ESSENTIAL_SKILLS` protects it
  from being *disabled*, not from being deleted; `hermes skills opt-in --sync` puts it back;
- it leaves the category directories behind — measured after the run: `devops/` and
  `software-development/` were empty shells. Cosmetic;
  `find <home>/skills -mindepth 1 -type d -empty` lists them.

**Rung 2 — `rm -rf <home>/skills/<category>/<name>` for one skill.** Use it when exactly one bundled
skill should go and the profile should keep receiving the others. It is durable in the direction people
care about — the sync's own contract is *user-DELETED skills are not re-added*
(`tools/skills_sync.py:2-7`), and measured:

```
$ rm -rf <home>/skills/productivity/notion
$ hermes skills list --source builtin | grep -c '^│ notion'     # 0 rows
$ hermes skills list --source builtin | tail -1                 # … 57 builtin …   (was 58)
$ grep -c '^notion:' <home>/skills/.bundled_manifest            # 1 — the entry stays
$ hermes skills opt-in --sync
Re-seeded 0 bundled skill(s).
$ test -d <home>/skills/productivity/notion && echo RE-ADDED || echo "NOT re-added"
NOT re-added
```

The row and the footer count both track the live directory, so the removal is visible immediately; only
the manifest keeps the name. Drop signal for going *up* to rung 1: the name must not be restorable by
the recovery ladder below.

**Rung 3 — official *optional* skills: use the hub, not any of this.** A skill that is meant to come
from upstream but is not in `list --source builtin` is an optional skill, and it *is* a hub entry
(`Source: official`, identifier `official/<category>/<name>`). Measured end to end in a sandbox:

```
$ hermes skills install excalidraw -y
Installed: creative/excalidraw
Files: SKILL.md, references/examples.md, references/colors.md, references/dark-mode.md, scripts/upload.py
      # lock: source=official, identifier=official/creative/excalidraw, install_path=creative/excalidraw
$ hermes skills uninstall excalidraw -y
Uninstalled 'excalidraw' from creative/excalidraw
```

So for these, the ordinary hub removal applies (`references/remove-hermes-skill-sh-skills.md`), and
`hermes skills repair-official <name> [--restore]` is what backfills or restores them — details in the
sibling `update-hermes-skills` → `references/update-hermes-built-in-skills.md`. Do **not** `rm -rf` one:
it would clear the directory and leave a lock entry pointing at nothing.

## Getting a bundled skill back

The inverse ladder, and which rung it belongs to:

| You want | Command | Measured |
|---|---|---|
| the stock copy back, edits discarded | `hermes skills reset <name> --restore -y` | edited `box` → `Restored 'box' from bundled source.` + `Copied: box`, edit gone (`grep -c` → 0), `list-modified` empty |
| a copy you deleted by hand, back | `hermes skills reset <name> -y` — clearing the entry makes the following sync see it as new | deleted `notion` → `Cleared manifest entry for 'notion'. …` + `Copied: notion`, directory back |
| the whole bundled set, after `opt-out --remove` | `hermes skills opt-in --sync` | `Re-seeded 58 bundled skill(s).` — the deleted names come back (their entries were dropped) |
| the whole set, after `opt-out` without `--remove` | `hermes skills opt-in --sync` | copies were never touched; the marker was the only change |

`reset` on a name that is neither tracked nor bundled is the one form that fails, and its message
deliberately points at the hub path:

```
$ hermes skills reset <name that was never seeded>
Error: '<name>' is not a tracked bundled skill. Nothing to reset. (Hub-installed skills use `hermes skills uninstall`.)
```

(Measured. Note the same command on a *deleted but still tracked* name re-copies it — the two cases look
identical from the outside, so read `.bundled_manifest` first.)

## Traps

- **`hermes skills update` re-seeds new bundled skills but never re-adds a deleted one.** "It came back"
  therefore means one of: you ran `opt-in --sync` after an `opt-out --remove` (entries were dropped), or
  a *different* copy exists in another profile/home, or the skill you are looking at was the hub-installed
  or local kind all along.
- **The marker is per home, i.e. per profile.** `<HERMES_HOME>/.no-bundled-skills` — opting out of one
  profile does nothing for the others (measured: the file is written at the home root, not under `skills/`).
- **Opting out also disables the manifest-cleanup step** of the sync (`skipped_opt_out`), so stale
  manifest entries linger while the marker exists. Never read a manifest line as proof of a live copy;
  `hermes skills list --source builtin` is the live view.
- **The curator can remove bundled skills without you.** With `curator.prune_builtins: true` a retired
  skill moves to `<home>/skills/.archive/`, and emptying `.archive/` makes the loss permanent for that
  name. Diagnose with `hermes curator list-archived`; the store table and the recovery order are in the
  sibling `maintain-hermes-skills` →
  `references/maintain-hermes-skills-inventory-and-availability.md`.
- **`hermes skills list` counts live directories, not the manifest** — measured 58 → 57 after a
  hand-delete, while the manifest still held 58 names. A footer that disagrees with the manifest is the
  expected state for a deleted-but-tracked skill, not corruption.
- **Do not hand-edit `.bundled_manifest` to make a deletion "stick".** Rung 2 already sticks; the entry
  is what makes `reset <name>` able to bring the copy back, and rewriting it by hand also moves the
  `user-modified` baseline the sync compares against.
