# Bundled-skill seeding — where built-in skills come from, and how to switch seeding off

Absorbed 2026-09-30 from the former standalone `manage-hermes-bundled-skills` skill (its `SKILL.md` and
both references), itself distilled from a note verified **2026-09-29** against the source at
`~/.hermes/hermes-agent/` (the git checkout the app / gateway loads) on macOS Apple Silicon. Blocks
marked *measured* are real output — the note's own output, or a read-only re-run done while this
reference was written. Nothing here was executed that changes state: `opt-out` / `opt-in` were never
run, only their `--help` and the on-disk reads.

## The causal model

Bundled (built-in) skills are **not downloaded**. `tools/skills_sync.py::sync_skills()` copies them
from the **current code root's `skills/`** into the **current profile's `HERMES_HOME/skills/`**. So
"can it seed" depends on exactly one thing — whether *that* code root has a `skills/` directory — and
not at all on how many skills already sit in HERMES_HOME.

The trap this reference exists for: when the code root has no `skills/`, `sync_skills()` early-returns
on `if not bundled_dir.exists(): return {...}` and reports `0 new / 0 updated`. That output reads like
"already up to date"; it actually means **there is no source**. A silent `0 new / 0 updated` is never
evidence of success.

```
code root's skills/  ──►  _get_bundled_dir()  ──►  hash gate (.bundled_manifest)  ──►  <HERMES_HOME>/skills/
```

## Diagnostic — work it in this order

**1. Which interpreter / launch chain am I on?** The code root is decided by the chain, not by the
question. Two chains coexist on a normal machine: a PATH-installed editable install (its `tools` maps
to a per-install `workspace/`) versus the desktop app / gateway launch script
`~/.hermes/hermes-agent/.hermes/bin/hermes`, which inserts the git checkout
`/Users/maxim/.hermes/hermes-agent` onto `sys.path`. Enumerate before answering — packaged, checkout and
launcher copies all coexist:

```bash
which -a hermes
```

Measured here, that prints the launcher first, then the two per-install venv scripts, then a
`~/.local/bin` copy. So "where do the bundled skills come from" is answered **per entry** in that list,
never once for the machine. The launcher wrapper is plain text; read it and note that it
`sys.path.insert(0, '/Users/maxim/.hermes/hermes-agent')` and pops `PYTHONPATH`/`PYTHONHOME` — that
insert is exactly why its `_get_bundled_dir()` lands on the checkout rather than a `workspace/`.

**2. Does that chain's code root have `skills/`?** Run the same `_get_bundled_dir()` call the sync
would make, on the interpreter in question:

```bash
env -u PYTHONPATH <venv>/bin/python3 -c \
  "from tools import skills_sync as s; p = s._get_bundled_dir(); print(p, p.exists())"
```

Two installs exist here, and both print `.../workspace/skills False`:

- `~/.hermes/installs/b200403c2b90970e/environments/52bc5256b3ca4a1bb91a06058efb2f54/workspace/skills False`
- `~/.hermes/installs/b200403c2b90970e/environments/d1c8e05cbd8b40dda7d9552a947e61ad/workspace/skills False`

while the app/gateway chain resolves `~/.hermes/hermes-agent/skills`, which exists and holds **58**
`SKILL.md` files. (PATH CLI code root provenance: the editable-install finder
`__editable___hermes_agent_0_0_0_finder.py:9` maps `tools` to `workspace/tools`.)

**3. Which knob applies?** Two different complaints, two different answers:

| Symptom | Cause | Knob |
|---|---|---|
| A PATH-installed `hermes` seeds nothing, while the app does | its code root has no `skills/` | point the chain at a real source — `HERMES_BUNDLED_SKILLS` |
| You want the app / install to *stop* seeding into a profile | opt-out is a profile decision | `.no-bundled-skills` marker via `hermes skills opt-out` |

`HERMES_BUNDLED_SKILLS` is a relocation hook for packagers (Homebrew / Nix), **not a switch**. To turn
seeding off use the marker.

## Commands

```bash
hermes skills opt-out           # write <HERMES_HOME>/.no-bundled-skills; touches nothing already on disk
hermes skills opt-out --remove  # marker + delete unmodified bundled copies (user-edited and hub/local kept)
hermes skills opt-in            # remove the marker; seeding resumes on the next `hermes update`
hermes skills opt-in --sync     # remove the marker and re-seed now → prints `Re-seeded N bundled skill(s)`
```

