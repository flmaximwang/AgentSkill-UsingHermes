# Commercial Biotech/Lab Product Research

When the user asks about a commercial biotech product (e.g. a culture medium, kit, reagent) and you need its **formulation, composition, or patent status**:

## Workflow

### 1. Identify Manufacturer
- Look at the product image/catalog for brand names (e.g. "2nd Lab®", "唯地生物")
- Note the Chinese company name if applicable

### 2. Find Product Page
- Many Chinese biotech sites use traditional ASP/PHP with `display.php?id=N` URL patterns
- Use the search function on the company website to find product listings
- If website navigation fails (single-page JS app), probe sequential IDs: `display.php?id=1214`, `display.php?id=1215`, etc.
- Chinese manufacturers often hide exact concentrations behind `------` in their formulation tables

### 3. Check Patents
- **Google Patents**: `https://patents.google.com/?assignee=<Chinese company name>&language=CHINESE`
- Search both the brand name (e.g. "唯地生物", "2nd Lab") and the company's full legal name
- Common result: small biotech resellers often do **not** patent their formulations — they protect them as trade secrets
- If the technology is based on published academic work (e.g. Studier 2005), the original inventor/academic institution may hold the patent, not the reseller

### 4. Determine Formulation Status
- **Published/Standard**: Check Formedium, GRiSP, Sigma, Teknova for documented g/L formulations
- **Semi-disclosed**: Product page shows base components (Tryptone, Yeast Extract) but hides exact buffer/ion/sugar concentrations
- **Trade secret**: No patent filed, detailed composition not published anywhere
- **Patented**: Check patent claims for specific formulations

### 5. Document in Obsidian
- Save findings to `🗂️ Classifications/Q-33 生物学实验与生物学技术/Culture medium/`
- Clearly note what is confirmed vs. inferred vs. hidden

## Known Commercial AIM (Autoinduction Medium) Formulations

### From Academic Literature / International Suppliers (fully disclosed)

**AIM-LB** (g/L): Tryptone 10, Yeast extract 5, (NH₄)₂SO₄ 3.3, KH₂PO₄ 6.8, Na₂HPO₄ 7.1, Glucose 0.5, α-Lactose 2.0, MgSO₄ 0.15, Trace elements 0.03

**AIM-2YT** (g/L): Tryptone 16, Yeast extract 10, (NH₄)₂SO₄ 3.3, KH₂PO₄ 6.8, Na₂HPO₄ 7.1, Glucose 0.5, α-Lactose 2.0, MgSO₄ 0.15, Trace elements 0.03

**AIM-TB** (g/L): Tryptone 12, Yeast extract 24, (NH₄)₂SO₄ 3.3, KH₂PO₄ 6.8, Na₂HPO₄ 7.1, Glucose 0.5, α-Lactose 2.0, MgSO₄ 0.15, Trace elements 0.03

### From 唯地生物 (2nd Lab) — partially disclosed

| Product | ID | Disclosed composition |
|:--------|:---|:---------------------|
| AIM-LP Broth | 1215 | Try 10 + N-Z-amine AS 6 + YE 5 + HY-YEST 444 5 + 17AA 2 + chaperoneⅠ 0.47 + thiamine 40 μg/L; extra: chaperoneⅡ |
| AIM-MP Broth | 1218 | Same base as LP + choline, inositol; extra: chaperone Ⅱ+Ⅲ |
| AIM-SB Broth | 1219 | Try 32 + YE 20 |
| AIM-TB Broth | 1221 | Try 12 + YE 24 |
| ZYM-5052 | 1222 | N-Z-amine AS 10 + YE 5 |
| AIM-Ac/Al/DiP/Hd | — | Only function description known |

> Ion concentrations, glucose/lactose: hidden (trade secret).

### Patent Status
- **Studier 2005 autoinduction**: Brookhaven Science Associates / patent applications assigned to Brookhaven
- **Fox & Blommel optimized media (2008)**: Wisconsin Alumni Research Foundation, US20080286749A1 (abandoned)
- **唯地生物 2nd Lab**: No patents found on Google Patents or CN databases

## Published Literature Strategies (by Specialized Type)

