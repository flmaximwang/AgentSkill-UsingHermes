# Bundled-skill seeding — the mechanism in full

Bundled skills ship **with the code tree**. There is no download step. The whole mechanism is:
`tools/skills_sync.py::sync_skills()` copies the current code root's `skills/` into the current
profile's `<HERMES_HOME>/skills/`, one skill at a time, gated by a hash manifest. Everything a user
reports ("my built-in skills are missing", "it says nothing to do", "it won't update") traces back to
one of the four pieces below: source resolution, target, the gate, or the early return.

Source note, verbatim: "Hermes 的 bundled（内置）技能**不来自网络**：它们随代码树一起发布，由
`tools/skills_sync.py::sync_skills()` 从**当前 code root 的 `skills/`** 复制到**当前 profile 的
`HERMES_HOME/skills/`**。所以\"能否播种\"只取决于 code root 下有没有 `skills/`，与 HERMES_HOME 里已装了
多少技能无关。"

## 1. Source directory resolution

```python
# tools/skills_sync.py:75-76
def _get_bundled_dir() -> Path:  # HERMES_BUNDLED_SKILLS env first, then repo-relative
    return get_bundled_skills_dir(Path(__file__).parent.parent / "skills")
```

The default is **repo-relative**: `Path(tools/skills_sync.py).parent.parent / "skills"` — the code
root that the running interpreter actually imported `tools` from. That is why the same question has a
different answer on different launch chains: the default follows the import, not a fixed path.

The override chain lives in `hermes_constants.py`:

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

Resolution order, in words: **`HERMES_BUNDLED_SKILLS` env var → the caller's `default` (the source
checkout) → `<HERMES_HOME>/skills`**. So `HERMES_BUNDLED_SKILLS` is a **relocation hook for
packagers** (Homebrew / Nix wrappers that move `skills/` out of the checkout) — it reorganises where
the source lives, it does **not** turn seeding on or off. Off is the marker, documented in the control
reference.

## 2. Target directory

`<HERMES_HOME>/skills/`, one tree per profile — `~/.hermes/skills/` for the default profile,
`~/.hermes/profiles/<name>/skills/` otherwise. `sync_skills()` creates it if missing
(`_skills_dir().mkdir(parents=True, exist_ok=True)`) before copying.

## 3. The hash gate and `.bundled_manifest`

The bookkeeping file is `<HERMES_HOME>/skills/.bundled_manifest`, a list of `name:md5` lines
(v2 "name:hash"; v1 plain names auto-migrate). On every sync, for each bundled skill:

- **never seen before** → copy it in and record its hash.
- **already on disk, bundled copy changed, your copy still matches the recorded hash** → update it.
- **already on disk and your copy no longer matches** → **skip it**, printing
  `user-modified, skipping`. A skill you edited is never silently overwritten, and `hermes update`
  keeps it too (`hermes skills list-modified` lists these, `diff` shows the delta, `reset` clears the
  modified tracking so updates resume).
- **you deleted it** → it is not re-added.

From the source docstring (`tools/skills_sync.py:2-6`):

```
"""Skills Sync -- manifest-based seeding and updating of bundled skills. Copies repo skills/ into
~/.hermes/skills/, tracking each synced skill's origin hash in .bundled_manifest (v2 "name:hash"
lines; v1 plain names auto-migrate). NEW skills are copied and recorded; EXISTING skills update
only when bundled changed AND the user copy still matches the origin hash (else user-customized
-> SKIP); user-DELETED skills are not re-added; ...
```

## 4. The early return — the trap

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

When the code root has no `skills/`, the function returns an all-empty result and copies nothing. A
caller that only reads `copied`/`updated` renders this as `0 new / 0 updated` — indistinguishable from
"you are already current", but the truth is **there was no source to sync from**. This is the trap the
note exists for; phrase it back to the user as "no source found", never as "up to date".

## 5. Two code roots on this machine — measured 2026-09-29

The source note's measured-evidence table (preserved verbatim):

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

Read the table the way the diagnostic does: the two **workspace** rows are editable installs whose
code root is a per-install `workspace/` that never shipped a `skills/` directory — both report
"**不存在**，0 个 SKILL.md". The **app / gateway** row is the launch script
`~/.hermes/hermes-agent/.hermes/bin/hermes`, which inserts the git checkout
`/Users/maxim/.hermes/hermes-agent` onto `sys.path`, so its code root *is* the checkout and its
`skills/` holds **58** SKILL.md files. The PATH CLI resolves to the two workspace installs; the app
and gateway resolve to the checkout.

Re-verified read-only on 2026-09-30: both `_get_bundled_dir()` calls printed
`.../workspace/skills False`; `find ~/.hermes/hermes-agent/skills -name SKILL.md | wc -l` printed
`58`; `wc -l ~/.hermes/skills/.bundled_manifest` printed `58`; `~/.hermes/.no-bundled-skills` is
absent (seeding is on, normal path). The manifest `mtime` had advanced by then (the app had synced
again since the note), which is exactly the closing loop below: a running app re-syncs and rewrites
the manifest.

## 6. The measured closing loop

`~/.hermes/skills/.bundled_manifest` having **58** lines, written moments after Hermes.app started, is
the proof that the app/gateway chain is the one actually seeding — its code root has the source, so
its `sync_skills()` run appended/refreshed 58 entries. The workspace-chain interpreters produce no
such write, because their `bundled_dir` does not exist and `sync_skills()` early-returns before
touching the manifest. So "which chain seeded" is observable two ways: the manifest's line count and
mtime, and the PIDs of the app's `serve` / `gateway run` processes.
