---
name: tushare-kline-pipeline
description: "Use for Tushare A-share K-line data, indicators, charts."
---

# Tushare K-line Pipeline (A股行情数据库 + 投资计划笔记)

Manage the user's A-share market data infrastructure: a SQLite K-line database fed by Tushare, precomputed indicators, matplotlib charts, and per-day investment plan notes in the Obsidian vault.

## Locations

- Vault: `~/Documents/Obsidian/wangfanlin2_Investment`
- DB: `💾 Database/kline.db` · Schema/usage doc: `💾 Database/README.md`
- Scripts (venv python): `⚙️ Scripts/sync_kline.py`, `chart_kline.py`, `indicators.py`
- Venv: `~/.hermes/profiles/quant-investor/venv` (tushare, pandas, matplotlib)
- Token: env `TUSHARE_TOKEN` (stored in profile `.env`; originally from `~/Documents/TradingRazer/settings.py`)
- Plan notes: `📈 投资计划/<ts_code>_<名称>/<YYYY.MM.DD>/<YYYY.MM.DD>.md`

## Database (5 tables)

| Table | Content |
|---|---|
| `daily` | RAW (unadjusted) OHLCV — source of truth, never overwrite with adjusted |
| `adj_factor` | Tushare adjustment factors per (ts_code, trade_date) |
| `indicators` | MA5/20/60/120/240 + Bollinger (bb_mid/up/low) — **computed on qfq close, full history** |
| `tickers` | symbol pool (ts_code PK, name, added_at, note) |
| `fetch_log` | audit of every fetch (dates, rows, ok, msg) |

Full DDL + useful queries: `references/db-schema.md`.

## 免费指数分钟线数据源（2026-08-16 实测矩阵）

指数/分钟级行情不依赖 tushare 时，候选免费源实测结论在 `references/free-index-minute-sources.md`：
新浪新接口 1m 上限 1023 根、**新浪老接口 5m+ 上限 5000 根**（当前最优 5m+ 源）、腾讯 mkline 1m 上限 800 根
（count>800 回退 320）、东财本机网络层不可用、baostock 登录连不上、Ashare=封装腾讯+新浪无魔法。
指数 1m 免费天花板 ≈1023 根，要更久历史只能每日增量落库累积。

## Commands (run from vault root)

```bash
P=~/.hermes/profiles/quant-investor/venv/bin/python
export TUSHARE_TOKEN=$(grep -oE '^TUSHARE_TOKEN=.*' ~/.hermes/profiles/quant-investor/.env | cut -d= -f2-)
$P "⚙️ Scripts/sync_kline.py" add 000537.SZ 绿发电力   # register + full fetch + adj + indicators
$P "⚙️ Scripts/sync_kline.py" sync [codes...]          # incremental daily update
$P "⚙️ Scripts/sync_kline.py" full <code>             # force full rebuild
$P "⚙️ Scripts/sync_kline.py" calc [codes...]          # recompute indicators only
$P "⚙️ Scripts/sync_kline.py" adj [codes...]           # fetch adj factors + recompute indicators
$P "⚙️ Scripts/sync_kline.py" list | stats
$P "⚙️ Scripts/chart_kline.py" 000537.SZ 2026-08-10 --name 绿发电力 --stop-loss 7.5 -o out.png
# chart flags: --adj qfq|raw (default qfq), --window N (default 250, 0=all),
#              --ylim MIN MAX (fixed price range), --future N (right-side blank for projection),
#              --start-date YYYY-MM-DD (mutually exclusive with --window), --title, --name
# production chart engine is mplfinance — see references/charting-pitfalls.md before editing draw()
```

## Core conventions (user-mandated — do not regress)

1. **Indicators on FULL history, then truncate for display.** Never compute MA/BB on the display window only — early-window values would be wrong. Load all rows ≤ end_date, compute indicators, then `.tail(window)` for plotting.
2. **Derived indicators are stored in the DB**, not recomputed ad hoc per request. `indicators` table is recomputed (delete + insert) after every add/sync/full/adj. Charts read from the table (fallback: compute on the fly only if table empty).
3. **前复权 (qfq) is the standard** for indicators and charts — matches the user's trading app. `qfq_price = raw_price × factor ÷ latest_factor`. Raw prices stay in `daily`; factors in `adj_factor`. When a new ex-rights event occurs, the whole qfq history shifts — that's inherent; `sync`/`adj` re-run refresh automatically. `--adj raw` exists for explicit raw view (indicators then computed on the fly, since DB indicators are qfq).

- **指标计算脚本（`ind_*.py`）**：缠论脚本遵循用户标准 CLI 参数模式（2026-08-14 规范），详见下方「缠论指标脚本」章节与 `references/chanlun-indicators.md`。

## 缠论指标脚本（ind_chanlun_*）

