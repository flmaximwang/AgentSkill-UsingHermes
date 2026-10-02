# Worker 的死亡方式与读哪一条命令

一个 kanban 卡的执行过程在库里分三层，排错时按**下→上**读，别从模型行为开始猜：

| 层 | 命令 | 它告诉你什么 |
|---|---|---|
| 事件流 | `hermes kanban show <id>` → `Events (N)` | `created` → `claimed`（带 lock/run_id）→ `spawned`（带 pid）→ `heartbeat`，以及终态的 `rate_limited` / `respawn_guarded` / `model_override_set` |
| 尝试表 | `hermes kanban runs <id> [--json]` | 每次 run 的 `outcome`、`error`、`metadata.exit_code`、耗时；`--json` 才有 `metadata`（含 `retry_status`、`claimer`） |
| 工人自己的输出 | `hermes kanban log <id> --tail N` | 唯一能看到 worker 在干什么的地方；没 spawn 过时它回 `(no log for <id> — task may not have spawned yet)` |

调度器本身在网关进程里（`kanban.dispatch_in_gateway: true`，默认 60s 一跳）：`grep 'kanban dispatcher' <HERMES_HOME>/logs/gateway.log`，正常行形如 `kanban dispatcher [default]: spawned=1 reclaimed=0 crashed=0 timed_out=0 promoted=0 auto_blocked=0`。**`spawned=0` 连着好几跳 = 没有东西被启动**，去看卡的事件流里是不是 `respawn_guarded`。

## 退出码（worker 进程 → 调度器怎么判）

| 退出码 | 调度器记的 outcome | 计不计失败 | 卡回到哪 |
|---|---|---|---|
| 75（BSD `EX_TEMPFAIL`） | `rate_limited` | **不计**（限流不该触发熔断） | `ready`，等冷却 |
| 78（BSD `EX_CONFIG`） | 终态 provider 拒绝（401/403/404/TLS） | 不耗重试次数 | **第一次就 `blocked`**：重试不可能修好 |
| 其它非零 | `crashed` / `spawn_failed` | 计 | 到 `kanban.failure_limit` 后 auto-block |

判据是**退出码**，不是错误文本。看到卡停在 `ready` 又没人跑，先 `runs` 看最后一条 `outcome`，别急着重跑或重建卡。

## `respawn_guarded` 的 reason

调度器每次跳会跑一次「这卡现在能不能起」的判定，拒绝时把 reason 写进事件流：

| reason | 触发条件 | 怎么办 |
|---|---|---|
| `rate_limit_cooldown` | 最近一次 run 是 `rate_limited`，且距其结束不足冷却时长（默认 300s；`HERMES_KANBAN_RATE_LIMIT_COOLDOWN_SECONDS` 改，0 = 下一跳就重试） | 等；把卡 pin 到能用的 provider 后到点会自己起 |
| `infrastructure_cooldown` | 最近一次是带 `infrastructure` 的 `spawn_failed`（宿主机问题，非卡的错） | 同样等冷却，它不会触发熔断 |
| provider/quota blocker | 卡上落了限流或鉴权的标记文本 | 换模型/凭据后重试 |

冷却的判据只看**最新一条已结束的 run**：更新的 crash/完成会顶掉限流那条。冷却走完会提前返回、绕过 provider blocker 分支——所以限流卡不需要人工清标记。

## 只改本卡，别改别人的 profile

```bash
hermes kanban set-model <id> <model> --provider <provider>   # 下次 dispatch 生效
hermes kanban set-model <id> none                            # 清掉（provider 一起清）
```

改用新 provider 前先证实那个 profile 自己也有可用的凭据：比两个 `.env` 里同名变量的 `sha256` 前缀（**不要把密钥打印出来**）。同名同哈希 = 直接 pin 即可；不同名/缺失 = 先问用户，别往别人的 profile 里写凭据。

重启网关来缩短冷却、或改被派 profile 的模型，都是**范围外**的动作：它会打断同机其它会话，而 `set-model` 本来就是为这个场景存在的。

## 状态语义速查

- `triage / todo / ready / running / blocked / review / done / archived`。`ready` = 排队中（可能正被冷却挡着），不是「在跑」。
- 有父卡时 `todo` → 父卡全 `done` 后由调度器提升为 `ready`；支持卡**不要** `link` 到它想解开的父卡，那会让支持卡 gated 在父卡后面、两张卡都不动。
- worker 结束不等于卡结束：只有 worker 自己 `kanban_complete` 才算完成；卡被 `blocked` 时它是在等人（comment 里写了要用户回什么）。
- 板子是**单机** SQLite（`<HERMES_HOME>/kanban.db`），调度器在同机 spawn；跨机器派活不在这个机制里。
