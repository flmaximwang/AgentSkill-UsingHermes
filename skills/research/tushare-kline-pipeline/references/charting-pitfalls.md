# 图表绘制踩坑记录 (matplotlib 3.11.1 / mplfinance 0.12.10b0)

生产画图引擎: `chart_kline.py` 已重构为 mplfinance。以下坑全部在本会话实际遇到并验证修复。

## 1. mplfinance x 轴是序号坐标，不是日期数字（最隐蔽的坑）

现象: `mpf.plot` 正常画出蜡烛后，执行 `ax.set_xlim(datetime, datetime)` 保存 → 整图变空白（红/绿蜡烛像素为 0）。
根因: mplfinance 内部把 DatetimeIndex 映射到**序号坐标**，`ax.get_xlim()` 返回 `(-0.45, n-1+0.45)`（1 单位 = 1 个交易日）。
`set_xlim` 收到 datetime 会被 matplotlib 转成日期数字(~46000)，视野挪到数据区外，蜡烛"消失"——artists 没被删，只是看不到。

修复（序号坐标）:
```python
ax.set_xlim(-0.5, n - 0.5 + future)      # future = 右侧留白的交易日数，精确到格
if future > 0:
    ax.axvline(n - 0.5, ...)             # 边界线也要用序号
    ax.fill_between(range(n), bb_up, bb_low, ...)   # 布林带填充同理
```
另: mplfinance 输入 DataFrame 必须是 `DatetimeIndex`（字符串日期会报 `TypeError: Expect data.index as DatetimeIndex`），列名 open/high/low/close/volume。

## 2. matplotlib 3.11 混和坐标变换异常（空白图 + 画布被撑爆）

现象: `ax.text(0.006, y, text, transform=ax.get_xaxis_transform())` 且 y 为数据坐标值（如 7.5），
保存后图片变成 1725×6072（98.5% 白底）——用户看到"空白图"。
根因: 该版本中 text 的 y 被按**坐标轴比例**解释（y=7.5 → 7.5 倍轴高），`bbox_inches="tight"` 把画布撑到包含这个远距文本。

修复 A（transAxes + 轴内比例，止损标签的现行方案）:
```python
y0, y1 = ax.get_ylim()
yfrac = min(max((stop_loss - y0) / (y1 - y0), 0.02), 0.98)   # 必须 ∈[0,1]
ax.text(0.008, yfrac, f"止损 {stop_loss:g}", transform=ax.transAxes,
        ha="left", va="center", ...)
```
修复 B（annotate + 纯数据坐标）:
```python
ax.annotate(text, xy=(n-1, stop_loss), xytext=(-6, 8), textcoords="offset points", ...)
```
两条路径都验证可用；minimal repro: 单轴 + axhline + 一个 text，对比保存尺寸即可定位。

## 3. mplfinance style 覆盖中文字体

现象: 先设 `plt.rcParams["font.sans-serif"]`，`mpf.plot(style=style)` 后中文变方块（DejaVu Sans 无中文字形）。
根因: mplfinance 应用 style 时重置字体 rcParams。
修复: 字体注入 style 本身:
```python
style = mpf.make_mpf_style(
    marketcolors=mc, gridstyle=":", gridcolor="#dddddd",
    facecolor="white", figcolor="white",
    rc={"font.family": "sans-serif",
        "font.sans-serif": [font_name, "Arial Unicode MS", "sans-serif"],
        "axes.unicode_minus": False},
)
```
验证: 渲染后 stderr 无 "Glyph ... missing from font" 警告即成功（grep -c 检查）。

## 4. mplfinance title 参数不可靠

现象: `mpf.plot(..., title=..., returnfig=True)` 标题可能不出现。
修复: 不传 title，plot 后用 `axes[0].set_title(..., fontsize=14, fontweight="bold")` 显式设置。

## 5. 红涨绿跌与成交量

```python
mc = mpf.make_marketcolors(up="#e0433e", down="#2ea44f", volume="inherit",
                           edge="inherit", wick="inherit")
```
成交量面板由 `volume=True` 自动生成，颜色随涨跌继承。

## 6. 止损标签靠画布最左侧（用户偏好）

红色虚线 `ax.axhline` + 标签用 transAxes 的 (0.008, yfrac) 放最左，避免遮挡K线。不要放在最新K线旁。

## 7. 快速定位"图怎么没了"的检查法

像素级验证（无视觉工具时用）:
```python
from PIL import Image; import numpy as np
a = np.asarray(Image.open(f).convert('RGB')).astype(int)
red = (abs(a[:,:,0]-224)<45)&(abs(a[:,:,1]-67)<45)&(abs(a[:,:,2]-62)<45)
green = (abs(a[:,:,0]-46)<45)&(abs(a[:,:,1]-164)<45)&(abs(a[:,:,2]-79)<45)
print(int(red.sum()), int(green.sum()))   # 正常图 red/green 各数万; 全 0 = 蜡烛没画/视野歪了
```
加检查点: 在 mpf.plot 后、set_ylim/set_xlim 后分别 savefig 对比，二分定位是哪一步让内容消失。