When the user needs formulations for autoinduction media optimized for specific protein types but the commercial product is a trade secret, use these published literature approaches:

| Protein Type | Literature Strategy | Key References |
|:-------------|:-------------------|:---------------|
| **Large (>80 kDa)** | Add **chemical chaperones** (osmolyte) to autoinduction base: glycine betaine 0.5–1 mM, proline 5–10 mM, trehalose 10–50 mM, or 0.3–0.5 M NaCl (induces betaine accumulation) | De Marco 2005; Blommel & Fox 2007 |
| **Membrane proteins** | Use **SBauto** (Try 32 + YE 20) base; systematically optimize glucose:glycerol:lactose ratio; add **25 mM succinate**; supplement with choline + inositol | Gordon 2008 (UK Membrane Protein Structure Initiative) |
| **Acidic (low pI)** | Use **low-phosphate buffer** (e.g. M9auto: Na₂HPO₄ 6 + KH₂PO₄ 3 + casamino acids 1 g/L) to avoid alkaline pH aggregation | General protein chemistry |
| **Alkaline (high pI)** | Use **ZYM-5052 (100 mM phosphate)** — strong buffer counters metabolic acidification | Studier 2005 |
| **Disulfide-bonded** | Autoinduction's **slow growth** naturally gives time for disulfide formation; supplement **1–2 mM GSSG** at induction (OD₆₀₀ ~0.6) to shift cytoplasmic redox; pair with **SHuffle/Origami** if needed; additional folding aids: L-Arg 50–200 mM, betaine 0.5–1 mM | Mohammad 2026 *PLoS ONE*; Michel 2012 *FEBS J*; Lobstein 2012 |
| **High-density (OD>20)** | **ZYP-20052S** formula: N-Z-amine AS 10 + YE 5 + 1× P buffer + 1× 5052 + 2 mM MgSO₄ + 25 mM succinate + 1.5% glycerol + 0.2× trace metals; can reach OD₆₀₀ ~45 | Studier 2005; Barondeau lab protocol |

### Defined (Synthetic) Autoinduction Medium

For NMR labeling or avoiding animal-derived components use **Li et al. 2011** defined medium:

| Component | Concentration |
|:----------|:-------------|
| (NH₄)₂SO₄ | 3.3 g/L |
| KH₂PO₄ | 6.8 g/L |
| Na₂HPO₄·2H₂O | 8.9 g/L |
| MgSO₄·7H₂O | 0.25 g/L |
| Glycerol | 5 g/L (0.5%) |
| Glucose | 0.5 g/L (0.05%) |
| Lactose | 2 g/L (0.2%) |
| Trace Metals (1000×) | 0.2 mL/L |

### GSH/GSSG Optimization for Disulfide-Bonded Proteins

**Problem**: E. coli cytoplasm has GSH:GSSG ~200–300:1 (highly reducing), preventing disulfide bond formation.

**Mechanism**: Exogenous GSSG lowers the cytoplasmic GSH/GSSG ratio, shifting the redox equilibrium toward thiol oxidation and promoting native disulfide pairing.

**In vivo reference doses (live culture)**:
| GSH | GSSG | Strain | Protein | Effect | Source |
|:---|:---:|:---|:---|:---|---:|
| — | **2 mM** | SHuffle T7 | Exotoxin A (8 disulfides) | 15× soluble yield increase | Mohammad 2026 *PLoS ONE* |

**Cell-free reference doses**:
| GSH | GSSG | System | Protein | Source |
|:---|:---:|:---|:---|:---|
| 2 mM | 5–10 mM | S30 extract (BL21 DE3) | hDpl(24–152) | Michel 2012 *FEBS J* |
| 2 mM | 5 mM | S30 + purified DsbC | mDpl(24–155) | Michel 2012 *FEBS J* |

**In vitro refolding reference**:
| GSH:GSSG | Ratio | Application |
|:---|---:|:---|
| 3 mM : 1 mM | 3:1 | General 2-disulfide protein refolding |
| 1:10 (5 mM total) | 1:10 | Cytoplasmic extract — promote disulfide bonding |

