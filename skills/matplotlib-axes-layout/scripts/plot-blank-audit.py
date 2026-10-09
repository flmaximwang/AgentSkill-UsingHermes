#!/usr/bin/env python
"""Audit a matplotlib PNG's layout WITHOUT a vision model.

Prints:
  1. image size + rightmost non-white ("ink") column -> right blank strip
  2. an ASCII ink-density grid so the layout is visible in a terminal

Usage:
  python plot-blank-audit.py figure.png [figure2.png ...]

Notes:
  - "Ink" = pixels darker than --threshold (default 0.85 on the 0-1
    scale).  Pure white background is 1.0.
  - A right margin reserved for an outside legend that nothing occupies
    shows up as a column of '.' cells on the right of the grid.
  - Works with any matplotlib-renderable PNG (matplotlib.image.imread).
"""
import sys
import numpy as np
import matplotlib.image as mpimg


def audit(path: str, threshold: float = 0.85, cols: int = 60, rows: int = 18):
    img = mpimg.imread(path)
    if img.dtype != np.float64 or img.max() > 1.0:
        img = img.astype(float) / 255.0
    h, w = img.shape[:2]
    gray = img.mean(axis=2)
    ink = gray < threshold

    col_ink = ink.any(axis=0)
    idx = np.where(col_ink)[0]
    right = idx.max() if len(idx) else 0
    print(f"{path}: {w}x{h}")
    print(
        f"  last ink column: {right} ({100 * right / w:.1f}%), "
        f"right blank strip: {w - 1 - right}px "
        f"({100 * (w - 1 - right) / w:.1f}% of width)"
    )
    print("  density grid (. = <2% ink, digit = ink%/10):")
    for r in range(rows):
        y0, y1 = int(h * r / rows), int(h * (r + 1) / rows)
        line = ""
        for c in range(cols):
            x0, x1 = int(w * c / cols), int(w * (c + 1) / cols)
            frac = ink[y0:y1, x0:x1].mean()
            line += "." if frac < 0.02 else str(min(9, int(frac * 100 / 10)))
        print(f"  {line}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for p in sys.argv[1:]:
        audit(p)
        print()
