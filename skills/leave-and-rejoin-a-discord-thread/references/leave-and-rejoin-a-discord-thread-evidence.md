# 原始回执：thread 成员资格与「退出≠闭嘴」

测量时刻 2026-10-04（本机 macOS 26.6.2 + TeamJade guild `1554352200313085962`）。所有数字都是那一次的实测输出，
不是从文档推的。行号是当天 Hermes clone（`~/.hermes/hermes-agent`，HEAD `f42f579cf8`）的快照。

## 1. 一次性测试 thread

| 项 | 值 |
|---|---|
| thread id | `1556208599146172476`（type 11 public thread，父频道 `1554352200950612001` = `💬-随便聊聊`） |
| 接收方 | `1554354291987451955` = `WFL-MacBook2022`（本机 default profile 的 bot，thread owner） |
| 发送方 | `1554386582969122877` = `TrvGdr1553`（本机 travel-guider profile 的 bot，用它的 token 调 REST 发消息） |
| 现状 | 已归档、改名为 `🧪 测试完成(可删除)`，成员表仍有上面两个 bot —— 没有 Manage Threads 就删不掉它，需要手动删 |

发送方用 REST 发消息（`POST /channels/<tid>/messages`，内容是字面 mention `<@1554354291987451955>`），
接收方走的是它自己常驻的 gateway —— 这样"投递"这件事才是真的被测到，而不是被模拟。

## 2. A/B：退出前后各发一条同样的 mention

网关日志逐字（`<HERMES_HOME>/logs/gateway.log`；同一 thread 两条）：

> `2026-10-04 15:37:26,589 INFO gateway.run: inbound message: platform=discord user=TrvGdr1553 chat=1556208599146172476 msg='测试A：连接测试，请只回复字母 A，不要调用任何工具。' reply_to_id=None reply_to_text=''`
> `2026-10-04 15:37:27,777 INFO gateway.run: response ready: platform=discord chat=1556208599146172476 session=agent:main:discord:thread:1556208599146172476:1556208599146172476 time=1.2s api_calls=1 response=1 chars`

> `2026-10-04 15:39:04,468 INFO gateway.run: inbound message: platform=discord user=TrvGdr1553 chat=1556208599146172476 msg='测试B：连接测试，请只回复字母 B，不要调用任何工具。' reply_to_id=None reply_to_text=''`
> `2026-10-04 15:39:05,474 INFO gateway.run: response ready: platform=discord chat=1556208599146172476 session=agent:main:discord:thread:1556208599146172476:1556208599146172476 time=1.0s api_calls=1 response=1 chars`

两者的差别只有一条：B 之前接收方执行了自退。

| 步骤 | 调用 | 回执 |
|---|---|---|
| A 前 | `GET /channels/<tid>/thread-members` | 两个成员（接收方 `flags=1`，thread owner） |
| 自退 | `DELETE /channels/<tid>/thread-members/@me`（接收方自己的 token） | `204` |
| 自退后 | 同上 GET | 只剩发送方 `1554386582969122877` |
| B | 发送方再发同形 mention | 接收方**照样** `inbound message` → 回复 `B` |
| 复原 | `PUT /channels/<tid>/thread-members/@me` | `204` |

结论：**成员表不是投递闸**。官方 Docs 的说法与此一致 —— 能看见父频道的 app 在连上 Gateway 时就订阅了 thread 事件：

> `Upon connecting to the Gateway, apps will be automatically subscribed to thread events and active threads.`

（`https://docs.discord.com/developers/topics/threads`，"Gaining Access to Public Threads" 节。私有 thread 不同：
只有成员或被邀者拿得到事件。）

## 3. 权限矩阵（同一个 bot 的 token 逐条实测）

bot 的角色：`Hermes`、`Maxim 的 Agent`；按 `GET /guilds/<id>/roles` 逐角色 OR 出来的权限里
`MANAGE_THREADS=False`、`MANAGE_CHANNELS=False`、`ADMIN=False`。

| 调用 | 结果 | 说明 |
|---|---|---|
| `DELETE /channels/<tid>/thread-members/@me` | `204` | 自己退，零权限 |
| `PUT /channels/<tid>/thread-members/@me` | `204` | 加回 |
| `DELETE /channels/<tid>/thread-members/1554386582969122877` | `403 {"message": "Missing Access", "code": 50001}` | 踢别人要 Manage Threads |
| `DELETE /channels/<tid>`（删 thread） | `403` | 删 thread 要 Manage Threads |
| `PATCH /channels/<tid>` `{"archived": true, "name": …}` | `200` | **thread creator** 可以归档/改名（不需要 Manage Threads） |
| `PATCH /channels/<tid>` `{"archived": false}`（后来解档） | `200` | 同上 |

## 4. 归档 thread 上的自进退（与 Docs 相反）

