# K线绘图库对比与选型 (2026-08 实测)

场景约束: 输出静态 PNG 嵌入 Obsidian 笔记、自动化流水线、中文标签。

## 对比表

| 库 | 便捷度 | 交互 | 静态图输出 | 适合本场景? |
|---|---|---|---|---|
| matplotlib 手写 | 低, K线全要自己堆 | 无 | ✅ 原生 | 最初方案, 代码长 |
| **mplfinance** (matplotlib 扩展) | **高**: 一行蜡烛+成交量+均线+水平线 | 无 | ✅ 原生 PNG | ✅ 首选 |
| Plotly | 高 (`go.Candlestick`) | ✅ 缩放/悬停/区间滑块 | 需 kaleido | ⚠️ 交互图是 HTML, Obsidian 不能原生嵌入 |
| pyecharts (ECharts 封装) | 高, 中文生态 | ✅ 漂亮 | 需 selenium/无头浏览器快照, 重 | ⚠️ 同上 |
| lightweight-charts (TradingView) | 中 (JS) | 最佳 | 需 puppeteer 服务端截图 | ❌ 重, 为网页设计 |
| Bokeh / Altair | 低 (蜡烛手拼) | ✅ | 一般 | ❌ 无优势 |

## 选型结论

Obsidian 静态笔记场景选 **mplfinance**:
- 输出 PNG、中文字体配置与 matplotlib 完全一致 (它就是 matplotlib 封装)
- 核心一行: `mpf.plot(df, type="candle", volume=True, mav=(5,20,60,120,240), hlines=dict(hlines=[7.5], colors=["red"], linestyle="--"), savefig=dict(fname="out.png", dpi=150))`
- 相比手写 matplotlib 代码量约减半

## 必须知道的坑

- `mav=` 在**传入窗口内**算均线 → 全量历史算指标原则下不可直接依赖, 自己算好再用 `make_addplot` 传窗口切片
- 需要 `DatetimeIndex` (字符串日期索引 TypeError)
- x 轴序号坐标问题见 SKILL.md 与 references/mplfinance-debug.md
- 中文字体: style 的 `rc={"font.sans-serif": [...]}` 注入, 见 SKILL.md

## 什么时候考虑交互库

- 需要临时深入分析一只票 (缩放/悬停) → 用 Plotly 起个临时 HTML, 笔记里仍用 mplfinance PNG
- 需要分享网页版图表 → pyecharts
- 用户明确要求网页仪表盘 → lightweight-charts / Plotly Dash
