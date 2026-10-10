---
name: manage-global-heartbeat
description: "要查哪些对话挂着 heartbeat、或把它从会话外清掉/暂停/换间隔时用：扫所有 profile 的 state.db 列出 active/paused/cleared 及所属线程、触发次数、累计 token，再用官方 HeartbeatManager 清/停/改。原名 scan-heartbeat-sessions（旧触发词保留）；首选仍是在那条会话里发 /heartbeat clear。"
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, heartbeat, sessions, tokens, clear]
    related_skills: [maintain-hermes-gateway, hermes-session-routing-forensics, manage-hermes-cron-jobs]
---

# 管理全机 heartbeat（扫出 + 从会话外清/停/改）

Hermes 的 heartbeat 是**会话里设的循环指令**（`/heartbeat every 10m <prompt>`）：到点就往那条会话里塞一个
合成 turn，agent 照常跑一整轮。它跟着 **session** 走、跨 profile 分散，没有任何内置命令能列出来 ——
`hermes sessions list` / `hermes status` / `hermes cron` 都看不到它。这个技能把它扫成一张表，并在**不想惊动
那条会话**时用官方 API 直接 clear / pause / resume / set。

## When to Use（触发与边界）

- 「我有哪些对话挂着 heartbeat？」「哪个对话开了 heartbeat？」「把所有带 heartbeat 的 session 列出来」。
- 「是不是有谁在每 10 分钟自己烧 token？」「怎么突然被限流了」——先用它定位是谁在重复跑。
- **「把那条 heartbeat 清掉/停掉」**「从外面把心跳关了」——用 `heartbeatctl.py`（Step 4），不必去那条会话里发命令。
- 要判断「某条心跳要不要动」：表里有它的触发次数、所属线程、该 session 的累计输入 token。

不属于本技能：

- **网关自身的活体心跳**（`$HERMES_HOME/gateway/gateway.heartbeat`、`state.db` 的 `gateway_heartbeats`
  表）——那是「网关进程还活着吗」，与循环指令同名不同物 → `maintain-hermes-gateway`。
- 消息进错了 agent / 线程被别的 bot 接管 → `hermes-session-routing-forensics`。
- cron 定时任务的增删 → `manage-hermes-cron-jobs`：heartbeat 不是 cron，两套存储两套命令。

## 流程

### Step 1 · 扫

```bash
python3 ~/.hermes/skills/hermes/manage-global-heartbeat/scripts/scan-heartbeats.py
```

默认扫 `$HERMES_HOME/state.db`（default profile）+ `$HERMES_HOME/profiles/*/state.db`（其余 profile），
active 排最前，然后按最近触发时间倒序。常用变体：

```bash
python3 …/scan-heartbeats.py --active            # 只看在跑的
python3 …/scan-heartbeats.py --fail-on-active    # 有 active 就退 1（当闸门用）
python3 …/scan-heartbeats.py --hermes-home /path/to/home
python3 …/scan-heartbeats.py --self-test         # 临时库自检，不碰真实数据
```

退出码：`0` 扫完、`2` Hermes home 不存在、`--fail-on-active` 且有 active 时 `1`。这个脚本**只读**
（每个库 `mode=ro` 打开）；要改就走 Step 4。

### Step 2 · 读表

| 列 | 含义 |
|---|---|
| `PROFILE` | `default` 或 `profiles/<name>`；同一个 heartbeat 只属于一个 profile |
| `SESSION` | 拥有它的 session id（**不是** chat id）——这就是 Step 4 要传给 `--session` 的东西 |
| `STATUS` | `active` 在跑 / `paused` 暂停 / `cleared` 已清 / `unparsable` 解析不了 |
| `EVERY` / `FIRES` | 间隔 / 累计触发次数（见 Step 3 的两条读法） |
| `LAST` | 最近一次触发（本地时间） |
| `MSGS` / `IN_TOK` | 该 session 的消息数与**累计输入 token** |
| `PROMPT` | 心跳里那句指令原文 |
| `TITLE / CHAT` | 从 `sessions` 表 join 出来的会话标题与 Discord chat/thread id |

