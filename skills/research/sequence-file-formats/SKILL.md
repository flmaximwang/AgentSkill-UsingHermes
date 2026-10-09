---
name: sequence-file-formats
description: "Use when handling plasmid/sequence files (.gb, .dna)."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [molecular-biology, file-formats, plasmid, genbank, snapgene, sbol, cloning]
    related_skills: [zsqlab-lab-records, literature-evidence-analysis]
---

# Plasmid / sequence file formats: read it, write it, render it

## When to Use

The user asks about plasmid maps or construct files: 质粒图谱文件, "annotate this plasmid", "convert .gb ↔ .dna", "what format should we store constructs in", "can you read my SnapGene file", a `.gb`/`.dna` from a zsqlab vault, or a map figure for a paper or slide. Also load it when the question is *whether to trust* a parser/writer for these formats in the user's daily workflow ("is this reverse-engineered library complete", "will SnapGene open what this wrote") — that is an audit, not a recommendation, and it has its own section below. Also load it when the question is whether two `.dna`/`.gb` files are *the same thing*, or whether a given construct file exists elsewhere in a copy — comparison has its own rules (see the pitfall below and `references/snapgene-dna.md`).

## Judge a format by its OPERATION SET, never by the extension

A plasmid file can carry six things: (1) sequence, (2) features (coords / strand / qualifiers), (3) primers, (4) map style (per-base colour, enzyme visibility, label layout), (5) cloning history, (6) derived data (restriction sites — always computed, never stored). Before recommending anything, state which of the six the format stores and, **separately for read and for write, whether a human and an agent have the same operations**. "Friendly to both" is essentially never one file; the honest answer names the asymmetry, and a format whose write path is a single reverse-engineering project is not symmetric even if reads are commodity.

Verified op coverage, measured sizes, and per-format verdicts: `references/format-matrix.md`. The `.dna` container layout, the measured write-path audit of `sgffp` (which layers pass and which fail), the block-id gate, and how to compare two `.dna` files (rotation, block multisets, what a "different" pair really differs in): `references/snapgene-dna.md`.

## Procedure

1. **Get the real file, don't reason from the format name.** NCBI: `curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=L09137&rettype=gb&retmode=text"` (pUC19c = L09137, 2686 bp circular). Vault `.dna` files: see `zsqlab-lab-records` for where they live.
2. **Read with BioPython.** `/Applications/BioRazer/bin/python` has BioPython 1.87; the system `python3` has no `Bio`. `SeqIO.read(path, "genbank")` → `.seq`, `.features`, `.annotations["topology"]`.
3. **Edit as text when the format allows** (GenBank/FASTA/GFF3). A hand-typed feature block parses: `     misc_feature    396..404` + `/label="..."`, 1-based inclusive, `complement(...)` for the reverse strand.
4. **Normalise by round-tripping through the writer** — `SeqIO.write(rec, path, "genbank")` rewrites the ORIGIN numbering and the LOCUS length for you. Never leave a hand-edited GenBank un-normalised.
5. **Render the map as a projection**, regenerated from the text record each time (`dna_features_viewer`, `pLannotate`).
6. **Verify before hand-off**: `/Applications/BioRazer/bin/python scripts/check_seq_file.py FILE...` — re-reads, compares the LOCUS-declared length against the actual ORIGIN length, checks feature bounds, and does a write→read round trip.

## Hard rules — GenBank, the format you will hand-edit

- **The LOCUS line is field- and column-sensitive.** Keep the canonical layout and its trailing fields. Measured: dropping date/division → hard `ValueError: No records found in handle`; single-spacing every field → parses but warns `Attempting to parse malformed locus line`.
- **The LOCUS length is redundant and NOT cross-checked.** Deleting a base from ORIGIN while LOCUS still declares the old length yields only `Expected sequence length N, found N-1` and parsing continues. **Treat that warning as an error** — after any text edit, re-read and compare `len(rec.seq)` to the intended length, or run the check script.
- Vendor extensions exist (`/pragma="Teselagen_Part"`, `/preferred5PrimeOverhangs=`): preserve what is there, never invent new nonstandard qualifiers. `/label` is display; keep a real `/gene` or `/note` when the meaning matters.

