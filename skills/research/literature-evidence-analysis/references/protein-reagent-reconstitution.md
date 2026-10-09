# Protein Reagent Reconstitution from Literature

**What**: Recover the full amino acid sequence AND a reproducible expression/purification protocol for a published recombinant protein reagent (nanobody, Fab, scFv, enzyme domain, etc.) from literature and public databases.

## Use Case

When the user asks "what's the sequence and how do I express/purify X protein?" — and X is a published reagent with a known structure or paper.

## Workflow

### Step 1: Identify the primary paper(s)

- **Web search**: Search for the reagent name + "expression purification" + relevant keywords
- **Look for**: The paper(s) that first developed the reagent. Many tools get mentioned in later application papers — go back to the origin paper for the actual Methods.
- **Search Zotero**: If the paper is in the user's library, skip web search and go straight to the paper.

### Step 2: Extract the sequence from PDB

Once you know the PDB ID(s) from the paper:

- **RCSB FASTA endpoint**: `curl -s "https://www.rcsb.org/fasta/entry/<PDBID>"`
  - Returns a multi-FASTA with all chains. Each header includes chain ID, auth chain, macromolecule name, and species.
  - Disambiguate chains by the `|auth K]|Anti-Fab nanobody|` format in the header.
  - Watch for cloning artifacts: N-terminal "GS" from restriction sites, C-terminal His-tags, etc. Note these separately from the core sequence.

Alternative: `https://pdbj.org/mine/summary/rest/newweb/fetch/file?cat=pdb&type=fasta&id=<pdb_id>` (PDBj mirror — may redirect to status search page instead of returning FASTA for recent entries)

- **RCSB Sequence page**: `https://www.rcsb.org/3d-sequence/<PDBID>?assemblyId=0` — interactive viewer with per-chain sequence annotation. Useful when FASTA returns an empty response.

### Step 3: Extract expression/purification protocol

From the paper's **Methods section** (NOT just the abstract):

| Parameter | Where to find it |
|-----------|-----------------|
| Expression vector | "cloned into pET26b+/pET28a/pRH2.2..." (Methods) |
| Signal peptide | "PelB leader for periplasmic expression" or cytoplasmic |
| Expression strain | "E. coli BL21(DE3) / C43(DE3) / SHuffle" |
| Growth medium | "Terrific Broth / 2×YT / LB" and supplements |
| Induction | IPTG concentration, OD at induction, pre/post-induction temperature & time |
| Purification step 1 | Affinity resin type, binding/wash/elution buffers |
| Purification step 2+ | Ion exchange, SEC (column type + size), tags cleaved |
| Storage | Final buffer (PBS / HEPES-NaCl), concentration method |

### Step 4: Cross-reference yield data

The primary paper may not report yield. Search for:

- **Follow-up protocol papers** that used the same reagent at larger scale
- **General nanobody yield benchmarks**:
  - Standard pET26b/PelB, TB shake flask, 25°C overnight: 5–15 mg/L purified
  - Cytoplasmic SHuffle: 10–30 mg/L
  - MBP fusion periplasmic: ≥12 mg/L
  - Fed-batch fermentation: up to 2 g/L

### Step 5: Synthesize a ready-to-use protocol

Combine Steps 3 + 4 into one self-contained protocol the user can follow. Include:

```markdown
## One-Sentence Summary
Anti-Fab nanobody, 117 aa, expressed in E. coli periplasm, IMAC + SEC.

## Sequence
>AfNb (core, 117 aa)
QVQLQESGGGLVQPGGSLRLSCAASGRTISRYAMSWFRQAPGKEREFVAVARRSGDGAFYADSVQGRFTVSRDDAKNTVYLQMNSLKPEDTAVYYCAIDSDTFYSGSYDYWGQGTQVTVSS

## Expression
- Vector: pET-26b(+) (KanR)
- Signal: PelB (N-terminal, cleaved during secretion)
- Tag: N-terminal 6×His
- Strain: E. coli C43(DE3) or BL21(DE3)
- Medium: TB + 0.4% glycerol
- Induction: 0.5–1 mM IPTG at OD₆₀₀ ≈ 0.6
- Expression: 25°C, 16–20 h

## Purification
1. Periplasmic extraction (sonication or osmotic shock)
2. Ni-NTA: bind in 20 mM Tris pH 7.5, 500 mM NaCl, 20 mM imidazole
   Elute with 250–500 mM imidazole
3. SEC: Superdex 75 Increase, 20 mM HEPES pH 7.5, 150 mM NaCl

## Expected Yield
~8–12 mg/L (standard shake flask)
```

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Paper describes the **Fab** expression in detail but says little about the **nanobody** | Look for "Nbs were purified as described previously (ref)" → follow the reference |
| RCSB FASTA returns empty | Use PDBj mirror or browser-based sequence page |
| PDBe/PDBj 3D viewer redirects to a SEARCH page instead of the structure | Append `?lang=en` or use RCSB primary site instead |
| The sequence from PDB has cloning artifacts (GS, LE, etc.) at N-terminus | Compare to the paper's description; flag these as non-native but harmless if the paper says they don't interfere |
| "Conveniently expressed in E. coli in large amounts" but **no numbers** | Use general nanobody benchmarks (5–15 mg/L shake flask) — this is a well-known range for VHHs |
| The paper cites a ref for the anti-Fab Nb protocol but never wrote it up separately | The ref (e.g. Koide 2007 for AfNb) may only describe the discovery, not the production. Synthesize from the application paper's Methods and general VHH protocols |

## Source Example

This reference was generated from a session on anti-Fab nanobody (AfNb) reconstitution:

- **Primary paper**: Bloch et al. (2021) PNAS 118(47):e2115435118 (NabFab)
- **Sequence source**: PDB 7PHP, chain E (auth K), "Anti-Fab nanobody"
- **Expression protocol**: Adapted from same paper's Methods section (pET26b, C43(DE3), TB, Ni-NTA → SEC) + general Kossiakoff lab practices (Bailey 2018 JMB, "Locking the Elbow")
- **Original discovery**: Koide et al. (2007) JMB 373:941–953 (affinity-matured anti-Fab sdAb)