**Protocol tips (Mohammad 2026)**:
- Prepare 1 M GSSG stock (in DMSO or pH 7.0 buffer, filter-sterilize)
- **Add at induction** (OD₆₀₀ ~0.6), NOT at inoculation
- Synergistic with low-temperature induction (12–18°C) and chaperone co-expression (DnaKJE/GroEL)
- Optimization gradient: 0.5 → 1 → 2 → 5 mM GSSG

**Strain priority for disulfide proteins**: SHuffle T7 > Origami > BL21(DE3)

### Related References (GSH/GSSG)

- Mohammad SF et al. (2026) *PLoS ONE* 21(4): e0347213
- Michel E, Wüthrich K (2012) *FEBS J* 279(17): 3176–3184
- Cumming RC et al. (2004) *J Biol Chem* 279(21): 21749–21758
- Lobstein J et al. (2012) *Microb Cell Fact* 11: 56 (SHuffle strain development)

### Selection Guide

| Protein Characteristic | Recommended Medium | Key Tuning |
|:----------------------|:-------------------|:-----------|
| Routine | ZYM-5052 or AIM-LB | Standard formula |
| High yield | AIM-TB / ZYP-20052S | High nitrogen + glycerol |
| Large (>80 kDa) | AIM-LP-type | Add chemical chaperones + N-Z-amine AS |
| Membrane protein | AIM-MP-type / SBauto | Choline + inositol, optimize carbon ratio |
| Acidic (low pI) | Low-phosphate / M9auto | Weak buffer, prevent aggregation |
| Alkaline (high pI) | ZYM-5052 / AIM-TB | Strong buffer, prevent acid denaturation |
| Disulfide bonds | AIM-DiP-type / SHuffle strains | Oxidative strain + small thiols |
| High density (OD>20) | ZYP-20052S | Succinate + glycerol |
| NMR labeling | Li 2011 defined medium | Fully synthetic, no complex components |

## Key References (for citation)

1. Studier FW (2005) *Protein Expr Purif* 41(1): 207–234
2. Blommel PG et al. (2007) *Biotechnol Prog* 23(3): 585–598
3. Fox BG, Blommel PG (2009) *Curr Protoc Protein Sci* Unit 5.23
4. Gordon E et al. (2008) *Mol Membr Biol* 25(8): 588–599
5. Li Z et al. (2011) *Appl Microbiol Biotechnol* 91(4): 1203–1213
6. De Marco A et al. (2005) *Cell Stress Chaperones* 10(4): 273–285
7. Kopp J et al. (2013) *Protein Expr Purif* 91(2): 173–180
8. Mohammad SF et al. (2026) *PLoS ONE* 21(4): e0347213 — 2 mM GSSG for disulfide-rich proteins in SHuffle
9. Michel E, Wüthrich K (2012) *FEBS J* 279(17): 3176–3184 — GSH/GSSG in cell-free disulfide protein expression
10. Lobstein J et al. (2012) *Microb Cell Fact* 11: 56 — SHuffle strain development

## Obsidian Note Path

All autoinduction medium research data (formulations, literature strategies, patent status, selection guide) is saved at:
```
🗂️ Classifications/Q-33 生物学实验与生物学技术/Culture medium/自诱导培养基 Autoinduction Medium.md
```

## Fox & Blommel Patent Details

The patent US20080286749A1 / WO2008127997A1 ("Enhanced protein expression using auto-induction media") from Wisconsin Alumni Research Foundation used a **factorial design approach** to evolve autoinduction media for specific proteins. Key features:
- Systematically varied glucose, glycerol, and lactose concentrations
- Ran ~60 rounds of experimental evolution per target protein
- The patent is now **abandoned/ceased** (status as of 2026)
- Assignee: Wisconsin Alumni Research Foundation (Fox & Blommel)
- Priority: US 60/923,104 (April 12, 2007)
- Does NOT contain specific g/L tables for the specialized formulations — it describes the METHOD of optimization, not the resulting formulations

## macOS Tip: Extracting .doc Files
```bash
textutil -convert txt -output /tmp/output.txt /tmp/input.doc
```
Useful when manufacturers publish product spec sheets in old .doc format.
