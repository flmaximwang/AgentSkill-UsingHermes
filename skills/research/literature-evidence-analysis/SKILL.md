---
name: literature-evidence-analysis
description: Methodological patterns for analyzing claims in scientific literature — evidence tiering, software dependency verification, method extraction, and common traps in methods-section interpretation.
---

# Literature Evidence Analysis

Methodological patterns for critically analyzing claims in scientific papers, with emphasis on:
- Evidence tiering (direct / extrapolation / unknown)
- Software dependency verification (what does "uses X" actually mean?)
- Extracting reproduction-critical parameters from methods sections
- Distinguishing computational prediction from experimental evidence

This umbrella skill **does not** replace domain-specific sub-skills (e.g. protein design, cell biology). It provides **cross-cutting methodology** applied during any literature-evidence review.

## References

References live in this skill's `references/` directory:

| File | Covers |
|---|---|
| `evidence-classification.md` | Three-tier evidence framework for literature answers, common generalization traps |
| `software-dependency-analysis.md` | How to verify whether a dependency is truly optional or functionally required, with case studies |
| `protein-reagent-reconstitution.md` | Recover full sequence + expression/purification protocol for a published recombinant protein reagent (nanobody, Fab, enzyme) from literature + PDB |
| `heme-porphyrin-redox-chemistry.md` | Source-verified notes + citations for heme-protein Q&A: DTT×hemin redox, heme dissociation, cyt c CXXCH thioether formation, vinyl activation (incl. the Fe(II)/Fe(III) direction trap) |
| `rna-modifications-early-embryo.md` | RNA modifications × early embryonic development: evidence-tiered comparison table (m6A/m5C/m2G/m1A/Ψ/m5U/ac4C), three-layer framing (paternal / embryo-intrinsic / maternal-uterine), key papers + DOIs, beginner review reading order |
| `protein-quantification.md` | Protein concentration determination: fluorescamine protocol + buffer amine-tier rule (primary/secondary/tertiary), hemoprotein quantification when heme:protein ratio is unknown (pyridine hemochromogen vs protein assays, single-stable-residue AAA method), evaluating Chinese amino-acid-analysis providers |
| `heme-protein-absorption-bands.md` | Reporting heme-protein absorption bands WITH extinction coefficients: ε basis (per heme vs per 24-mer) trap, EcBfr reference dataset + citations, cross-species Bfr comparison, pyridine hemochromogen quantitation |
| `ligand-binding-plot-equations.md` | Carey *Ligand-binding Basics*: Klotz-vs-Carey symbol translation, Ch3 figure → y–x equation map, the three linearizations with slope/intercepts, Appendix C derived relations (1.91 log units, (80/9)K_d), and two caption/plot inconsistencies |

## Evidence Classification (Quick Ref)

When answering a scientific question, structure evidence in **three tiers**:

1. **Direct experimental evidence** — the specific system/compound was tested.
2. **Extrapolation from related chemistry/principles** — plausible but not directly tested. **Must be flagged** every time.
3. **Unknown / not studied** — no published work addresses it.

Common traps: parent-compound extrapolation, absence-of-evidence-as-absence, stability-constant migration, Cu/Zn→Fe³⁺ generalization, computational-prediction-as-structural-proof.

- **Rule-scope overreach.** A source's decision rule carries its own stated purpose; never apply it to a different purpose just because the numbers fit. Example: a textbook's "target concentration ≥ 50× Kd" thumb-rule exists to reach the stoichiometric limit for **molar-ratio** determination; using it to design a **Kd** titration collapses the isotherm to a rectangle and destroys Kd resolution (the information lives in the curved region near [Lf] ≈ Kd; the book itself prescribes complementary high/low target regimes). When building a derived tool (cheatsheet, calculator) from a source, preserve the source's scenario distinctions and label any inferred numbers explicitly as inference — never as the source's rule.

Two more traps from a live heme-chemistry session (DTT × hemin; case notes in `references/heme-porphyrin-redox-chemistry.md`):

- **Mechanism-story-as-fact.** An unverified rationalization offered as settled chemistry ("ferric heme activates the vinyls — keep the system aerobic") was later directly contradicted by experimental evidence found in the same session (spontaneous thioether formation needs Fe(II)/divalent metalloporphyrins, NOT Fe(III)). Rule: never let a plausible mechanism drive practical advice (buffer recipes, redox conditions, reagent choices) without a direct citation; tag it Tier 2 and actively search for the direct experiment before committing.
- **Electronic-argument direction check.** Before accepting a plausible-sounding inference — including the user's own — verify the underlying principle points the same way. Example: "Fe(III) can't stabilize the Cα carbanion, hence covalent binding is blocked" is backwards — electron-withdrawing groups stabilize adjacent carbanions (EWG lower π*, better acceptor), so an electron-poor Fe(III) ring should stabilize the carbanion *better*. If a plausible electronic argument contradicts a direct observation, the argument is not the explanation: say so plainly and cite what the authors actually proposed instead (here: a pre-complexation/hydrophobicity effect, explicitly "mechanistic basis not given").

## Figures and captions: read the pixels, recompute the numbers

