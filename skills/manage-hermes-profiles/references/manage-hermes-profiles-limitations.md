# Known limitations, workarounds and use cases

These are the two limitations the note records (as of **v0.14.0+**), and they are the most
operationally important part of this skill: they decide which requests are **not possible today** and
what the honest workaround is.

## Limitation 1 — the gateway is profile-blind

**GitHub Issue [#30626](https://github.com/NousResearch/hermes-agent/issues/30626)**

1. **Gateway 是 profile-blind**
   - `hermes gateway run` 在启动时**只读取一次** `active_profile`，将其配置/技能/记忆载入内存
   - 之后运行的 Gateway 进程**不会感知** external profile 切换
   - `hermes profile use <name>` 修改的只是磁盘上的 active_profile 标记，对已启动的 Gateway 无影响

Mechanism, plainly: the profile is resolved **once at process start** and cached; there is no
re-read, no watch, no signal. So a running gateway keeps serving the profile it booted with,
regardless of what `hermes profile use` writes afterwards.

Consequences to state without hedging:

- "Switch this gateway to another profile" is **not possible** while it runs.
- "Two profiles from one gateway process" is **not possible** — that is one gateway per profile.
- A switch that appears to have done nothing is this limitation, not a bug in the switch command.

**Workaround — restart.** Switch first, restart second: `hermes profile use <name>`, then restart the
gateway (or the Desktop app) so the new `active_profile` is the one read at startup.

## Limitation 2 — the Desktop GUI has no profile switcher

**GitHub Issue [#44063](https://github.com/NousResearch/hermes-agent/issues/44063)**

2. **Desktop GUI 无 Profile 切换器**
   - Desktop 应用的设置中没有 profile 下拉框/选择器
   - 唯一办法：CLI 中执行 `hermes profile use <name>`，然后重启 Gateway 或 Desktop

**Workarounds, in order of directness:**

1. Switch in the CLI — `hermes profile use <name>` — then restart the gateway or the Desktop app.
2. Point the Desktop at a **different Remote URL**: each profile's gateway listens on its own port,
   so a per-profile port (see `manage-hermes-profiles-gateways.md`) reaches the instance you want
   without a GUI selector.
3. Use the dashboard's `/chat` tab, which bypasses the gateway entirely and follows `--profile`.

Note the asymmetry: workaround 1 is the only *supported* path the note records; 2 and 3 are the
indirect routes the note itself names.

## Use-case matrix

Scenarios where separate profiles, each with its own gateway, are the right shape:

| 场景 | Profile A | Profile B |
|------|-----------|-----------|
| 多 Telegram Bot | 个人助手 Bot | 编码助手 Bot |
| 多 Slack 工作区 | 团队 A 的 Slack App | 团队 B 的 Slack App |
| 环境隔离 | 生产实例 | 沙箱/测试实例 |
| 角色隔离 | 研究助手（专用 skills + MCP） | 写作助手（不同 skills + 模型） |
| Kanban 工作流 | Orchestrator Profile | Worker Profile（自动调度） |

The Kanban row is where `--description` pays off: with a role description, the decomposer routes by
role rather than profile name.

## Official documentation

- [Profiles: Running Multiple Agents](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
- [Running Many Gateways at Once](https://hermes-agent.nousresearch.com/docs/user-guide/multi-profile-gateways)
- GitHub Issue [#30626](https://github.com/NousResearch/hermes-agent/issues/30626) — Gateway profile-blind
- GitHub Issue [#44063](https://github.com/NousResearch/hermes-agent/issues/44063) — Desktop profile switcher feature request
- [Kanban Guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban)

## Verification date

The source note this skill was distilled from has **no verification-date header**; the limitation
behaviour above was not re-measured, because verifying it would require restarting a live gateway.
The version marker to quote is the one the note gives — **v0.14.0+** — and the issue links are the
place to check whether it still holds.