`opt-out` default leaves every file in place — the marker alone stops future seeding. Only `--remove`
deletes copies, and only "unmodified" ones. `opt-in` is the write/delete of that same marker; the file,
not the command, is the switch (`tools/skills_sync.py:400`).

---

## Details — the four moving pieces

### 1. Source directory resolution

The note's summary, verbatim: "Hermes 的 bundled（内置）技能**不来自网络**：它们随代码树一起发布，由
`tools/skills_sync.py::sync_skills()` 从**当前 code root 的 `skills/`** 复制到**当前 profile 的
`HERMES_HOME/skills/`**。所以\"能否播种\"只取决于 code root 下有没有 `skills/`，与 HERMES_HOME 里已装了
多少技能无关。"

```python
# tools/skills_sync.py:75-76
def _get_bundled_dir() -> Path:  # HERMES_BUNDLED_SKILLS env first, then repo-relative
    return get_bundled_skills_dir(Path(__file__).parent.parent / "skills")
```

The default is **repo-relative**: `Path(tools/skills_sync.py).parent.parent / "skills"` — the code root
the running interpreter actually imported `tools` from. That is why the same question has a different
answer on different launch chains: the default follows the import, not a fixed path.

```python
# hermes_constants.py:388-395
def _packaged_dir(env_var: str, default: Path | None, subdir: str) -> Path:
    """Resolve a package-manager-relocatable directory.

    Order: *env_var* (Nix wrapper / explicit override) → caller ``default`` (source checkout) →
    ``<HERMES_HOME>/<subdir>``.
    """
    override = os.getenv(env_var, "").strip()
    return Path(override) if override else default if default is not None else get_hermes_home() / subdir

# hermes_constants.py:408-410
def get_bundled_skills_dir(default: Path | None = None) -> Path:
    """Return the bundled skills directory, honoring package-manager wrappers (``HERMES_BUNDLED_SKILLS``)."""
    return _packaged_dir("HERMES_BUNDLED_SKILLS", default, "skills")
```

In words: **`HERMES_BUNDLED_SKILLS` env var → the caller's `default` (the source checkout) →
`<HERMES_HOME>/skills`**. The env var reorganises where the source lives; it does not turn seeding on
or off.

### 2. Target directory

`<HERMES_HOME>/skills/`, one tree per profile — `~/.hermes/skills/` for the default profile,
`~/.hermes/profiles/<name>/skills/` otherwise. `sync_skills()` creates it if missing
(`_skills_dir().mkdir(parents=True, exist_ok=True)`) before copying.

### 3. The hash gate and `.bundled_manifest`

The bookkeeping file is `<HERMES_HOME>/skills/.bundled_manifest`, a list of `name:md5` lines (v2
"name:hash"; v1 plain names auto-migrate). On every sync, for each bundled skill:

- **never seen before** → copy it in and record its hash.
- **already on disk, bundled copy changed, your copy still matches the recorded hash** → update it.
- **already on disk and your copy no longer matches** → **skip it**, printing `user-modified, skipping`.
  A skill you edited is never silently overwritten, and `hermes update` keeps it too
  (`hermes skills list-modified` lists these, `diff` shows the delta, `reset` clears the modified
  tracking so updates resume).
- **you deleted it** → it is not re-added.

From the source docstring (`tools/skills_sync.py:2-6`):

```
"""Skills Sync -- manifest-based seeding and updating of bundled skills. Copies repo skills/ into
~/.hermes/skills/, tracking each synced skill's origin hash in .bundled_manifest (v2 "name:hash"
lines; v1 plain names auto-migrate). NEW skills are copied and recorded; EXISTING skills update
only when bundled changed AND the user copy still matches the origin hash (else user-customized
-> SKIP); user-DELETED skills are not re-added; ...
```

### 4. The early return — the trap

```python
# tools/skills_sync.py:396-407
def sync_skills(quiet: bool = False) -> dict:
    essential_only = (_hermes_home() / NO_BUNDLED_SKILLS_MARKER).exists()
    if essential_only and not quiet:
        print("  (profile opted out of bundled skills via .no-bundled-skills — seeding essential skills only)")
    bundled_dir = _get_bundled_dir()
    if not bundled_dir.exists():
        return {"copied": [], "updated": [], "skipped": 0, "user_modified": [], "cleaned": [],
                "suppressed": [], "total_bundled": 0, "optional_provenance_backfilled": []}
```

