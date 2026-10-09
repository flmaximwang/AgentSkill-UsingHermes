# Literature Methodology Tracing with Zotero MCP

Use this workflow when the user asks you to trace **how a research group's methodology evolved** across their publications (e.g., "how did Baker Lab's symmetric protein design approach develop from HBNet to RFdiffusion?").

## Workflow

### 1. Start with the known anchor paper

If the user gives you a specific paper or concept (e.g., "HBNet"), search it in Zotero first:

```
zotero_search_items(query='Author 2016 keyword')
zotero_get_item_metadata(item_key='...')     # for abstract + full ref
zotero_get_item_fulltext(item_key='...')      # for the actual paper text (10K+ tokens — use only when needed)
```

### 2. Use citation chaining

- **Forward**: search for newer papers citing the anchor (via web_search: `"Author 2016" "method/term" Baker` or Google Scholar)
- **Backward**: look at the paper's own references (from metadata or fulltext "References" section)
- **Sibling**: search Zotero for other papers by the same lead author or group member

### 3. Distinguish related but distinct methods

This is the critical step users will correct you on. When studying a research group's methodological evolution, watch for:

- **Different layers of the same problem** — e.g., backbone generation (parametric) vs. interface docking (RPX) vs. sequence design (HBNet). A naive question "what method does X" may need an answer that separates these layers.
- **Parallel tracks** — a lab may have two independent routes (e.g., Cₙ coiled-coil design vs. T/O/I nanocage design) published simultaneously by different people.
- **Prerequisite relationships** — some methods enable others (DiMaio 2011 symmetry framework enables HBNet 2016, RPX 2017, King 2012).
- **Scope limitations** — a method may only apply to a specific symmetry type (Cₙ only, not T/O/I).

### 4. Validate with metadata

When you propose a categorization, **search for the actual paper metadata** before committing:

```
zotero_get_item_metadata(item_key='...')   # confirms title, authors, year, journal
```

The user's memory of a paper is often correct about the *concept* but may be fuzzy on details. Always verify: year, author order, journal, and **what the method actually does** (not what it sounds like).

### 5. Know when to use fulltext vs. metadata

| Level of detail | Tool | When |
|----------------|------|------|
| Title + authors + year | `zotero_search_items` | Quick lookup, confirming a paper exists |
| Abstract + full citation | `zotero_get_item_metadata` | Understanding the paper's claims and methods |
| Method description | `web_search` + `web_extract` | Getting supplementary/PMC fulltext when Zotero has no attachment |
| Complete paper text | `zotero_get_item_fulltext` | **Only** when the user explicitly asks to read the paper — 10K+ tokens |

## Pitfalls

- **Do NOT conflate methods from different years/people** just because they belong to the same lab or same paper series. E.g., HBNet (Boyken 2016, sequence design) ≠ RPX (Fallas 2017, docking) — they solve different sub-problems.
- **Do NOT assume a method covers all cases** just because it's the most famous one. E.g., Crick parameterization only generates Cₙ symmetric coiled-coils, NOT T/O/I symmetries.
- **When the user corrects a factual distinction** (e.g., "Crick params only do rotational symmetry"), save that correction — it reveals a key boundary of the method's scope.
- **Multiple search strategies may be needed** — Zotero keyword search uses substring matching (not semantic). If `zotero_search_items(query='Author Year')` fails, try `zotero_search_items(query='Author')` alone, or `zotero_semantic_search` for topic discovery.
