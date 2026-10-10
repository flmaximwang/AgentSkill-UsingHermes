#!/usr/bin/env python3
"""Does a profile's installed skill still match the repo it came from?

For every hub-installed skill in <profile>, byte-compare the installed copy with the same skill in
its source tree on this machine:

    <repo clone>/<repo-side path>   vs   <profile>/skills/<install_path>

Verdicts, one per locked skill:
  same          every file identical
  DRIFT         a file differs, or a file exists on only one side (names are listed)
  repo missing  the clone has no such directory — clone behind, or the skill left the repo
  not installed lock entry without a directory: ghost entry, nothing on disk
  unmeasurable  no local clone for that source (clawhub / url, or the pack was never cloned here)

The clone's HEAD / dirty / behind-origin counts are printed per repo: when the clone is ahead of
what the profile was installed from, part of a DRIFT is just "the repo moved on and the profile has
not been updated", not a local edit.

Covers lock entries only. A hand-copied skill has no lock entry, so it is never compared here —
`where-do-a-profiles-skills-come-from.py` is the one that guesses provenance for those.

Usage: where-a-profiles-skills-drift-from-their-repos.py <profile> [--json] [--selftest]
Exit:  0 all comparable skills identical / 1 drift found / 2 usage or unreadable input
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile

SKIP_DIRS = {'__pycache__', '.git', '.hub', '.archive', '.curator_backups'}
SKIP_SUFFIX = ('.pyc', '.pyo')
SIBLING = 'where-do-a-profiles-skills-come-from.py'


_SIB = []


def load_sibling():
    """The provenance script next to this one — it knows the clone roots. Its module-level code is
    constants + functions, so exec'ing it is safe. Cached: callers may patch its PACK_ROOTS."""
    if _SIB:
        return _SIB[0]
    here = pathlib.Path(__file__).resolve().parent
    p = here / SIBLING
    if not p.exists():
        sys.exit(f'exit 2: sibling {SIBLING} not found; looked in {here}\n'
                 'It ships with this skill — reinstall the package.')
    spec = importlib.util.spec_from_file_location('wdapscf', p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _SIB.append(mod)
    return mod


def skills_root(profile):
    home = pathlib.Path(os.environ.get('HERMES_HOME') or pathlib.Path.home() / '.hermes')
    if profile in ('', 'default'):
        return home / 'skills'
    return home / 'profiles' / profile / 'skills'


def tree(root):
    """{posix relpath: sha256} of every regular file under root."""
    out = {}
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        parts = p.relative_to(root).parts
        if any(x in SKIP_DIRS for x in parts) or p.suffix in SKIP_SUFFIX or p.name == '.DS_Store':
            continue
        out[pathlib.PurePosixPath(*parts).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def compare(inst, repo_dir):
    """(verdict, detail) for one skill: installed copy vs its copy in the source tree."""
    if repo_dir is None:
        return 'unmeasurable', {}
    if not inst.is_dir():
        return 'not installed', {}
    if not repo_dir.is_dir():
        return 'repo missing', {}
    a, b = tree(inst), tree(repo_dir)
    detail = {
        'changed': sorted(k for k in a.keys() & b.keys() if a[k] != b[k]),
        'only_profile': sorted(a.keys() - b.keys()),
        'only_repo': sorted(b.keys() - a.keys()),
    }
    return ('same' if not any(detail.values()) else 'DRIFT'), detail


def find_skill(root, name):
    """The one directory named <name> that holds a SKILL.md under root, or None (0 or >1 hits)."""
    if not root or not root.is_dir():
        return None
    hits = [p for p in sorted(root.rglob(name)) if (p / 'SKILL.md').is_file()]
    return hits[0] if len(hits) == 1 else None


def repo_side(sib, entry):
    """(path of this skill inside the source tree, repo key, expected relpath).

    A pack that reorganized its `skills/` layout is looked up by directory name before giving up: a
    relocated skill is still comparable, a deleted one is not."""
    src = entry.get('source')
    parts = [p for p in (entry.get('identifier') or '').split('/') if p]
    if src == 'skills.sh' and len(parts) >= 4:            # skills-sh/<owner>/<repo>/<path...>
        repo, rel = '/'.join(parts[1:3]), '/'.join(parts[3:])
        clone = sib.clone_root(repo)
        if clone is None:
            return None, repo, rel
        hit = clone / rel
        return (hit if hit.is_dir() else find_skill(clone, parts[-1])), repo, rel
    if src == 'official' and len(parts) >= 2:             # official/<cat>/<name>
        rel = pathlib.Path(*parts[1:])
        roots = [sib.CODE_ROOT, sib.CODE_ROOT.parent / 'optional-skills']
        for root in roots:
            if (root / rel).is_dir():
                return root / rel, 'hermes-agent (bundled)', rel.as_posix()
        for root in roots:
            hit = find_skill(root, parts[-1])
            if hit:
                return hit, 'hermes-agent (bundled)', rel.as_posix()
        return None, 'hermes-agent (bundled)', rel.as_posix()
    return None, (src or '?'), ''


def git(cwd, *args):
    r = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


_STATE = {}


def repo_state(clone):
    """(HEAD short sha, dirty files, behind origin/main) of a clone, cached. None = not a checkout."""
    key = str(clone)
    if key not in _STATE:
        if not (clone / '.git').exists():
            _STATE[key] = None
        else:
            head = git(clone, 'rev-parse', '--short', 'HEAD')
            dirty = git(clone, 'status', '--porcelain')
            behind = git(clone, 'rev-list', '--count', 'HEAD..origin/main')
            _STATE[key] = (head, len(dirty.splitlines()) if dirty else 0,
                           int(behind) if behind and behind.isdigit() else None)
    return _STATE[key]


def survey(profile, root=None):
    """[{skill, repo, verdict, detail, clone, state, revision}] for every lock entry."""
    sib = load_sibling()
    root = pathlib.Path(root) if root else skills_root(profile)
    if not root.is_dir():
        return root, None
    lockf = root / '.hub/lock.json'
    lock = json.loads(lockf.read_text()).get('installed', {}) if lockf.exists() else {}
    rows = []
    for name, e in sorted(lock.items()):
        repo_dir, repo, expected = repo_side(sib, e)
        inst = root / (e.get('install_path') or '')
        verdict, detail = compare(inst, repo_dir)
        clone = sib.clone_root(repo) if repo_dir is not None else None
        rows.append({'skill': name, 'repo': repo, 'verdict': verdict, 'detail': detail,
                     'expected': expected,
                     'install_path': e.get('install_path'),
                     'repo_path': str(repo_dir) if repo_dir else None,
                     'revision': ((e.get('metadata') or {}).get('source_revision') or '')[:7],
                     'clone': str(clone) if clone else None,
                     'state': repo_state(clone) if clone else None})
    return root, rows


def report(profile, root, rows, as_json=False):
    bad = [r for r in rows if r['verdict'] in ('DRIFT', 'repo missing', 'not installed')]
    if as_json:
        print(json.dumps({'profile': profile, 'skills_root': str(root), 'drifting': bad,
                          'all': rows}, indent=1))
        return 1 if bad else 0

    counts = {}
    for r in rows:
        counts[r['verdict']] = counts.get(r['verdict'], 0) + 1
    print(f"# {profile}: {len(rows)} locked skills @ {root}")
    print(f"# {' '.join(f'{k}={v}' for k, v in sorted(counts.items()))}\n")

    print(f"## 与仓库不同 ({len(bad)})")
    if not bad:
        print('   (none)')
    for r in bad:
        print(f"   {r['verdict']:14} {r['skill']}  [{r['repo']}] rev={r['revision']}")
        if r['verdict'] == 'repo missing' and r['expected']:
            print(f"        repo 里没有这个路径: {r['expected']}（clone={r['clone']}）")
        for k, files in r['detail'].items():
            if files:
                print(f"        {k}: {', '.join(files[:8])}{' …' if len(files) > 8 else ''}")

    unmeas = [r for r in rows if r['verdict'] == 'unmeasurable']
    if unmeas:
        print(f"\n## 不可比 — 本机没有 source tree ({len(unmeas)})")
        print('   ' + ', '.join(f"{r['skill']}[{r['repo']}]" for r in unmeas[:20])
              + (' …' if len(unmeas) > 20 else ''))

    print('\n## 逐仓库')
    repos = {}
    for r in rows:
        repos.setdefault(r['repo'], []).append(r)
    for repo, rs in sorted(repos.items(), key=lambda kv: -len(kv[1])):
        st = next((x['state'] for x in rs if x['state']), None)
        head = f"HEAD={st[0]} dirty={st[1]}" + (f" behind origin/main={st[2]}" if st and st[2] else '') \
            if st else 'no git state'
        tally = {}
        for x in rs:
            tally[x['verdict']] = tally.get(x['verdict'], 0) + 1
        print(f"   {repo:42.42} {len(rs):3}  {head}   "
              + ' '.join(f'{k}={v}' for k, v in sorted(tally.items())))
    return 1 if bad else 0


def selftest():
    """Structure + verdict check on synthetic trees. Fails if the comparison logic breaks."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='drift-selftest-'))
    inst, repo = tmp / 'profile/skills/hermes/fake', tmp / 'packs/AgentSkill-Fake/skills/fake'
    for d in (inst, repo):
        (d / 'scripts').mkdir(parents=True)
        (d / 'SKILL.md').write_text('# fake\n')
        (d / 'scripts/x.py').write_text('print(1)\n')
    assert compare(inst, repo)[0] == 'same', 'identical trees must be same'

    (inst / 'SKILL.md').write_text('# fake edited\n')
    v, d = compare(inst, repo)
    assert v == 'DRIFT' and d['changed'] == ['SKILL.md'], (v, d)

    (inst / 'SKILL.md').write_text('# fake\n')
    (inst / 'extra.md').write_text('x')
    assert compare(inst, repo)[1]['only_profile'] == ['extra.md']
    (inst / 'extra.md').unlink()

    (repo / 'new.md').write_text('x')
    assert compare(inst, repo)[1]['only_repo'] == ['new.md']
    (repo / 'new.md').unlink()

    (inst / '__pycache__').mkdir()
    (inst / '__pycache__/x.pyc').write_bytes(b'\x00')
    assert compare(inst, repo)[0] == 'same', 'caches must not count as drift'
    (inst / '__pycache__/x.pyc').unlink()
    (inst / '__pycache__').rmdir()

    assert compare(inst, tmp / 'nope')[0] == 'repo missing'
    assert compare(tmp / 'nope', repo)[0] == 'not installed'
    assert compare(inst, None)[0] == 'unmeasurable'

    # end-to-end on a synthetic profile: fake pack roots + lock entries -> verdicts
    sib = load_sibling()
    sib.PACK_ROOTS = [tmp / 'packs']
    moved = tmp / 'packs/AgentSkill-Moved/newplace/moved'
    moved.mkdir(parents=True)
    (moved / 'SKILL.md').write_text('# moved\n')
    root = tmp / 'profile/skills'
    (root / 'hermes/moved').mkdir(parents=True)
    (root / 'hermes/moved/SKILL.md').write_text('# moved\n')
    (root / '.hub').mkdir()
    (root / '.hub/lock.json').write_text(json.dumps({'installed': {
        'fake': {'source': 'skills.sh', 'install_path': 'hermes/fake',
                 'identifier': 'skills-sh/owner/AgentSkill-Fake/skills/fake',
                 'metadata': {'source_revision': 'deadbee' + 'f' * 33}},
        'moved': {'source': 'skills.sh', 'install_path': 'hermes/moved',
                  'identifier': 'skills-sh/owner/AgentSkill-Moved/skills/moved'},
        'ghost': {'source': 'skills.sh', 'install_path': 'hermes/ghost',
                  'identifier': 'skills-sh/owner/AgentSkill-Fake/skills/fake'}}}))
    (inst / 'SKILL.md').write_text('# fake edited\n')
    _, rows = survey('default', root=root)
    got = {r['skill']: r['verdict'] for r in rows}
    assert got == {'fake': 'DRIFT', 'moved': 'same', 'ghost': 'not installed'}, got
    assert report('default', root, rows) == 1, 'drift must exit 1'
    (inst / 'SKILL.md').write_text('# fake\n')
    _, rows = survey('default', root=root)
    assert {r['skill']: r['verdict'] for r in rows} == {'fake': 'same', 'moved': 'same',
                                                        'ghost': 'not installed'}
    assert report('default', root, rows) == 1, 'ghost entry alone must still exit 1'
    print('selftest: ok')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--selftest' in sys.argv:
        return selftest()
    if len(args) != 1:
        print(__doc__.strip().split('Usage:')[-1].strip())
        return 2
    root, rows = survey(args[0])
    if rows is None:
        print(f'exit 2: no skills tree at {root}', file=sys.stderr)
        return 2
    return report(args[0], root, rows, as_json='--json' in sys.argv)


if __name__ == '__main__':
    sys.exit(main() or 0)
