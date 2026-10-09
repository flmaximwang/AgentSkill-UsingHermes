# Heme-Protein Absorption Bands + Extinction Coefficients: Literature Lookup

Use when asked for a heme protein's characteristic absorption bands (UV-Vis) — the answer must carry an extinction coefficient per band, not just a wavelength.

## Always-on reporting rules

- **Report ε with every band, not just the wavelength** (user preference). If a band has no published absolute ε, state that explicitly and give the alternative quantitation route — never fabricate a number.
- **State the concentration basis explicitly**: per heme / per subunit / per 24-mer. Mixing these up changes the number by ~24× or ×n_heme — the most common error in this task. E.g. EcBfr ε418 = 107,000 M⁻¹cm⁻¹ is PER HEME, not per 24-mer.
- **Tier the evidence**: protein-of-interest-direct vs other-species Bfr extrapolation; flag extrapolation every time (evidence-tiering rule).
- Heme content of purified Bfr is variable (EcBfr isolated with ~1.0–1.5 heme/24-mer, loadable to 12) → any per-cage number must specify the heme count used.
- Read past the abstract into the methods section — abstracts never state the ε basis; the methods paragraph does.

## Workflow

1. Zotero MCP first (short queries, author+year) for the specific literature.
2. Web for concrete ε numbers: search `author year extinction coefficient <band>nm <protein>`; extract full text (PMC/RSC/OUP open access) and confirm the number AND its basis before reporting.
3. Report: λ + ε + basis + source, tiering species-direct vs extrapolated.

## EcBfr (E. coli bacterioferritin) reference dataset

| Band | λ | ε | Basis | Source |
|---|---|---|---|---|
| Soret, oxidized Fe³⁺ heme | 418 nm | 107,000 M⁻¹cm⁻¹ | per heme | Yasmin 2011 JBC; Bradley 2017 Metallomics |
| Protein (apo) | 280 nm | 33,000 M⁻¹cm⁻¹ | per subunit (variant-specific: W133F 23375, Y25F 25585, Y58F 24600) | Yasmin 2011; Bradley 2017; RSC Nanoscale 2022 (3.33×10⁴) |
| Free hemin stock | 385 nm | 5.9×10⁴ M⁻¹cm⁻¹ | per hemin | RSC Nanoscale 2022 |
| β / α bands (reduced Fe²⁺ heme) | ~527–530 / 557–560 nm | **no absolute ε published for EcBfr** | — | used only as reduced-minus-oxidized difference indicator (Pullin 2021 monitors A558–A571 for heme redox state) |
| Pyridine hemochromogen (heme-b quantitation) | ε557(red) = 34.7 mM⁻¹cm⁻¹; Δε557−540 = 22.1 M⁻¹cm⁻¹ | per heme | Paul 1953; Barr & Guo 2015; Falk |
| Ferroxidase center Fe | ~300 nm | ~3,380 M⁻¹cm⁻¹ per Fe | per iron | Yang 2000 Biochemistry |
| Iron mineral core | 400 nm | 870 M⁻¹cm⁻¹ per Fe | per iron | Yasmin 2011 JBC |
| Dithionite (reductant stock) | 320 nm | 8,000 M⁻¹cm⁻¹ | per dithionite | Yasmin 2011 JBC |
| Ferrozine (released Fe²⁺) | 562 nm | 27.9 mM⁻¹cm⁻¹ | per Fe²⁺ | ferrozine method (generic) |

Key papers: Yariv 1983 (Biochem J 211:527, 417/530/560 nm); Andrews 1995 JBC 270:23268 (Soret/β/α of oxidized heme = 418/525/560, heme-free M52H variant); Pullin 2021 Angew Chem Int Ed 60:8376 (reduced→oxidized: Soret blue-shifts, α/β bleached; A558–A571 redox probe); Bradley 2017 Metallomics 9:1421; Yasmin 2011 JBC 286:3473; Yang 2000 Biochemistry 39:4915.

## Cross-species Bfr comparison (extrapolation tier — flag when used)

- R. capsulatus Bfr (reduced): 557 (α) / 526 (β) / 417 (Soret) nm — Ringeling 1994.
- A. baumannii Bfr: 418 Soret, 567/530 α/β, ~740 nm bis-Met CT, ~300 nm Fe³⁺ core — Sci Rep 2024.
- M. tuberculosis BfrA: ox Soret 409 → red 423; α/β 557/526 — PLoS One 2009.
- D. desulfuricans Bfr: 715 nm weak band (bis-Met axial ligation) — Biochemistry 2000.
- Bis-Met coordinated low-spin ferric heme gives a weak ~715–740 nm CT band; a Soret below 400 nm signals HIGH-spin (unbound) heme.