A caller that only reads `copied`/`updated` renders this as `0 new / 0 updated` — indistinguishable from
"you are already current", but the truth is **there was no source to sync from**. Phrase it back to the
user as "no source found", never as "up to date".

### 5. Two code roots on this machine — measured 2026-09-29

The note's measured-evidence table (preserved verbatim):

| 解释器 / 启动链 | code root | bundled dir | 结果 |
|---|---|---|---|
| `installs/…/52bc…/venv/bin/python3`（中性 cwd，`env -u PYTHONPATH`） | `…/52bc…/workspace` | `…/workspace/skills` | **不存在**，0 个 SKILL.md |
| `installs/…/d1c8e05…/venv/bin/python3` | `…/d1c8e05…/workspace` | `…/workspace/skills` | **不存在**，0 个 SKILL.md |
| app / gateway 启动脚本 `~/.hermes/hermes-agent/.hermes/bin/hermes` | `~/.hermes/hermes-agent` | `~/.hermes/hermes-agent/skills` | 存在，**58** 个 SKILL.md |

- PATH CLI 的 code root 来源：editable 安装的映射文件 `__editable___hermes_agent_0_0_0_finder.py:9` 把
  `tools` 指向 `workspace/tools`。
- 播种闭环：`~/.hermes/skills/.bundled_manifest` 有 58 行，mtime `2026-09-29 19:16:06`；Hermes.app 启动于
  `19:16:03`（`ps` 抓到 PID 1676 `serve`、PID 58255 `gateway run`）。
- 注：`HERMES_BUNDLED_SKILLS` 是给包管理器（Homebrew / Nix 打包）用的 relocation 钩子，**不是开关**；关播种要用
  opt-out 标记。

Read the table the way the diagnostic does: the two **workspace** rows are editable installs whose code
root is a per-install `workspace/` that never shipped a `skills/` directory — both report "**不存在**，0
个 SKILL.md". The **app / gateway** row is the launch script `~/.hermes/hermes-agent/.hermes/bin/hermes`,
which inserts the git checkout onto `sys.path`, so its code root *is* the checkout and its `skills/` holds
**58** SKILL.md files. The PATH CLI resolves to the two workspace installs; the app and gateway resolve to
the checkout.

Re-verified read-only on 2026-09-30: both `_get_bundled_dir()` calls printed `.../workspace/skills False`;
`find ~/.hermes/hermes-agent/skills -name SKILL.md | wc -l` printed `58`;
`wc -l ~/.hermes/skills/.bundled_manifest` printed `58`; `~/.hermes/.no-bundled-skills` is absent
(seeding is on, normal path). The manifest `mtime` had advanced by then (the app had synced again since
the note) — which is exactly the closing loop below: a running app re-syncs and rewrites the manifest.

### 6. The measured closing loop

`.bundled_manifest` having **58** lines, written moments after Hermes.app started, is the proof that the
app/gateway chain is the one actually seeding — its code root has the source, so its `sync_skills()` run
appended/refreshed 58 entries. The workspace-chain interpreters produce no such write: their
`bundled_dir` does not exist, so `sync_skills()` early-returns before touching the manifest. "Which chain
seeded" is therefore observable two ways: the manifest's line count and mtime, and the PIDs of the app's
`serve` / `gateway run` processes.

---

## Control — the marker, and the two commands that write it

Seeding is controlled by **one file**, not by a config key:

```
<HERMES_HOME>/.no-bundled-skills
```

The CLI commands are just its writer and deleter. If you reason about "the switch" as the file, every
question resolves cleanly; if you reason about it as a flag, you will look for a config setting that
does not exist. The note's three semantics lines, verbatim:

- `hermes skills opt-out`：写 `<HERMES_HOME>/.no-bundled-skills` 标记，让播种停止；默认**不动**盘上任何文件，加
  `--remove` 才额外删掉"未被你改过"的内置副本。
