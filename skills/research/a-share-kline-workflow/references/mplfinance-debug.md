# mplfinance "蜡烛消失/空白图" 调试实录

症状: 图表生成无报错, 但整图几乎全白 (或 mplfinance 版红绿蜡烛像素为 0)。

## 案例 A: matplotlib 3.11 坐标变换撑爆画布 (手写版)

- `ax.text(0.006, stop_loss, ..., transform=ax.transAxes)` 且 stop_loss=7.5 → y 被当轴比例 7.5, 文字放到坐标轴上方 7.5 倍高度
- `bbox_inches="tight"` 把画布撑到 1725×6072 px (正常 1725×1136), 图内容被挤成一条 → 看起来"空白"
- 换 `get_xaxis_transform()` 也一样 (matplotlib 3.11.1 混和变换行为异常)
- **解法**: 先 `ax.get_ylim()` 算出 `yfrac = (y - y0)/(y1 - y0)`, clamp 到 [0.02, 0.98], 再 `ax.text(x=0.008, y=yfrac, transform=ax.transAxes)`。或 `ax.annotate(xy=(数据x, 数据y), xytext=(偏移pt))` 纯数据坐标。

## 案例 B: mplfinance x 轴是序号坐标 (mplfinance 版)

现象: `mpf.plot` 后图正常 (红 55k 绿 51k 像素), 一旦 `ax.set_xlim(datetime, datetime)` → 红绿像素归零, 图空白。

定位过程 (二分检查点法):
1. 在 `mpf.plot` 后立即 savefig → 蜡烛正常 → 问题在后续操作
2. 只加 `fill_between` → 正常; 只加 `set_ylim(6,14)` → 正常
3. 加 `set_xlim(日期, 日期)` → 蜡烛消失
4. 打印 `ax.get_xlim()` → 返回 `(-0.446, 119.446)` — **序号坐标!** (0..n-1, 1单位=1交易日), 不是日期数字
5. 传 datetime 进去被转成日期数字 (~46000), 视图飞到数据范围外 → 蜡烛都在, 只是看不见

解法 (在 draw 末尾):
```python
ax.set_xlim(-0.5, n - 0.5 + future)   # future=右侧留白交易日数
ax.axvline(n - 0.5, ...)              # 边界线也用序号
ax.fill_between(range(n), bb_up, bb_low, ...)  # 填充也用序号
```

## 验证方法 (每次画完必做)

用 PIL/numpy 数红绿像素 — 无视觉工具时判断渲染是否成功的客观手段:

```python
a = np.asarray(Image.open(f).convert('RGB')).astype(int)
red   = (abs(a[:,:,0]-224)<45)&(abs(a[:,:,1]-67)<45)&(abs(a[:,:,2]-62)<45)
green = (abs(a[:,:,0]-46)<45)&(abs(a[:,:,1]-164)<45)&(abs(a[:,:,2]-79)<45)
print(int(red.sum()), int(green.sum()))
```
- 健康 (120根K线): 红+绿 ≈ 8~10 万像素, 整体非白占比 ≈ 8~9%
- 红=0 且绿=0 → 蜡烛没画出来 → 查坐标/视图
- 检查尺寸: 高度异常大 (数千 px) → bbox_inches="tight" 被远处文字撑开

## 最小复现模板

```python
import mplfinance as mpf, pandas as pd
df = pd.DataFrame({"open":[1,2,3],"high":[2,3,4],"low":[1,1.5,2],"close":[1.5,2,3],
                   "volume":[100,200,150]},
                  index=pd.to_datetime(["2026-01-05","2026-01-06","2026-01-07"]))
fig, axes = mpf.plot(df, type="candle", volume=True, returnfig=True)
print(axes[0].get_xlim())   # 应是序号坐标 (-0.4..., n-1+0.4...)
```
