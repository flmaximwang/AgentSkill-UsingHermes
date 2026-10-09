# kline.db Schema & Queries (wangfanlin2_Investment)

## DDL

```sql
CREATE TABLE daily (
  ts_code TEXT NOT NULL, trade_date TEXT NOT NULL,   -- PK (ts_code, trade_date)
  open REAL, high REAL, low REAL, close REAL,
  pre_close REAL, change REAL, pct_chg REAL, vol REAL, amount REAL);

CREATE TABLE adj_factor (
  ts_code TEXT NOT NULL, trade_date TEXT NOT NULL, adj_factor REAL,
  PRIMARY KEY (ts_code, trade_date));

CREATE TABLE indicators (
  ts_code TEXT NOT NULL, trade_date TEXT NOT NULL,
  ma5 REAL, ma20 REAL, ma60 REAL, ma120 REAL, ma240 REAL,
  bb_mid REAL, bb_up REAL, bb_low REAL,
  PRIMARY KEY (ts_code, trade_date));

CREATE TABLE tickers (ts_code TEXT PRIMARY KEY, name TEXT, added_at TEXT, note TEXT);

CREATE TABLE fetch_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts_code TEXT,
  start_date TEXT, end_date TEXT, rows INTEGER, ok INTEGER, msg TEXT, fetched_at TEXT);
```

## 前复权 (qfq) formula

`qfq_price = raw_price × adj_factor ÷ latest_adj_factor` (latest = factor of last trade_date in range).
Volume adjusts inversely: `vol_qfq = vol × latest ÷ factor` (keeps 成交额 consistent).
qfq == raw for all bars AFTER the most recent ex-rights date.

## Useful queries

```sql
-- MA5 golden cross above MA20 on latest day
SELECT a.ts_code FROM indicators a
JOIN indicators b ON a.ts_code=b.ts_code AND b.trade_date='20260810'
WHERE a.trade_date='20260811' AND a.ma5 > a.ma20 AND b.ma5 <= b.ma20;

-- Coverage per ticker
SELECT t.ts_code, t.name, COUNT(d.trade_date), MIN(d.trade_date), MAX(d.trade_date)
FROM tickers t LEFT JOIN daily d ON t.ts_code=d.ts_code
GROUP BY t.ts_code ORDER BY t.ts_code;

-- Ex-rights event dates (factor changes) for a ticker
SELECT trade_date, adj_factor FROM adj_factor
WHERE ts_code='000537.SZ'
ORDER BY trade_date;

-- Spot-check verification (compare DB indicators vs on-the-fly pandas):
-- compute qfq close = close*f/last_f on full history, rolling(240).mean() etc.,
-- compare against indicators table for same (ts_code, trade_date).
```

## Session facts (2026-08-11)

- 000537.SZ 绿发电力 (新型电力, listed 1993-12-10): 7,684 daily rows; last ex-rights 2026-06-26 (factor 7.0576); earlier 2025-10-28 (6.9467), 2025-06-25 (6.9154) — the 250-day display window includes the 2025-10-28 event, so raw vs qfq differ visibly there.
- 600533.SH 凌钢股份: 5,741 daily rows; last ex-rights 2024-06-26 → qfq == raw within any recent window.
- Verified qfq shift at 2025-10-27: raw close 8.87 → qfq 8.69.
- Indicator delta after switching raw→qfq (000537.SZ @ 2026-08-10): MA60 8.50→8.39, MA120 9.39→9.28, MA240 9.05→8.92; MA5/MA20 unchanged (window entirely post-ex-rights).
