# Skills tree layout and probe snippets

## Layout

```
~/.hermes/skills/
  <category>/<skill>/SKILL.md                most skills
  <category>/<skill>/skills/<sub>/SKILL.md   umbrella skill bundling sub-skills
  <category>/<skill>/.env/…                  embedded venv (name collisions live here)
  <category>/DESCRIPTION.md                  category descriptor, no SKILL.md
  .archive/                                  curator-archived skills — delete ONLY on an explicit
                                             user request (SKILL.md §8), never as a side effect
  .curator_backups/ .hub/ .locks/ .codegraph/ .reasonix/   infra — DO NOT DELETE
  .bundled_manifest                          <name>:<hash> per line — the deletion record (§below)
  .usage.json                                sidecar telemetry; never evidence of existence (§8)
```

A plain `ls` hides the dotted dirs, so "skills I can see" and "SKILL.md count" differ by
exactly the archived population. Always state which subtree a count covers.

Profiles other than the active one live under `~/.hermes/profiles/<name>/skills/` with their
own `config.yaml`. The active profile's tree is `~/.hermes/skills/` plus
`~/.hermes/config.yaml`. Do not edit another profile's skills/config unless the user asks for
that profile by name.

## Map disabled names → dirs

```python
import os, re, subprocess
root = os.path.expanduser('~/.hermes/skills')
txt  = open(os.path.expanduser('~/.hermes/config.yaml')).read()
disabled = re.findall(r'^\s+-\s+(\S+)$',
                      txt.split('\nskills:\n', 1)[1].split('\ncurator:', 1)[0], re.M)

# by name, then keep only real skill dirs (SKILL.md present)
hits = {}
for n in disabled:
    out = subprocess.run(['find', root, '-type', 'd', '-name', n],
                         capture_output=True, text=True).stdout.split()
    hits[n] = [p for p in out if os.path.isfile(os.path.join(p, 'SKILL.md'))]

# nested-under-another-target collapse
alldirs = sorted({p for v in hits.values() for p in v})
top = [d for d in alldirs if not any(d.startswith(o + os.sep) for o in alldirs)]

# safety gate: nothing enabled may live inside a target
live_inside = [(t, p) for t in alldirs
               for p, _, files in os.walk(t)
               if 'SKILL.md' in files and os.path.basename(p) not in disabled]
```

Note the last comprehension walks every target rather than trusting a name filter — that is
the check that makes deleting a category directory safe.

## Two-method verification after deleting

```python
one = subprocess.run(['find', root, '-name', 'SKILL.md'], capture_output=True, text=True).stdout.split()
two = [os.path.join(dp, f) for dp, _, fn in os.walk(root) for f in fn if f == 'SKILL.md']
assert sorted(one) == sorted(two), 'traversal disagreement — investigate before reporting'
```

When the two disagree, the filesystem is right and the traversal is wrong: probe the exact
suspect path with `os.path.exists` / `stat -f '%N %HT %z'` and act on that. Do not report a
delete as complete from the traversal count alone.

## Whole-config diff after a CLI edit

```python
import yaml
def flat(d, pre=''):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from flat(v, pre + k + '.')
        else:
            yield pre + k, v
before = dict(flat(yaml.safe_load(open('<config>.bak'))))
after  = dict(flat(yaml.safe_load(open('<config>'))))
assert [k for k in before if before[k] != after.get(k)] == ['skills.disabled']
```

Run this with a python that has PyYAML; if the sandbox interpreter lacks it, run the snippet
through `terminal` next to a `python3 -c "import yaml"` availability check rather than adding
a dependency.

## Probe a config write in a throwaway HERMES_HOME

To learn what a `hermes config …` call really does to a file — or to test whether it clobbers
unrelated keys — never experiment on the live config. Point the CLI at a scratch home:

```bash
P=~/.hermes/cache/scratch/configprobe
mkdir -p $P && cat > $P/config.yaml <<'EOF'
plugins:
  enabled: [disk-cleanup, ponytail]
curator:
  prune_builtins: true
skills:
  disabled: [alpha, beta]
EOF
HERMES_HOME=$P hermes config set curator.prune_builtins false
cat $P/config.yaml          # every other key must survive verbatim
```

