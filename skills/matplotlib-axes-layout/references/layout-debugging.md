# Worked example: blank strip on the right of Chrom figures

InstrumentalDataAnalyzer `Unicorn5Chrom` (Capto Core purification
logbook script `workspace/captocore.py` in the zsqlab10 vault).  Every
saved figure had a blank white band on the right.

## Code path (repo HEAD 49ab7eb, version 0.3.3)

1. `concrete/chromatography.py` — `ChromPlotArgs.__post_init__`
   hardcodes `mode = 1` and `ax_size = (16, 5)` (cm) → the fixed-size
   layout in `Signal1DCollection._make_axes` runs and `tight_layout` is
   never called.
2. `_make_axes` (signal_1d_collection.py):
   `fig_w = ax_width_in + margin_left + margin_right`, where for mode 1
   `margin_right = max(plot_args.margin[1] / 2.54, 0.7 + axis_shift * (n_twins - 1) * ax_width_in)`.
3. Mode 1 (`plot_with_all_annotations`) draws the legend with
   `ax.legend(handles=handles)` — NO `bbox_to_anchor` → default
   `loc="best"` puts the legend INSIDE the axes.
4. Result: the 2.5" right margin (reserved "outside legend") holds only
   the Conc twin y-axis spine + tick labels + ylabel "Conc (%B)"
   (~0.6"), leaving ~1.9" (~20 % of image width) pure white.

Mode 0 (`plot_with_collection_annotations`) passes
`bbox_to_anchor=(1.05, 1), loc="upper left"` (the
`legend_bbox_to_anchor` default in display.py) → legend outside → the
same margin is used.  Mode 1 is the inconsistent path.

## Measured numbers (re-check after any layout change)

- `fig.get_size_inches()` = [9.5492, 2.9685]  (16 cm = 6.2992" data area)
- main axes bbox fraction = (0.0785, 0.2021, 0.6597, 0.6631) → right
  edge at 73.8 % of figure width
- legend bbox 0.64–0.73 of figure width → inside the axes
- PNG pixel audit (300 dpi, 2861×888): last dark column ≈ 80 % of
  width; right blank strip ≈ 570 px ≈ 1.9 in
- twin-axis floor (FIXED): `0.7 + axis_shift * (n_twins - 1) * ax_width`
  = 0.7" for one twin (the first spine sits at the Axes edge, offset 0);
  the old off-by-one `n_twins` version gave 1.96" and silently clamped
  `margin_right = 0`

## Fix options (discussed; user chose option 3)

1. Anchor the mode-1 legend outside too: `bbox_to_anchor=(1.05, 1),
   loc="upper left"` so the reserved margin is actually used.
2. Shrink `margin_right` to what the twin-axis labels really need.
3. Make the margins configurable via `plot_args` (implemented).

## API change implemented (final state)

Margins moved from `Signal1DCollection` class constants
(`_MARGIN_LEFT/RIGHT/BOTTOM/TOP`) into `Signal1DPlotArgs`:

- `plot_args.margin` — **cm** (same unit as `ax_size`), ordered
  `(left, right, bottom, top)`.  Assign a scalar to set all four
  sides, or a 4-tuple.  Defaults (1.905, 6.35, 1.524, 1.016) cm = the
  historic 0.75 / 2.5 / 0.6 / 0.4 in → default output byte-identical.
- Four per-side properties `margin_left / margin_right / margin_bottom
  / margin_top`, sharing the same `_margin` tuple.  Negative values
  raise ValueError.
- No `set_margins()` method — the user explicitly preferred property
  assignment over setter methods, and required cm units (never mix
  inches with the cm `ax_size`).
- `_make_axes` converts margins to inches internally (`/ 2.54`);
  `plot_with_all_annotations` reads `margin[1] / 2.54`.

## Second bug: mode-1 margin floor silently clamped margin_right

User set `plot_args.margin_right = 0` and saw no change.  Cause:
`margin_right = max(margin[1]/2.54, 0.7 + axis_shift * n_twins *
ax_width_in)` — off-by-one.  The first twin spine sits at
`("axes", 1.0)` (offset 0); only twins after the first shift outward,
so the floor is `0.7 + axis_shift * (n_twins - 1) * ax_width_in`.
Before the fix margin_right = 0 was clamped to 1.9598" (figure 9.009"
wide, blank still 15.7 % of width); after the fix the floor is 0.7"
and the same script yields 2322 px-wide figures with content to 98.0 %
(blank ~2 %).  The 2-twin case (UV+Conc+Cond) correctly keeps the
1.9598" floor because the second spine really does shift outward.

Regression proof used: default layout reproduced identical (figsize +
axes bbox to 4 decimals); margin_right now takes effect across the
whole range — 0 → 0.7", 2.0 cm → 0.787", 5.0 cm → 1.9685", default
6.35 cm → 2.5" (figsize 9.5492); margin_left = 0 → 8.7992".

## Environment notes

- Project env: `/Applications/InstrumentalDataAnalyzer` (mamba).
- Data lives in Obsidian vault zsqlab10
  (`/Users/org_zsqlab/Obsidian/zsqlab10_gammaPFD-Fiber_2026.06.25/Logs/.../workspace/`).
- Pre-existing test failures (test_unicorn7 import error + 16 fails in
  tests/) are NOT caused by layout changes — verify with git stash
  before reporting them as regressions.
