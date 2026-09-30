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

---

## Getting an edited copy back to stock — `reset` versus `reset --restore`

The skip above is **sticky**: the manifest keeps the *old* origin hash, so a copy that has diverged can
never match it again — it is reported `user-modified` on every later sync and `hermes update` keeps
skipping it. A bundled skill you once edited therefore stops receiving upstream changes *permanently*, with
no error anywhere. Clearing the manifest entry is what breaks the loop, and there are two opposite ways to
do it (`tools/skills_sync_bundled_ops.py:17-58`; CLI `hermes_cli/skills_hub.py:988-1004`):

| Command | What it does | What you end up with |
|---|---|---|
| `hermes skills reset <name>` | clears the manifest entry, then syncs | **your** copy is re-baselined as the origin — your edits survive, stock is never fetched |
| `hermes skills reset <name> --restore` | rmtrees your copy **first**, then clears the entry and syncs | the stock copy, re-copied from the code root's `skills/` — your edits are **gone** |

`hermes skills list-modified` prints that distinction in its footer — `reset <name>` = *"keep your copy,
re-baseline"*, `reset <name> --restore` = *"revert to stock"* — and the plain form's own message agrees:
*"Cleared manifest entry for `<name>`. Future `hermes update` runs will re-baseline against your current
copy and accept upstream changes."* So plain `reset` is **not** a revert; "give me the stock version
back" is `--restore`.

### `--restore` keeps no backup

`--restore` calls `_rmtree_writable(dest)` — an outright delete with no `.bak` sibling (that dance belongs
to the *update* path, `_replace_skill_dir`). The prompt says so verbatim: *"Restore `<name>` from bundled
source? This will DELETE your current copy and re-copy the bundled version."* Copy the directory aside
yourself before running it; if it held notes that exist nowhere else, that copy is the only one left. The
same delete is why the code runs it *before* writing the manifest — a failed rmtree then leaves the entry
intact instead of stranding the skill in a manifest-less limbo (#34972).

### The tested procedure — measured 2026-09-30 on the launcher chain `~/.hermes/hermes-agent`

```bash
hermes skills list-modified                      # what is stuck (here: computer-use, hermes-agent, obsidian)
hermes skills diff hermes-agent                  # what you would lose — file-by-file unified diff
cp -R ~/.hermes/skills/autonomous-ai-agents/hermes-agent \
      ~/.hermes/backups/hermes-agent-user-copy-$(date +%Y%m%d_%H%M%S)/   # your own backup
hermes skills reset hermes-agent --restore --yes
```

Measured output of that last line, complete:

```
Restored 'hermes-agent' from bundled source.
Copied: hermes-agent
```

`--yes` is needed only because `--restore` prompts (plain `reset` never prompts). `diff` summarised the
delta in one header line — `'hermes-agent' differs from the stock version in 29 file(s).` — then, per file,
either a unified diff or `+ only in your copy: <rel>` / `- only in stock: <rel>`. Nine references existed
only in the stale local copy and the stock tree carried its own, different set: that is why `--restore`
replaces the **whole directory**, not just `SKILL.md`.

### Verify — three checks, not the exit code

Exit code 0 also covers the re-baseline case, and a printed `Copied:` line alone does not prove the tree is
stock. Check all three:

1. `hermes skills list-modified` — the name is gone from the list.
2. `diff -r <code root>/skills/<category>/<name> <HERMES_HOME>/skills/<category>/<name>` prints nothing.
   The code root is the *launch chain's* (see §1); on this machine's app/gateway chain that is
   `~/.hermes/hermes-agent/skills/`.
3. The copy's directory hash equals the manifest's recorded hash — recompute the sync's own `_dir_hash`
   (md5 over each file's `relative_path` bytes + the file bytes, runtime-cache files excluded):

```python
import hashlib, pathlib
def dir_hash(d):                      # mirrors tools/skills_sync.py::_dir_hash
    h = hashlib.md5()
    for f in sorted(pathlib.Path(d).rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(d)).encode()); h.update(f.read_bytes())
    return h.hexdigest()

home = pathlib.Path.home() / ".hermes/skills"
manifest = dict(l.split(":", 1) for l in (home / ".bundled_manifest").read_text().splitlines() if ":")
print(dir_hash(pathlib.Path.home() / ".hermes/hermes-agent/skills/autonomous-ai-agents/hermes-agent"))
print(dir_hash(home / "autonomous-ai-agents/hermes-agent"))
print(manifest.get("hermes-agent"))
```

Measured after the reset above: all three printed `37da26e707faa89f36cfb5ffe6dd5bb5`. The pre-reset copy's
`SKILL.md` alone hashed `d4492e5b962d1f8847a85485ab326065`, declared `version: 2.1.0` and carried 22 files,
against the stock copy's `version: 3.2.0`. Equal hashes are the proof that the copy is package-owned again —
which is also what the next `hermes update` reads.

### When it is not `--restore`

- **The name is hub-installed, not bundled** → `'<name>' is not a tracked bundled skill. Nothing to reset.
  (Hub-installed skills use `hermes skills uninstall`.)` The sibling `remove-hermes-skills` owns that path.
- **Upstream dropped the skill** → `bundled_missing`: *"has no bundled source — manifest entry preserved but
  cannot restore from bundled (skill was removed upstream)"*; restore from your own backup instead.
- **The delete fails** (permissions, immutable source) → `not_reset`: *"Could not delete user copy at …"*,
  the manifest entry is preserved and **nothing was changed** — fix permissions and retry.
- **Upstream renamed or recategorised it** is a second trigger for the same flag. The sync prints
  `⚠ <name>: upstream moved this skill to <new>, but your modified copy at <old> was kept — it will not
  receive updates. Run 'hermes skills reset <name> --restore' to move to the new location.`
  (`tools/skills_sync.py:246-251`), and the stale path stays where it is until you run it.
- **You meant to keep the edit** → do not leave the copy diverged. Port the change into the source the
  skill ships from and copy it in, or the copy silently stops tracking upstream forever. Same rule as
  "hand copies have no lock entry": a diverged copy has no path back to updates.