When the question is about a **figure** (axis variables, slope/intercept annotations, tick
values, curve shape), text extraction is not evidence. `pdftotext` / `read_file` scramble or
drop text inside figures, so a grep can return the caption while none of the labels appear.
Render the page and read it visually:

```bash
pdftoppm -f <pdfpage> -l <pdfpage> -r 200 -png book.pdf out   # then vision_analyze
```

Go to `-r 400` plus a PIL crop when labels are small — a whole-page read misses tiny axis
text. Text-stream order also cannot tell you *which* label sits at which intercept, so verify
label-to-position assignment visually before quoting it.

Three rules that follow:

- **Mark every equation as printed-in-source or reconstructed.** Figures reprinted from
  another source (e.g. a textbook reproducing Klotz 1997 plots) carry no equation in this
  book's text layer; the equation you supply is your reconstruction and must be labelled so.
- **Recompute what the caption claims.** Caption parameter values can fail to reproduce the
  plotted curve — simulate the equation with the caption's numbers before repeating them as
  fact, and report the discrepancy instead of quoting the caption (a hemoglobin-binding
  caption in Carey 2026 does exactly this; see `references/ligand-binding-plot-equations.md`).
- **Cite the printed page, not the PDF page.** See the page-mapping step below.

## Locating content in a book PDF

**Printed page ≠ PDF page** — they typically differ by 15–25 pages (cover/front matter/TOC
occupy leading PDF pages), and citing the wrong one silently mislabels every source reference.
Build the map before citing:

```bash
for p in $(seq 30 60); do echo -n "PDF $p :: "; pdftotext -f $p -l $p book.pdf - 2>/dev/null | head -3 | tr '\n' ' '; echo; done
```

Then **grep by PDF page, cite by printed page** (most books carry the printed number in the
running head; a chapter's first page shows the chapter number there instead).

Three extraction facts that save a detour:

- **`read_file` reporting `NeedsOcrError` does not mean the PDF needs OCR.** If `pdftotext`
  returns text, extract and proceed — typeset publisher PDFs are misdetected this way; OCR is
  only for genuinely image-only scans.
- **`pdftotext` printing `Syntax Error: Invalid XRef entry 0` while still writing output** is a
  cross-reference-table warning, not a failure — check the output is non-empty and continue.
- A Zotero item's `.zotero-ft-cache` beside the PDF is a greppable plain-text full-text cache,
  but it can be **truncated** (one cache stopped mid-book). Use it to locate, then `pdftotext`
  the whole document; never treat the cache as the complete text.

## Heme-protein absorption data (always-on)

When asked for a heme protein's characteristic absorption bands (UV-Vis), report an extinction coefficient at each band — the user wants ε, not just the wavelength ("我要对应波长的消光系数，不仅仅是对应的波长"). State the ε basis explicitly (per heme / per subunit / per 24-mer) — the biggest trap is quoting a per-heme Soret ε as if it were the whole-cage value. Bands with no published absolute ε (e.g. EcBfr reduced α/β ~558/527 nm) must be flagged as such with the alternative quantitation route (pyridine hemochromogen ε557 = 34.7 mM⁻¹cm⁻¹), never padded with a made-up number. Full dataset and workflow: `references/heme-protein-absorption-bands.md`.

## Calibrating depth to the user's familiarity

- Maxim's expert domains (protein design, Rosetta/RPXDock, geometry/group theory, crystallography): deep source-verified, definition-first, evidence-tiered answers — the default standard.
- **New/unfamiliar domains** — signals: "我对机制没有深入研究" / "介绍general的知识即可" / "只是希望开始了解": deliver a **general-level overview FIRST** and recommend review articles (综述) for further reading. Do NOT jump into deep tiering/verification; he will explicitly ask to go deeper if he wants.
- When saving such an intro answer to Obsidian, include the review list in the note so he can read further.

## Flawed-premise questions: verify, reframe, table

When a question presupposes a mechanism/finding that may not exist (e.g. "which specific RNA modification determines embryo development?" — see `references/rna-modifications-early-embryo.md`):

1. **Verify the premise with strict database queries before answering** — e.g. NCBI eutils `esearch` combining ALL claimed elements (sperm + epididymis + m6A + embryo → 0 hits = strong negative evidence). Broad web search alone returns tangential papers that mask the absence of the direct claim.
2. If the premise fails, say so plainly and **reframe the question** (user prefers this: "这个问题不好，让它更清晰") — list the flaws (single-cause assumption, conflation of independent levels, overstated causality), then answer the reframed version.
3. Answer with a **comparison table** (entity × role × mechanism × evidence strength) plus an explicit legend (e.g. ★★★ direct causal / ★★ functional / ★ correlative) — map each entity to its tier instead of implying uniform support.
4. Close with primary sources (DOIs) and a review reading order.

## Software Dependency Analysis (Quick Ref)

When a paper says a tool "depends on" or "uses" a library:

1. Check `setup.py` → `install_requires` (truly required) vs `extras_require` (metadata says optional)
2. Check the actual code: **top-level imports** = functionally required despite packaging metadata; **deferred imports** (`try/except` or inside functions) = genuinely optional
3. License-restricted software (PyRosetta, Schrödinger, Gaussian) is **always** in `extras_require` due to PyPI distribution constraints, even when functionally required
