#!/usr/bin/env python3
"""Read-only probe: would `hermes skills install` accept this install target?

Usage:
    python3 probe_install_target.py <skill-name> <category> [<category> ...]
    python3 probe_install_target.py grill-me software-development productivity

Prints OK/BLOCKED per (profile home, category) pair. Writes nothing, installs
nothing. Category "" means the flat target <skills>/<name>.

It calls the REAL guard (tools/skills_hub_install.py::_check_install_target)
when a Hermes source tree is found, so the verdict cannot drift from shipped
behaviour; otherwise it falls back to the same two path-level conditions.

Mirrors _check_install_target, which is the code that produces:
    Refusing to install into '<dir>': it is an existing skill directory, not a
    category. Choose a different category.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import sys


def skills_dirs() -> list[pathlib.Path]:
    """Active profile's skills dir (from HERMES_HOME) plus the default one."""
    cands = []
    home = os.environ.get("HERMES_HOME", "")
    if home:
        cands.append(pathlib.Path(home) / "skills")
    cands.append(pathlib.Path(os.environ.get("HOME", "~")) / ".hermes" / "skills")
    seen, out = set(), []
    for c in cands:
        if c.exists() and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def find_src() -> str | None:
    """Best-effort Hermes source tree (the dir holding tools/skills_hub_install.py)."""
    env = os.environ.get("HERMES_SRC")
    starts = [env] if env else []
    which = shutil.which("hermes")
    if which:
        starts.append(os.path.realpath(which))
    for start in starts:
        p = pathlib.Path(start)
        for anc in [p, *list(p.parents)[:6]]:
            if (anc / "tools" / "skills_hub_install.py").is_file():
                return str(anc)
    return None


def path_check(skills_root: pathlib.Path, rel: str) -> str:
    """Path-level replica of _check_install_target (used when src is absent)."""
    target = skills_root / rel
    ancestor = target.parent
    while ancestor != skills_root:
        if not ancestor.is_relative_to(skills_root):
            break
        if (ancestor / "SKILL.md").is_file():
            return f"BLOCKED (ancestor is a skill dir): {ancestor}"
        ancestor = ancestor.parent
    if not target.exists():
        return "OK (fresh install)"
    if not target.is_dir():
        return "BLOCKED (name exists and is not a directory)"
    if not (target / "SKILL.md").exists():
        # ponytail: ignores vendored-path exclusions; may over-report for
        # reference-only SKILL.md files. Fine for a diagnostic.
        kids = sorted(
            p.name
            for p in target.iterdir()
            if p.is_dir() and not p.name.startswith(".") and any(p.rglob("SKILL.md"))
        )
        if kids:
            return f"BLOCKED (category bucket holds {len(kids)} skill(s): {', '.join(kids)})"
    return "OK (would overwrite an existing install)"


def real_checker():
    src = find_src()
    if not src:
        return None
    sys.path.insert(0, src)
    try:
        import tools.skills_hub as hub
        from tools.skills_hub_install import _check_install_target
    except Exception:
        return None
    return hub, _check_install_target


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    name, categories = argv[0], argv[1:]
    real = real_checker()
    mode = "real _check_install_target" if real else "path-level fallback (no source tree found)"
    print(f"guard: {mode}")
    for root in skills_dirs():
        print(f"=== {root} ===")
        for cat in categories:
            rel = f"{cat}/{name}" if cat else name
            if real:
                hub, check = real
                hub._skills_dir = lambda p=root: p
                try:
                    check(root / rel)
                    verdict = "OK (would install)"
                except ValueError as exc:
                    verdict = f"BLOCKED ({exc})"
            else:
                verdict = path_check(root, rel)
            print(f"  category={cat!r:24} target={rel:34} -> {verdict}")
    return 0


def selftest() -> int:
    """Smallest thing that fails if the fallback logic breaks."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "hybrid").mkdir()
        (root / "hybrid" / "SKILL.md").write_text("x")
        (root / "hybrid" / "inner").mkdir()
        (root / "hybrid" / "inner" / "SKILL.md").write_text("x")
        (root / "clean").mkdir()
        (root / "clean" / "other").mkdir()
        (root / "clean" / "other" / "SKILL.md").write_text("x")

        assert path_check(root, "clean/new").startswith("OK"), "clean bucket must pass"
        assert path_check(root, "hybrid/new").startswith("BLOCKED"), "hybrid must block"
        assert path_check(root, "new").startswith("OK"), "flat install must pass"
        assert "category bucket" in path_check(root, "clean"), "bucket overwrite must block"
        (root / "clean" / "new").mkdir()
        (root / "clean" / "new" / "SKILL.md").write_text("x")
        assert path_check(root, "clean/new").startswith("OK"), "existing install is overwritable"
    print("selftest OK")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    raise SystemExit(selftest() if args[:1] == ["--selftest"] else main(args))
