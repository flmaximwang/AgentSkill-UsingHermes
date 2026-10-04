---
name: leave-and-rejoin-a-discord-thread
description: "要让 bot 自己退出某个 Discord thread、或问「把它踢出 thread 后它还会不会回话」时用：`DELETE`/`PUT /channels/<id>/thread-members/@me` 零权限自进退，附 A/B 实测的「退出≠闭嘴」结论与真正让某个 bot 在这个 thread 闭嘴的三条配置路。"
---

# 让 bot 自己进退一个 Discord thread

## When to Use

触发：

- 要让某个 bot **自己**退出一个 thread（不想找服务器管理员、也没打算给它 Manage Threads）
- 要确认「把它踢出 thread 之后，它还会不会继续回话」（**会** —— 硬事实 3）
- 一个 thread 里有多个 bot，只想让其中一个不再参与
- 要查一个 thread 当前有哪些成员、自己在不在里面

边界（不属于本 skill）：bot 离线 / 在线但静默 / 日志里没有 `inbound message` 这一类网关诊断 →
`maintain-hermes-gateway`；把这个 skill 装到别的 profile 或别的机器 → `install-hermes-skills`。

## 硬事实（2026-10-04 在本机与 TeamJade 实测）

| # | 事实 | 证据 |
|---|---|---|
| 1 | **自己退出**：`DELETE /channels/<thread_id>/thread-members/@me` → `204`，**不需要任何权限**（不需要 Manage Threads）；`PUT` 同路径加回 → `204` | 实测 204 / 204；成员表读回只剩另一个 bot |
| 2 | **踢别人**：`DELETE /channels/<thread_id>/thread-members/<user_id>` 需要 **Manage Threads** | 推荐权限装出来的 Hermes bot（角色 `Hermes`、`Maxim 的 Agent`，无 MANAGE_THREADS）实测 `403 Missing Access (50001)` |
| 3 | **退出 ≠ 闭嘴**：退出 thread 之后，这个 bot 仍然收到该 thread 的消息、仍然回话 | A/B 对照见下 |
| 4 | Hermes 侧压根不看 Discord 成员表：discord adapter 里没有任何 `thread-members` 调用；是否回话由**本地**参与记录 `<HERMES_HOME>[/profiles/<p>]/discord_threads.json` + mention 规则决定 | `grep -rn "thread-members" plugins/platforms/discord/adapter.py` 零命中；`_in_bot_thread()`（`adapter.py:2363`）、`ThreadParticipationTracker`（`gateway/platforms/helpers.py:157`） |
| 5 | **归档 / 锁定 thread 也能自进退**（与官方 Docs 的 "Also requires the thread is not archived" 相反） | `archived=true` 的 thread 上 leave → `204`、join → `204` |
| 6 | 加入/移除会留下一条 `added/removed … from the thread` **系统消息，Discord 不允许删除** | discord-api-docs issue #6108、discussion #5038 |
| 7 | 被 `@` 一次就会被 Discord **自动加回**成员表 | Discord 行为：人类 mention 会把目标用户加进 thread |
| 8 | 想让某个 bot 真的闭嘴 → 改它自己的配置（见 Step 4），踢成员表没用 | 硬事实 3 + 4 |

### 硬事实 3 的 A/B 对照（一次性 thread `1556208599146172476`，父频道 `1554352200950612001`）

| 轮次 | 接收方 WFL-MacBook2022 是不是 thread 成员 | 发送方（另一个 bot）发的同一条 mention | 结果 |
|---|---|---|---|
| A | 是（thread owner） | `<@1554354291987451955> 测试A：…回复字母 A` | 网关 `inbound message … chat=1556208599146172476` → 回复 `A` |
| B | **已被 `DELETE @me` 移出（204，成员表只剩发送方）** | 同一路径、同样字面 mention，`测试B` | **照样** `inbound message` → 回复 `B` |

机制：官方 Docs 说明 app 连上 Gateway 时就订阅了 thread 事件（"Upon connecting to the Gateway, apps will be automatically
subscribed to thread events and active threads"），投递看的是**父频道可见性**，不是 thread 成员表；而 Hermes 的中继判断
（硬事实 4）又只读自己的本地记录。所以"踢出成员表"只改变参与者列表，副作用是留下一条删不掉的系统消息。

