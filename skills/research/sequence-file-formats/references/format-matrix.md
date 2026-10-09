# Format × operation matrix (plasmid / sequence files)

Numbers are measured, not estimated: BioPython 1.87 for GenBank, `sgffp` for `.dna`,
`sbol3` + `sbol-utilities` for SBOL3. Re-measure if the toolchain version moves.

## Stored operations

| Format | seq | features | primers | map style | cloning history | text-editable by hand | agent write path |
|---|---|---|---|---|---|---|---|
| GenBank `.gb` | yes | yes | only as `primer_bind` | no | no | yes (easy) | BioPython `SeqIO.write` |
| SnapGene `.dna` | yes | yes | yes | yes | yes | **no** (binary TLV) | `sgffp` (reverse-engineered) |
| SBOL3 `.ttl` / RDF-XML | yes | yes | no | glyphs only (SBOL Visual) | provenance, not cloning | readable, not authorable | `sbol-utilities` / `sbol3` |
| generalized JSON | yes | yes | yes | partial | no | yes (easy) | bio-parsers `jsonToGenbank/Fasta/Bed` only |
| GFF3 + FASTA | yes (FASTA) | yes (GFF3) | no | no | no | yes (easy) | any text tool |

## Measured sizes

- 301 bp / 4 features (promoter, RBS, CDS, terminator, one reverse-strand):
  GenBank **927 B / 25 lines** → SBOL3 Turtle **8381 B / 77 lines** = **9.0×**.
- Real plasmid L09137.2 (pUC19c, 2686 bp, circular, 1 source feature):
  GenBank **8367 B / 157 lines** → SBOL3 Turtle **15448 B** (1.85×).
- Fixed SBOL3 boilerplate ≈ **7.1–7.5 kB** (8381−927 = 7454; 15448−8367 = 7081).
- `sgffp`-authored minimal `.dna` (24 bp, 1 feature, 1 primer): **360 B**; header bytes
  `\t\x00\x00\x00\x0eSnapGene\x00\x01\x00\x0f...`; 92.5% printable bytes.
- Token cost matters for agent-friendliness: a 2686 bp GenBank (~8.4 kB ≈ 2.5k tokens)
  fits in context whole, so an agent can reason over the entire plasmid; a `.dna` cannot
  be read at all without a tool call.

## GenBank fragility, measured

| Mutation to the LOCUS line | Result |
|---|---|
| canonical column layout | parses clean |
| all fields present, single-spaced | parses + `Attempting to parse malformed locus line` |
| date/division fields dropped | `ValueError: No records found in handle` (hard fail) |
| ORIGIN shortened, LOCUS length stale | `Expected sequence length 2686, found 2685` — **warning only, parse succeeds** |
| hand-written feature block added to FEATURES | parses normally (`misc_feature 396..404` → `[395:404](+)`) |

Round trip through BioPython on the real pUC19 GenBank: 12 annotation keys in → 0 lost,
8367 → 8183 bytes, feature count unchanged.

## Verdicts

- **Want text symmetry (both edit the same bytes) → GenBank.** Cost: no map, no map style,
  no cloning history; the map is regenerated. Three format rules to respect (see SKILL.md).
- **Want the map itself to be the document → the generalized JSON model** (Open Vector Editor
  state *is* this JSON, so GUI edits and agent edits are the same object). Cost: a library
  convention, not a standard, and no write-back to `.dna`.
- **Want the human's favourite map → SnapGene `.dna`**, but accept it as a one-way delivery
  artifact: write path is one reverse-engineered project tracking one vendor's releases.
- **Want semantics/interchange → SBOL3**, if nobody has to author it by hand.

## Map rendering is one-way

- `dna_features_viewer` (MIT, BioPython-native): PNG / JPEG / SVG / PDF.
- `pLannotate` (GPL-3.0): FASTA in → annotated GBK + interactive Bokeh HTML; CLI
  `plannotate batch -i x.fa --html --output DIR --file_name NAME`.
- `PlasMapper 3.0` web server also imports/exports its own JSON format (not shared with
  the other JSON dialects).
- None of them read a rendered map back into features. The text record stays canonical.
