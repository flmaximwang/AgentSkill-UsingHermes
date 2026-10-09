# Evidence Classification for Scientific Factual Answers

When answering a scientific/literature-based question, structure your answer around **three distinct tiers of evidence**. Never collapse them.

## The Three Tiers

### Tier 1: Direct Experimental Evidence
Claims supported by studies that specifically tested the system/compound/relationship in question.

**Format**: "Paper X [citation] showed Y by method Z in model W."
**Example**: "Nguyen et al. 2017 resolved the crystal structure of Cu(II)-PBT2 by X-ray diffraction."

### Tier 2: Extrapolation from Related Chemistry/Principles
Claims derived from general chemical principles, parent compounds, or analogous systems — plausible but not directly tested.

**Format**: Lead with the extrapolation AND its limitation in the same sentence.
**Example**: "8-hydroxyquinoline has a reported Fe(III) binding constant of K₁≈4.9×10¹³ [Ref], so PBT2 — being an 8HQ derivative — could in principle bind Fe(III), but **no study has directly measured this for PBT2 specifically**."

**Never present Tier 2 claims without the qualifier.**

### Tier 3: Unknown / Not Studied
Gaps that no published work has addressed.

**Format**: State the gap explicitly and name what kind of experiment would settle it.
**Example**: "No paper has tested PBT2-Fe(III) binding by ITC, UV-vis, EPR, or XAS. A UV-vis titration at pH 7.4 would clarify this."

## When You Have Only Tier 2

If web search returns only general chemistry or parent-compound data but nothing specific:
1. **Acknowledge the gap immediately** — don't build a confident answer on extrapolation alone.
2. Offer to search more specifically if the user wants a definitive answer.
3. The user may still want the theoretical reasoning for context, but they deserve to know its status.

## Common Pitfalls

- **The "parent compound" trap**: A derivative (PBT2) may differ fundamentally from the parent (8HQ) in metal-binding mode, stoichiometry, or redox behaviour. Substitutions at specific positions (C2 sidechain, C5/C7 halogens) change electron density, sterics, and denticity.
- **The "no negative result" asymmetry**: Absence of evidence ≠ evidence of absence. If no one has tested PBT2-Fe(III) binding, you cannot conclude it doesn't bind — only that it hasn't been tested.
- **The "ICP-MS indirect signal" trap**: A change in total cellular iron after drug treatment does not prove direct Fe binding/transport. It may be an indirect effect of zinc influx disrupting metal homeostasis.
- **The "stability constant migration" trap**: Never cite stability constants (logK values) measured on a parent molecule (e.g. 8HQ) as if they apply to its derivative (e.g. PBT2). Differences in substituents alter ligand electronics, denticity, and steric accessibility — and therefore the binding constant entirely. A 1968 paper on 8HQ+Fe(III) tells you nothing quantitative about PBT2+Fe(III) unless a dedicated study is cited.
- **The "Cu/Zn → Fe(III) generalization" trap (periodic-table shortcut)**: A ligand's Cu²⁺/Zn²⁺ binding properties do not predict Fe³⁺ behaviour. Fe³⁺ is a much harder Lewis acid than Cu²⁺/Zn²⁺. HSAB theory predicts different donor-atom preferences, coordination geometries, and complex stability. An 8HQ derivative that efficiently binds Cu²⁺ may bind Fe³⁺ poorly or not at all, and vice versa. If only Cu/Zn data exists, state that explicitly — don't interpolate to Fe.
- **The "citation cargo-cult" trap**: Retrieving a numeric value from a search result (e.g. "K₁ = 4.9·10¹³") and reusing it without verifying (a) what compound it was measured on, (b) what conditions (pH, solvent, ionic strength, temperature), (c) the year and method of the original study, and (d) whether it's still cited as authoritative. A spectrophotometric value from 1968 in non-physiological conditions is not a current fact unless corroborated.
- **The "computational prediction as structural proof" trap**: A molecular docking prediction (DiffDock, AutoDock, AlphaFold complex prediction) is **not** a structure determination. It proposes a plausible binding pose, but cannot confirm coordination geometry, bond lengths, axial ligand identity, or metal spin state. Always distinguish in your answer: (a) "the prediction suggests X binds at site Y" vs (b) "the crystal/cryo-EM structure shows X binds at site Y with residue Z as ligand." Papers that use docking alone to claim a specific binding mode almost always overstate their confidence — flag this explicitly when presenting evidence.
