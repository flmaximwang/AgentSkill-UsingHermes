# heartbeat 的存储与生命周期

## 存在哪

每个 profile 一份 session 库：default 是 `<HERMES_HOME>/state.db`，其余是
`<HERMES_HOME>/profiles/<名字>/state.db`（同一个 `SessionDB` 实现，schema 相同）。

heartbeat 作为**表 `state_meta` 里的一行**存在：key = `heartbeat:<session_id>`，value = 一段 JSON：

```json
{"prompt": "检查当前进度", "interval_seconds": 600, "status": "active",
 "created_at": 1791157400.0, "last_fired_at": 1791600000.0, "fire_count": 805}
```

`status` 取值：`active`（在跑）、`paused`（暂停）、`cleared`（已清）。源码在
`hermes_cli/heartbeat.py`（`_META_PREFIX = "heartbeat:"`、`load_heartbeat` / `save_heartbeat` /
`HeartbeatManager.set|pause|resume|clear|due_prompt`）。驱动侧有两处，**都每次轮询新建 manager、从库里
load**：`tui_gateway/session_notifications.py`（`HeartbeatManager(session_id=sid_key)` 建在轮询函数里）与
网关的 heartbeat restore 路径；交互式 CLI 那条（`hermes_cli/cli_loops_mixin` 的 watchdog）**缓存实例**，
见下面「会复活」。`POLL_SECONDS = 5`，锚点在触发后重置 ⇒ 忙的时候一小时只弹一次；间隔下限
`MIN_INTERVAL_SECONDS = 60`。

直接读（不改任何东西）：

```bash
sqlite3 -readonly "$HERMES_HOME/state.db" \
  "select key, json_extract(value,'\$.status'), json_extract(value,'\$.fire_count')
     from state_meta where key like 'heartbeat:%';"
```

## 为什么同一个 chat 下有好几条

heartbeat 是 **session 级**的，而 session id 会换（进程重启、`/new`、压缩后新开）。换的时候
`migrate_heartbeat_to_session(old, new)` 把这一行搬到新 key 上 —— 计数与 `created_at` **继续累加**。
于是：

- 活跃那条的 `created_at` 可能早在几天前，`fire_count` 是好几代 session 的累计值；
- 同一 chat 里留着若干条旧 session 的残留行，多数已被标成 `cleared`（迁移时给旧 id 写了 `status=cleared`）；
- 少数行是**早期格式/空值**，`json.loads` 直接失败 ⇒ 本技能把它们判成 `unparsable`（status 未知），
  **不要**当成「还在跑」。判活跃只看 `status == 'active'`。

`clear` 与 `pause` 都**保留那一行**，所以「key 存在」不等于「在跑」；反过来
`store_has_active_heartbeat()` 对解析不了的行**按 active 处理**（未知即保守）—— 这是「别手写那一行」的原因。

## 成本为什么会失控

heartbeat 每触发一次就是一个正常的 agent turn：**整段会话历史重发一遍**。所以

- 成本 ≈ (会话上下文长度) × (每小时触发次数)；12 万 token 的讨论线程 + 10 分钟间隔 ≈ 每小时 ~144 万输入 token。
- 表里的 `IN_TOK` 是该 session 的累计输入 token（`sessions.input_tokens`），可以直接当「这条心跳养出来的会话有多贵」的下界看。
- 429 / 限流通常先出现在**这条会话所用的 provider** 上（例如自定义 base_url 的套餐按 1h/6h 加权额度计费），
  对照 `$HERMES_HOME/logs/agent.log` 里的 `API call #N: model=… in=… cache=…` 与 `Sustained usage limit` 行即可定位。

## 停 / 改：两条路，选哪条

**① 在持有它的那条会话里发命令**（最不容易出意外）：

| 目的 | 命令 |
|---|---|
| 看当前会话的 heartbeat | `/heartbeat` |
| 设 | `/heartbeat every 10m <prompt>` |
| 暂停 / 恢复 | `/heartbeat pause` / `/heartbeat resume` |
| 清掉 | `/heartbeat clear` |

**② 从会话外改**（不想惊动那条会话时）——`scripts/heartbeatctl.py`，走同一套官方 API：

```bash
python3 heartbeatctl.py --session <session_id> status|pause|resume|clear
python3 heartbeatctl.py --session <session_id> set 10m "检查当前进度"
```

它 `sys.path` 挂上 `~/.hermes/hermes-agent`、把 `HERMES_HOME` 设成目标 profile 的 home（**必须在 import
`hermes_cli` 之前设**：`SessionDB` 按 `HERMES_HOME` 缓存），然后 `HeartbeatManager(session_id=…)`。
每个动作先打 `before`、改完 `load_heartbeat()` 再打 `after`。

## 会复活的那一种（外部 clear 的唯一例外）

`due_prompt()` 用的是**实例内存里的** `self._state`，并在触发时 `save_heartbeat()` 写回去（源码
`hermes_cli/heartbeat.py:223-230`）。所以：

- **交互式 CLI** 的 watchdog 把 manager 缓存在 `self._heartbeat_manager` 上 ⇒ 你从另一个进程把库里改成
  `cleared`，它下一次轮询仍按内存里的 `active` 触发并**把 `active` 写回库**。这种会话必须在它自己里面发
  `/heartbeat clear`（那条命令走的就是那个缓存实例，`clear()` 会把 `self._state` 置 `None`，不再复活）。
- **Discord / gateway** 侧每次轮询都 `HeartbeatManager(session_id=…)` 新建、从库 load ⇒ 外部 clear 立刻生效，
  实测（2026-10-10）清掉后越过下一个 due 时刻，`fire_count` 冻结在 810、该 chat 无新的 heartbeat 注入。

判据固定两条一起看：`after` 显示 no heartbeat **且**下一个 due 时刻之后 `FIRES` 没涨。

代价说清楚：`clear` 之后没有历史可恢复，要重建就得重新 `set` 一遍；只想停就 `pause`（可 `resume`）。
