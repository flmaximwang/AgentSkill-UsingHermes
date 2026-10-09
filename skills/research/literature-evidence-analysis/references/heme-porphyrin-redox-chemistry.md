# Heme / Porphyrin Redox Chemistry — Verified Notes

Condensed, source-verified knowledge bank for heme-protein Q&A (protein-design-relevant). Built from a DTT × hemin discussion (Aug 2026). Direct quotes = Tier 1; principle-based interpretations = Tier 2/3. Everything below was verified against the cited sources during the session.

## DTT × hemin — does the structure change?

- **Aerobic**: hemin CATALYSES DTT oxidation. Per 2 mol DTT oxidized, 1 mol O₂ consumed; DTT → intramolecular disulfide; O₂ → H₂O (4-electron main path; minor 2-electron H₂O₂ path); O₂ radicals not involved; H₂O₂ not an intermediate. Hemin regenerated each cycle (transient Fe³⁺/Fe²⁺) → **net hemin structure unchanged**. Reaction is specific for dithiols and for FREE heme. [Usha Devi & Ramasarma, Mol Cell Biochem 77:111–120 (1987); PMID 3437884, DOI 10.1007/BF00221919]
- **Anaerobic**: DTT reduces Fe(III) → Fe(II) heme — a real change at the metal center (iron oxidation state; axial Cl⁻/thiolate exchange; Soret ~398 nm → ~420 nm + α/β bands). Reversible on O₂ exposure. Porphyrin macrocycle NOT covalently modified under mild incubation.
- Ring opening/degradation needs strong oxidants (HOCl) or heme oxygenase; not expected in hemin+DTT+O₂ (1987 paper explicitly rules out ROS involvement).
- DTT covalently modifying the ring (vinyl thioether, heme-c-like): no direct evidence for free hemin + DTT under mild conditions (Tier 3). In biology it is enzyme-directed (see cyt c section).

## Why DTT accelerates heme dissociation (DGCR8 case)

- Reduction Fe(III)→Fe(II) causes LOSS of the two Cys thiolate axial ligands (electronic absorption, MCD, resonance Raman) and greatly increases heme dissociation rate; ferric heme is the active form. [Barr et al., PNAS 109(6):1919–1924 (2012), DOI 10.1073/pnas.1114514109]
- Chemistry: Fe(III) (harder Lewis acid, +3) binds thiolate strongly; Fe(II) binds it weakly → reduction removes the protein's ferric-specific stabilization → labile heme.
- **NOT universal**: "Most canonical heme proteins stably bind both the ferrous and ferric forms of heme" (same paper). Applies to ferric-stabilized + noncovalent heme (DGCR8-type); myoglobin/hemoglobin do NOT shed heme on DTT.

## Cyt c CXXCH thioether — covalent vs noncovalent reconciliation

- DTT in cyt c experiments serves TWO positive roles: (1) keep CXXCH Cys reduced — "maintain the thiols in the reduced form, a prerequisite for attachment"; (2) keep heme FERROUS — the productive substrate state for spontaneous thioether formation.
- Once both thioether bonds form (+ His axial ligand), heme is covalently locked; retention no longer depends on iron redox state (mature cyt c cycles Fe³⁺/Fe²⁺ as its function).
- System-dependent iron states — **no universal "ferric activates" rule**:
  - CcsBA (System II): "reduced heme (Fe²⁺) is needed for thioether formation to CXXCH".
  - CcmC (System I): "proposed to require oxidation (to Fe³⁺) for His130E adduct formation". [both: Li et al., Nat Commun 13:6422 (2022), DOI 10.1038/s41467-022-34136-5]
  - CcmE His130 adduct formation yields OXIDIZED (ferric) heme; reducing the iron ejects His/thiol adducts, freeing the vinyl for the Cys attack. [Kranz et al., Microbiol Mol Biol Rev 73(3):510–528 (2009), PMC2738134; PMC5554621: "reduction to Fe²⁺ of holoCcmE heme would also favor ejection of the CcmE His130 adduct"]
- Net picture: Fe(II) = substrate state (vinyl attackable); Fe(III) = product state (adduct stabilized). Reduction is used as choreography in Ccm (ejects adduct, frees vinyl).

