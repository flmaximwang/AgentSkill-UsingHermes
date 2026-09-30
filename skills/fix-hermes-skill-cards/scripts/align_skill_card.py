#!/usr/bin/env python3
"""Align a hub-installed skill's lock record with the catalog row the UI matches on.

Fixes Skills & Tools page symptoms: duplicate "Hub" card, source shown as "Hub"
instead of ClawHub, or `invalid_install` after a hand-edited lock.

    align_skill_card.py <profile_home> <skill-name> [--apply] [--identifier X]

<profile_home>   ~/.hermes (default profile) or ~/.hermes/profiles/<name>
<skill-name>     the name the Skills page shows = SKILL.md frontmatter `name:`

Dry run by default. --apply backs the lock up, renames the skill directory when
needed, and rewrites the lock key / install_path / identifier. Stdlib only; the
catalog snapshot is downloaded once and cached next to the profile.
"""
import argparse
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

SNAPSHOT = "https://nousresearch.github.io/hermes-agent/docs/api/skills.json"


def frontmatter_name(skill_md: Path):
    for raw in skill_md.read_text(encoding="utf-8", errors="replace").splitlines()[:40]:
        line = raw.strip().lstrip("\ufeff")
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("'\"")
        if line == "---" and raw.strip() != "---":
            break
    return None


def ui_install_identifier(row: dict):
    """apps/shared/src/catalog-install.ts:9"""
    if row.get("installIdentifier"):
        return row["installIdentifier"]
    ident = row.get("identifier") or ""
    source = (row.get("source") or "").lower()
    if not ident:
        if source == "built-in":
            return None
        return f"official/{row['name']}" if source == "optional" else row["name"]
    if source == "clawhub" and not ident.startswith("clawhub/"):
        return f"clawhub/{ident}"
    return ident


def catalog_rows(profile: Path, name: str):
    cache = profile / "cache" / "scratch" / "catalog-skills.json"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        print(f"  downloading catalog snapshot (~63 MB) -> {cache}")
        with urllib.request.urlopen(SNAPSHOT, timeout=180) as resp, cache.open("wb") as out:
            shutil.copyfileobj(resp, out)
    rows = json.loads(cache.read_text())
    target = name.lower()
    return [r for r in rows if isinstance(r, dict) and str(r.get("name", "")).lower() == target]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("profile_home")
    ap.add_argument("skill_name")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--identifier", help="override the identifier instead of reading the snapshot")
    args = ap.parse_args()

    profile = Path(os.path.expanduser(args.profile_home))
    lock_path = profile / "skills" / ".hub" / "lock.json"
    skills_dir = lock_path.parent.parent
    if not lock_path.is_file():
        sys.exit(f"no lock file at {lock_path}")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    installed = lock.get("installed", {})

    # Find the entry by lock key first, then by the name its SKILL.md declares
    # (the broken state IS a key/frontmatter mismatch, so key lookup alone fails).
    want = args.skill_name.lower()
    key = next((k for k in installed if k.lower() == want), None)
    if key is None:
        for k, e in installed.items():
            md = skills_dir / e.get("install_path", k) / "SKILL.md"
            if md.is_file() and (frontmatter_name(md) or "").lower() == want:
                key = k
                break
    if key is None:
        sys.exit(f"no lock entry for {args.skill_name!r} in {lock_path}")
    entry = installed[key]
    old_path = entry.get("install_path", key)
    skill_md = skills_dir / old_path / "SKILL.md"
    if not skill_md.is_file():
        sys.exit(f"{skill_md} missing — orphaned entry; run: hermes skills uninstall {key}")

    ui_name = frontmatter_name(skill_md) or key
    identifier = args.identifier
    if not identifier:
        rows = catalog_rows(profile, ui_name)
        rows.sort(key=lambda r: (str(r.get("source", "")).lower() != "clawhub",))
        if not rows:
            sys.exit(f"no catalog row named {ui_name!r} — pass --identifier explicitly")
        identifier = ui_install_identifier(rows[0])
    parent = str(Path(old_path).parent)
    new_path = ui_name if parent == "." else f"{parent}/{ui_name}"

    print(f"lock key      : {key}  ->  {ui_name}")
    print(f"install_path  : {old_path}  ->  {new_path}")
    print(f"identifier    : {entry.get('identifier')}  ->  {identifier}")
    if not args.apply:
        print("dry run — rerun with --apply")
        return

    backup = lock_path.with_name(lock_path.name + f".bak-align-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(lock_path, backup)
    if new_path != old_path:
        (skills_dir / new_path).parent.mkdir(parents=True, exist_ok=True)
        os.rename(skills_dir / old_path, skills_dir / new_path)
    entry["install_path"] = new_path
    entry["identifier"] = identifier
    installed[ui_name] = entry
    if key != ui_name:
        del installed[key]
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"applied. backup: {backup}")
    print(f"verify: HERMES_HOME={profile} hermes skills check {ui_name}")


if __name__ == "__main__":
    main()
