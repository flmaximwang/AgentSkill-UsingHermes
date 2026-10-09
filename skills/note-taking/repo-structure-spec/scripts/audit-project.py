#!/usr/bin/env python3
"""Audit ONE project against the org spec (SKILL.md section 4).

Usage:  python3 audit-project.py [<project-dir>]        (default: current directory)

Stdlib only. Prints, in order:
  1. record-folder classification under Logs/ (Type-NNN vs legacy vs other)
  2. per-record checks: note named after its folder, assets/, workspace/data/, frontmatter fields
  3. archive-id histogram
  4. inlink counts
  5. dangling wiki-link / embed targets

Read the counts straight out of this output into the report; do not eyeball a directory listing.
"""
import collections
import os
import re
import sys

NEW = re.compile(r'^([A-Za-z]+)-(\d{3})$')                  # <Type>-<NNN>
LEGACY = re.compile(r'^\((\d{4}[.\-]\d{2}[.\-]\d{2})\)')  # (YYYY.MM.DD) <Title>
DAY = re.compile(r'^\d{2}$')
KEY = re.compile(r'^([A-Za-z][\w.\-]*)\s*:')
LINK = re.compile(r'(!?)\[\[([^\]|#]+)(\|[^\]]*)?\]\]')
ASSET = re.compile(r'\.(png|jpe?g|svg|gif|heic|csv|xlsx|txt|tsv|asc|ab1|pdf|json|base)$', re.I)
SKIP_DIRS = {'Data', 'Backup', '.git', '.obsidian'}


def walk(root, exts):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith('.library')]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in exts:
                yield os.path.relpath(os.path.join(dirpath, name), root)


def read(path):
    """(frontmatter block or None, whole text)"""
    with open(path, encoding='utf-8', errors='replace') as handle:
        text = handle.read()
    if not text.startswith('---'):
        return None, text
    end = text.find('\n---', 3)
    return (text[3:end] if end > 0 else None), text


def fields(block):
    """{key: [scalar values]} — enough for presence checks and list-valued frontmatter.

    A key with no value still yields an entry (empty list) so the caller can tell
    'missing key' from 'present but empty'.
    """
    out = collections.defaultdict(list)
    if not block:
        return out
    current = None
    for line in block.splitlines():
        match = KEY.match(line)
        if match and not line.startswith(('-', ' ')):
            current = match.group(1)
            out.setdefault(current, [])
            rest = line.split(':', 1)[1].strip()
            if rest and rest != '[]':
                out[current].append(rest)
        elif line.strip().startswith('- ') and current:
            out[current].append(line.strip()[2:].strip())
    return out


def record_dirs(root):
    """[(relpath, kind)] for every record folder under Logs/."""
    found = []
    logs = os.path.join(root, 'Logs')
    if not os.path.isdir(logs):
        return found
    for year in sorted(os.listdir(logs)):
        ydir = os.path.join(logs, year)
        if not (year.isdigit() and os.path.isdir(ydir)):
            continue
        for month in sorted(os.listdir(ydir)):
            mdir = os.path.join(ydir, month)
            if not (month.isdigit() and os.path.isdir(mdir)):
                continue
            for entry in sorted(os.listdir(mdir)):
                path = os.path.join(mdir, entry)
                if not os.path.isdir(path):
                    continue
                rel = os.path.relpath(path, root)
                if NEW.match(entry):
                    found.append((rel, 'Type-NNN'))
                elif LEGACY.match(entry):
                    found.append((rel, 'legacy'))
                else:
                    subs = [d for d in sorted(os.listdir(path))
                            if os.path.isdir(os.path.join(path, d))]
                    if DAY.match(entry) and subs:      # a day folder: its entries are the records
                        for sub in subs:
                            found.append((os.path.join(rel, sub),
                                          'Type-NNN' if NEW.match(sub) else 'other'))
                    else:
                        found.append((rel, 'other'))
    return found


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
    print('# audit of %s\n' % root)

    records = record_dirs(root)
    kinds = collections.Counter(kind for _, kind in records)
    print('## record folders: %d  %s' % (len(records), dict(kinds)))
    for rel, kind in records:
        if kind == 'other':
            print('   OTHER  %s   (legacy form or off-spec name - judge from the name)' % rel)
    print()

    md = list(walk(root, {'.md'}))
    bases = list(walk(root, {'.base'}))
    names = {os.path.splitext(os.path.basename(p))[0] for p in md + bases}

    print('## per-record checks (new-form records only)')
    header = ('   %-46s%-12s%-8s%-11s%-6s%-6s%-5s%-5s%-13s%s' %
              ('record', 'note=folder', 'assets', 'work/data', 'UID', 'Logs', 'hl', 'kw', 'proto', 'arch-id'))
    print(header)
    for rel, kind in records:
        if kind != 'Type-NNN':
            continue
        folder = os.path.basename(rel)
        note = os.path.join(root, rel, folder + '.md')
        block, _ = read(note) if os.path.exists(note) else (None, '')
        meta = fields(block)

        def state(key, required=True):
            if key not in meta:
                return 'MISS' if required else '-'
            return 'ok' if meta[key] else ('empty' if required else '-')

        proto = state('protocols')
        if proto == 'MISS':
            proto = 'protocol:' + state('protocol')
        print('   %-46s%-12s%-8s%-11s%-6s%-6s%-5s%-5s%-13s%s' % (
            rel,
            os.path.exists(note),
            os.path.isdir(os.path.join(root, rel, 'assets')),
            os.path.isdir(os.path.join(root, rel, 'workspace', 'data')),
            state('UID'),
            '- Logs' in ' '.join(meta.get('tags', [])),
            state('highlight', False),
            state('keywords', False),
            proto,
            state('archive-id', False)))
    print()

    print('## archive-id values')
    hist = collections.Counter()
    for rel, _ in records:
        folder = os.path.basename(rel)
        note = os.path.join(root, rel, folder + '.md')
        if os.path.exists(note):
            for value in fields(read(note)[0]).get('archive-id', ['(none)']):
                hist[value] += 1
    for value, count in hist.most_common():
        print('   %3dx  %s' % (count, value))
    print()

    inlinks = collections.Counter()
    dangling = collections.Counter()
    first_seen = {}
    for path in md + bases:
        _, text = read(os.path.join(root, path))
        for match in LINK.finditer(text):
            leaf = match.group(2).strip().rstrip('\\').split('/')[-1]
            inlinks[leaf] += 1
            first_seen.setdefault(leaf, path)
            if (leaf in names or ASSET.search(leaf) or re.match(r'^\(?\d{4}', leaf)
                    or leaf.startswith('<%')):
                continue
            dangling[leaf] += 1

    print('## most-linked notes')
    for leaf, count in inlinks.most_common(25):
        print('   %3dx  %s' % (count, leaf))
    print('\n## dangling link targets (no note/base of that name; code-span examples are false positives)')
    for leaf, count in sorted(dangling.items()):
        print('   %3dx  [[%s]]   first seen in %s' % (count, leaf, first_seen[leaf]))


if __name__ == '__main__':
    main()
