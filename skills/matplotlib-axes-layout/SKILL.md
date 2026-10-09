---
name: matplotlib-axes-layout
description: >
  Replace figsize + tight_layout with a fixed Axes data-area size
  (ax_size) + explicit positioning, so Axes dimensions stay identical
  across figures regardless of legend width, tick-label length, or
  title content.
category: software-development
---

# Matplotlib Axes Layout: Fixed Data-Area Size

## Problem

`fig, ax = plt.subplots(figsize=(w, h))` + `fig.tight_layout()` gives
the **Figure** a fixed size but lets `tight_layout` shrink/grow the Axes
data area to fit labels, legends, and titles.  When two figures have
different legend widths (e.g. short vs long signal names), their Axes
data areas end up with different **absolute** dimensions — making visual
comparison unreliable.

## Solution: `ax_size` + manual positioning

Define the **Axes data area** (region between spines, not including
labels/ticks/title/legend) as a fixed (width, height) in inches.
Compute the Figure size = `ax_size` + fixed margins, then place the Axes
explicitly with `fig.add_axes()` or `ax.set_position()`.

### Margin constants (inches)

| Margin    | Default | Purpose                        |
|-----------|---------|---------------------------------|
| left      | 0.75    | ylabel + ytick labels           |
| right     | 2.5     | outside legend / twin axes      |
| bottom    | 0.6     | xlabel + xtick labels           |
| top       | 0.4     | title                           |

Override `margin_right` when the plot has twin axes (mode 1) — each twin
spine at `("axes", 1 + shift * i)` needs extra right space.

### Reference implementation

See `references/axes-layout-impl.md` for a full `_make_axes()` helper
that handles 1×1, multi-grid, and fallback-to-`plt.subplots` paths.

### Usage

```python
# Instead of:
fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(x, y)
fig.tight_layout()

# Do:
ax_w, ax_h = 10, 3        # desired data-area size
margins = dict(ml=0.75, mr=2.5, mb=0.6, mt=0.4)
fig_w = ax_w + margins['ml'] + margins['mr']
fig_h = ax_h + margins['mb'] + margins['mt']
fig = plt.figure(figsize=(fig_w, fig_h))
ax = fig.add_axes((
    margins['ml'] / fig_w,
    margins['mb'] / fig_h,
    ax_w / fig_w,
    ax_h / fig_h,
))
ax.plot(x, y)
# No tight_layout call — Axes position is fixed.
```

### Pitfalls

- **Do NOT call `fig.tight_layout()` after manual positioning** — it
  overrides explicit positions and defeats the purpose.
- **`ax.set_position()` vs `fig.add_axes()`**: `add_axes` is simpler
  when creating one Axes; `set_position` is useful when modifying an
  existing Axes created by `plt.subplots`.
- **Right margin for outside legend**: `bbox_to_anchor=(1.05, 1)` in
  axes coords places the legend's upper-left corner 5 % beyond the Axes
  right edge.  The legend box then extends rightward — ensure `mr` is
  generous enough.
- **Grid layout (subplot grid)**: `ax_size` becomes the per-subplot
  data-area size.  Figure width = `ax_size[0] * ncols + ml + mr`.
  Each cell at column `c` gets `left = (ml + c * ax_size[0]) / fig_w`.