This is also how to attribute a change you did not make: if the same `set` preserves unrelated
keys in the probe, then a key that changed in the live file afterwards belongs to another writer
— often a second live session in the same profile, or the desktop app. Say what you ruled out
and what you could not attribute, hand over the one-line fix command instead of applying it.

List values are passed as a YAML/JSON literal in one quoted argument:
`hermes config set plugins.enabled '["disk-cleanup", "ponytail"]'`.

## Probe that a skill removal sticks (throwaway HERMES_HOME)

Never test "does `hermes update` bring this skill back" by deleting from the live tree and waiting
for an update. Seed a scratch home, delete there, re-run the sync that `hermes update` calls, and
read the counts. Run from the Hermes install root (`cd <hermes install>`) with its bundled
interpreter (`venv/bin/python3`) so `tools.*` imports; the probe writes only into the scratch home.

```python
import os, shutil
from pathlib import Path
os.environ['HERMES_HOME'] = scratch = '/Users/maxim/.hermes/cache/scratch/skillrm_probe'
from tools.skills_sync import sync_skills, _read_manifest

r = sync_skills(quiet=True)                     # seeds the whole bundled set into the scratch home
print('seeded', len(r['copied']), 'of', r['total_bundled'])

victim = next(p for p in (Path(scratch) / 'skills').rglob('SKILL.md')
              if p.parent.name == '<bundled-skill-name>')
shutil.rmtree(victim.parent)
print('still in manifest:', victim.parent.name in _read_manifest())   # True = the deletion record

r2 = sync_skills(quiet=True)
print('copied', r2['copied'], '| skipped', r2['skipped'], '| back on disk:', victim.parent.exists())
```

Expected: `still in manifest: True`, `copied []`, the dir absent, and the name inside `skipped`
("in manifest but not on disk — user deleted it"). That pair of facts is the whole reason a
hand-delete survives `hermes update`: **keep the `.bundled_manifest` line**; deleting it makes the
same probe report the skill re-copied as new.

The same harness answers the neighbouring questions without touching the live profile — what a
hub `uninstall` does (write a `lock.json` entry with `install_path` pointing at a seeded dir, then
call `tools.skills_hub_install.uninstall_skill(name)` and read the lock back), and what a bundled
name returns from `uninstall_skill` (`refused: not a hub-installed skill (may be a builtin)`).

## Restore bundled skills after a bulk removal

The removal probe above reads forward. The same engine reads backward once two records are cleared:

```python
import os
scratch = '/Users/maxim/.hermes/cache/scratch/restore_probe'
os.environ['HERMES_HOME'] = scratch
os.environ['HERMES_BUNDLED_SKILLS'] = os.path.expanduser('~/.hermes/hermes-agent/skills')
from tools.skills_sync import (_read_manifest, _write_manifest, _read_suppressed_names,
                               _get_bundled_dir, sync_skills)

print(_get_bundled_dir(), _get_bundled_dir().exists())   # print this FIRST, every time
man, sup = dict(_read_manifest()), set(_read_suppressed_names())
targets = [n for n in man if not (skills / n).exists()]   # manifest-tracked, gone from disk
sup -= set(targets)                                       # 1. un-suppress
for n in targets: man.pop(n, None)                        # 2. drop the manifest line
(skills / '.curator_suppressed').write_text('\n'.join(sorted(sup)) + '\n')
_write_manifest(man)
print(sync_skills(quiet=True)['copied'])                  # 3. re-seed copies exactly `targets`
```

Both steps are load-bearing, and they fail silently on their own: suppressing a name makes the sync
skip it (the curator writes these lines when `curator.prune_builtins: true` retires a built-in), and
a manifest line with no directory on disk is classified "user deleted it". A profile can carry both
for the same name and stay empty through any number of updates. Un-suppress only the names being
restored so unrelated prunes stay pruned.

### Why a sync reports "0 copied" and is still working