- `hermes skills opt-in`：删掉该标记恢复播种；加 `--sync` 立刻重灌，打印 `Re-seeded N bundled skill(s)`。
- `.no-bundled-skills` **存在** = 只再播种 essential 的 `hermes-agent`；**不存在** = 正常播种（判据在
  `tools/skills_sync.py:400`）。文件是开关本体，两条命令只是它的写/删器。

### The judgement site

```python
# tools/skills_sync.py:72-73
NO_BUNDLED_SKILLS_MARKER = ".no-bundled-skills"

# tools/skills_sync.py:400
essential_only = (_hermes_home() / NO_BUNDLED_SKILLS_MARKER).exists()
```

The marker's existence flips `essential_only`. Note the exact meaning: **it does not mean "seed
nothing"** — it means "seed only essential skills", a singleton set:

```python
# agent/skill_utils.py:295
ESSENTIAL_SKILLS: frozenset = frozenset({"hermes-agent"})
```

and `sync_skills()` filters the candidate list to it
(`bundled_skills = [(name, src) for name, src in bundled_skills if name in ESSENTIAL_SKILLS]`). The same
marker name is mirrored in `hermes_cli/profiles.py:92` (`NO_BUNDLED_SKILLS_MARKER`), written when a
profile is created with `--no-skills` and read at `:2443`.

### `opt-out` — default versus `--remove`

Measured `hermes skills opt-out --help` on this machine (2026-09-30):

```
usage: hermes skills opt-out [-h] [--remove] [--yes]

Write the .no-bundled-skills marker so the installer, `hermes update`, and any
direct sync stop seeding bundled skills into the active profile. By default
nothing already on disk is touched. Pass --remove to ALSO delete bundled
skills that are unmodified (user-edited and hub/local skills are never
removed).

options:
  -h, --help  show this help message and exit
  --remove    Also delete already-present unmodified bundled skills
  --yes, -y   Skip confirmation prompt when using --remove
```

So:

- plain `hermes skills opt-out` → writes the marker, **touches nothing on disk**. The skills already
  seeded stay usable; only future seeding stops.
- `hermes skills opt-out --remove` → writes the marker **and** deletes bundled copies that are
  "unmodified" (copy still matches its recorded `name:md5` hash). Skills you edited, plus hub-installed
  and manually-copied local skills, are **never** removed. It prompts unless `--yes` is passed.

### `opt-in` — restoring, and the re-seed

Measured `hermes skills opt-in --help` on this machine (2026-09-30):

```
usage: hermes skills opt-in [-h] [--sync]

Remove the .no-bundled-skills marker so bundled skills are seeded again on the
next `hermes update`. Pass --sync to re-seed now.

options:
  -h, --help  show this help message and exit
  --sync      Re-seed bundled skills immediately instead of waiting for update
```

- `hermes skills opt-in` → deletes the marker. Seeding returns on the next `hermes update`.
- `hermes skills opt-in --sync` → deletes the marker and re-seeds immediately, printing
  `Re-seeded {copied} bundled skill(s).` (`hermes_cli/skills_hub.py:1079`). This is the fastest way to
  confirm the chain's code root actually has a source — if it prints `Re-seeded 0 bundled skill(s).`, the
  problem is the early return above, not the marker.

### Making a PATH-installed `hermes` seed too

The marker can turn seeding off but cannot turn it *on* when the code root has no `skills/` to seed from.
On this machine the PATH CLI resolves to per-install `workspace/` code roots that have no `skills/` (see
the table above). To make such an install seed, point its source at a code root that does have one:

```bash
export HERMES_BUNDLED_SKILLS=~/.hermes/hermes-agent/skills
```

(measured on this machine: neither the shell nor `.env` currently sets it). This is the **only**
situation the env var is for in a diagnostic conversation.

### The explicit warning

> `HERMES_BUNDLED_SKILLS` is a relocation hook for packagers (Homebrew / Nix), **not a switch**. It
> changes *where the source directory lives*; it does not stop or start seeding. To stop seeding set the
> `.no-bundled-skills` marker (`hermes skills opt-out`); to restart it remove the marker
> (`hermes skills opt-in [--sync]`).

Keep the two knobs apart when answering: the marker is a **profile** decision ("stop seeding here"), the
env var is a **packaging / chain** decision ("the source lives over there"). A user asking "how do I stop
bundled skills" wants the marker; a user asking "why does my `hermes` not seed" wants the env var or a
different launch chain.
