#!/usr/bin/env python3
"""Survey a multi-project root: presence matrix, item frequencies, record-folder types.

Writes nothing; prints three reports. Run this before writing any organisation spec so the
rules cite counts instead of impressions.

  PRESENCE   one row per sibling project directory, listing which candidate top-level items exist
  FREQUENCY  how many projects actually carry each item (the claimed-vs-actual check)
  RECORDS    folders under --record-root classified by name pattern; a folder counts as a record
             only when it holds a note named after itself

Examples
  python3 survey-layout.py /Users/org_zsqlab/Obsidian
  python3 survey-layout.py ~/repos/monorepo --candidates pipelines,summary,docs
"""

import argparse
import collections
import glob
import os
import re

DEFAULT_CANDIDATES = (
    "Records,Logs,Projects,Protocols,Dashboard,Reports,Inventory,Templates,Toolbox,"
    "Configurations,Archive,Snippets,Calender,Tasks,Home,QAs,Memos,Pipelines,Skills,"
    "Cheatsheet,SnapGene,Data,Backup,Migration,Lookup,Widgets,Rules,Timer,Samples"
).split(",")
DEFAULT_RECORD_ROOT = "Logs"
DEFAULT_RECORD_DEPTH = 5  # levels to descend below --record-root before stopping


def projects_of(root):
    return sorted(d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d))


def presence_matrix(projects, candidates):
    for p in projects:
        present = [c for c in candidates if os.path.exists(os.path.join(p, c))]
        print(f"  {os.path.basename(p)[:44]:46s} {len(present):2d}  {' '.join(present)}")


def frequencies(projects, candidates):
    counts = collections.Counter()
    for p in projects:
        for c in candidates:
            if os.path.exists(os.path.join(p, c)):
                counts[c] += 1
        for name in os.listdir(p):  # loose top-level notes/dirs worth naming in the spec
            if name.endswith(".md") and name != "README.md":
                counts[name] += 1
    total = len(projects)
    for name, n in counts.most_common():
        print(f"  {n:3d}/{total}  {name}")


def classify(name):
    if re.match(r"^\d{6,}$", name):
        return "TIMESTAMP (asset dump)"
    m = re.match(r"^(.*?)-(\d+)$", name)
    if m:
        return f"TYPE: {m.group(1).strip()}"
    if re.match(r"^\(?\d{4}", name):
        return "DATE-TITLE"
    return f"OTHER: {name[:40]}"


def record_types(projects, record_root, max_depth):
    kinds = collections.Counter()
    for p in projects:
        base = os.path.join(p, record_root)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            rel = os.path.relpath(root, base)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if depth >= max_depth:
                dirs[:] = []
                continue
            if root == base:
                continue
            name = os.path.basename(root)
            if f"{name}.md" in files:  # a record carries a note named after its own folder
                kinds[classify(name)] += 1
            elif re.match(r"^\d{6,}$", name) and files:
                kinds["TIMESTAMP (asset dump)"] += 1
    for kind, n in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {n:4d}  {kind}")


def main():
    parser = argparse.ArgumentParser(
        description="Survey a multi-project root: presence matrix, frequencies, record types.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("root", help="directory holding sibling project directories")
    parser.add_argument(
        "--candidates",
        default=",".join(DEFAULT_CANDIDATES),
        help="comma-separated top-level item names to test in every project",
    )
    parser.add_argument(
        "--record-root",
        default=DEFAULT_RECORD_ROOT,
        help="subdirectory whose dated subfolders are the records",
    )
    parser.add_argument(
        "--record-depth",
        type=int,
        default=DEFAULT_RECORD_DEPTH,
        help="levels (count) to descend below --record-root before stopping",
    )
    args = parser.parse_args()

    projects = projects_of(args.root)
    if not projects:
        raise SystemExit(f"no project directories under {args.root}")
    candidates = [c for c in args.candidates.split(",") if c]

    print(f"# root: {args.root}  (projects: {len(projects)})\n")
    print("# PRESENCE")
    presence_matrix(projects, candidates)
    print("\n# FREQUENCY (projects carrying the item)")
    frequencies(projects, candidates)
    print(f"\n# RECORDS under {args.record_root}/ (max depth {args.record_depth})")
    record_types(projects, args.record_root, args.record_depth)


if __name__ == "__main__":
    main()