- 位置：`🧠 System/多空信号验证/指标计算/`；三个独立脚本 `ind_chanlun_bi/v2/v3.py`（互不影响，各写自己的 signals CSV）+ 公共库 `ind_chanlun_common.py`（笔+lag+CSV）+ `ind_common.py`（数据加载/周期重采样）
- **v3 通用参数模式（用户 2026-08-14 规范；其他指标脚本若要统一接口照此）**：
  ```bash
  python ind_chanlun_v3.py 000001.SH 318000.SZ --database <库路径> \
      -o <输出目录> --interval d --start-time 2024-01-01 --end-time 2026-08-13
  ```
  - 位置参数：标的代码可多个（ts_code 格式；GC=F/XAU 亦可）
  - `--database`：**必填、无默认指向**（脚本设 `KlineDBAPI.DB = path` + `_RAW_CACHE.clear()`）
  - `-o/--output`：默认 `.`，每标的一个 `<标的>_chan_v3.csv`，列 = date, signal(1/-1/0), lag
  - `--interval`：**与 vnpy 对齐** `1m/5m/15m/30m/1h/2h/4h/d/w/mn`（默认 d）；d/w/mn 走 K_DAY/K_WEEK/K_MON（周/月由日线 resample W-FRI/ME 聚合，与 KlineDBAPI._load 规则一致）
  - `--start-time/--end-time`：时间范围过滤；`chan_bi_signal` 必须传同样 begin/end（截断重算，否则笔 idx 与 df 对不上）
  - 分钟级数据现状：库里只有 d / 4h / 30m(部分个股)；2h/1h/15m/5m/1m 无数据会提示"无该标的/周期数据"
- 数据读取走缠论 KlineDBAPI（用户仓库 `指标计算/KlineDBAPI.py`，sys.modules 注入供 CChan 加载，双结构支持任意 DB）——详见 `references/chanlun-indicators.md` 与 `scripts/prove_kline_api.py`

## Investment plan notes

For "give <code> a plan note for <date>": register ticker if missing → generate chart (end_date = day BEFORE note date — **never include the note day's bar**) → write note. Template: `templates/plan-note.md`. Frontmatter keys are fixed by user convention: `tags`, `stop-loss`, `source` (YAML frontmatter, not loose lines). Image embedded via `![[<same-dir>.png]]` or relative path.

## Pitfalls

- **跨会话接手"上个会话未完成任务"**：先 `session_search` + 查 todo 完成状态，勿重复验证/重复做已完成的工作（2026-08-14 用户两次纠正："迁移已经结束了，你在上个会话里已经检查过了"、"为什么缠论的数据源问题你做了这么久"）。被中断的"进行中"任务 ≠ 未完成——先查状态再动手。
- **改共享适配层先确认入口文件**：chan.py 只加载 `DataAPI.<文件名>`（`importlib.import_module`），顶层同名副本不生效且相对导入直接报错；改 KlineDBAPI 前先确认权威版路径（2026-08-14 改错顶层副本白费一轮）。调试残留文件要及时清理，勿留冗余副本。
- **Tushare single-call cap ≈ 6000 rows** (daily and adj_factor). Always chunk by year (loop `start_date=YYYY0101`, `end_date=YYYY1231`) with ~0.35s sleep.
- **Never print the token.** Extract via shell variable from TradingRazer settings.py (`grep -oE 'TUSHARE_TOKEN = "[^"]+"'` + sed) and append to profile `.env`; verify with masked output (`grep -q ... && echo STORED`). Token is 40+ hex chars.
- **adj_factor needed for qfq correctness**: fetch factors for ALL history (year-chunked), not just recent; latest factor in range is the qfq reference.
- matplotlib: macOS Chinese font via `font_manager.addfont('/System/Library/Fonts/PingFang.ttc')` then set `font.sans-serif`; the "Failed to find font weight bold" warning is harmless (falls back to 400).
- **mplfinance x-axis uses ORDINAL coordinates** (1 unit = 1 trading day), NOT date numbers. `ax.set_xlim(datetime, datetime)` converts to date numbers (~46000) and zooms to empty space → candles appear to vanish (blank-looking chart) even though the artists are fine. Use `ax.set_xlim(-0.5, n - 0.5 + future)`; boundary `axvline` and `fill_between` x must also use ordinal `range(n)`.
- **mplfinance style overrides matplotlib font settings** → Chinese glyphs become tofu boxes. Inject the font via `mpf.make_mpf_style(rc={"font.family":"sans-serif","font.sans-serif":[font_name,"Arial Unicode MS","sans-serif"],"axes.unicode_minus":False})`.
- **matplotlib ≥3.11 blended-transform trap**: `ax.text(..., transform=ax.get_xaxis_transform())` with a data-coordinate y misplaces the text (~y axes-heights above the plot); with `bbox_inches="tight"` the canvas balloons to thousands of px tall (observed 1725×6072, 98.5% white → user sees a "blank chart"). Fix: `transAxes` with a clamped fraction `yfrac∈[0.02,0.98]` derived from `ax.get_ylim()`, or `annotate` with pure-data `xy` + offset-points `xytext`.
- **mplfinance `title=` is unreliable with `returnfig=True`** → call `axes[0].set_title(...)` explicitly after `mpf.plot`.
- **mplfinance input must be a DatetimeIndex** DataFrame with columns open/high/low/close/volume.
- Stop-loss label convention (user-mandated): dashed red hline + label anchored at the FAR LEFT of the canvas (transAxes + yfrac), so it never covers candles.
- Candles: Chinese convention 红涨绿跌 (`close>=open` red).
- A recent ex-rights date inside the display window means raw vs qfq charts differ visibly at that bar (artificial gap-down); check `adj_factor` change dates before asserting price moves.
- Verification pattern: row counts `daily == indicators` per ticker, and spot-check last indicator values against an on-the-fly computation.

## Verify after changes

`stats` (row counts match), `list` (coverage ranges), one SQL spot-check of MA/BB values vs on-the-fly pandas computation (see `references/db-schema.md` for the query).
