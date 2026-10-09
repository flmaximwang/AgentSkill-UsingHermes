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