### Step 3 · 判读（三条反直觉的读法）

1. **`FIRES` 与 `created_at` 是跨 session 续命的**：网关重启会换 session id，heartbeat 由
   `migrate_heartbeat_to_session()` 搬到新 id 上，计数与创建时间**继续累加**。所以同一条心跳会在同一个
   chat 里留下多条记录（迁移前的旧 id 变成 `cleared` 残余），而 active 那条看起来像
   「设了 6 天、触发 800 次」——那是这条 heartbeat 的血统，不是 6 天里有 800 次真实调度。
2. **烧的不只是心跳本身**：`IN_TOK` 是该 session 的累计输入 token，而每次调度都要把**整段历史**重发一遍。
   一个 12 万 token 的会话，每 10 分钟就是 2 次调用 × ~12 万 = ~24 万/10 分钟，一天量级是亿。
   换句话说：**heartbeat 的成本是它挂着的那个会话的长度**，不是那 9 个字符的回复。
3. **`unparsable` 不等于在跑**：这几条是老格式/空值的残留行，status 未知。判「有没有东西在跑」只看
   `STATUS=active`；`--active` 已经把这类排除掉了。

### Step 4 · 改（从会话外，走官方 API）

```bash
P=~/.hermes/skills/hermes/manage-global-heartbeat/scripts/heartbeatctl.py
python3 $P --session <session_id> status          # 只读：看这条的现状
python3 $P --session <session_id> clear           # 等价于在那条会话里发 /heartbeat clear
python3 $P --session <session_id> pause           # 保留、不再触发（可 resume）
python3 $P --session <session_id> resume
python3 $P --session <session_id> set 10m "检查当前进度"
python3 $P --self-test                            # 临时 HERMES_HOME 里跑一遍全流程
```

每个动作都先打 `before`、改完从库里 `load` 一次打 `after` —— **看见 after 才算改到**。
`clear` 走官方 `HeartbeatManager.clear()`：把 `status` 置成 `cleared` 并**保留那一行**（触发次数与创建时间
是它唯一的审计痕迹），`load_heartbeat()` 之后返回 `None`，轮询端不再触发。

**为什么不能手改库**：`state_meta` 那行 JSON 是 `HeartbeatState.to_json()` 的产物，手写一个字段就可能写成
解析不了的行，而 `store_has_active_heartbeat()` 对解析不了的行**按 active 处理**（未知即保守）——你以为停了，
别的调用方照样按「有活跃心跳」对待。

**唯一的例外（会复活）**：交互式 CLI 里开着的会话，它的 watchdog 把 `HeartbeatManager` 缓存在内存里，
下次轮询用自己的内存态 `save_heartbeat()` 把 `active` 写回去（`due_prompt()` 自己就会 save）。那种情况必须
在**那条会话里**发 `/heartbeat clear`。Discord / gateway 侧每次轮询都新建 manager、从库里 load，所以从会话外
清是有效的（实测见基线）。判据：`after` 为 no heartbeat，**并且**越过下一个 due 时刻后 `FIRES` 不再增长、
`gateway.log` 里该 chat 没有新的 heartbeat 注入。

## 检查点

| 触发 | 动作 |
|---|---|
| 要 clear 一条 active heartbeat | 先说清代价（不可恢复；要重建就重新 `set`）与影响范围（哪个对话、多少 token），再动 |
| 手上这条挂在交互式 CLI 会话上 | STOP：内存态会把它写回来 —— 改在那条会话里发 `/heartbeat clear` |
| 用户问的是「网关还活着吗」而不是「谁在循环跑」 | STOP：走 `maintain-hermes-gateway`，别拿 heartbeat 表当活体证据 |
| 表里有 active 就想直接停 | 先报「它在哪个对话、烧了多少 token、是谁开的」，把「停不停」留给用户 |
| 想动非 default 的 profile | 加 `--hermes-home`，别改脚本默认值 |
| 想手写 `state_meta` 那一行 | STOP：走 Step 4 的 API（手写容易变成「解析不了 = 被当成 active」的行） |