## Step 4 · 想真闭嘴：三条配置路（改那个 bot 的 profile）

三个都是**该 bot 自己的**设置（`<HERMES_HOME>/config.yaml` 或 `<HERMES_HOME>/profiles/<name>/config.yaml`，env 变量优先），
改完 `hermes gateway restart`：

| 目标 | 设置 | 依据 |
|---|---|---|
| 只在这个 thread 闭嘴 | `discord.ignored_channels: ["<thread_id>"]`（thread id 就是 channel id） | 频道闸的 key 集合含 thread 自身 id 与父频道 id（`_discord_channel_keys`，`adapter.py:5057`），且 "Ignored beats allowed"（`adapter.py:4078`）；env：`DISCORD_IGNORED_CHANNELS` |
| 多 bot 共用 thread：只有被 @ 才回 | `discord.thread_require_mention: true` | `_in_bot_thread()`（`adapter.py:2363`）：thread_require_mention 打开后 thread 与频道同口径；env：`DISCORD_THREAD_REQUIRE_MENTION` |
| 别把它拉进来 / 别 @ 它 | —— | @ 一次就被自动加回（硬事实 7）；`DISCORD_ALLOW_BOTS` 管的是「别的 bot 发来的消息」，与成员表无关 |

行号是 2026-10-04 的快照，函数名比行号耐用。

## Workflow

```bash
S="<本 skill 目录>/scripts/discord_thread_membership.py"

# Step 1 · 拿 thread id：Discord 客户端右键 thread → Copy Thread ID（需开 Developer Mode）；
#          或 curl GET /guilds/<guild_id>/threads/active；Hermes 会话里 thread id 就是它的 chat id
# Step 2 · 看清现状（自己在不在里面、谁在里面、是否已归档）
python3 "$S" status <thread_id>
# Step 3 · 进退
python3 "$S" leave <thread_id>          # 自己退出，零权限
python3 "$S" join  <thread_id>          # 再加回来
# Step 4 · 要它别说话：改配置，不是踢成员表
```

token 与代理都由脚本自己从 profile 的 env 文件读（`--profile light` → `<HERMES_HOME>/profiles/light/.env`；
`default` → `<HERMES_HOME>/.env`），**token 永不回显**。

代理解析顺序：`--proxy` → 本进程的 `HTTPS_PROXY`/`HTTP_PROXY`/`ALL_PROXY` → **profile env 文件里的
`DISCORD_PROXY`/`HTTPS_PROXY`/`HTTP_PROXY`**。第三条是必须的：Hermes 网关的代理写在 env 文件里、由 `env_loader`
注入进程，**手跑一个 shell 拿不到它**，而这类主机往往又不能直连。两台机器的实测正好互为反面：

| 机器 | 直连 | 代理 | 说明 |
|---|---|---|---|
| 本机 macOS | `http=000` | 进程 env `HTTPS_PROXY=http://127.0.0.1:7890` → 200 | 代理在进程 env 里 |
| NAS DS220+（`light` profile） | 连接被拒 | env 文件 `DISCORD_PROXY=http://127.0.0.1:7893` → 通 | 只在 env 文件里；脚本自己读它才跑得通 |

`status` 的第一行把这两件事回显出来，先看它再怀疑别处：`auth: <env 文件路径>` ＋ `proxy: on|off (<来源>)`。

## 退出码

| 码 | 含义 | 触发点 |
|---|---|---|
| 0 | 成功（`status` / `leave` / `join` / `remove` 走通） | 204 / 200 |
| 1 | 用法或 API 错误（含网络/代理不通） | token 有效但请求失败 |
| 2 | 找不到 token | env 文件缺失或没有 `DISCORD_BOT_TOKEN` |
| 3 | 权限不足（403） | 典型：`remove` 别人而没有 Manage Threads |
| 4 | thread 不可操作（403 且 thread 处于 archived/locked） | 预测分支，**本轮实测未复现**（硬事实 5：归档 thread 上的自进退照样 204） |
| 5 | thread 不存在或该 bot 看不见（404） | 私有 thread 未受邀、id 写错 |

## 检查点

