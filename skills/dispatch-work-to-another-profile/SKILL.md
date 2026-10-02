---
name: dispatch-work-to-another-profile
description: "Use when work must go to another Hermes profile."
---

# 把活派给另一个 Hermes profile

## When to Use

- 用户点名另一个 profile / Bot 干活：「叫 <X> profile 帮我整理 …」「让 rdm-assistance 去做这个」。
- 一件活需要**那个 profile 的身份**（它自己的 memory / skills / SOUL / 模型）而不是你的。
- 你已经在对话里，但执行方是另一个 profile，且用户要它自己跑完再回来汇报。

这管的是**派发机制**（Hermes 里怎么把活交出去、怎么盯住它真跑起来）。任务的**内容契约**（任务书 + 边界 + 验收清单 + 互审）是 `agent-handoff-spec` / `agent-handoff-and-review` 的活——写卡 body 时照它们的骨架写，本技能只管怎么把这张卡送出去并确认它被执行。

## 第 0 步：先判断那个 profile 到底能不能被「叫」到

别假设 @ 一下就有人接。三种可达性，判据都是实测：

| 情况 | 判据 | 怎么办 |
|---|---|---|
| 它有自己的平台 bot | `profiles/<name>/.env` 里有 `DISCORD_BOT_TOKEN` / `FEISHU_*`；`hermes profile list` | 可以 @ 它；本文不适用 |
| 没有自己的 bot，只被 multiplex 网关代管 | `.env` 里没有 token，`gateway.profile_routes` 也没有把某个频道钉到它 | 在聊天里**无法**把它叫出来（@ 不到、路由不落它）⇒ 走 kanban |
| 它连 profile 都写错/不存在 | `hermes kanban assignees` 里没有该名字 | 先跟用户确认名字 |

- 全机只有一条 gateway 进程时（`gateway.multiplex_profiles: true`），profiles 是**共享 bot 的租户**，谁接消息由 `gateway.profile_routes` 决定；没配 routes 的 profile 在 Discord 里是隐形的，**这不是故障**，而是必须换机制。
- `hermes kanban assignees` 直接列出可以当 worker 的 profile 名（附 `ON DISK`）。用它确认名字，别猜。

## 第 1 步：写任务书（body）再建卡

先做**只读侦察**，把 body 写成可判定的规格——含糊的卡会换来一份含糊的产物：

1. 交付物收敛成**一条**验收标准：确切路径 + 确切文件名（「新建 `<repo>/summary/design_summary.csv`」）。
2. 贴**实测的地面真值**：仓库/目录当前状态、已有同类产物的路径与表头（同族仓库的先例最好，直接给路径让 worker 自己读）、可追的来源清单。标一句「逐条核，不要照抄我的数字」。
3. **点名叫出别人的在制品**：`git status --porcelain` 里不属于本次任务的改动，写明「不要 add / commit / 还原」。
4. 硬约束写死：不许编造缺失字段（读不到就留空 + 说明）、每行要能追到具体文件、抽取方法写进 comment。
5. **歧义出口**：写「先把能定的做完；发现另一层含义就 `kanban_comment` 说清缺什么 + 需要用户回什么，再 `kanban_block`」——不要因为一部分不全就整张表不做，也不要自己扩大工作面。

body 用文件传，别塞进命令行引号：`--body-file <path>`。

## 第 2 步：建卡

```bash
hermes kanban create "<一句话标题>" \
  --body-file <spec.md> \
  --assignee <profile> \
  --workspace dir:<绝对路径> \
  --created-by "<谁派的>" \
  --max-runtime 2h \
  --json
```

- **`--workspace` 默认是 `scratch`（隔离目录）**。产物要落进真实仓库就必须显式 `dir:<path>`，否则 worker 在一个空目录里凭空造文件。`worktree:<path>` 用于要开分支的代码改动。
- `--json` 的输出很长，id 常被截断——建完用 `hermes kanban ls` / `ls --json` 取 `t_xxxxxxxx`。
- 之后所有动词都用这个 id：`show` / `tail` / `runs` / `log` / `comment` / `set-model` / `complete`。

## 第 3 步：把原对话订阅到卡的终态事件

否则工人跑完了没人知道（尤其 Discord 线程里）：

```bash
hermes kanban notify-subscribe <task_id> \
  --platform discord \
  --chat-id <thread_id> --thread-id <thread_id> \
  --chat-type thread \
  --parent-chat-id <父频道 id> --guild-id <guild id> \
  --user-id <发起人 id> \
  --notifier-profile <持有该平台 bot 的 profile> \
  --delivery-mode notify
```

- **线程订阅必须给 `--parent-chat-id`（+ Discord 还要 `--guild-id`）**：没有锚点的 thread 订阅匹配不到频道级 `profile_routes`，会被路由闸静默跳过，每个 tick 都投递失败——只在日志里留一条 WARNING。
- `--notifier-profile` = 真正持有该平台适配器的 profile（多 profile 共用一个 bot 时就是主 profile），不是被派活的那个。
- `--delivery-mode`：`notify` 只发终态消息；`notify+wake` 还会唤醒目标 profile 的会话让它读板并以自己口吻回复。默认 `notify` 已经够用。
- 核对：`hermes kanban notify-list <task_id>`。

