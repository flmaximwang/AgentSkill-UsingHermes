---
name: a-share-kline-workflow
description: "Use for A-share K-line data & charts: Tushare, mplfinance."
---

# A股K线数据与图表工作流 (Tushare + SQLite + mplfinance + Obsidian)

维护 A 股日线数据库、计算技术指标、生成日K图、创建投资计划笔记的完整流程。
用户为本流程定下的口径规则（曾被逐条纠正过）务必遵守，见「关键规则」。

## 环境（用户机器，勿假设通用路径）

- 虚拟环境: `/Applications/InvestAdvisor/venv`（tushare、pandas、mplfinance）
- 脚本（可直接执行，shebang 指向上述 venv）：
  `~/Documents/Obsidian/wangfanlin2_Investment/⚙️ Scripts/`
  - `sync_kline.py` — 数据同步/指标/复权因子
  - `kline_daily.py` — 画图（mplfinance 引擎）
  - `indicators.py` — 共享指标模块
- Tushare token: 环境变量 `TUSHARE_TOKEN`（存于 Hermes profile 的 .env；源头 `~/Documents/TradingRazer/settings.py` 的 `TUSHARE_TOKEN` 字段）
- 数据库: `💾 Database/kline.db` — 表: `daily`(不复权原始价, 真值来源)、`adj_factor`(复权因子)、`indicators`(MA5/20/60/120/240 + bb_mid/up/low, **前复权口径**全量计算)、`tickers`、`fetch_log`
- 投资计划笔记: `📈 投资计划/<ts_code>_<名称>/<YYYY.MM.DD>/<YYYY.MM.DD>.md` + `<日期>_kline.png`

## 日常命令

```bash
# 登记标的(全量拉取 + 复权因子 + 指标) / 增量更新 / 重算指标 / 拉复权因子
"⚙️ Scripts/sync_kline.py" add 000537.SZ 绿发电力
"⚙️ Scripts/sync_kline.py" sync [代码...]
"⚙️ Scripts/sync_kline.py" calc [代码...]
"⚙️ Scripts/sync_kline.py" adj  [代码...]

# 画日K图
"⚙️ Scripts/kline_daily.py" 000537.SZ 2026-08-10 -o out.png \
    --stop-loss 7.5 --window 120 --future 10 [--ylim 6 15] [--start-date ...] [--adj qfq|raw]
```

建当天投资笔记的流程：`sync` 更新数据 → `kline_daily.py` 生成图（数据截止**前一交易日**，不含当天）→ 写 md（YAML frontmatter: `tags`、`stop-loss`、`source`）→ 嵌入图片 `![[<日期>_kline.png]]`。

## 关键规则（用户纠正过的，勿再犯）

1. **指标必须用全量历史计算，再截取显示窗口**。只算窗口内数据会让 MA240 等早期数值错误。mplfinance 的 `mav=` 参数就是在传入窗口内算的，不可直接用——自己全量算好再 addplot。
2. **图表与指标统一前复权口径**：`前复权价 = 原始价 × 当日复权因子 ÷ 最新复权因子`。`daily` 表永远存不复权原始价；指标、图表用 qfq。volume 同步调整: `vol_qfq = vol × 最新因子/当日因子`。
3. **复权因子接口单次上限 6000 行**，必须按年分块拉取（同 daily）。
4. **价格区间禁止硬编码**。默认自适应: 下限=区间最低价−差值×10%，上限=最高价+差值×10%（差值=最高−最低，系数 `YLIM_PAD=0.1`）。`--ylim` 仅作临时覆盖。
5. **止损线标签固定在画布最左侧**（轴内比例 yfrac∈[0,1] + `transAxes`），不要放在最新K线旁挡行情。
6. **红涨绿跌**（中国惯例）：up `#e0433e`，down `#2ea44f`。

## mplfinance 陷阱（都实际踩过）

- **x 轴是序号坐标**（0..n-1，1 单位 = 1 个交易日），**不是日期数字**。`ax.set_xlim`/`ax.axvline` 必须用序号；传 datetime 会把视图挪到图外，蜡烛看似"消失"（图不报错、空白）。留白 N 个交易日 = `set_xlim(-0.5, n-0.5+N)`。`fill_between` 同样用 `range(n)`。
- **style 会覆盖中文字体**：`mpf.make_mpf_style(..., rc={"font.sans-serif": [字体名, ...], "axes.unicode_minus": False})`；字体名用 `font_manager.addfont(".../PingFang.ttc")` 后 `FontProperties(fname=...).get_name()` 取得。
- **`title=` 参数在 `returnfig=True` 下不可靠** → 画完后 `axes[0].set_title(...)`。
- **必须 DatetimeIndex**（字符串日期索引直接 TypeError）。
- `hlines=` 参数可用，但自己 `axhline` + 标注更好控制。

## matplotlib 3.11 通用陷阱

- `ax.text` 配混和坐标变换（如 `get_xaxis_transform`）或 `transAxes` 且 y>1 时，`bbox_inches="tight"` 会把画布撑到数千像素高 → 图看起来"全空白"。
- 解法：把位置换算成轴内比例 `yfrac∈[0,1]` 后用 `transAxes`；或 `annotate` + 纯数据坐标。

## 验证图表是否正常渲染（画完必查）

用 PIL/numpy 数红绿蜡烛像素：红/绿像素为 0 或整体非白占比骤降 = 渲染失败（最常因视图坐标错位）。脚本见 `scripts/verify_chart.py`。典型健康值: 120 根K线时红+绿像素约 8 万级，非白占比 ~9%。

## 绘图库选型结论（详细对比见 references/plotting-libraries.md）

本场景（Obsidian 静态 PNG 笔记）选 **mplfinance**：输出格式、字体处理与 matplotlib 一致，代码量减半。Plotly/pyecharts 交互强但输出 HTML，Obsidian 笔记无法原生嵌入。

## 支持文件

- `references/plotting-libraries.md` — mplfinance/plotly/pyecharts/lightweight-charts 对比与选型
- `references/mplfinance-debug.md` — 序号坐标 bug 的定位过程与最小复现（含二分检查点法）
- `scripts/verify_chart.py` — 图表渲染健康检查（尺寸/非白占比/红绿像素/留白区）
