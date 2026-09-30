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
`manage-hermes-profiles-limitations.md`):

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