## Auditing a parser/writer before trusting it — four layers

A README is a claim, not evidence. When the user asks whether a library's write path is "complete", test it against **their own real files** and report the verdict **per layer** — "it round-trips" alone hides which layer failed.

1. **Content layer** — read → write → re-read, then compare *semantically*: sequence string, topology, per-feature `(name, type, start, end, strand, sorted qualifiers)`, primers, notes, and the cloning-history tree. Counting features is not enough; qualifier-level equality is the bar.
2. **Byte layer** — `sha256` input vs output. Containers holding XML/RDF get re-serialised, so expect non-identical bytes even with a `preserve=True` flag; quote the per-block size deltas. Byte churn is what makes sync tools report conflicts.
3. **Version/legacy layer** — write back an old-`export_version` file and confirm both the version-specific blocks and the version field survive.
4. **Forward-compatibility layer** — the one that usually fails. Inject a synthetic unknown block into a *copy* of a real file, read → write, rescan: a library that drops what it cannot decode will silently delete that data from every file it touches once the vendor adds or re-encodes a block.

Rules that keep the audit honest:

- **Never validate a library with itself when a vendor app exists.** Re-reading its own output is circular; say so and hand over the acceptance test (open the rewritten file in the vendor app, save, rescan) instead of implying verification.
- **Write an independent container scanner** rather than trusting the library's block accounting — it reports what it decoded, not what was in the file. `.dna` is 19 header bytes plus repeating *(1-byte type, 4-byte big-endian length)*, with `seek()` over payloads; a whole vault then scans in seconds.
- **A "known block" marker from one subcommand does not mean the writer keeps it.** Check the id against the module the reader/writer actually consults — `sff check -l`'s `[*]` comes from a different set than `parsers.py` uses, and block 35 is marked safe and then dropped.
- **Cost-stratify the sampling.** A read-only header scan may cover the entire library (seconds); a full read→write→compare sweep gets ~20 randomly sampled real files, not thousands — the user will interrupt a full-library content sweep. Stratify by size too (largest files carry history/traces/alignments).
- **Never write over a source file while auditing.** Output under the scratch dir, and tell the user the originals were untouched.

`scripts/scan_dna_blocks.py` implements this for `.dna`: read-only scan, `--tree` whole-library inventory, unknown/at-risk block report, and a `--roundtrip` probe.

## Toolchain — the exact entry point, per format

- **Scratch toolchains**: `uv venv VENV --python 3.11 && uv pip install --python VENV/bin/python <pkg>`. Do not install into the BioRazer conda env.
- **SBOL3**: use the console scripts, not the Python functions. `genbank-to-sbol IN.gb -n <namespace-URL> -o OUT.ttl` — the namespace is **required** for GenBank→SBOL3; reverse with `sbol-to-genbank OUT.ttl -o back.gb`. `sbol_utilities.conversion.genbank2sbol(a, b)` raises `TypeError: takes 0 positional arguments` because it is an argparse CLI wrapper with no usable signature.
- **SnapGene `.dna`**: writing needs `sgffp` (`SgffObject.new(seq, topology="circular").add_feature(...).add_primer(...)`, `SgffWriter.to_file(obj, path)`, `SgffReader.from_file(path)`). Read-only alternatives: `snapgene_reader` (PyPI), bio-parsers' `snapgeneToJson`. Measured: `sgffp`'s write is **content-lossless but not byte-preserving, and not forward-compatible** — unknown block types are skipped with only `logger.debug`, so a read→write cycle silently deletes them. Gate every write with `sff check FILE -l` plus a scheme cross-check (`scripts/scan_dna_blocks.py`), land the output on a new path, and default to using it as a **read-only exporter**. Full audit: `references/snapgene-dna.md`.
- **JSON route**: bio-parsers / `ve-sequence-parsers` "generalized JSON" (`{size, sequence, circular, name, features[], primers[], parts[]}`, 0-based inclusive, `strand` ±1) with writers `jsonToGenbank` / `jsonToFasta` / `jsonToBed`. It is the document model of TeselaGen's Open Vector Editor, which is the one stack where GUI edits and programmatic edits hit the same object — but it has **no** `jsonToSnapgene`.
- **Maps**: `dna_features_viewer` (`pip install dna_features_viewer`; `BiopythonTranslator().translate_record("x.gb").plot()` → PNG/SVG/PDF); `pLannotate` (`plannotate batch -i x.fa --html --output DIR --file_name NAME` → annotated GBK + interactive Bokeh HTML, FASTA in).

