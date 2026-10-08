---
name: maintain-hermes-profiles
description: Manage Hermes Agent profiles and their per-profile gateways — create, clone, rename or delete a profile, run several gateways online at once, keep instances isolated, and switch profiles. Use when the user wants multiple bots or agents running simultaneously, asks about `hermes profile create`, `rename`, `delete`, `use`, `list` or `show`, about per-profile LaunchAgent or systemd gateway services, gateway ports, or about why a profile switch did not take effect. Covers the two hard limits that decide which requests are possible today — the gateway is profile-blind and the Desktop GUI has no profile switcher — plus the workarounds for each.
---

# Manage Hermes Profiles and Their Gateways

A **Profile** is an independent Hermes home directory (`~/.hermes/profiles/<name>/`) holding its own
`config.yaml`, `.env`, skills, sessions and memory — and its own **Gateway** process. Multi-profile
gateway management means giving each profile a separate gateway service so several agents are
**online at the same time**, each served through its own channel (Telegram Bot, Discord Bot,
Slack App …).

Provenance: the source note this skill was distilled from carries **no verification-date header**.
Treat the version-dependent claims below as that note states them, and separate them from the blocks
marked *measured on this machine* (2026-09-30), which are real command output re-verified while
writing this skill.

## Read this first — the gateway topology has moved on

The note describes **one gateway service per profile** (its own LaunchAgent plist / systemd unit).
Measured on this machine (2026-09-30), that is no longer the shape: `hermes gateway list` reports
every non-default profile as *served by the default multiplexer*, only **one** plist exists
(`ai.hermes.gateway.plist`), and `hermes gateway --help` carries a `migrate` subcommand worded
"Converge every per-profile gateway onto the ONE host gateway".

So on a current install the thing to reason about is **one multiplexed host gateway serving many
profiles**, not N independent services. The per-profile commands below are still the documented
interface and still say *which profile's* gateway is meant, but establish which model the machine
actually runs before answering — `hermes gateway list` and `hermes gateway status` are the read-only
way to see it, and the measured block at the end of
`references/maintain-hermes-profiles-gateways.md` records what was found here.

## Decide first — two limits that decide what is even possible

Read these before promising anything. Each one turns a plausible request into "not like that":

