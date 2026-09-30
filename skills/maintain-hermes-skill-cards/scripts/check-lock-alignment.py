#!/usr/bin/env python3
"""Audit one profile's hub lock for the three strings that must agree.

The Skills page folds a catalog row into an installed skill only when BOTH hold:

  * the lock entry's ``identifier`` matches the catalog row's computed
    installIdentifier (``skillCatalogInstallIdentifier()``), and
  * ``installedByName.get(record.name)`` hits a local skill of provenance
    ``hub`` -- where ``record.name`` is the lock entry's KEY.

A third string must equal that same key too: the last segment of
``install_path`` (``_normalize_lock_install_path`` / ``_resolve_lock_install_path``
in ``tools/skills_hub_install.py``), otherwise ``hermes skills check`` reports
``invalid_install`` and hub updates stop silently. A ClawHub install routinely
arrives with the registry slug as key + directory while the skill declares a
different ``name:`` in SKILL.md, which is what leaves one skill rendering as two
rows (a local one plus the catalog one).

Run from the hermes source tree, with the install's own venv python:

  cd <install>/hermes-agent
  HERMES_HOME=<home> <install>/environments/<id>/venv/bin/python \
      scripts/check-lock-alignment.py [skill ...]

Read-only: prints one row per lock entry (or per named skill) plus the fix
commands for any entry whose strings disagree. Run it again after every
``hermes skills install`` / ``update`` of that skill -- both rewrite the entry
by the registry slug and silently undo a hand alignment.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys


def dir_exists_note(path: str, home: pathlib.Path) -> bool:
    """True when the recorded install_path is a real directory under this home's skills tree."""
    return bool(path) and (home / "skills" / path).is_dir()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    ap.add_argument("names", nargs="*", help="skill names to audit; default = every lock entry")
    ap.add_argument(
        "--home",
        default=os.environ.get("HERMES_HOME") or str(pathlib.Path.home() / ".hermes"),
        help="profile home to audit (the helpers below read $HERMES_HOME, not this flag)",
    )
    args = ap.parse_args()

    home = pathlib.Path(args.home).expanduser()
    os.environ["HERMES_HOME"] = str(home)
    sys.path.insert(0, str(pathlib.Path.cwd()))

    from hermes_cli.web_server_profiles import _installed_hub_identifiers
    from tools.skill_usage import provenance
    from tools.skills_hub_install import _resolve_lock_install_path
    from tools.skills_tool import _find_all_skills

    lock_path = home / "skills" / ".hub" / "lock.json"
    if not lock_path.is_file():
        print(f"no hub lock at {lock_path}")
        return 1
    installed = (json.loads(lock_path.read_text()).get("installed") or {})

    skills = {s["name"]: provenance(s["name"]) for s in _find_all_skills(skip_disabled=True)}
    payload = _installed_hub_identifiers(None)  # {identifier: {name, trust_level, scan_verdict}}

    wanted = set(args.names)
    print(f"home: {home}")
    print(f"{'lock key':26} {'record.name':26} {'prov':7} {'fold':4} {'path check':9} dir  identifier")
    fixes: list[tuple[str, str, str, str]] = []
    for key, entry in installed.items():
        ident = entry.get("identifier", "")
        path = entry.get("install_path", "")
        record_name = payload.get(ident, {}).get("name", key)
        if wanted and key not in wanted and record_name not in wanted:
            continue

        prov = skills.get(record_name, "missing")
        fold = prov == "hub"
        try:
            accepted = bool(_resolve_lock_install_path(path, key))
            check = "ok" if accepted else "EMPTY"
        except Exception as exc:  # ValueError -> the invalid_install status
            check = "INVALID"
            print(f"  ! _resolve_lock_install_path({path!r}, {key!r}) -> {type(exc).__name__}: {exc}")
        dir_exists = bool(path) and (home / "skills" / path).is_dir()

        print(
            f"{key:26} {record_name:26} {prov:7} {'yes' if fold else 'NO':4} "
            f"{check:9} {'yes' if dir_exists else 'NO':4} {ident}"
        )
        if not (fold and check == "ok" and dir_exists and key == record_name):
            fixes.append((key, record_name, path, ident))

    if not fixes:
        print("\nall lock entries agree: key == record.name == install_path last segment")
        return 0

    print("\ndisagreeing entries -- back up the lock, then:")
    for key, record_name, path, ident in fixes:
        target = record_name if record_name != "missing" else key
        if key != target:
            print(f"  mv {home}/skills/{path} {home}/skills/{target}")
            print(f"    lock: rename installed key {key!r} -> {target!r}; install_path {path!r} -> {target!r}")
        if not dir_exists_note(path, home):
            print(f"    lock: install_path {path!r} has no directory -> orphan; 'hermes skills uninstall {target}'")
        print(f"    lock: identifier {ident!r} -> the catalog form for that row (e.g. 'clawhub/@owner/slug')")
        print(f"    then: HERMES_HOME={home} hermes skills check {target}   # expect up_to_date, not invalid_install")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
