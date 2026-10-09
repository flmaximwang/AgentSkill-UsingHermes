#!/Applications/InvestAdvisor/venv/bin/python
"""K线图渲染健康检查 — 判断 PNG 是否真的画出了蜡烛。

用法: verify_chart.py <png路径> [--expect-ticks 120]

检查项:
  1. 文件有效且尺寸正常 (高度不被 bbox_inches='tight' 异常撑大)
  2. 红涨绿跌蜡烛像素存在 (红/绿为 0 = 蜡烛未渲染, 常见于 x 轴视图错位)
  3. 整体非白占比在合理区间

退出码: 0 = 健康, 1 = 异常
"""
import sys
import numpy as np
from PIL import Image


def check(path: str, expect_ticks: int = 120) -> int:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    a = np.asarray(img).astype(int)

    ok = True
    # 1. 尺寸: 正常日K图高宽比约 0.5~0.8; 异常高(>2500)说明被远处文字撑开
    if h > 2500:
        print(f"FAIL: 高度异常 ({h}px), bbox_inches='tight' 可能被坐标变换异常撑开")
        ok = False

    # 2. 蜡烛像素 (红涨 #e0433e / 绿跌 #2ea44f)
    red = (abs(a[:, :, 0] - 224) < 45) & (abs(a[:, :, 1] - 67) < 45) & (abs(a[:, :, 2] - 62) < 45)
    green = (abs(a[:, :, 0] - 46) < 45) & (abs(a[:, :, 1] - 164) < 45) & (abs(a[:, :, 2] - 79) < 45)
    nr, ng = int(red.sum()), int(green.sum())
    if nr + ng < expect_ticks * 50:
        print(f"FAIL: 蜡烛像素过少 red={nr} green={ng} (期望 >={expect_ticks*50}), 视图可能偏移")
        ok = False
    else:
        print(f"OK: 蜡烛像素 red={nr} green={ng}")

    # 3. 非白占比: 正常 8~15% (只有网格线会 ~3%)
    np_ratio = 100 * (a.max(axis=2) < 250).mean()
    if np_ratio < 5:
        print(f"FAIL: 非白占比过低 {np_ratio:.1f}% (图疑似空白)")
        ok = False
    else:
        print(f"OK: 非白占比 {np_ratio:.1f}%")

    print(f"size={w}x{h}")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(check(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 120))
