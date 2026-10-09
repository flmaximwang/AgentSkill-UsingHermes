#!/usr/bin/env python3
"""Verify a Hermes profile's SOUL.md through the real loader.

Eyeballing the file proves nothing: the loader scans context files for prompt-injection
patterns and head/tail-truncates anything over the char budget (70% head, 20% tail, 10%
marker), so an over-budget persona silently loses its newest rules from the middle.
This runs `agent.prompt_builder.load_soul_md()` and reports what the model will actually get.

Usage:
    python3 verify_soul.py --profile protein-designer
    python3 verify_soul.py --home /path/to/profile/home --context-length 1048576

Exit codes:
    0  loaded cleanly
    1  not loaded, blocked, or truncated
    2  could not import the loader (repo/venv not found)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROBE = r"""
import json, sys
from pathlib import Path
from agent.prompt_builder import load_soul_md, drain_truncation_warnings

home = Path(sys.argv[1])
ctx = int(sys.argv[2])
out = load_soul_md(context_length=ctx, home_override=home)
warnings = drain_truncation_warnings()
raw = (home / "SOUL.md")
raw_chars = len(raw.read_text(encoding="utf-8")) if raw.exists() else 0
print(json.dumps({
    "loaded": out is not None,
    "injected_chars": len(out or ""),
    "file_chars": raw_chars,
    "blocked": "BLOCKED" in (out or ""),
    "truncated": "truncated SOUL.md" in (out or ""),
    "warnings": warnings,
    "head": (out or "")[:120],
}))
"""


def profile_home(name: str) -> Path:
    """`~/.hermes/profiles/<name>`, or `~/.hermes` for the default profile."""
    root = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    if name in ("default", ""):
        return root
    return root / "profiles" / name


def find_repo(explicit: str | None) -> Path | None:
    """Locate the hermes-agent source checkout that owns the loader."""
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("HERMES_REPO"):
        candidates.append(Path(os.environ["HERMES_REPO"]).expanduser())
    root = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    candidates.append(root / "hermes-agent")
    for cand in candidates:
        if (cand / "agent" / "prompt_builder.py").is_file():
            return cand
    return None


def find_python(repo: Path) -> str:
    """Prefer the repo's own venv; the loader imports hermes-agent's dependencies."""
    for rel in ("venv/bin/python", ".venv/bin/python", "venv/Scripts/python.exe"):
        cand = repo / rel
        if cand.is_file():
            return str(cand)
    return sys.executable


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify a Hermes profile's SOUL.md through the real loader.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--profile", "-p", default="default", help="Profile name ('default' for ~/.hermes).")
    ap.add_argument("--home", default=None, help="Explicit profile home; overrides --profile.")
    ap.add_argument("--repo", default=None, help="Path to the hermes-agent source checkout.")
    ap.add_argument(
        "--context-length",
        type=int,
        default=1048576,
        help="Model context window in tokens; sets the dynamic char cap (units: tokens).",
    )
    args = ap.parse_args()

    home = Path(args.home).expanduser() if args.home else profile_home(args.profile)
    if not home.is_dir():
        print(f"ERROR: profile home not found: {home}", file=sys.stderr)
        return 1

    repo = find_repo(args.repo)
    if repo is None:
        print("ERROR: could not find the hermes-agent checkout (pass --repo).", file=sys.stderr)
        return 2

    proc = subprocess.run(
        [find_python(repo), "-c", PROBE, str(home), str(args.context_length)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout, end="")
        print(proc.stderr, end="", file=sys.stderr)
        return 2

    import json

    info = json.loads(proc.stdout.strip().splitlines()[-1])
    print(f"home:            {home}")
    print(f"file chars:      {info['file_chars']}")
    print(f"injected chars:  {info['injected_chars']}")
    print(f"loaded:          {info['loaded']}")
    print(f"blocked:         {info['blocked']}")
    print(f"truncated:       {info['truncated']}")
    if info["warnings"]:
        for w in info["warnings"]:
            print(f"warning:         {w}")
    print(f"head:            {info['head']!r}")

    ok = info["loaded"] and not info["blocked"] and not info["truncated"]
    print("RESULT: OK" if ok else "RESULT: PROBLEM — see flags above")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