## 第 4 步：确认它**真的跑起来了**（建完就走 = 没做完）

调度器活在网关进程里（`kanban.dispatch_in_gateway`，默认 60s 一跳），不是后台守护进程：

```bash
hermes kanban ls                      # ready → running
hermes kanban runs <task_id>          # 每次尝试的 outcome / 耗时
hermes kanban log <task_id> --tail 3000   # 工人自己的输出（唯一能看出它在干什么的地方）
hermes kanban show <task_id>          # Events: created/claimed/spawned/heartbeat/...
grep -n 'kanban dispatcher' <HERMES_HOME>/logs/gateway.log | tail   # spawned=N
```

出现 `spawned=1` 且 `runs` 里有一条 `(running)` 才算真的派成功了。

## 第 5 步：工人起了又死 —— 先读 `runs` 的 outcome，再决定动不动

`runs` 的 `outcome` 决定该不该重试，**不要一看到没跑完就重建卡**：

| outcome | 含义 | 动作 |
|---|---|---|
| `rate_limited` | 被**被执行方 profile 自己的** provider 配额/限流挡下（退出码 75）；不计失败、自动 requeue | 见下：换 provider，别等 |
| `spawn_failed` | 进程没起来（环境/依赖），可能带 `infrastructure` 标记 | 看 `log` 里的启动错误 |
| `crashed` / `timed_out` | 真失败，计入 consecutive failure，到 `kanban.failure_limit` 会被 auto-block | 修卡或修配置 |

**配额墙的正解：只给这张卡 pin 一个能用的 provider，别改那个 profile 的配置。**

```bash
hermes kanban set-model <task_id> <model> --provider <provider>   # 只作用于本卡，下次 dispatch 生效
```

- 先证明新 provider 的 key 在那个 profile 里也存在：比两个 profile `.env` 里同名 key 的 `sha256` 前缀，别把密钥打印出来。key 相同 ⇒ pin 过去即可，不需要往别人的 profile 里塞凭据。
- 限流后调度器会 `respawn_guarded {reason: rate_limit_cooldown}`（默认 300s，`HERMES_KANBAN_RATE_LIMIT_COOLDOWN_SECONDS` 可调）。**等它自己过，不要为了缩短冷却去重启共享网关**——那会打断别人正在跑的会话。
- 用户要么被明确告知这个墙（哪一把配额、什么时候重置），要么就被误导成「已经交给它了」。这是必须写进汇报的事实，不是内部细节。

## 第 6 步：交出去之后不要自己接着做产物

- 侦察（读仓库、列文件、算清来源）是**写规格**的一部分，允许；把交付物先做一半再交出去就是抢活，两边产物会打架。
- 工人会自己 `kanban_comment` / `kanban_complete` / `kanban_block`，别替它改状态。

## 第 7 步：向用户汇报（结论先行）

四段，短句，别写成章节报告：

1. **已派发 + 机制**：卡 id、执行 profile、工作目录（说明产物写回仓库本体还是隔离目录）；点名「Discord 里没有它的 bot，所以不能 @ 它」这类**为什么用这个机制**。
2. **中途踩到的坑 + 已绕过**（如配额墙 + pin provider），带原始报错的关键句和退出码。
3. **怎么自己看**：`hermes kanban show <id>` / `tail <id>`。
4. **已订阅**：跑完或阻塞会自动发到本线程。

## 陷阱

- **`--workspace` 默认 scratch**：忘了写 `dir:` ⇒ 产物落在隔离目录，用户在自己的仓库里什么也看不到。
- **线程订阅漏 `--parent-chat-id`**：订阅「建成功」却不投递，唯一线索是日志里的一条 WARNING。`notify-list` 只会告诉你订阅存在，别把它当投递证明。
- **把 `ready` 当成「在跑」**：`ready` 只是排队；只有 `runs` 里有未结束的行 + 日志有 `spawned=1` 才是真在跑。
- **`rate_limited` 不计失败**：配额墙不会把卡 auto-block，它会退成 `ready` 静静等冷却——不看 `runs` 就会以为还在跑。
- **别去改被派 profile 的模型/密钥/技能来「让它能跑」**：per-card 的 `set-model` 是为此存在的，改动别人的 profile 是范围外的破坏。
- **kanban 是单机的**：板子是本机 SQLite，调度器在同机 spawn worker；跨机器派活不在这个机制里。

## 支持文件

- `references/dispatch-work-to-another-profile-kanban-worker-failure-modes.md` — 退出码 / outcome / 冷却 / respawn 守卫的对照表，以及每格该读哪条命令。

## Skill Structure

<!-- Generated by Scripts -->

```
dispatch-work-to-another-profile/
├── SKILL.md  (150 lines)
├── test-prompts.json  (14 lines)
└── references/
    └── dispatch-work-to-another-profile-kanban-worker-failure-modes.md  (51 lines)
```

<!-- Generated by Scripts -->
