# Full `_make_axes()` helper — reference implementation

This is the pattern applied in `InstrumentalDataAnalyzer`'s
`Signal1DCollection` (commit `ax_size` refactor).  Adapt the margin
constants and fallback logic to your project.

```python
from dataclasses import dataclass, field
import matplotlib.pyplot as plt


@dataclass
class PlotArgs:
    ax_size: tuple[float, float] | None = None


class MyPlotter:

    # Margins around the data area in inches
    _MARGIN_LEFT = 0.75
    _MARGIN_RIGHT = 2.5
    _MARGIN_BOTTOM = 0.6
    _MARGIN_TOP = 0.4

    def __init__(self):
        self.plot_args = PlotArgs()

    def _make_axes(self, nrows=1, ncols=1, *, margin_right=None):
        """
        Create a Figure + Axes with a fixed data-area size.

        When *ax_size* is set, the Axes data area (between spines) is
        exactly *ax_size* inches and its position is explicit —
        *tight_layout* must NOT be called afterwards.

        When *ax_size* is None, falls back to ``plt.subplots``.

        Returns
        -------
        ``(fig, ax)`` for 1\N{MULTIPLICATION SIGN}1,
        ``(fig, axes_2d)`` for larger grids.
        ``axes_2d`` is ``list[list[plt.Axes]]``.
        """
        ax_size = self.plot_args.ax_size
        if ax_size is None:
            fig, a = plt.subplots(nrows, ncols)
            if nrows == 1 and ncols == 1:
                return fig, a
            # Normalise to list[list[Axes]]
            if nrows == 1:
                return fig, [list(a)]
            if ncols == 1:
                return fig, [[ax] for ax in a]
            return fig, a.tolist()

        # ---- fixed-size layout ------------------------------------------------
        ml = self._MARGIN_LEFT
        mr = margin_right if margin_right is not None else self._MARGIN_RIGHT
        mb = self._MARGIN_BOTTOM
        mt = self._MARGIN_TOP

        fig_w = ax_size[0] * ncols + ml + mr
        fig_h = ax_size[1] * nrows + mb + mt

        fig = plt.figure(figsize=(fig_w, fig_h))

        axes_2d = []
        for row in range(nrows):
            row_axes = []
            for col in range(ncols):
                left = (ml + col * ax_size[0]) / fig_w
                bottom = (mb + (nrows - 1 - row) * ax_size[1]) / fig_h
                row_axes.append(
                    fig.add_axes((
                        left,
                        bottom,
                        ax_size[0] / fig_w,
                        ax_size[1] / fig_h,
                    ))
                )
            axes_2d.append(row_axes)

        if nrows == 1 and ncols == 1:
            return fig, axes_2d[0][0]
        return fig, axes_2d
```