## 黑名单

- 别手改/删 `state_meta` 里的 `heartbeat:` 行：写坏 = 被判成 active；删行 = 丢掉触发次数与创建时间这两样
  唯一的审计痕迹（`clear` 保留行就是这个原因）。
- 别以为「清了就永远不回来」：交互式 CLI 的 watchdog 会从内存态写回去。
- 别把 `gateway.heartbeat` 文件或 `gateway_heartbeats` 表当成本技能的 heartbeat —— 同名不同物。
- 别用 `hermes sessions list` 找 heartbeat：它不显示，看不到 ≠ 没有。
- 别按 chat id 判定：状态挂在 **session id** 上，一个 chat 会有一串 session。
- 别把 `unparsable` 读成「还在跑」，也别拿 `FIRES` 当「这几天发生了几次」（它跨 session 续命）。

## 实测基线（2026-10-10 · default profile · 16 个库）

扫描（14:54）：

```
10 heartbeat row(s): active 1, cleared 5, paused 1, unparsable 3 | profiles scanned: 16
active: 20261010_094556_f55873  10m  805 次  大型自组装蛋白与SEC多峰研究 · 1556138222843600927  in_tok 1,101,252
```

从会话外 clear 这条（15:48，`heartbeatctl.py --session 20261010_094556_f55873 clear`）：

- `before: status=active every=10m fired=810` → `cleared: True` → `after: (no heartbeat)`
- `load_heartbeat()` 立刻返回 `None`；`scan-heartbeats.py --active` 输出 `no heartbeat rows`，
  10 行里那条变成 `cleared`，**行还在、`fired=810` 冻结**
- 越过下一个 due 时刻（15:54）后重扫：`FIRES` 仍是 810，`gateway.log` 里该 chat 无新的 heartbeat 注入
  ⇒ 外部 clear 对 gateway 侧有效
- 写路径自检：`heartbeatctl.py --self-test` 在临时 HERMES_HOME 里跑 set→status→pause→resume→clear 全过；
  真实库上用一个假 session id 走了一遍 set→clear 并核对行状态（随后删掉那行，行数回到 10）

**这是快照不是常量**：计数、token、行数每次都在变；复查时重跑脚本，别照抄上面的数字。

## 改名

2026-10-10 前叫 `scan-heartbeat-sessions`；改名 `manage-global-heartbeat` 是为了让名字覆盖「扫」与「改」两半（
head 的 57 字符窗口、判据与实测基线都没变，r6/r7 两轮盲测记录在 `test-results.md` 与 `docs/routing-blind-tests/`）。旧名留在 description 里当触发词。

## Support files

| 文件 | 承担什么 |
|---|---|
| `scripts/scan-heartbeats.py` | 只读扫描器（扫全机所有 profile）（`--active` / `--fail-on-active` / `--hermes-home` / `--self-test`） |
| `scripts/heartbeatctl.py` | 会话外改：`status`/`pause`/`resume`/`clear`/`set`（官方 `HeartbeatManager`，自带 before/after 与 `--self-test`） |
| `references/heartbeat-state-store.md` | heartbeat 存在哪、表结构、迁移机制、为什么内存态会复活、清/停的落点 |

## Skill Structure

<!-- Generated by Scripts -->

```
manage-global-heartbeat/
├── SKILL.md  (177 lines)
├── test-prompts.json  (47 lines)
├── test-results.md  (63 lines)
├── references/
│   └── heartbeat-state-store.md  (89 lines)
└── scripts/
    ├── heartbeatctl.py  (144 lines)
    └── scan-heartbeats.py  (230 lines)
```

<!-- Generated by Scripts -->
