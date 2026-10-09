# Tushare 财务接口批量能力实测（2026-08-30）

权限结论见 `finance-interfaces.md`（17 接口最小调用全 PASS、2000 档判定）。
本文件记录**批量能力**——能否不带 ts_code 按日期拉增量，是增量同步架构的分水岭。

## 实测矩阵（无 ts_code 批量能力）

| 类别 | 接口 | 批量能力 | 说明 |
|---|---|---|---|
| 报表类 | income / balancesheet / cashflow / fina_indicator / fina_audit | ❌ 必须 ts_code 逐票 | 全市场 5551 只 × N 接口 ≈ 110 分钟（200 次/分）。只适合披露窗口（1/4/8/10 月底）后台补，**不适合每日** |
| 事件类 | express(start_date, end_date) | ✅ 公告日区间 | 实测 8/1-8/28 → 16 行 |
| | forecast(ann_date) | ✅ 单日 | 无 ts_code 时 ann_date 必填；单日 20260828 → 1 行 |
| | stk_holdernumber(start_date, end_date) | ✅ 区间 | 返回行 ann_date 列精确匹配当日（单日 20260828 → 778 行） |
| | dividend(ann_date) | ⚠️ 可疑 | 单日返回 1462 行，疑似"截止日往前"全量语义 → **未纳入每日扫描** |
| 日频 | daily_basic(trade_date) | ✅ 按交易日全市场 | 1 次调用/交易日，秒级 |

**每日增量通道 = daily_basic（1 次调用）+ 事件类区间批量（≤20 次调用）**；
报表类只在披露窗口补漏（命令见 tradingrazer2-sync-ops references/finance-incremental-ops.md）。

## ⚠️ 增量同步必须节流（实测教训）

裸 `pro_api()` 逐票猛拉立刻撞 200 次/分钟频控；超限调用被 except 跳过 → **静默丢标的**
（每只打 `✗ ... 频率超限` 后 continue，RC 仍 0，一次实测 268+ 只失败且不中断）。
修复：改用 `TushareDataSource`（`__init__` 建 `_rate_lock` 全局限流锁 + `_rate_limit()`），
逐次调用前 `src._rate_limit()`（多接口共享 200/min 硬上限）。启动后 60-90s 内
`tr '\r' '\n' < log | grep 频率超限` 应为 0。

## 其他实测

- 财务接口参数校验严格：`--part`（arparse append）多表必须 `--part a --part b`；
  `--part a b c` 只取第一个，b/c 被当位置参数 → `unrecognized arguments` EXIT=2。
- 增量实现仍"逐票拉全历史再本地过滤"（变相全量），未利用 period/ann_date 区间参数；
  估时公式：`5551 票 × 接口数 / 200 次每分`（4 接口 ≈ 2.2 万次 ≈ ~2 小时，必须后台跑）。