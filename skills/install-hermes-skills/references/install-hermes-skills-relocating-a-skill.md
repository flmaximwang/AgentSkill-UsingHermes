# Moving an installed skill to another category

The request shapes: "删除 `<skill>` 并重新安装到 `<category>` category", "move this skill to another
category", "this belongs under `<cat>`" — anything whose net effect is that `install_path` changes while
the tree keeps what it had locally.

**A move is uninstall + install — there is no move verb, and `update` cannot do it.** `--category` is read
at install time only, and a surviving lock entry cannot hand its path over: `update` re-fetches the
*recorded* source + identifier and leaves `install_path` where it stands (sibling `update-hermes-skills`).
So it is the same two commands as a bloodline change (`SKILL.md` § Replacing an installed skill with a
better bloodline), with a different second half — the **same** identifier, and the category re-supplied.

## Recipe

1. **Read the entry out of the lock** (`skills/.hub/lock.json` → `installed.<key>`), never off the name
   `hermes skills list` prints: `source`, `identifier`, `install_path`, `trust_level`, `scan_verdict`,
   `content_hash`, `metadata.source_revision`. `scripts/lock-provenance.py` prints all of it plus
   `local_edits` in one call.
2. **Audit the local delta before anything is removed.** `uninstall` has no local-edit guard, `-y` skips
   the only prompt, and whatever the tree carries that upstream does not is what dies. The recipe — fetch
   the upstream tree at the recorded revision and `diff -r` it against the installed copy — is
   `remove-hermes-skills` § Before you remove; report the delta before deleting anything.
3. **Back up twice — they cover different things.** `hermes skills snapshot export <file>` records lock
   entries and no files at all; a `tar` of the installed tree is the only thing that captures nested and
   self-authored content. Keep both outside the profile.
4. **Probe the move in a throwaway home first** — mirrored `.env` **and** `config.yaml`, a fresh directory
   name, the real command including `--category`. Then compare hashes: **the probe's `content_hash` equal
   to the installed one proves the same revision, so the move is a pure relocation.** A different hash
   means the route pulled newer upstream content — that is an update wearing a move's clothes, and the user
   asked for a move, so say so instead of shipping it silently.
5. **Remove by the lock key**: `hermes skills uninstall <key> -y`.
6. **Install with the category re-supplied**, output redirected to a log file rather than piped through
   `head` / `tail` (SKILL.md § Non-negotiables):
   `hermes skills install "<identifier>" --category <cat> --force -y > <home>/<name>-install.log 2>&1`.
   `--force` is required whenever trust × verdict says so — `community` + `caution` is exactly that case,
   and a bundle of large assets is *structurally* cautioned (oversized files, file count), which is not a
   judgement about its content.
7. **Restore whatever the bundle owned locally**, at the same relative path inside the new tree. A
   self-authored child skill has no separate identity — it went with the bundle — so the reinstall returns
   only upstream's files. State plainly that restoring it re-creates a local edit inside a hub bundle,
   which makes `update` skip the whole skill unless `--force`.

## Prove it moved (three checks)

```bash
python3 -c "import json,pathlib; e=json.loads((pathlib.Path.home()/'.hermes/skills/.hub/lock.json').read_text())['installed']['<key>']; print(e['install_path'], e['content_hash'], len(e['files']))"
hermes skills check <key>          # up_to_date
python3 -c "import pathlib; print([l for l in (pathlib.Path.home()/'.hermes/skills/.hub/audit.log').read_text().splitlines() if '<name>' in l])"
```

- `install_path` is the new category path, `content_hash` is unchanged, `files` still holds the same count.
- `audit.log` carries one `UNINSTALL <name> <source>:<trust> n/a user_request` line followed by one
  `INSTALL <name> <source>:<trust> <verdict> <hash>` line; that pair, with different timestamps, is the
  move's timeline — and the only place the old and the new state are visible together.
- The old directory must be absent from `skills/`. `uninstall` prints
  `Uninstalled '<name>' from <install_path>` (relative to `skills/`), so read that line rather than assuming.
- In an already-running session the skill list keeps the old category until `/reload-skills` (or a new
  session) — an in-session listing is not evidence about disk.

## Facts that shape the report

- **One lock entry covers the whole bundle.** Sub-directories that carry their own `SKILL.md` are discovered
  as separate skills with `Source: local`, and they take the **parent's** category — so a category move
  shows up as several rows changing category while only one of them has a lock entry. Report the children
  too: they moved as a side effect nobody asked for (the measured case lives in
  `remove-hermes-skills` → `references/remove-hermes-skill-sh-skills.md`).
- **The recorded `content_hash` stays the upstream hash** while the on-disk tree hash differs — local noise
  such as `.DS_Store` and `__pycache__` is in the tree hash and never in the lock, which is what
  `local_edits: True` reports. Say what the delta is instead of reporting the flag.
- **Name a move as a move.** Same identifier, same revision, same hash, and only `install_path` different —
  otherwise it was an update and the report is wrong.

Measured (2026-09-30, session `20260930_164609_12e4ffd9`, `paper2agent` → `agent-evolution`): the probe's
`sha256:c20a6094082b688a` equalled the installed hash, 69 files on both sides, `audit.log` gained
`08:50:03Z UNINSTALL paper2agent skills.sh:community n/a user_request` then
`08:51:51Z INSTALL paper2agent skills.sh:community caution sha256:c20a6094082b688a`, and one self-authored
child (`paper2skill-delivery-checks/SKILL.md`) had to be restored by hand afterwards.