## Vinyl "activation" — what is actually established

- The vinyl (-CHα=CHβ₂, Cα ring-attached) is conjugated to the porphyrin π system; the ring is the charge reservoir: "the carbanion on Cα could be stabilized through conjugation with the porphyrin π system". [Bowman & Bren, Nat Prod Rep 25:1118–1130 (2008), DOI 10.1039/b717196j, PMC2654777]
- **Regiochemistry**: native heme c = S at Cα (→ -CH(S-Cys)-CH₃), enzyme-directed — "the Ccm factors assist with directing attack of thiol at the Cα". The uncatalyzed paths (nucleophilic: attack terminal Cβ → carbanion at Cα; or radical anti-Markovnikov) put S at Cβ — the INCORRECT isomer observed in mis-matured Tt rC552. So the "Cα carbanion stabilized by conjugation" story corresponds to the wrong-isomer pathway, not the native one.
- **Metal dependence (Ht cyt c552 in vitro, no maturation factors)**: thioether forms only with divalent M(II) metalloporphyrins (Fe(II), Zn(II), Mn(II)); Fe(III), Co(III), Mn(III), and metal-free PPIX do NOT react. Zn(II) is d10/redox-inert → metal's role is NOT electronic activation of the vinyl. Authors: "A mechanistic basis for this observation was not given, but it is possible that the higher hydrophobicity of the divalent metalloporphyrin facilitates formation of a productive metalloporphyrin-apocytochrome complex." Reconstitution protocol: "combining apoprotein and heme under reducing conditions". [Bowman & Bren 2008]
- **Terminology + direction trap**: the addition intermediate is a carbanion, NOT a carbene (no carbene proposed in either nucleophilic or radical mechanism). And electron-withdrawing groups stabilize adjacent carbanions (EWG lower π* → better acceptor), so an electron-poor Fe(III) ring should stabilize the Cα carbanion BETTER — "Fe(III) can't stabilize the carbanion, hence blocked" is backwards. The Fe(II)/Fe(III) difference is a pre-complexation/hydrophobicity effect (authors' stated hypothesis), not vinyl electronics.
- **Practical**: in vitro CXXCH covalent attachment = reducing conditions + ferrous heme (Ht cyt c552 is the gold-standard case). hemin(Fe³⁺) aerobic is NOT the recipe for thioether formation (it IS fine for noncovalent reconstitution, myoglobin-type). DGCR8-type proteins (Cys-coordinated, noncovalent heme): avoid thiol reductants or verify with UV-vis.

## Extraction technique (used to build this bank)

Long PMC/Nature pages get truncated by web_extract (~15k chars) with the FULL text saved to `~/.hermes/cache/web/*.md`. Use `search_files(pattern, path=<cache file>, context=N)` to locate the needed section (e.g. "nucleophilic|Markovnikov|carbanion"), then `read_file` the cache with offset/limit. Beats re-fetching or guessing at the omitted middle.

## Key sources

| Source | What it proves |
|---|---|
| Usha Devi & Ramasarma 1987 (PMID 3437884) | Hemin catalyses DTT oxidation; hemin regenerated (net structure unchanged) |
| Barr et al. PNAS 2012 (10.1073/pnas.1114514109) | Reduction → Cys axial ligands lost → fast dissociation; not universal |
| Bowman & Bren, Nat Prod Rep 2008 (10.1039/b717196j, PMC2654777) | Vinyl/carbanion conjugation; regiochemistry (S at Cα enzyme-directed); Fe(II)-yes/Fe(III)-no; Zn(II) works; mechanism "not given" |
| Kranz et al., MMBR 2009 (PMC2738134) | Adduct → oxidized heme; reduction ejects thiol/His adducts |
| PMC5554621 | Fe²⁺ reduction of holoCcmE ejects His adduct, frees vinyl |
| Li et al., Nat Commun 13:6422 (2022) | Reduced thiols prerequisite; CcsBA needs Fe²⁺; CcmC proposed Fe³⁺ for His adduct |
| Sutherland et al., eLife 10:e64891 (2021) | In vitro HCCS/CcsBA reconstitution (dithionite for reduction) |
