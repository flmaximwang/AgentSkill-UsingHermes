#!/usr/bin/env python3
"""Bulk-load a skill repo's index (name + description only) into an agent context.

Usage:
    python3 skill-index.py <dir|owner/repo|git-url> [--out FILE] [--max-desc N] [--quiet]

Prints one line per skill: "<category>/<name>: <description>" plus a stats footer
(skills / raw files / index chars / est tokens / full bytes / ratio).

Nothing is installed and nothing touches the profile or the system prompt: this is plain
conversation data produced by reading files. Remote sources are shallow-cloned into the
Hermes scratch dir and reused on later runs.

Needs pyyaml; use the venv that has it:
    ~/.hermes/hermes-agent/venv/bin/python3 skill-index.py ...

The frontmatter MUST be parsed as YAML, not with a regex: `description: >-` is a folded
block scalar, and a regex captures the literal `>-` instead of the text.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

SCRATCH = pathlib.Path.home() / ".hermes" / "cache" / "scratch"


def resolve_source(src: str) -> tuple[pathlib.Path, str]:
    """Local dir as-is; owner/repo or URL -> shallow clone into the scratch dir (reused)."""
    p = pathlib.Path(src).expanduser()
    if p.is_dir():
        return p, str(p)
    url = src if "://" in src or src.startswith("git@") else f"https://github.com/{src}.git"
    name = url.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1]
    dest = SCRATCH / f"skillrepo-{name}"
    if not (dest / ".git").is_dir():
        SCRATCH.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", "-q", url, str(dest)], check=True)
    return dest, url


def frontmatter(path: pathlib.Path) -> dict:
    import yaml

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    try:
        data = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def category_of(fm: dict, rel: pathlib.Path) -> str:
    meta = fm.get("metadata")
    hermes = meta.get("hermes") if isinstance(meta, dict) else None
    cat = hermes.get("category") if isinstance(hermes, dict) else None
    if cat:
        return str(cat).strip()
    return rel.parts[0] if len(rel.parts) > 1 else "general"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("source", help="local dir, owner/repo, or git URL")
    ap.add_argument("--out", default="", help="also write the index to this file")
    ap.add_argument("--max-desc", type=int, default=110, help="truncate each description to N chars")
    ap.add_argument("--quiet", action="store_true", help="write to --out only, print stats")
    args = ap.parse_args()

    root, origin = resolve_source(args.source)
    rows, full_bytes, missing = [], 0, []
    for skill_md in sorted(root.rglob("SKILL.md")):
        if ".git" in skill_md.parts:
            continue
        fm = frontmatter(skill_md)
        name = str(fm.get("name") or "").strip()
        if not name:
            missing.append(str(skill_md.relative_to(root)))
            continue
        desc = " ".join(str(fm.get("description") or "").split())
        if len(desc) > args.max_desc:
            desc = desc[: args.max_desc - 1].rstrip() + "…"
        rel = skill_md.relative_to(root)
        rows.append((category_of(fm, rel), name, desc))
        full_bytes += skill_md.stat().st_size

    # Dedupe by skill name: snapshot copies of the same skill inflate the raw walk.
    unique: dict[str, tuple[str, str, str]] = {}
    for cat, name, desc in rows:
        unique.setdefault(name, (cat, name, desc))
    body = "\n".join(
        f"{cat}/{name}: {desc}" if desc else f"{cat}/{name}" for cat, name, desc in unique.values()
    )
    if args.out:
        pathlib.Path(args.out).expanduser().write_text(body + "\n", encoding="utf-8")
    if not args.quiet:
        print(body)
    chars = len(body)
    print(
        f"\n[skill-index] source={origin} skills={len(unique)} raw_files={len(rows)}"
        f" index_chars={chars} est_index_tokens~{chars // 2} full_skill_md_bytes={full_bytes}"
        f" est_full_tokens~{full_bytes // 4} ratio={chars / max(full_bytes, 1):.1%}",
        file=sys.stderr,
    )
    if missing:
        print(f"[skill-index] skipped (no name: in frontmatter): {', '.join(missing)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