- **Twin axes (mode 1)**:  Twin spines sit at `("axes", 1 + shift*i)`.
  The FIRST twin (i = 0) sits exactly at the Axes right edge (offset
  0) — only spines beyond the first shift outward.  The right-margin
  floor must therefore be `0.7 + axis_shift * (n_twins - 1) *
  ax_size[0]` (~0.7" for the last twin's tick labels + ylabel, plus
  the shift of every twin after the first).  An off-by-one `n_twins`
  in this floor silently clamps user-set margins:
  `mr = max(margin_right, floor)` ignores any setting below the floor
  (margin_right = 0 still reserved ~1.96" for a single twin).  Debug
  hint: when a user reports "setting X has no effect", look for
  `min()`/`max()` floors clamping it before suspecting the setter.
- **Blank strip on the right = margin reserved but not used**: a wide
  right margin sized for an outside legend (`bbox_to_anchor=(1.05, 1)`)
  stays empty when the code path draws the legend INSIDE the axes
  (`ax.legend(handles=handles)` — default `loc="best"`).  Seen in
  InstrumentalDataAnalyzer Chrom mode 1: 2.5" right margin, legend
  inside, only the twin y-axis labels occupy ~0.6" → ~20 % of image
  width blank white.  Fix: anchor the legend outside in EVERY plot
  path, or size `margin_right` from what actually lives there.
- **Keep margins in the plot-args object, not class constants**: in
  InstrumentalDataAnalyzer the margins live on `Signal1DPlotArgs` as a
  single `margin` property in **cm** (same unit as `ax_size` — never
  mix inches for margins with cm for the data area) plus four per-side
  properties `margin_left/right/bottom/top`:
  `plot_args.margin = 1.0` (all sides) | `= (left, right, bottom,
  top)` | `plot_args.margin_right = 2.5`.  Defaults (1.905, 6.35,
  1.524, 1.016) cm = the historic 0.75 / 2.5 / 0.6 / 0.4 in so default
  output is unchanged.  Negative values raise ValueError.  Layout code
  reads them from `plot_args` and converts to inches internally
  (`/ 2.54`).
- **User API style: property assignment, not setter methods** (Maxim):
  when exposing configurable values prefer `.attr = value` properties
  (incl. one per individual field) over `set_*(...)` methods — the
  `set_margins()` method was explicitly rejected in favour of
  `plot_args.margin = ...` / `plot_args.margin_left = ...`.

### Annotating curves without collisions

Interval brackets, arrow spans and formula labels that describe a curve
are the main source of ugly figures. Two failure modes, both avoidable
by construction rather than by nudging coordinates:

- **A label parked on the curve.** Nudging the text off the curve and
  giving it a white `bbox` masks the curve instead of fixing the
  overlap — the figure now hides data.
- **Two spans stacked at the same `y`.** Nested interval brackets drawn
  at one height force their labels to collide with each other and with
  whatever curve crosses that band.

Fix: give the annotations their own **gutter**. Extend `ylim` below the
data range (e.g. `set_ylim(-0.55, 1.06)` for data in `[0, 1]`), draw a
solid line at the data floor, and lay the spans out as a short row of
bars in the negative space with each label directly beneath its bar.
Collision becomes geometrically impossible, and the reader compares the
intervals side by side at one fixed scale — usually the whole point of
the figure. Keep the y-ticks explicit
(`set_yticks(np.arange(0, 1.01, 0.2))`) so the gutter does not acquire
meaningless negative tick labels.

For a **schematic** panel with no data (a number line, a concept
drawing), draw exactly ONE axis: `spines["left"].set_visible(False)`
plus `set_yticks([])`. Otherwise a hand-drawn baseline floats above a
second real axis complete with its own ticks — two axes for one
variable.

### Verifying a layout

**With a vision model available, look at the PNG.** Render a throwaway
first version, load it with `vision_analyze`, and ask a *directed*
question that names the elements and asks about collisions, clipping and
overlaps ("do the two bracket labels overlap each other or the curve; is
anything clipped at the edges?"). An open "does this look okay?"
returns reassurance and misses the defects. Patch, re-render, look again
— two passes is normal. The defects this catches (label-over-curve,
ambiguous label ownership, a duplicate axis) are exactly the ones a
numeric audit cannot see.

**Without a vision model**, when a figure "looks wrong" (blank strips,
cut-off labels), verify numerically instead of guessing:

- Introspect the live Figure: `fig.get_size_inches()`,
  `ax.get_position()` (fractional bbox), `legend.get_window_extent()`
  — decide inside-vs-outside and measure the unused margin.
- Audit saved PNGs with an ASCII ink-density grid (downsample to
  ~60×18 cells, print dark-pixel fraction per cell) — the layout
  becomes visible in a terminal.  Ready-to-run:
  `scripts/plot-blank-audit.py <png> ...`.
- Regression-check a layout change by reproducing and comparing
  `fig.get_size_inches()` + `ax.get_position()` before/after; the data
  area must stay identical.
- Reproduce the user's script in a temp dir (copy script + data files)
  instead of re-running it in their workspace — never clobber their
  generated artifacts (PNGs, logs).  Confirm the interpreter resolves
  the editable repo install (`instrumental_data_analyzer.__file__`
  points at the repo, not site-packages) and compare file mtimes
  (script vs output) to see whether the script was actually re-run
  after the edit.
- Before blaming your change for test failures, `git stash` → run the
  suite → `git stash pop`; pre-existing failures fail identically on
  the clean tree.

Worked example (Chrom blank-strip diagnosis + the plot_args margin
API): `references/layout-debugging.md`.

### When NOT to use this

- Quick interactive exploration: `plt.subplots` + `tight_layout` is
  simpler and usually good enough.
- Figures that must fill a fixed paper or slide size: set `figsize` and
  keep `tight_layout`.