| 触发 | 动作 |
|---|---|
| 要 `remove` 别人的成员资格 | STOP：那要 Manage Threads。先说明权限从哪来（服务器设置里给 bot 角色勾 Manage Threads，或让所有者手动），别默默升权限 |
| 「踢出去之后它就不说话了吧？」 | STOP：先纠正（硬事实 3），再给 Step 4 的配置路；不要把踢成员表当作静音手段交付 |
| 手上没有 thread id | 不要猜：`status` 一个错的 id 会照常跑（404/exit 5），但会更像"权限问题" |

## 坑

- **"踢出 thread" 有三种含义**，先分清再动手：① 让 bot 自己退（Step 3，零权限）；② 把别人的成员资格删掉（需 Manage
  Threads）；③ 让它别回话（Step 4，配置）。用户说"踢出去"时问的往往是 ③。
- **归档的 thread 上照样能自进退**（实测），所以别把"thread 已归档"当成 leave 失败的解释——先读 `status` 的真实字段。
- **系统消息删不掉**：每一次加/退都会在 thread 里留下一条系统提示（硬事实 6），所以别拿"leave → join"当无痕的探活手段；
  本 skill 的实测都在一次性 thread 上做。
- **`PUT @me` 不是"重新加入"的唯一后果**：只要你还能看见父频道，你从来就没有"收不到消息"过（硬事实 3）——把它讲成
  "退出了就收不到" 是最容易犯的解释错误。
- **别把 token 写进命令行**：脚本默认读 env 文件；`--token` 是给一次性调试的，出现在 shell 历史里就等于泄露。
- **网关的代理不在你的 shell 里**：`<HERMES_HOME>/profiles/<profile>/.env` 里的 `DISCORD_PROXY` /
  `HTTPS_PROXY` 只被 gateway 进程读到（`hermes_cli/env_loader.py` 在进程内注入），手跑脚本时进程 env 是干净的，
  而这类主机又常常不能直连 —— 症状是一个没有上下文的 `URLError: [Errno 111] Connection refused`（NAS `light`
  profile 上实测）。脚本现在自己会去 env 文件读代理；换机器/换端口时先看 `status` 的第一行。

## 实测基线（2026-10-04，本机 macOS + TeamJade）

```
status    exit=0   thread '🧪 测试完成(可删除)'  archived=False member_count=2  self_is_member=True
leave     exit=0   204，成员表 2 → 1
status    exit=0   self_is_member=False（--json 可解析）
join      exit=0   204，成员表 1 → 2
remove    exit=3   403 Missing Access (50001)   # 无 Manage Threads 时踢别人
token缺   exit=2   指定不存在的 env 文件
归档后     leave → 204 / join → 204             # 与官方 Docs 相反
--profile travel-guider status → exit=0，self_id 变成那个 profile 的 bot（token 解析正确）
```

远端 NAS（host `10.10.74.242`，hostname `WFL-DS220p2022`）的 `light` profile，**从 hub 安装的那份**再跑一遍：

```
修代理前 → error: request failed: URLError: [Errno 111] Connection refused          # exit=1
修代理后 → auth: /var/services/homes/…/.hermes/.env / proxy: on (…:DISCORD_PROXY)
           status exit=0，列出两个成员、self_is_member=True
```

第一次的失败就是上面那条"坑"：NAS 只能走它自己的代理，而代理只写在 profile 的 env 文件里。

## 汇报形状

结论先行（"能，零权限；但踢出去不等于它会闭嘴"）→ 一条可复制命令 → 然后是机制与配置路。给用户看的永远是**可执行的**
那一段；把"为什么踢了没用"放在后面，因为这是他会回来追问的第一个问题。

## Support files

| 文件 | 承担什么 |
|---|---|
| `scripts/discord_thread_membership.py` | `status` / `leave` / `join` / `remove` 四个子命令，stdlib、退出码见上；token 从 profile env 文件读，不回显 |
| `references/leave-and-rejoin-a-discord-thread-evidence.md` | 原始回执：A/B 的日志原文、权限矩阵、Hermes 侧代码指针、归档 thread 的矛盾点、遗留测试 thread |

## Skill Structure

<!-- Generated by Scripts -->

```
leave-and-rejoin-a-discord-thread/
├── SKILL.md  (169 lines)
├── test-prompts.json  (27 lines)
├── references/
│   └── leave-and-rejoin-a-discord-thread-evidence.md  (164 lines)
└── scripts/
    └── discord_thread_membership.py  (332 lines)
```

<!-- Generated by Scripts -->
