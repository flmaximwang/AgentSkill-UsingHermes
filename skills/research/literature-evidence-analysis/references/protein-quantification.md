# Protein Concentration Determination — Fluorescamine, Hemoproteins, Amino-Acid Services

Durables for answering "how do I quantify this protein correctly" — covers fluorogenic amine assays, buffer-interference tiers, and hemoprotein-specific traps (heme:protein ratio unknown).

## Fluorescamine assay essentials

- Principle: fluorescamine is non-fluorescent until it reacts with **primary amines** (N-terminal α-NH₂, Lys ε-NH₂) to give a fluorescent pyrrolinone. Ex ≈ 380–400 nm (365 nm UV LED works), Em ≈ 460–480 nm.
- Microplate protocol (Udenfriend 1972 / Lorenzen 1993): 150 µL sample in PBS pH 7.4 per well, add 50 µL of 3 mg/mL (10.8 mM) fluorescamine in **anhydrous acetone** while shaking, shake 1 min, read Ex 400/Em 460. Linear 0–500 µg/mL BSA; hyperbolic to 1000 (4-param fit).
- Micro-volume variant (NanoDrop 3300 manual): 9 µL sample + 3 µL 3 mg/mL in DMSO, 15 min RT, Ex 365/Em 470, linear 8–500 µg/mL.
- Always matrix-match: blanks/standards/samples in the **identical** buffer, and calibrate with the **same purified protein**, not BSA — response scales with Lys content and free N-terminus, so protein-to-protein variation is large.
- Reagent handling: stock must be fresh and dry (rapid aqueous hydrolysis, seconds at pH 8–9 — add fast while mixing); protect reagent and reacted solutions from light; keep the organic-solvent fraction constant across wells (fluorescence depends on solvent ratio); read within a few hours; avoid microbubbles and turbidity; a blocked N-terminus (acetylated / pyroGlu) gives no signal.

## Buffer amine-tier rule (the core decision table)

Fluorescamine fluorescence requires PRIMARY amines, so buffer interference splits by amine class — not all "amine buffers" are equal:

| Buffer class | Examples | Outcome |
|---|---|---|
| Primary amine | Tris, glycine, ammonium | **BAD** — two independent mechanisms |
| Secondary amine | Tricine, TES, TAPS | React to **non-fluorescent** products; at high concentration compete and suppress protein signal |
| Tertiary amine | Bis-Tris, HEPES, MOPS, MES, PIPES | Safe — no background, no reagent competition; only caveat is low working pH |
| No amine | PBS, borate | Preferred |

- The Tris failure is TWO-layer: (1) Tris itself forms a fluorescent adduct → constant background; (2) Tris competitively **consumes the reagent**, suppressing protein signal **multiplicatively** (e.g. 50 mM Tris in 150 µL sample ≈ 14× the ~2.7 mM final reagent). Mechanism (2) is why blank subtraction cannot rescue a Tris-buffer measurement.
- Practical fallback when a sample is stuck in Tris: (a) desalt/exchange into PBS/borate (cleanest), or (b) matrix-match standards AND keep Tris low and identical in every well — variable Tris (gradient elution) makes this unreliable.
- Bis-Tris (tertiary amine) is safe for the amine-background problem, but its 5.8–7.2 working range sits below the assay optimum of 8–9 → lower yield; compensate with longer incubation, keep pH ≥ 6.5.
- The same primary-amine interference applies to ninhydrin-based amino acid analyzers — vendors likewise warn against Tris/glycine in samples.

## Hemoprotein quantification when heme:protein ratio is UNKNOWN

- The classic "cytochrome quantification" methods measure **heme, not protein**:
  - **Pyridine hemochromogen** (Berry & Trumpower 1987, Anal Biochem 161:1-15): 20% pyridine / 50–75 mM NaOH, ferricyanide-oxidized vs dithionite-reduced, scan 500–650 nm; c-type heme ε₅₅₀(red) ≈ 29.1 mM⁻¹cm⁻¹ (30.27 used in literature), Δε₅₅₀₋₅₃₅(red−ox) ≈ 24 mM⁻¹cm⁻¹. Returns heme concentration only.
  - **Reduced-minus-oxidized difference spectra**: α-band ~550–552 nm (c-type) or Soret ~416–420 nm (reduced); calibrate with horse-heart cytochrome c.
- **Never convert heme concentration into protein concentration unless the heme:protein ratio is established** — bacterial multi-heme cytochromes carry 2–16 hemes per protein, and recombinant c-type cytochromes often have <100% heme occupancy (partial loading). Establish the ratio once, then routine quantification may use the cheap heme assay.
- Heme interference in protein assays (pick accordingly):
  - A₂₈₀: inflated by heme UV/Soret tail — unusable.
  - BCA: heme Fe reduces Cu²⁺ → overestimate (any copper-reducing species interferes).
  - Lowry: heme reduces Folin reagent → high; only usable with a heme-tolerant standard.
  - Bradford: cleanest colorimetric — no redox step, reads 595 nm away from heme absorption; still calibrate with the same protein.
  - Fluorescamine: no redox problem, but heme Soret (~409–420 nm) absorbs the 380–400 nm excitation → **inner filter**; dilute heavily.
  - Amino acid analysis: gold standard, fully heme-independent.
- **Known-sequence recombinant protein → use the single-stable-residue method**, not the sum of all residues: acid hydrolysis destroys Trp and oxidizes Cys, so the sum under-estimates. Take a hydrolysis-stable residue (Ala or Lys) nmol ÷ its count in the known sequence = protein moles, independent of Trp/Cys loss. Ask the provider to report per-residue absolute nmol.

## Evaluating Chinese amino-acid-analysis providers

- When the user asks to evaluate a named "service," first check whether the vendor actually **sells that service** or just a kit/consumable — a kit vendor is not comparable to a service lab.
- 北京百泰派克 (biotech-pack.com): genuine amino-acid-composition service — amino-acid auto-analyzer (post-column ninhydrin) plus an HPLC pre-column platform; BSA standard on every run; CNAS-accredited; requires >2 mg, no high salt, no primary-amine buffers; recommends 3 biological replicates for protein-concentration purposes.
- 南京建成 (njjcbio.com): **kit vendor**, not an analysis lab. Its "总氨基酸 T-AA" kit (A026) is Cu²⁺-complexation colorimetry for total free amino acids in serum/urine/food — no hydrolysis-to-composition, useless for protein absolute quantification.
- Ask any AAA provider before ordering: internal standard (norleucine/norvaline)? hydrolysis-loss correction (Ser/Thr/Tyr partial destruction, Val/Ile slow release)? Cys/Trp handling? prior experience with hemoproteins (does heme precipitate/survive acid hydrolysis, does Fe oxidize Met/Cys)? price and lead time. A provider who immediately understands the single-residue-known-sequence request is a competent analyst.
