#!/usr/bin/env python3
"""Print install provenance for Hermes skills out of skills/.hub/lock.json. Read-only.

For each entry: source / identifier / trust / scan verdict + finding patterns / install and
update timestamps / pinned revision / recorded vs on-disk content hash / whether `update`
would skip it as locally edited / file count. Also tails skills/.hub/audit.log for that name.

Run it with the interpreter Hermes itself runs from -- a fresh `python3` is often 3.9 and dies
on `str | object` inside hermes_constants, and the managed toolchain has no site-packages for
this tree:

    PY=$(for p in ~/.hermes/installs/*/environments/*/venv/bin/python3; do
           "$p" -c 'import rich,httpx' 2>/dev/null && { echo "$p"; break; }; done)
    HERMES_HOME=~/.hermes PYTHONPATH=~/.hermes/hermes-agent "$PY" \
        lock-provenance.py [skill-name | --all]

HERMES_HOME must be set (default profile assumed when absent); SKILLS_DIR binds at import time.
No argument lists every hub-installed entry.
"""

import json
import os
import sys
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")
TREE = Path(os.environ.get("HERMES_AGENT_TREE") or HOME / "hermes-agent")
if str(TREE) not in sys.path:
    sys.path.insert(0, str(TREE))

HUB = HOME / "skills" / ".hub"
lock_path = HUB / "lock.json"
if not lock_path.is_file():
    sys.exit(f"no lock file at {lock_path} (wrong HERMES_HOME?)")

from hermes_cli.skills_hub import _has_local_edits  # noqa: E402
from tools.skills_guard import content_hash  # noqa: E402
from tools.skills_hub import SKILLS_DIR  # noqa: E402

installed = json.loads(lock_path.read_text()).get("installed", {})
args = [a for a in sys.argv[1:] if not a.startswith("-")]
if args:
    wanted = [a for a in args if a in installed]
    missing = [a for a in args if a not in installed]
    for m in missing:
        print(f"!! {m}: not a hub-installed skill (hand copy or nested child -> no lock entry)")
else:
    wanted = sorted(installed)

for name in wanted:
    e = installed[name]
    md = e.get("metadata") or {}
    prov = e.get("scan_provenance") or {}
    path = SKILLS_DIR / e.get("install_path", "")
    print("=" * 60)
    print(f"{name}")
    print(f"  source     : {e.get('source')}   trust: {e.get('trust_level')}")
    print(f"  identifier : {e.get('identifier')}")
    print(f"  verdict    : {e.get('scan_verdict')}  "
          f"findings: {sorted({f.get('pattern_id') for f in prov.get('findings', [])})}")
    print(f"  installed  : {e.get('installed_at')}   updated: {e.get('updated_at')}")
    print(f"  revision   : {md.get('source_revision')}")
    print(f"  source_url : {md.get('source_url')}")
    print(f"  files      : {len(e.get('files', []))} recorded")
    print(f"  on disk    : {path}  dir={path.is_dir()}")
    recorded = e.get("content_hash", "")
    print(f"  hash       : recorded {recorded or '<none>'}")
    try:
        ondisk = content_hash(path) if path.is_dir() else "<missing>"
    except Exception as exc:  # noqa: BLE001 - a probe should not die on one bad entry
        ondisk = f"<error: {exc}>"
    print(f"  hash       : on-disk  {ondisk}")
    print(f"  local_edits: {_has_local_edits(e)}   "
          f"(True => `update` prints 'you have local edits' and skips; --force wipes them)")
    print("  check says : run `hermes skills check {}` -- blind to local edits".format(name))

log = HUB / "audit.log"
if log.is_file():
    lines = [ln for ln in log.read_text().splitlines() if any(w in ln for w in wanted)]
    print("=" * 60)
    print(f"audit timeline ({log}):")
    for ln in lines or ["  (no lines for these names)"]:
        print(f"  {ln}")
