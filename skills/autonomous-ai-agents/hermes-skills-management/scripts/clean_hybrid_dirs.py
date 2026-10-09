#!/usr/bin/env python3
"""Make HYBRID skill buckets clean: <skills>/<H>/SKILL.md -> <skills>/<H>/<H>/SKILL.md

Usage:
    python3 clean_hybrid_dirs.py [--skills DIR]     # dry run (default)
    python3 clean_hybrid_dirs.py --apply            # perform the moves
    python3 clean_hybrid_dirs.py --selftest

Why: a bucket that holds its own SKILL.md is an "existing skill directory" to
`tools/skills_hub_install.py::_check_install_target`, which refuses to nest any
new skill inside it — so no catalog skill whose category is that name can ever
be installed there. Nesting the umbrella keeps it loadable (bare-name lookup
matches directory OR frontmatter name at any depth) and gives the bucket a real
category (a skill is only labelled with one when its path under <skills> has
>= 3 parts; see tools/skills_tool.py::_get_category_from_path).

Dry run by default and nothing is backed up for you: tar the buckets first
(`tar czf "$HERMES_HOME/cache/scratch/hybrid_backup_$(date +%Y%m%d-%H%M%S).tgz" <H> ...`).
Bucket-owned files (category README.md, a nested skills/ subcategory, .DS_Store)
are left where they are; only the umbrella's SKILL.md and its own support dirs move.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil

SUPPORT = ("references", "scripts", "templates", "assets")


def skills_root(explicit: str | None = None) -> pathlib.Path:
    """<active profile>/skills, or --skills. HERMES_HOME wins, else ~/.hermes."""
    if explicit:
        return pathlib.Path(explicit).expanduser()
    home = os.environ.get("HERMES_HOME") or str(pathlib.Path.home() / ".hermes")
    return pathlib.Path(home) / "skills"


def hybrids(root: pathlib.Path):
    """[(bucket, inner, [paths to move])] for every bucket holding its own SKILL.md."""
    out = []
    for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if not (d / "SKILL.md").is_file():
            continue
        inner = d / d.name
        moves = [d / "SKILL.md"] + [d / s for s in SUPPORT if (d / s).is_dir()]
        out.append((d, inner, moves))
    return out


def apply_moves(bucket: pathlib.Path, inner: pathlib.Path, moves: list) -> str:
    if inner.exists():
        return f"SKIP {bucket.name}: {inner} already exists"
    inner.mkdir()
    for src in moves:
        shutil.move(str(src), str(inner / src.name))
    return f"{bucket.name}/ -> {bucket.name}/{bucket.name}/   moved: {', '.join(p.name for p in moves)}"


def selftest() -> int:
    """Smallest thing that fails if the plan/apply logic breaks."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "hyb" / "references").mkdir(parents=True)
        (root / "hyb" / "SKILL.md").write_text("x")
        (root / "hyb" / "references" / "a.md").write_text("x")
        (root / "hyb" / "README.md").write_text("bucket-level, stays")
        (root / "clean" / "other").mkdir(parents=True)
        (root / "clean" / "other" / "SKILL.md").write_text("x")

        found = hybrids(root)
        assert [b.name for b, _i, _m in found] == ["hyb"], f"only the hybrid bucket counts: {found}"
        bucket, inner, moves = found[0]
        assert [p.name for p in moves] == ["SKILL.md", "references"]
        apply_moves(bucket, inner, moves)
        assert (inner / "SKILL.md").is_file() and (inner / "references" / "a.md").is_file()
        assert not (bucket / "SKILL.md").exists(), "root SKILL.md must be gone"
        assert (bucket / "README.md").is_file(), "bucket-owned files must stay"
        assert hybrids(root) == [], "bucket is clean after the move"
        assert apply_moves(bucket, inner, moves).startswith("SKIP"), "re-run must be a no-op"
    print("selftest OK")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--skills", default=None, help="skills root (default: $HERMES_HOME/skills)")
    ap.add_argument("--apply", action="store_true", help="perform the moves (default: dry run)")
    ap.add_argument("--selftest", action="store_true", help="run the built-in self-check and exit")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()

    root = skills_root(args.skills)
    if not root.is_dir():
        print(f"no skills dir at {root}")
        return 2
    print(f"skills root: {root}")
    found = hybrids(root)
    if not found:
        print("no hybrid buckets — every bucket is already clean")
        return 0
    for bucket, inner, moves in found:
        rel = f"{bucket.name}/ -> {bucket.name}/{bucket.name}/   moves: {', '.join(p.name for p in moves)}"
        print(f"  {'DO  ' if args.apply else 'PLAN'} {rel}")
        if args.apply:
            print(f"        {apply_moves(bucket, inner, moves)}")
    print(f"{len(found)} hybrid bucket(s){'' if args.apply else ' (dry run — re-run with --apply)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
