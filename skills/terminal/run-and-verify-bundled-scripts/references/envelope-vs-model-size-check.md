# Envelope vs model: is the ab initio shape oversized?

Symptom to answer: "the bead model looks big but the mass is small — the density looks low". Settle it with numbers, in
this order, before touching any algorithm setting.

## 1. Envelope volume (from the fit program's own numbers)

- Bead volume: `V_beads = N_beads x (4/3) pi r^3`, with `r` the bead ("dummy atom") radius printed in the fitter's own
  log — not a guessed default. Compare against any volume the program reports itself; ab initio fitters commonly print an
  excluded/hydrated volume together with a volume-to-mass convention (~1660 A^3/kDa).
- `N_beads` and `r` move together with Dmax: a series whose Dmax is inflated by low-q contamination gets both more beads
  and larger beads, so a volume gap can be inherited from the input curve.

## 2. Dense volume for the model's mass

`V_dense = MW[Da] x 1.22 A^3` (partial specific volume 0.735 cm^3/g). Quote `V_dense / V_envelope` as the apparent
density:

- about 1.0 — the envelope is about the protein's own volume;
- 0.3–0.4 — the envelope is 2.5–3x the model's volume and something is wrong with the pairing.

Do the division a second time with the data-derived masses (Porod volume, Vc, Bayes MW, class MW) so the reader sees
whether the envelope is oversized relative to *the model* and relative to *the data* — the two can disagree, and which one
disagrees is the whole answer.

## 3. The model's own geometry, next to the SAXS side

From coordinates: Rg over CA, maximum CA-CA distance as a Dmax proxy, residue count and MW. Put them beside the SAXS
values (Guinier Rg, IFT Rg/Dmax, MW methods). A model markedly more compact in *both* Rg and Dmax than the IFT values
cannot be made to sit in the envelope by any placement algorithm — that is an input problem, not a fitting problem.

## 4. Independent fit check

Fit the model to the same curve with a computation-based fitter (CRYSOL — see `references/atsas-cli-entrypoints.md`) and
quote chi-square. A compact ab initio envelope that reproduces the curve at chi-square about 1 for volume V is direct
evidence the scattering particle really has volume V; if the model is far smaller, the model is under-sized rather than the
envelope wrong.

## 5. Count the model before interpreting any score

Count chains / residues / CA atoms and compare with the expected oligomer. A file holding exactly **half** the CA count of
its previous version, or of the assembly the data implies, is a truncated export — ask for a re-export instead of
"fixing" the envelope.

## Metric reading rules

- Rigid-body fit correlation **rises** when the model shrinks: a small model can bury itself in the densest region of a
  coarse map. Never use it as a size check.
- Superposition NSD **rises** when the envelope is oversized (unfilled envelope volume is penalised) while the
  atom-to-nearest-bead distance distribution can improve at the same time. Report both, plus the selection parameter.
- A score that tracks concentration across a dilution series is reporting the curves, not the model.