1. **The gateway is profile-blind** (Issue [#30626](https://github.com/NousResearch/hermes-agent/issues/30626)).
   `hermes gateway run` reads `active_profile` **once** at startup and loads that profile's
   config / skills / memory into memory; afterwards the process **does not observe** an external
   profile switch. `hermes profile use <name>` only rewrites an on-disk marker, so it has no effect
   on a gateway that is already running. → **Workaround: restart the gateway** after the switch.
2. **The Desktop GUI has no profile switcher** (Issue [#44063](https://github.com/NousResearch/hermes-agent/issues/44063)).
   Desktop settings contain no profile dropdown or selector. → **Workaround: switch from the CLI**
   (`hermes profile use <name>`) and then restart the gateway or the Desktop app. Connecting the
   Desktop to a **different Remote URL** also works indirectly, because each profile's gateway
   listens on its own port.

One deliberate exception keeps the dashboard usable: the dashboard's embedded `/chat` tab is **not
routed through the gateway** — it opens a `hermes --tui` PTY per WebSocket connection
(`hermes_cli/web_server.py:3404-3450`), so it **does** follow the CLI's `--profile` argument and is
not subject to the profile-blind limit.

## Order of operations

1. **Create** the profile — `hermes profile create <name>` (blank), `hermes profile create <name>
   --clone default` (copy config/docs/skills from an existing profile), or add
   `--description "Code review and security audit agent"` (used by the Kanban decomposer to route
   by role). Details and flags: `references/maintain-hermes-profiles-lifecycle.md`.
2. **Configure** it — creation auto-registers a `<name>` CLI alias, so `<name> setup` (API key and
   model) then `<name> chat` reach the new profile without `-p`.
3. **Start the gateway per profile** — the note's model is one independent system service each
   (`hermes -p <name> gateway start`); on a current install a single multiplexed gateway may already
   serve them all (see the block at the top). Service paths, the batch script and per-profile ports:
   `references/maintain-hermes-profiles-gateways.md`.
4. **Verify** — `hermes profile list` (does each profile show a gateway?), `hermes profile show
   <name>` (path, model, skills count, alias), `hermes gateway status` (is the service supervised?).
5. **Switch** — `hermes profile use <name>` sets the sticky default; `hermes -p <name> chat` scopes a
   single new session. Either way the switch only takes effect **after a gateway restart**.

The rule that decides whether step 3 even targets the right service:

> 注意：`default` Profile 使用 `hermes gateway <action>`（不带 `-p`），而非 `hermes -p default gateway <action>`。

Everything else names its profile explicitly. `-p` is a global flag and belongs **before** the
subcommand (`hermes -p <name> gateway start`, never `hermes gateway start -p <name>`), and a switch
is CLI-only until the Desktop GUI gains a switcher.

Changing a profile's **default model** is *not* a profile switch: the `model:` block in that profile's
`config.yaml` is resolved per turn, so the next message picks it up and **no gateway restart is needed**
(procedure and verification: the `maintain-hermes-models` skill). Restarting for a model change bounces
every other profile's in-flight turn on this host for nothing.

## The lifecycle verbs, and where they bite

`create` lands an **empty shell** — no model key, so a real question-and-answer turn (not a file listing) is
what proves it runs; `rename` fixes the directory and the identity itself but leaves every hard-coded old
name stale (cron script paths, distribution packages, other profiles' notes), so a bare-name grep is part of
the job; `delete` also purges that profile's session/routing identity, and `migrate-identity` /
`purge-identity` are the idempotent retries when either did not settle. Full procedures, the collateral
table and the two grep traps: `references/maintain-hermes-profiles-lifecycle.md`.

## Architecture, in the note's own terms

| 概念 | 说明 |
|------|------|
| **Profile** | 一个独立的 Hermes 主目录（`~/.hermes/profiles/<name>/`），含完整配置、技能、记忆、会话 |
| **Gateway** | 负责接收消息平台事件的守护进程，一个 Profile 一个 Gateway 实例 |
| **Profile Alias** | 创建 Profile 后自动注册的 CLI 别名（如 `coder chat`、`coder gateway start`） |

## What "independent" actually buys you

Every profile owns its own `config.yaml`, `.env`, **skills**, **sessions**, **memory**, and gateway
process. Nothing is shared between profiles — not the skill directory, not the model choice, not the
`.env` bot tokens. That is the whole value of the mechanism, and it is also why "share one gateway
between two profiles" is not a thing you can set up: a gateway instance belongs to the profile it
read at startup.

## Common requests, and the order that answers them

| The user asks | Do this, in order |
|---|---|
| "Run a second bot for another platform" | `hermes profile create <name> --clone default` → `<name> setup` (its own bot token) → `hermes -p <name> gateway start` |
| "Keep my test instance away from production" | separate profile, separate port in `config.yaml`, separate gateway; profiles share no skills/memory/sessions |
| "Switch this instance to another profile" | `hermes profile use <name>` then **restart the gateway** — a running gateway is profile-blind (Issue #30626) |
| "Pick the profile in the Desktop app" | not supported (Issue #44063) — switch on the CLI, or connect the Desktop to the other profile's Remote URL/port |
| "Give each profile a role for Kanban" | `hermes profile create <name> --description "…"`, or `hermes profile describe <name>` later |

## Verify before and after

```bash
hermes profile list                 # Profile | Model | Gateway | Alias | Distribution
hermes profile show <name>          # path, model, gateway, skills count, .env, SOUL.md, alias
hermes gateway status               # is the service supervised, and under which plist/unit?
```

Read-only, safe on a live machine. `hermes gateway start|stop|restart` and anything under `launchctl`
are **not** read-only — on a machine whose bots are serving users, a wrong one disconnects them.

## 本机命名 profile 现状（快照）

- **非默认 profile 的技能操作，两条写法都实测通**：`hermes --profile <name> skills list|install|check|update`
  （`--profile` 是**全局 flag，放在子命令前**），以及
  `HERMES_HOME=/Users/maxim/.hermes/profiles/<name> hermes skills …`（等价选中该 profile）。
- **投资双 agent profile（2026-10-02）**：
  - **`quant-investor` = 原 `investment-advisor` 改名** —— 级联已做：profile 内 `cron/jobs.json`、
    `scripts/*.sh|py`、技能正文里硬编码的 `profiles/investment-advisor` 路径、分发包目录、`distribution.yaml` 的
    `name`，全部已改；multiplexer 已服务 `quant-investor:feishu`。
  - **`value-investor` = 价值投资学派**（`turtle-skill`→`investment` 类目 / UsingGit 13 个→`git` / StructuredResponse 2 个→`secretary`；
    `config.yaml` 抄 default、`.env` 有 DEEPSEEK+PARALLEL+TUSHARE+OBSIDIAN_VAULT_PATH、`SOUL.md` 已写；**无 bot channel**）。
  - 龟龟 skill = `wsadneal-debug/turtle_project` 的 `龟龟skill` 分支下 `skill/skills/turtle-skill`
    （默认分支 `main` 无该目录 → 三段式标识符**结构上不可用**；官方正路 = raw URL **钉 commit SHA**，本次 11 文件 SAFE，
    只掉一个不被引用的 `agents/openai.yaml`）。

## Route by what was asked

| The request is about | Read |
|---|---|
| creating / cloning / describing a profile, the alias, `setup`/`chat`, `list`/`show`, `use` vs `-p`, when a switch takes effect, the empty-shell key layers, per-profile skill installs, and **rename / delete / identity retries** | `references/maintain-hermes-profiles-lifecycle.md` |
| per-profile gateway services, LaunchAgent / systemd paths, the batch `hermes-gateways` script, ports, the dashboard `/chat` exception | `references/maintain-hermes-profiles-gateways.md` |
| "why did the switch not apply", "why is there no profile switcher", the two GitHub issues, workarounds, use-case matrix, official docs | `references/maintain-hermes-profiles-limitations.md` |

Answer the isolation question from the limitations file **before** designing a multi-bot setup: if
the plan needs one running gateway to serve a profile it was not started for, it cannot work today,
and the two issue links are the honest answer to give.

## Skill Structure

<!-- Generated by Scripts -->

```
maintain-hermes-profiles/
├── SKILL.md  (171 lines)
└── references/
    ├── maintain-hermes-profiles-gateways.md  (111 lines)
    ├── maintain-hermes-profiles-lifecycle.md  (221 lines)
    └── maintain-hermes-profiles-limitations.md  (76 lines)
```

<!-- Generated by Scripts -->