`sync_skills` returns `{'copied': [], 'total_bundled': 0}` when the bundled directory does not
exist, and every CLI wrapper prints that as an ordinary success line (`Re-seeded 0 bundled skill(s).`).
The source resolves as `HERMES_BUNDLED_SKILLS` → `<dir of tools/skills_sync.py>/../skills` →
`<home>/skills`, so printed paths answer it; guessing from the install tree does not. A managed /
lease install puts the runtime code under
`~/.hermes/installs/<id>/environments/<id>/workspace/`, which ships no `skills/` tree at all — the
default source is a missing path there, and `HERMES_BUNDLED_SKILLS=<checkout>/skills` (the hook
Homebrew/Nix wrappers use) is the fix. Confirm with the same numbers as a healthy run: a working
source reports `total_bundled` equal to the package tree's skill count.

**Where a managed environment's `skills/` tree would have come from.** `workspace/` is assembled by
`scripts/build/agent.py`: the code is copied in (`_copy(inputs.code, repo)`), then **only the resource
names the caller listed** are copied as `repo/<name>` (`for name, source in inputs.resources.items()`).
The resource vocabulary is fixed — `skills, optional-skills, plugins, locales, optional-mcps`
(`scripts/build/inputs.py::RESOURCE_ENV`) — and the callers that pass all five are the packaged-payload
builds: `docker/build_agent.py`, `scripts/termux/payload_facts.py`, `scripts/bundles/native.py`,
`hermes_cli/bundled_app.py` (all as `{name: repo / name for name in RESOURCE_ENV}`). A source install
has no packaged resource trees to pass, because for that kind the trees *are* the checkout's — which is
exactly the assumption baked into `_get_bundled_dir()`'s default (`<dir of skills_sync.py>/../skills`).

Read the install's identity instead of guessing: `<home>/.install_method` and
`<checkout>/install-stamp.json` (`source: git`, `payload: bootstrap`, `distribution: null`,
`updateMechanism: self` = source install). Two on-disk tells that the environment was built with an
empty resources map: no `workspace/<resource-name>` for any of the five names, and **no
`command-map.json` anywhere under the install** (only the `references` placement writes that file, and
it is where the resource env vars would be recorded). `hermes_cli/post_update.py::step_adopt_blessed_checkout`
is not a suspect — it only writes a missing install stamp and copies no code.

Do not repair this by copying a `skills/` tree into `workspace/`: it is rebuilt. Set
`HERMES_BUNDLED_SKILLS` around the command, or symlink for a one-off probe and say it is temporary.

**Instrument the real process instead of reasoning about it.** Wrap the function and print what it
resolved, via a `sitecustomize.py` on `PYTHONPATH`:

```python
# <scratch>/probe_pkg/sitecustomize.py
import sys, tools.skills_sync as s
_orig = s.sync_skills
def patched(*a, **k):
    print('bundled:', s._get_bundled_dir(), s._get_bundled_dir().exists(), file=sys.stderr)
    print('skills_dir:', s._skills_dir(), 'home:', s._hermes_home(), file=sys.stderr)
    print('suppressed:', len(s._read_suppressed_names()), file=sys.stderr)
    print('external:', sorted(s._build_external_skill_index())[:5], file=sys.stderr)
    r = _orig(*a, **k)
    print('result:', {k2: (len(v) if isinstance(v, list) else v) for k2, v in r.items()},
          file=sys.stderr)
    return r
s.sync_skills = patched
```

Then `PYTHONPATH=<scratch>/probe_pkg HERMES_HOME=<scratch> hermes skills opt-in --sync` — the wrapper
binds at call time because the caller does `from tools.skills_sync import sync_skills` inside the
function, so the patch is seen. This is how the missing bundled tree was found; reading the CLI's
one-liner never would have.

**A `python -c` probe is not the CLI.** `-c` puts the current directory first on `sys.path`, so run
from the checkout it imports the *checkout's* `tools/` and sees the checkout's `skills/` (58 found);
the `hermes` console script's editable install resolves to the *workspace* copy (0 found). Two
probes, same env, opposite answers — reproduce a CLI behaviour by invoking the CLI, or set the env
explicitly and say which interpreter you used.

### High-fidelity rehearsal before touching a live home

Copy the real home's two state files into a scratch home and stage the built-ins that are still
present from the package tree — the restore logic then sees the user's exact counts (manifest
population, suppression list, missing set) without the live tree being touched:

```python
for f in ('.bundled_manifest', '.curator_suppressed'):
    shutil.copy2(live / 'skills' / f, scratch / 'skills' / f)
# stage SKILL.md-bearing dirs for the names that ARE present, from <checkout>/skills
```

Expected closure: `copied` == the missing count, `on disk now` == manifest population, and an empty
"still missing" set.

### What is left on disk after `rm -rf <skill dir>`

| Leftover | Effect |
|---|---|
| `<home>/cache/banner_snapshot.json` | **Visible.** Fingerprint = `config.yaml`/`.env` mtime+size + version/commit, so the skills tree is not an input and the CLI banner keeps listing the removed name. Delete the file; it is rebuilt on next launch. |
| another skill's `SKILL.md` | The only functionally meaningful leftover — a hand-written cross-reference to the removed name dangles. Flag it and offer to fix or keep. |
| `.curator_ledger.jsonl` | Append-only audit: absolute paths + sha256 of each removed file. Cosmetic; `hermes curator ledger --skill <name> --compact` shrinks it. |
| `.usage.json` | Inert: report rows are built from on-disk skills, with an explicit guard against ghost rows for deleted dirs. |
| `state.db` / session transcripts | Never rewritten by a skill removal; `session_search` can still surface the name. Age-prune with `hermes sessions prune`. |
| `.archive/`, `.curator_suppressed`, `.locks`, `.codegraph/codegraph.db`, `memories/` | Verified absent in a clean removal — query `codegraph.db` by name (sqlite) rather than grepping the binary. |

## API-level mechanics behind these probes

Read in the install tree, so the answer is the mechanism rather than a plausible story:

- **Bundled seeding / the `hermes update` sync** — `tools/skills_sync.py::sync_skills`. Per name:
  curator-suppressed → skipped; name claimed by another home's `external_dirs` → deferred; *not in
  manifest* → `_install_new_skill` (copied); *in manifest + on disk* → `_update_existing_skill`;
  *in manifest + missing* → `skipped += 1  # user deleted it`. The manifest is rewritten at the end
  (`_write_manifest`), so a hand-delete adds no entry and removes none.
- **`_rmtree_writable`** (`tools/skills_sync.py`) is that module's own remover: an `onerror` handler
  that `chmod`s the failing path *and its parent* to `S_IRWXU` before retrying (Nix/deb/rpm installs
  keep read-only `r-x` dirs, and unlinking a child needs a writable parent), plus a scope guard that
  raises unless the target is strictly under the skills root. Prefer it over a bare `shutil.rmtree`
  in any scripted delete.
- **Hub uninstall** — `tools/skills_hub_install.py::uninstall_skill(name)`: look the name up in
  `skills/.hub/lock.json`; resolve `install_path` via `_resolve_lock_install_path` (same scope
  guard); `rmtree`; `lock.record_uninstall(name)` pops the entry; append to `skills/.hub/audit.log`.
  Anything with no lock entry returns `(False, "'<name>' is not a hub-installed skill (may be a
  builtin)")` — bundled and local skills included, which is a routing signal, not a defect.
- **Agent-side delete** — `tools/skill_manager_tool.py::_delete_skill`: `shutil.rmtree` in the
  foreground, `skill_usage.archive_skill` when `_is_background_review()` is true, refused outright
  for a pinned skill. `absorbed_into` requires the umbrella to exist first.
- **Curator restore** — `tools/skill_usage.py::restore_skill`: permitted for a *bundled* name only
  while `curator.prune_builtins: true`; does not consult `.bundled_manifest`; moves the archived
  directory to `<home>/skills/<name>/` **flat** (nesting is not reconstructed); removes exactly that
  name from `.curator_suppressed`. Restore returns the archived copy, a sync returns the shipped
  version — different bytes, so pick per intent (keep edits → restore, want pristine → re-seed).
- **Cache invalidation** — `_finish_change(invalidate_cache=True)` → `_clear_skills_cache()`, so
  `uninstall` / `opt-out` land immediately; install and config changes keep the deferred default
  (`--now` / next session).
