# Profile lifecycle — create, configure, inspect, switch

Use this file for everything that acts on a profile **before** a gateway enters the picture: making
one, cloning one, giving it a role description, reaching it through its auto-registered alias, and
switching the sticky default (`hermes profile use`) versus scoping one session (`hermes -p <name>`).

## Create

Three shapes, from the note's operations guide:

```bash
# 空白 Profile（需后续配置）
hermes profile create coder

# 从现有 Profile 克隆
hermes profile create coder --clone default

# 带角色描述的 Profile（用于 Kanban 工作流）
hermes profile create auditor --description "Code review and security audit agent"
```

So: no flag = an empty profile you must configure; `--clone <source>` = a copy; `--description` =
metadata the Kanban decomposer uses to route work **by role instead of by profile name**.

Measured `hermes profile create --help` on this machine (2026-09-30) — the clone family is wider than
the note's single `--clone default` line:

```
usage: hermes profile create [-h] [--clone] [--clone-all]
                             [--clone-from SOURCE] [--clone-channels]
                             [--sync-imports] [--no-alias] [--no-skills]
                             [--description DESCRIPTION]
                             profile_name
```

What the flags that matter mean, in the help text's own words:

- `--clone` — "Copy config.yaml, .env, SOUL.md, and skills from active profile (messaging bot
  tokens/allowlists are left behind; see `--clone-channels`)".
- `--clone-all` — "Full copy of active profile (all state, excluding per-profile history and
  messaging channels)".
- `--clone-from SOURCE` — clone from a named profile instead of the active one.
- `--clone-channels` — "Also copy the source's messaging channels (bot tokens, allowlists, platform
  sections). **Two profiles holding one bot token collide**; refused when the source is served by a
  live multiplexed gateway."
- `--no-alias` / `--no-skills` — skip the wrapper script / start with no bundled skills.
- `--description` — "used by the kanban decomposer to route tasks based on role instead of profile
  name alone. Skip and add later via `hermes profile describe`."

The collision warning is the one to surface: cloning channels is how you accidentally point two
gateways at the same bot token.

## The auto-registered alias

Creating a profile registers a wrapper script on `PATH` named after the profile, so the profile can be
driven without `-p`. From the note:

```bash
coder setup                  # 配置 API Key 和模型
coder chat                   # 进入交互式聊天
coder gateway start          # 启动该 Profile 的 Gateway 服务
```

Measured wrapper content on this machine (2026-09-30), `~/.local/bin/game-research` — the whole
file, two lines:

```
#!/bin/sh
exec /Users/maxim/.hermes/hermes-agent/venv/bin/hermes -p game-research "$@"
```

