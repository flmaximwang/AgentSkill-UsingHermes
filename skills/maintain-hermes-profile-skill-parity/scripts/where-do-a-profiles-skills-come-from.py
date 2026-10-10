#!/usr/bin/env python3
"""Where a profile's skills come from — grouped by source repo x category.

Reports:
  A. live skills as <source repo> -> <installed category> -> skills, flagging
     (1) a repo whose skills sit in MORE THAN ONE category, and
     (2) a skill whose installed category differs from the category its source
         repo keeps it in.
  B. repos that are only PARTIALLY installed (clone has more skills than the profile).

Provenance comes from <profile>/skills/.hub/lock.json (`source` + `identifier`), which encodes
both the repo and the repo-side path. For local/bundled copies with no lock entry the repo is
INFERRED by directory name against ~/Documents/AgentSkill/* and marked with '~'.

Usage: where-do-a-profiles-skills-come-from.py <profile> [--json]
"""
import json, pathlib, sys

H = pathlib.Path.home()
# Where a repo's clone may live. A repo key is matched by its last path segment.
# ponytail: fixed root list; a pack cloned somewhere else reads as "no local clone" (unmeasurable).
PACK_ROOTS = [H / 'Documents/AgentSkill', H / 'Repositories/Repo']
CODE_ROOT = H / '.hermes/hermes-agent/skills'
BUNDLED_REPO = 'bundled (hermes-agent code root)'
SKIP = ('/.archive/', '/.curator_backups/', '/.hub/')


def _root_of(path):
    for r in PACK_ROOTS:
        try:
            path.relative_to(r)
            return r
        except ValueError:
            continue
    return None


def clone_root(repo):
    """Local clone dir for a repo key, if we have one."""
    if repo == BUNDLED_REPO:
        return CODE_ROOT
    short = repo.split('/')[-1]
    for r in PACK_ROOTS:
        d = r / short
        if d.is_dir():
            return d
    return None


def repo_key(repo):
    """Group by repo, not by spelling: 'flmaximwang/Loomerto' (lock identifier) and 'Loomerto'
    (inferred from the clone dir) are the same repo, as are 'owner/AgentSkill-X' and 'AgentSkill-X'."""
    return repo.split('/')[-1] if '/' in repo else repo


def cat_of(path, root):
    """Repo-side / installed category of a skill dir: path segments minus the root and a
    leading 'skills'/'skill', minus the skill name itself."""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return None
    parts = [p for p in parts[:-1] if p not in ('skills', 'skill')]
    return '/'.join(parts) if parts else '(root)'


def parse_identifier(source, identifier):
    """(repo, repo-side category) from a hub identifier."""
    if not identifier:
        return f'{source or "?"}', None
    if source == 'skills.sh':
        parts = identifier.split('/')            # skills-sh/<owner>/<repo>/<path...>
        if len(parts) >= 3:
            repo = '/'.join(parts[1:3])
            rest = parts[3:]
            while rest and rest[0] in ('skills', 'skill'):
                rest = rest[1:]
            return repo, ('/'.join(rest[:-1]) or '(root)')
        return identifier, None
    if source == 'official':
        rest = identifier.split('/')[1:]
        return 'official (Hermes bundled registry)', ('/'.join(rest[:-1]) or '(root)')
    if source == 'clawhub':
        return 'clawhub/' + identifier.split('/')[-1], None
    if source == 'url':
        return identifier.split('/')[2] if identifier.count('/') > 2 else identifier, None
    return f'{source}', None


def clone_copies(name):
    """Every pack clone holding a directory of this skill name (dir with its own SKILL.md)."""
    out = set()
    for r in PACK_ROOTS:
        if not r.is_dir():
            continue
        for p in r.rglob(name):
            if p.is_dir() and (p / 'SKILL.md').exists() and '/~/' not in str(p):
                out.add(p)
    return sorted(out)


def repo_inventory(repo):
    """{skill name: category} for every skill the repo/clone ships."""
    root = clone_root(repo)
    if root is None:
        return None
    inv = {}
    for md in root.rglob('SKILL.md'):
        if any(x in str(md) for x in SKIP):
            continue
        inv[md.parent.name] = cat_of(md.parent, root)
    return inv