## Pitfalls

- **Never hand-edit a `.dna` file.** It is TLV binary after a 19-byte header (magic byte `\t`, title `SnapGene`), with 2-bit-packed sequence, inline XML for features/primers, LZMA for history. ~92% of bytes are printable ASCII so `cat -v` shows readable XML fragments — that is a trap, not an invitation: the length prefixes are binary. Write `.dna` through `sgffp` **only** for content-level edits on a file whose `sff check -l` is clean, onto a new path; otherwise treat `.dna` as read-only input and export to GenBank, editing there.
- **Comparing two `.dna` files: compare block multisets, and never call a rotation a difference.** Byte equality is not the test — XML re-serialisation, reordered blocks and a shifted circular origin all change bytes while the construct is unchanged. A measured pair whose offset diff showed 135,277 differing bytes had every block payload identical; only the block order differed. Match a circular sequence modulo rotation (`sb in sa + sa`, shift = `(sa+sa).find(sb)`) and shift the other file's feature coordinates `(start+shift) % L` *before* comparing feature sets, or every feature reads as "different". Vendor cache blocks (2/3/13/35) are regenerable and are not user data; history nodes (11) and traces (16) are. This is also the right test when asking "is this construct already somewhere else?" — check the union over **all** candidate copies. Recipe in `references/snapgene-dna.md`.
- **A rendered map is not data.** SVG/PNG/HTML outputs from DnaFeaturesViewer or pLannotate cannot be read back into features. Keep the GenBank as the single source of truth and regenerate the figure; never hand a map file to an agent as input.
- **SBOL3 Turtle is human-*readable*, not human-*authorable* at plasmid scale.** Every line is a triple; a 4-feature, 301 bp construct inflates from a 927-byte GenBank to an 8381-byte `.ttl` (9.0×), and a real 8367-byte pUC19 to 15448 bytes. The inflation is ~7.1–7.5 kB of fixed boilerplate, then roughly 1:1 with sequence. Do not propose hand-editing `.ttl` for real plasmids.
- **SBOL3 conversion needs private namespaces to stay lossless** (`genbank#locus`, `genbank#date`, `genBankConversion#label`) — evidence the mapping is not natively lossless. Say so instead of calling SBOL3 a superset.
- **Verbosity/size claims must be measured.** Converting one small construct and one real plasmid and quoting both byte counts is what makes the comparison usable; "SBOL3 is verbose" alone is not.
- **When a vendor app is installed, offer the vendor acceptance test instead of declaring success.** A container-level audit proves nothing about how the vendor's own reader renders or re-saves it; the user can run that last step in minutes, and it is the only non-circular evidence.

## Reporting this for the user

- For "有什么…格式/方案" questions: inventory the existing options first, each with its cost, then a verdict. Do not open with a self-built pipeline — it reads as "you want to build a product".
- Back every claim with a real number from a real run (bp, bytes, feature counts) and say which commands you actually executed. When an investigation like this finishes, list the artifact paths (scratch venv outputs, scripts) so the user can re-run it.
- Discord: no tables. Use labelled bullet lists; answer in Chinese for this user.
- If a format's write path is missing or reverse-engineered, say that plainly — it is usually the deciding fact.
