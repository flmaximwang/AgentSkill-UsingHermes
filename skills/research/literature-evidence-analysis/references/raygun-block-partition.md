# Raygun K=50 block partition — case study

Source: Devkota et al., "Miniaturizing and modifying natural proteins with Raygun," *Nature*, 2026-07-29, DOI 10.1038/s41586-026-10842-8. Zotero key SVQSDHNR. (Preprint family; this entry is the peer-reviewed Nature article.)

Q1: Why split an arbitrary protein into K=50 blocks? (Author-stated rationale)
- Fixed-length representation: partition each protein's ESM-2 embedding into K=50 contiguous stretches of residues (blocks). Block size scales with protein length (e.g. 10 residues/block for a 500-residue template). The whole protein becomes a fixed 64,000-dim latent (50 × 1,280) regardless of original length — this length-invariance is what lets one autoencoder handle proteins of any length and generate at any target length.
- By the central limit theorem, averaging embedding vectors within a block approximates a multivariate Gaussian (Extended Data Fig. 1: unimodal, Shapiro-Wilk median 0.96, mild deviation from normality but effective in practice).
- A directly-samplable Gaussian makes generation single-shot: the decoder acts as a one-shot denoiser mapping one noisy sample from the template distribution to a new sequence — vs. diffusion methods that need iterative denoising. Hence 0.3 s/generation.
- K=50 was chosen empirically over K=25 via reconstruction fidelity (BLOSUM score on SwissProt; Extended Data Fig. 2b). Trade-off: more blocks = more local/sequence detail preserved but less compression and noisier statistics; K=50 is the sweet spot.
- Architecture: autoencoder on ESM-2 embeddings. Reduction layers do within-block averaging (variable-length → fixed-length); Repetition layers expand fixed-length → target length; T-Block layers (transformer + 1D-conv) refine features. 701M trainable params.

Q2: Is the split uniform? — evidence-tiering trap (the interesting lesson)
- The main text says: "we partition each protein's embedding into K=50 contiguous stretches of residues (blocks), where the size of each block scales with the protein length (for example, 10 residues per block for a 500-residue template)."
- This strongly IMPLIES a uniform/equal partition (≈N/50 residues per block; 500/50=10). But the authors never write the words "uniform" or "equal-sized," and the exact partition-boundary algorithm for lengths not divisible by 50 (floor/ceil, remainder handling, overlap handling) is NOT in the main text — it lives in Supplementary Methods (referenced, but not present in the extracted full-text spillover).
- Lesson: distinguish what a paper EXPLICITLY states from what it only IMPLIES. Here the correct answer was "the text supports uniform/equal splitting as the intended scheme, but the authoritative partition-boundary rule is in Supplementary Methods / source code — I have not verified it from that source." Flag the unverified boundary rather than asserting strict uniformity as fact. Offer next step (read source repo / pull supplementary PDF) instead of guessing. This matches the umbrella's "direct vs extrapolation" tiering.

## Reusable technique: parsing Zotero MCP full-text spillover files
- `zotero_get_item_fulltext` returns large full texts as a single-line JSON blob spilled to disk under `~/.hermes/cache/spillover/call_*.txt`. The tool auto-suggests `zotero_semantic_search` as an alternative when output is huge.
- Pitfall: the spilled file is ONE line. Line-based tools (`search_files`, read_file line navigation) fail to find anything meaningful on it. Don't grep line-wise.
- Correct approach: use `execute_code` (or a Python one-liner) to load the file, then `re.finditer` over keyword(s) and print a ±200–700 char window around each hit. Because output itself is large, iterate: first count hits per keyword to choose the right anchor, then print windows for promising indices in small batches.
- `strip escapes before printing`: replace `\n` and `\"` in the window so the extracted text is readable.
- Full text often contains the main article + Extended Data figure captions but NOT the full Supplementary Methods (those are only referenced). If a method detail lives in Supplementary Methods, say it's not in the extracted text and offer to fetch the supplementary attachment.

Worked example (this session): keywords `block`, `K = 50`, `K = 25`, `Extended Data Fig. 2`, `Supplementary Methods`, `uniform` — counting hits first, then windowing around `contiguous@11086` etc. surfaced the exact quoted sentences above.