So the alias is literally `hermes -p <name> "$@"` behind a two-line `sh` wrapper. Managed by
`hermes profile alias <name> [--remove] [--name <alias>]` (measured `--help`: `--name` "Custom alias
name (default: profile name)").

## Inspect

```bash
hermes profile list         # 列出所有 Profile
hermes profile show coder   # 查看详情
```

Measured `hermes profile show game-research` (2026-09-30) — the fields a support answer usually needs:

```
Profile: game-research
Path:    /Users/maxim/.hermes/profiles/game-research
Model:   deepseek-v4-flash (deepseek)
Gateway: running
Skills:  120
.env:    exists
SOUL.md: exists
Alias:   game-research → hermes -p game-research  (/Users/maxim/.local/bin/game-research)
```

Measured `hermes profile list` columns on this machine (2026-09-30):
`Profile | Model | Gateway | Alias | Distribution`, with the active profile prefixed by `◆` and the
default profile's Alias column showing `—`.

## Switch, and when it takes effect

**CLI is the only working method** (the Desktop GUI has no switcher — see
`maintain-hermes-profiles-limitations.md`):

```bash
# 切换 sticky default Profile
hermes profile use coder

# 新建会话时临时指定
hermes -p coder chat
```

The two are not the same thing and the difference is the whole point:

| command | scope |
|---|---|
| `hermes profile use <name>` | rewrites the **sticky default** on disk — every later CLI call without `-p` resolves to it |
| `hermes -p <name> <subcommand>` | scopes **that one command / new session** only; changes nothing persistent |

切换后需重启 Gateway（或 Desktop 应用）才能生效 — because the gateway read `active_profile` once at
startup (Issue #30626). A switch that "did nothing" is almost always this: the marker changed and the
running process never re-read it.

`hermes -p` is a global flag: put it **before** the subcommand. `hermes profile alias --remove`
(measured `--help`) is the way to take an alias back off `PATH`.

## Create lands an empty shell — two layers to fill

`hermes profile create` prints its own warning (`has no API keys yet … or it will inherit keys from your
shell environment`): a fresh profile has no model key, so "created" ≠ "runnable". Fill two layers:

- **Settings layer — `config.yaml`** (machine-local; not part of a distribution package). The quick route is
  copying a working home's file, but **check the source for a top-level `platforms:` section first** —
  copying that binds the other profile's bot tokens along with it. Parse, do not grep:
  `display.platforms` makes a string search a false positive.

  ```bash
  python3 -c "import yaml;print('platforms' in yaml.safe_load(open('<home>/config.yaml')))"
  ```

- **Secrets layer — `.env`**: copy only the keys that agent actually needs (model key, web-search key, its
  own data tokens) out of another profile's `.env`, and **never print the values**.

**Verification is a real turn, not a file check:**

```bash
hermes -p <name> chat -q "只回复两个字：就绪"     # an answer means it runs
find <home>/skills -name SKILL.md | wc -l        # skills land per profile
```

### Installing skills into the new profile

Skills are per-profile: `hermes -p <name> skills install "<identifier>" --category <cat> -y`. Having
installed a skill in another profile does not give this one the skill. **A skill that exists only on a
non-default branch is structurally unreachable through the three-segment identifier**: the syntax has no ref
slot, always pulls the default branch, and answers `Could not download '<owner>/<repo>/<path>'` — that is
"wrong branch", not "skill does not exist". The official route is a raw URL with the ref pinned to a **commit
SHA** (not a branch name: non-ASCII branch names break at the HTTP layer, and a SHA also freezes the
content). The cost, stated plainly: that entry carries no `source_revision`.

## Rename — what it fixes itself, and the collateral it leaves

```bash
hermes profile rename <old> <new>
```

It handles, without help: the directory rename, the wrapper alias (old removed, new installed), stopping and
removing the old name's gateway service, unbinding the old name from the live multiplexer's routes,
migrating the identity keyed by profile name (`agent:<old>:*` routing keys, `sessions.profile_name`,
`gateway_heartbeats`, the delivery/routing index), appending the old name to the new profile's
`profile.yaml → previous_names`, retargeting `active_profile`, and hot-serving the new name back.

**It does not touch these — scan them by hand, or they break silently:**

| 写死了旧名的地方 | 不改的后果 |
|---|---|
| `cron/jobs.json` 里 job prompt 内的绝对脚本路径（`bash /Users/…/profiles/<old>/scripts/x.sh`） | 那个 cron 当晚就 `Script exited with code 1` |
| profile 自己的 helper 脚本按字面路径读自己的 `.env` | 读不到 token，静默走错配置 |
| 技能正文引用的 `~/.hermes/profiles/<old>/…`（run-book 类笔记最常见） | 下次照笔记执行时路径不存在 |
| 分发包 `~/Repositories/Agent-*/`：`distribution.yaml → name`（**就是** profile 名；sync/统计脚本都从这里解析，脚本本身不硬编码名）、README 标题与每个示例命令、仓库目录名 | 包指向一个不存在的 profile |
| 别的 profile 的技能 / 笔记里提到的旧名 | 指路指到空气 |

Two traps while scanning:

- **Grep the bare name, not just the `profiles/<old>` path form.** The path may be assembled at runtime
  (`Path.home() / ".hermes" / "profiles" / "<old>" / ".env"`), and any replacement keyed on `profiles/<old>`
  misses it — after replacing, grep the bare name again to confirm.
- **Exclude the record-class files**: `.curator_ledger.jsonl`, `.curator_backups/`, `cron/output/`,
  `cache/`, `sessions/`, `logs/`, `state.db*`, `*.bak-*`. They are history; rewriting them is forging
  history, and leaving them alone changes nothing at runtime.
- **SOUL.md has two kinds of old-name mentions — only one is a path.** "I am the `job-hunter` agent"
  is an identity declaration and stays. "My partner is `quant-investor`" is a cross-profile reference
  and must be updated. Replace `` `<old>` `` (backtick-quoted) and `profiles/<old>` for OTHER
  profiles' names; keep the self-identity mention.
- **Check whether the rename target already exists as a profile.** `hermes profile rename <old> <new>`
  when `<new>` already exists merges the old profile's content into the existing one (the old
  directory is gone, the target's `previous_names` gains `<old>`). This is silent — `hermes profile
  list` afterward shows only `<new>`. Before renaming, `ls ~/.hermes/profiles/<new>` to check for a
  collision. If it exists, decide: merge (rename anyway) or pick a different name.

Verification:

- `hermes profile list` — both names present, each gateway `running`.
- **Read the multiplexer's state, not the profile's own `gateway_state.json`** — the latter is stale and will
  show `served_profiles: []`, which is a lie. Look at `<root>/gateway_state.json`: `served_profiles` and
  `platforms` should carry `<new>` and `<new>:<platform>` (e.g. `quant-investor:feishu`), which is the proof
  the platform route survived.
- Commit the distribution-package side (push only if it has a remote). Say in the commit message which
  changes belong to this rename and which pre-existed, and stage by pathspec — a shared clone may hold
  someone else's uncommitted work.

## Delete, and retrying an identity migration

- **Back up before deleting.** `cp -R ~/.hermes/profiles/<name> ~/.hermes/backups/profile-retire-<date>/<name>`
  before `hermes profile delete`. The delete is permanent — it removes config, .env, memories, sessions,
  skills, cron jobs, and the CLI alias. A backup is the only way to recover.
- **Remove cron jobs first.** `hermes cron list --profile <name>` to find jobs, then
  `hermes cron remove <job_id> --profile <name>` for each. A deleted profile's cron jobs will fail
  silently (the scheduler can't find the profile directory).
- Deletion is `hermes profile delete` (it also purges that profile's session/routing identity).
- If the rename's identity migration did not settle: `hermes profile migrate-identity <old> <new>`
  (idempotent, retryable). If a delete did not settle: `purge-identity`. Both only mean anything for a named
  profile — `default` can only change its display name.

## Pitfalls

- **"Created" is not "runnable"**: without a key layer the profile is a shell, and one real
  question-and-answer turn is the only proof.
- Before copying `config.yaml`, check the top-level `platforms:` (parse the YAML, do not grep): two profiles
  holding one bot token collide — the clone path has a guard, a hand copy has none.
- Reporting a rename as done without the bare-name grep leaves a broken cron for the user to find that
  night.
- Use the official verbs instead of a home-made fallback: `create` / `rename` / `delete` /
  `migrate-identity` / `purge-identity` are all first-class.
- `previous_names` (in `profile.yaml`) is the only record of what this profile used to be called — do not
  clean it up as dirt after a rename.
