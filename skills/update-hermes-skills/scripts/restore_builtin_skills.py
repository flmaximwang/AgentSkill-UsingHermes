#!/usr/bin/env python3
"""Restore bundled ("built-in") Hermes skills into one Hermes home.

After a manual ``rm -rf`` or a curator prune, a built-in is blocked from ever being
re-seeded by TWO records on disk:

  1. ``<home>/skills/.curator_suppressed`` -- curator-pruned built-ins are skipped by sync.
  2. ``<home>/skills/.bundled_manifest``   -- an entry whose directory is gone reads as
     "user deleted it", so sync skips it (by design: deleting a built-in must stick).

This script clears both records *only for the built-ins that are missing from disk*,
then calls the real ``sync_skills()`` so the copies come back from the bundled source.

Usage (run with the Hermes checkout's venv python -- its code must import):
    <checkout>/venv/bin/python3 restore_builtin_skills.py --home ~/.hermes            # report only
    <checkout>/venv/bin/python3 restore_builtin_skills.py --home ~/.hermes --apply

Options:
    --home PATH       Hermes home (default profile: ~/.hermes; profile: ~/.hermes/profiles/<name>)
    --bundled PATH    bundled-skills source tree (default: ~/.hermes/hermes-agent/skills)
    --repo PATH       Hermes source checkout to import from (default: ~/.hermes/hermes-agent)
    --apply           actually clear the records and re-seed (default: dry run)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


def skill_names(root: Path) -> set[str]:
    """Directory names + frontmatter names of every skill under *root* (dot-dirs skipped)."""
    out: set[str] = set()
    if not root.is_dir():
        return out
    for md in root.rglob("SKILL.md"):
        rel = md.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        out.add(md.parent.name)
        try:
            head = md.read_text(encoding="utf-8", errors="ignore")[:400]
        except OSError:
            continue
        if m := re.search(r"^name:\s*(.+)$", head, re.M):
            out.add(m.group(1).strip().strip("\"'"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--home", required=True, help="Hermes home to repair")
    ap.add_argument("--bundled", default=str(Path.home() / ".hermes/hermes-agent/skills"),
                    help="bundled-skills source tree")
    ap.add_argument("--repo", default=str(Path.home() / ".hermes/hermes-agent"),
                    help="Hermes source checkout")
    ap.add_argument("--apply", action="store_true", help="clear records and re-seed")
    args = ap.parse_args()

    home = Path(args.home).expanduser()
    bundled = Path(args.bundled).expanduser()
    repo = Path(args.repo).expanduser()
    skills = home / "skills"

    # Env must be set BEFORE importing the runtime: its module-level home/bundled
    # constants are captured at import time.
    os.environ["HERMES_HOME"] = str(home)
    os.environ["HERMES_BUNDLED_SKILLS"] = str(bundled)
    sys.path.insert(0, str(repo))
    from tools.skills_sync import (_read_manifest, _read_suppressed_names, _write_manifest,
                                   sync_skills)

    if not skills.is_dir():
        print(f"no skills dir at {skills} -- refusing to touch anything")
        return 1
    if not bundled.is_dir():
        print(f"bundled source {bundled} does not exist -- nothing to restore from")
        return 1

    manifest = dict(_read_manifest())
    suppressed = set(_read_suppressed_names())
    on_disk = skill_names(skills)
    bundled_names = skill_names(bundled)

    missing = sorted(name for name in manifest if name not in on_disk)
    restorable = [name for name in missing if name in bundled_names]
    gone_upstream = [name for name in missing if name not in bundled_names]
    blocked_suppressed = [name for name in restorable if name in suppressed]

    print(f"home            : {home}")
    print(f"bundled source  : {bundled}")
    print(f"manifest-tracked: {len(manifest)}   on disk: {len(on_disk)}   missing: {len(missing)}")
    print(f"restorable      : {len(restorable)}")
    print(f"  of those, blocked by .curator_suppressed: {len(blocked_suppressed)}")
    print(f"gone upstream   : {len(gone_upstream)}  {gone_upstream}")
    if restorable:
        print("to restore      : " + ", ".join(restorable))

    if not args.apply:
        print("\nDRY RUN -- nothing changed. Re-run with --apply to restore.")
        return 0

    # 1) un-suppress exactly the names we are restoring (leave other prunes alone)
    if blocked_suppressed:
        remaining = sorted(suppressed - set(blocked_suppressed))
        (skills / ".curator_suppressed").write_text(
            "\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")
        print(f"\n.curator_suppressed: {len(suppressed)} -> {len(remaining)} entries")
    # 2) drop their manifest entries so sync treats them as new and copies them
    for name in restorable:
        manifest.pop(name, None)
    _write_manifest(manifest)

    # 3) re-seed
    result = sync_skills(quiet=True)
    print(f"sync: copied={len(result['copied'])} updated={len(result['updated'])} "
          f"skipped={result['skipped']} total_bundled={result['total_bundled']}")
    after = skill_names(skills)
    now_missing = [name for name in restorable if name not in after]
    print(f"on disk now: {len(after)} skills; still missing from the restore set: {now_missing}")
    return 0 if not now_missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