官方 Docs 在 Remove/Add Thread Member 两节各写一句 `Also requires the thread is not archived.`。
实测在 `archived=true` 的 thread 上：

```
$ discord_thread_membership.py leave 1556208599146172476
left thread 1556208599146172476 (member id 1554354291987451955)      # exit=0, HTTP 204
$ discord_thread_membership.py join  1556208599146172476
joined thread 1556208599146172476 (member id 1554354291987451955)    # exit=0, HTTP 204
```

所以脚本里那条"403 且 archived/locked → exit 4"的分支**一天都没被触发过**：它是防御性的，不是实测行为。
本轮交付的所有实测都在**未归档**状态下完成，唯一在归档态做过的就是上面这两条（也是 204）。
这条差别值得留着：下次有人报"归档 thread 上 leave 失败"，先读 `status` 的真实字段，别拿文档那句解释现象。

## 5. Hermes 侧：为什么踢成员表不影响它回话

| 事实 | 证据（clone HEAD `f42f579cf8`，2026-10-04） |
|---|---|
| adapter 从不改 thread 成员 | `grep -rn "thread-members" plugins/platforms/discord/adapter.py` → 零命中；只有测试桩 `tests/fakes/platforms/discord_standin.py` 注册了 `PUT …/thread-members/@me` 路由 |
| 是否回话由本地状态 + mention 规则决定 | `_in_bot_thread()`（`adapter.py:2363`）：`isinstance(message.channel, discord.Thread) and str(message.channel.id) in self._threads and not self._discord_thread_require_mention()` |
| 那个本地状态是什么 | `ThreadParticipationTracker`（`gateway/platforms/helpers.py:157`），落在 `<HERMES_HOME>/discord_threads.json`（每 profile 一份，上限 500 条）；adapter 用 `self._threads.mark_async(thread_id)` 在发消息时记录 |
| 频道闸认哪些 key | `_discord_channel_keys_from_channel()`（`adapter.py:5062`）：thread 自身 id、`name`、`#name`、父频道 id、父频道名 —— 所以 `ignored_channels` / `free_response_channels` / `allowed_channels` **都可以直接写 thread id** |
| 一个 thread 的静音开关 | `discord.ignored_channels: ["<tid>"]`（`adapter.py:6033`，注释在 4078 写着 "Ignored beats allowed, including via a thread's parent"）；env `DISCORD_IGNORED_CHANNELS` |
| 多 bot 共线程的通用开关 | `discord.thread_require_mention: true`；env `DISCORD_THREAD_REQUIRE_MENTION`。用户本机各 profile 的 `config.yaml` 现在都是 `false` |

## 6. 脚本的实测输出（四个子命令 + 两条失败路径）

```
$ python3 scripts/discord_thread_membership.py status 1556208599146172476
thread '🧪 测试完成(可删除)'  id=1556208599146172476 type=11 parent=1554352200950612001
  archived=False locked=False owner=1554354291987451955 member_count=2
  member 1554354291987451955 <- this bot
  member 1554386582969122877
self 1554354291987451955 is a member: True                                      # exit=0

$ python3 scripts/discord_thread_membership.py leave 1556208599146172476
left thread 1556208599146172476 (member id 1554354291987451955)                 # exit=0

$ python3 scripts/discord_thread_membership.py status 1556208599146172476 --json
{ "archived": false, "locked": false, "member_count": 1, "members": ["1554386582969122877"], …,
  "self_is_member": false, … }                                                  # exit=0

$ python3 scripts/discord_thread_membership.py join 1556208599146172476
joined thread 1556208599146172476 (member id 1554354291987451955)               # exit=0

$ python3 scripts/discord_thread_membership.py remove 1556208599146172476 --user-id 1554386582969122877
error: cannot remove 1554386582969122877 -> HTTP 403 Missing Access (50001)
hint: removing *another* member needs Manage Threads …                           # exit=3

$ python3 scripts/discord_thread_membership.py status 1556208599146172476 --env-file /nonexistent.env
error: no DISCORD_BOT_TOKEN found (looked at /nonexistent.env)                    # exit=2

$ python3 scripts/discord_thread_membership.py status 1556208599146172476 --profile travel-guider
… member 1554386582969122877 <- this bot ; self 1554386582969122877 is a member: True   # exit=0
```

最后一条证明 `--profile` 的 token 解析是真的（`<HERMES_HOME>/profiles/travel-guider/.env`）。

## 7. 网络侧

本机 `curl --noproxy '*' https://discord.com/api/v10/users/@me` → `http=000`；同一条加默认代理（`HTTPS_PROXY=http://127.0.0.1:7890`）
→ `200`。脚本用 urllib 的默认代理行为（吃 env + macOS 系统代理），所以在这台机器上不加参数就是通的；`--no-proxy`
/ `--proxy` 只在确知要换路径时用。
