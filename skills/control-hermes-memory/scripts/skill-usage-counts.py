#!/usr/bin/env python3
"""Per-skill `skill_view` load counts for one profile (read-only).

Answers "was this skill ever actually loaded?". The skill name is parsed out of the JSON body of
each `skill_view` tool result, so a payload that was compacted cannot be attributed and lands in
the `?` bucket — those are loads of *some* skill, not evidence of none. Counts are per profile:
a skill can be loaded heavily in one profile and never in another.

    python3 scripts/skill-usage-counts.py                 # every skill in $HERMES_HOME/skills
    python3 scripts/skill-usage-counts.py respond to-     # only names matching any keyword

Stdlib only, so any python3 runs it. Other profiles: open
`<profile>/state.db` with `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` and run the same
query — never a writable connection into a profile you are not working in.
"""

import collections
import glob
import json
import os
import re
import sqlite3
import sys


def home():
    return os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")


def load_counts(db_path):
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    counts = collections.Counter()
    for row in db.execute("SELECT content FROM messages WHERE tool_name='skill_view'"):
        try:
            counts[json.loads(row["content"]).get("name", "?")] += 1
        except Exception:
            counts["?"] += 1
    return counts


def skill_names(skills_root):
    names = []
    for path in glob.glob(os.path.join(skills_root, "**", "SKILL.md"), recursive=True):
        text = open(path, encoding="utf-8", errors="replace").read()[:1500]
        match = re.search(r"^name:\s*(.+)$", text, re.M)
        names.append(match.group(1).strip() if match else os.path.basename(os.path.dirname(path)))
    return set(names)


def main():
    root = home()
    counts = load_counts(os.path.join(root, "state.db"))
    names = skill_names(os.path.join(root, "skills"))
    if len(sys.argv) > 1:
        names = {n for n in names if any(k in n for k in sys.argv[1:])}
    for name in sorted(names, key=lambda n: -counts.get(n, 0)):
        print(f"{counts.get(name, 0):4d}  {name}")
    never = sum(1 for n in names if not counts.get(n))
    print(f"-- {len(names)} skills, {never} never loaded, "
          f"{counts['?']} unattributable loads (compacted payloads)")
    print(f"-- home: {root}  (another profile: its own state.db, opened ?mode=ro)")


if __name__ == "__main__":
    main()
