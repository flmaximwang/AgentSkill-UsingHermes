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
`HeartbeatManager.set|pause|resume|clear|due_prompt`），触发由 `hermes_cli/cli_loops_mixin` 里的 watchdog
轮询（`POLL_SECONDS = 5`，锚点在触发后重置 ⇒ 忙的时候一小时只弹一次）。间隔下限 `MIN_INTERVAL_SECONDS = 60`。

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
- 同一 chat 里留着若干条旧 session 的残留行，多数已被标成 `cleared`；
- 少数行是**早期格式/空值**，`json.loads` 直接失败 ⇒ 本技能把它们判成 `unparsable`（status 未知），
  **不要**当成「还在跑」。判活跃只看 `status == 'active'`。

残留行没有维护者，删不删都不影响行为；要清理就删 `state_meta` 里对应的那一行（本技能的脚本不做这件事）。

## 成本为什么会失控

heartbeat 每触发一次就是一个正常的 agent turn：**整段会话历史重发一遍**。所以

- 成本 ≈ (会话上下文长度) × (每小时触发次数)；12 万 token 的讨论线程 + 10 分钟间隔 ≈ 每小时 ~144 万输入 token。
- 表里的 `IN_TOK` 是该 session 的累计输入 token（`sessions.input_tokens`），可以直接当「这条心跳养出来的会话有多贵」的下界看。
- 429 / 限流通常先出现在**这条会话所用的 provider** 上（例如自定义 base_url 的套餐按 1h/6h 加权额度计费），
  对照 `$HERMES_HOME/logs/agent.log` 里的 `API call #N: model=… in=… cache=…` 与 `Sustained usage limit` 行即可定位。

## 停 / 改的正确落点

都在**持有它的那条会话**里发命令，heartbeat 不认 chat id：

| 目的 | 命令 |
|---|---|
| 看当前会话的 heartbeat | `/heartbeat` |
| 设 | `/heartbeat every 10m <prompt>` |
| 暂停 / 恢复 | `/heartbeat pause` / `/heartbeat resume` |
| 清掉 | `/heartbeat clear` |

代价说清楚：`clear` 之后没有历史可恢复，要重建就得重新发一遍设置命令；只想停就 `pause`。
