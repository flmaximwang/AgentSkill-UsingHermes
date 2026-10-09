# Ligand-binding plot equations (Carey, *Ligand-binding Basics*, 2026)

Domain note for "give me the y–x equation of each figure" requests on this book. The user
works through it chapter by chapter, so later chapters reuse this.

## Symbol systems do NOT match between text and figures

Ch3's figures are reprinted from Klotz (1997), so their labels contradict the running text
(Carey's own symbols). Translate explicitly, and say which system an equation is written in.

| Klotz (Ch3 figures) | Carey (Ch2/Ch4 text) | Note |
|---|---|---|
| `B` | `ν̄·n` (mol ligand per mol target) | 1:1 ⇒ `B = ν̄` |
| `L` | `[A_f]` | figures plot **free** ligand, not total |
| `n` | molar ratio (sites per target) | |
| `k` | `K_a` | `k = 1/K_d` (Klotz uses the association constant) |

Master equations: 1:1 `ν̄ = K_a[A_f]/(1+K_a[A_f]) = [A_f]/(K_d+[A_f])` (Eq 8, p.20); any
molar ratio with equal independent sites, same form with `ν̄ = [A_b]/[S_t]` (Eq 9, p.57);
any number of events / cooperativity, Klotz–Adair (Eq 10, p.59). Klotz's plot form:
`B = nkL/(1+kL)`.

## Ch3 (Graphical Analysis, pp.33–51) — figure → y–x equation

| Fig | p | y | x | equation / relation |
|---|---|---|---|---|
| 3.1 | 34 | `B` | `L` (μM, linear) | no closed form — laurate/HSA multi-site data; the three panels are ONE dataset under different x-axis compression (Klotz's steepness illusion) |
| 3.2 | 35 | `B` | `log(L)` (ticks −9…−4) | no closed form; 1:1 equivalent `ν̄ = 1/(1+10^(pK_d−x))`, `x = log[L]_f` |
| 3.3 | 37 | `ν̄` | `−log([A_f])` (ticks 9…5) | `ν̄ = 1/(1+10^(x−pK_d))`, `K_d = 10⁻⁷ M` |
| 3.4 | 38 | — | — | structures only (PDB 3RGK / 1A3N) |
| 3.5 | 39 | `ν̄` | pO₂ (torr, linear) | Mb: `ν̄ = p/(2.5+p)`; Hb: Eq 10 with n = 4 |
| 3.6 | 41 | see next table | | three linearizations of Eq 8 |
| 3.7 | 42 | `Y` | `X` | `y = a + βx` — the linear-regression model itself |
| 3.8 | 43 | `K×10⁻⁴` (log scale) = `log K_eq` | `1/T` | van't Hoff; text says only "slope relates to ΔH°" (no coefficient printed) |
| 3.9 | 45 | upper `B/L`, lower `B` | upper `B`, lower `log L` | Scatchard, then back-transformed to semi-log |
| 3.10 | 46 | `B/L` (M⁻¹) | `B` | Scatchard form; both axes approached asymptotically ⇒ neither intercept usable |
| 3.11 | 48 | `ν̄`; `ν̄/[L]_f`; `log(ν̄/(1−ν̄))` | `[L]_f`; `log[L]_f`; `ν̄` | four-way overview: Direct ✅ Semi-log ✅ Scatchard ❌ Hill ❌ |

### Figure 3.6 — the three linearizations (all three verified algebraically)

| Panel | y | x | equation | y-int | x-int | slope |
|---|---|---|---|---|---|---|
| A | `1/B` | `1/L` | `1/B = 1/n + (1/nk)(1/L)` | `1/n` | `−k` | `1/(nk)` |
| B | `L/B` | `L` | `L/B = L/n + 1/(nk)` | `1/(nk)` | `−1/k` | `1/n` |
| C (Scatchard) | `B/L` | `B` | `B/L = nk − kB` | `nk` | `n` | `−k` |

Hill panel of Fig 3.11: `y = n_H·log[L]_f − n_H·log K_d`, straight line through `(log K_d, 0)`
when `n_H = 1`.

## Derived relationships (Appendix C) — do not re-derive

- Semi-log interval: `Δlog[A_f] = log(9 / (1/9)) = log 81 ≈ 1.9085` (i.e. 1.91 log units),
  from `[A_f]_10% = K_d/9` and `[A_f]_90% = 9K_d`.
- Direct plot has **no** constant interval: `Δ[A_f] = 9/K_a − 1/(9K_a) = (80/9)K_d ≈ 8.89 K_d`
  — it scales with K_d, which is the algebraic reason the isotherm breadth is not constant
  there (answers Thought Experiment 6).
- `ν̄ = 0.5 ⇒ [A_f] = K_d`.
- Molar ratio unknown ⇒ fit the quadratic in total ligand (Appendix C derivation 2):
  `−(1/[B_t])[A_b]² + (K_d/[B_t] + [A_t]/[B_t] + 1)[A_b] − [A_t] = 0`.
- Back-transform Scatchard → semi-log: `L = B / (k(n − B))`.
- Appendix D gives the fitting route (custom-equation fit) with the simulation snippet
  `Af = linspace(0,0.01,10000); nuBar = Af./(Kd+Af)`.

## Two caption/plot inconsistencies — flag, never repeat as fact

1. **Fig 3.5 (hemoglobin).** The caption's `K_1 = 178, K_2 = 140, K_3 = 0.01, K_4 = 0.1` torr
   do not reproduce the plotted curve: substituted into Eq 10 they put half-saturation at
   ~2.2 torr and `ν̄ = 0.999` at 26 torr — saturating *before* myoglobin (0.912), the opposite
   of the figure's low initial slope. Treat them as illustrative only; do not use them to
   regenerate the figure.
2. **Fig 3.3 caption** calls the interval "the ratio of the log … to the log …", but the
   Appendix C derivation is a **difference of logs** (`Δlog = log 81`). A ratio of logs is not
   what the math gives.

Also mind the sign convention flip: Fig 3.2 plots `log(L)` (negative ticks), Fig 3.3 plots
`−log([A_f])` (positive ticks) — same quantity, opposite sign; substituting into the wrong
form inverts the curve.

## Answer shape the user asks for

"把 Chapter N … 的 y–x 方程都告诉我" ⇒ a table: figure | page | y-axis | x-axis | equation,
plus the underlying master equation up front. Mark each equation as **printed in the source**
vs. **reconstructed** — figures reprinted from Klotz (1997) carry no equation in the book's
own text layer, so most Ch3 entries are reconstructions and must be labelled as such.
