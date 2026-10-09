# sync-basic 整表刷新：隐藏的逐只 tushare 探测（2026-08-27 实测）

## 现象

`tradingrazer sync-basic a_fund` 打印完

```
== sync-basic a_fund  source=tushare  刷新: fund_basic ==
```

后长时间（实测 1 小时级）无任何输出，看起来像卡死。**不是死锁，是设计如此 + 无进度输出。**

## 根因链（cli.py `_cmd_sync_basic` → single.py `ensure_basic` → `probe_daily`）

1. `a_fund` 是整表对象 → `scope=None` → 拉整张 fund_basic（tushare 全量场内基金约 9000 只）
2. `ensure_basic` 先批量预载 `store.list_overview_symbols("d")`（dbbaroverview interval='d'
   的 (symbol, exchange) 集合）——**库内已有日线的直接跳过探测**（秒级）
3. 无日线的每只 → `probe_daily(source, kind='fund', ts_code)` → tushare
   `pro.fund_daily(ts_code=..., start_date=19900101, end_date=today)`
4. 每次调用前 `_rate_limit()` 强制 `time.sleep(0.4 - elapsed)`（tushare `_REQUEST_INTERVAL=0.4`，
   150 次/分钟安全余量，见 sources/tushare/__init__.py）
5. `fund_daily` 按年分块（`_chunk_years`，6000 行上限）——老基金（2001 年成立）一次探测
   = 20+ 次请求
6. 限流时 `call_with_retry` 退避 5s→90s 指数翻倍、最多约 12 次，期间只打印「等待」提示

## 为什么 a_index 快、a_fund 慢

- 库里已有指数日线 → overview 命中 → 秒级跳过（9800+ 只指数瞬间完成）
- 库里基金日线 overview 实测 **0 行**（行情主库主要存股票）→ 全量探测：
  ~9000 只 × 0.4s ≈ 1 小时起步，且零进度输出

## 诊断「卡住」三步

```bash
# ① 进程还活着？CPU 低 = 在网络等待（不是死锁）
ps aux | grep "tradingrazer sync-basic" | grep -v grep
# ② 估探测量：该 exchange 集在 dbbaroverview(d) 的行数（≈可跳过数）
#    fund_basic 行数 vs overview 行数 → 差 ≈ 要探测数
sqlite3 /Volumes/SSD/TradingRazer2/vnpy.db \
  "SELECT COUNT(*) FROM dbbaroverview WHERE interval='d' AND exchange IN ('SH','SZ')"
# ③ 探测量 × 0.4s = 预估时长；限流退避期间无输出是设计
```

## 改进方向（未实施，待用户拍板）

1. `ensure_basic` 逐只循环加进度输出（每 50 只一行：已探测/总数/保留/排除）——零成本高收益
2. `call_with_retry` 限流提示带上已等待秒数/次数（区分「等待」与「卡死」）
3. 长耗时批量命令先给「预计时长 + 为什么慢」，别让用户对着黑屏猜