def main():
    prof = sys.argv[1]
    as_json = '--json' in sys.argv
    sk = H / '.hermes/profiles' / prof / 'skills'
    lock = json.loads((sk / '.hub/lock.json').read_text()).get('installed', {}) \
        if (sk / '.hub/lock.json').exists() else {}
    by_path = {v['install_path'].rstrip('/'): (v.get('source'), v.get('identifier'))
               for v in lock.values() if v.get('install_path')}
    bundled = {l.split(':')[0] for l in (sk / '.bundled_manifest').read_text().splitlines()
               if ':' in l} if (sk / '.bundled_manifest').exists() else set()

    rows = []   # (installed rel, repo, installed cat, repo cat, guessed)
    for md in sorted(sk.rglob('SKILL.md')):
        if any(x in str(md) for x in SKIP):
            continue
        rel = str(md.parent.relative_to(sk))
        cat = '/'.join(rel.split('/')[:-1]) or '(root)'
        name = md.parent.name
        guessed = False
        if rel in by_path:
            repo, repo_cat = parse_identifier(*by_path[rel])
        elif name in bundled:
            repo, repo_cat = BUNDLED_REPO, cat_of(md.parent, CODE_ROOT)
        else:
            copies = clone_copies(name)
            repos = sorted({c.relative_to(_root_of(c)).parts[0] for c in copies})
            if len(repos) == 1:
                repo = repos[0]
                repo_cat, guessed = cat_of(copies[0], clone_root(repo)), True
            else:
                repo = 'local only — no external repo' if not repos else 'local, ambiguous: ' + ', '.join(repos)
                repo_cat, guessed = None, True
        rows.append((rel, repo, cat, repo_cat, guessed))

    groups = {}
    for rel, repo, cat, rcat, guessed in rows:
        groups.setdefault((repo_key(repo), cat), []).append(rel)
    by_repo = {}
    for (repo, cat), items in groups.items():
        by_repo.setdefault(repo, {})[cat] = sorted(items)
    # full repo names, for display next to the key
    display = {}
    for repo in by_repo:
        display[repo] = next((r for _, r, _, _, _ in rows if repo_key(r) == repo), repo)

    drift = [(rel, repo, cat, rcat) for rel, repo, cat, rcat, _ in rows
             if rcat and rcat != '(root)' and cat != rcat]
    multi_cat = {r: cats for r, cats in by_repo.items()
                 if len(cats) > 1 and r != BUNDLED_REPO}
    # bundled skills legitimately span categories; only a *pack* repo is expected to be coherent
    partial = []
    everywhere = {rel.split('/')[-1] for items in by_repo.values() for v in items.values() for rel in v}
    for repo, cats in by_repo.items():
        inv = repo_inventory(repo)
        if not inv:
            continue
        have = {rel.split('/')[-1] for items in cats.values() for rel in items}
        gone = set(inv) - have
        # a name installed from ANOTHER repo is not missing -- say where it came from instead
        elsewhere = sorted(n for n in gone if n in everywhere)
        missing = sorted(gone - set(elsewhere))
        if missing or elsewhere:
            partial.append((repo, len(have), len(inv), missing, elsewhere))

    if as_json:
        print(json.dumps({'groups': {f'{r} | {c}': v for (r, c), v in groups.items()},
                          'category_drift': drift, 'multi_category_repos': multi_cat,
                          'partially_installed': partial}, indent=1))
        return

    print(f"# {prof}: {len(rows)} live skills from {len(by_repo)} source repos\n")
    print("## by source repo -> installed category")
    for repo, cats in sorted(by_repo.items(), key=lambda kv: -sum(len(v) for v in kv[1].values())):
        n = sum(len(v) for v in cats.values())
        flag = f"  \u26a0 {len(cats)} CATEGORIES" if repo in multi_cat else ''
        show = display[repo]
        head = f"{repo}  ({n})" + (f"   [= {show}]" if show != repo and '/' in show else '')
        print(f"\n{head}{flag}")
        for cat, items in sorted(cats.items()):
            print(f"   [{cat}]")
            for i in items:
                print(f"      {i}")
    if drift:
        print(f"\n## \u26a0 repo has a category but the profile installed it elsewhere ({len(drift)})")
        for rel, repo, cat, rcat in drift:
            print(f"   {rel:52} installed=[{cat}]  repo=[{rcat}]  <- {repo}")
    print(f"\n## partially installed repos ({len(partial)})")
    for repo, have, total, missing, elsewhere in sorted(partial, key=lambda t: len(t[3])):
        extra = f"; {len(elsewhere)} present from another repo: {', '.join(elsewhere[:6])}" if elsewhere else ''
        print(f"   {repo}: {have}/{total} installed; missing {len(missing)}{extra}")
        if missing:
            print(f"      {', '.join(missing[:12])}{' …' if len(missing) > 12 else ''}")


if __name__ == '__main__':
    main()
