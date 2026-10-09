---
name: life-science-research
description: General life-sciences research skill — routes broad/multi-step research questions (genetics, expression, pathways, structure, chemistry, clinical, literature) through 50 specialized sub-skills with entity normalization, evidence synthesis, and optional parallel subagent analysis. Based on OpenAI's Codex life-science-research plugin.
---

# Life Science Research

This is a meta-skill bundling 50 specialized life-sciences sub-skills from OpenAI's Codex plugin (v1.0.2). Use it when the user asks a broad life-sciences research question.

## Structure

All sub-skill files are under this skill's directory:
- `~/.hermes/skills/life-science-research/skills/<skill-name>/SKILL.md` — sub-skill instructions
- `~/.hermes/skills/life-science-research/skills/<skill-name>/scripts/` — Python lookup scripts
- `~/.hermes/skills/life-science-research/skills/<skill-name>/agents/openai.yaml` — Codex subagent definitions (informational)
- `~/.hermes/skills/life-science-research/skills/<skill-name>/references/` — API docs / reference notes

**To load a sub-skill**: use `skill_view(name='life-science-research', file_path='skills/<skill-name>/SKILL.md')` to read its SKILL.md, then follow the instructions there.

**To use a sub-skill's script**: reference it at `file_path='skills/<skill-name>/scripts/<script>.py'` and run it via `terminal()`.

## Entry Point

Use **research-router-skill** as the default orchestration layer for broad, ambiguous, or multi-step life-sciences research tasks:
`skill_view(name='life-science-research', file_path='skills/research-router-skill/SKILL.md')`

The router handles:
1. Understanding the research objective
2. Normalizing entities (gene, disease, variant, compound, etc.)
3. Selecting the minimum useful set of downstream skills
4. Gathering evidence (optionally via parallel subagents)
5. Synthesizing evidence-backed answers

## 50 Sub-Skills by Research Area

### Human Genetics & Variant Evidence
- `opentargets-skill`, `gwas-catalog-skill`, `clinvar-variation-skill`, `gnomad-graphql-skill`
- `ensembl-skill`, `eva-skill`, `epigraphdb-skill`, `genebass-gene-burden-skill`
- `gtex-eqtl-skill`, `eqtl-catalogue-skill`, `locus-to-gene-mapper-skill`
- `finngen-phewas-skill`, `ukb-topmed-phewas-skill`, `biobankjapan-phewas-skill`, `tpmi-phewas-skill`

### Expression, Cell Context & Functional Genomics
- `bgee-skill`, `human-protein-atlas-skill`, `cellxgene-skill`, `encode-skill`, `rnacentral-skill`

### Protein, Structure, Pathway & Functional Biology
- `alphafold-skill`, `rcsb-pdb-skill`, `uniprot-skill`, `string-skill`
- `quickgo-skill`, `reactome-skill`, `rhea-skill`

### Chemistry, Metabolites & Pharmacology
- `bindingdb-skill`, `chembl-skill`, `pubchem-pug-skill`, `chebi-skill`
- `pharmgkb-skill`, `hmdb-skill`

### Clinical, Translational & Disease Evidence
- `clinicaltrials-skill`, `cbioportal-skill`, `civic-skill`, `ipd-skill`

### Literature, Search & Public Study Discovery
- `ncbi-entrez-skill` — has a `references/ncbi-entrez-curl-fallback.md` for direct `curl` API access when web_search is down
- `ncbi-pmc-skill`, `biorxiv-skill`, `biostudies-arrayexpress-skill`
- `ncbi-datasets-skill`, `ncbi-blast-skill`, `ncbi-clinicaltables-skill`

### Reference Notes (Condensed Domain Knowledge)
- `references/ntbi-zip14-iron-transport.md` — mammalian NTBI/ZIP14/Fe³⁺-citrate iron transport mechanism
- `references/evidence-classification.md` — how to tier evidence (direct / extrapolation / unknown) when synthesising literature answers, and common pitfalls
- `references/commercial-product-research.md` — workflow for researching commercial biotech/lab products: finding manufacturer product pages, checking patents vs trade secrets, navigating Chinese vendor websites, and known commercial AIM autoinduction medium formulations
- `references/zotero-local-api-write.md` — adding Zotero items when MCP is in local-only mode (no API key) via the desktop connector API at port 23119

### Multi-Omics, Proteomics & Specialized
- `pride-skill`, `proteomexchange-skill`, `metabolights-skill`, `mgnify-skill`, `efo-ontology-skill`

## Quick Usage

For a broad life-sciences question:
1. Load `skill_view(name='life-science-research', file_path='skills/research-router-skill/SKILL.md')`
2. Follow the router's instruction: classify → normalize → select skills → gather → synthesize
3. For each sub-skill you need, load it via its own SKILL.md in this skill's tree
4. Run scripts directly via `terminal()` using the full path under `~/.hermes/skills/life-science-research/`

**For compound-mechanism / metal-binding questions specifically** (e.g. "does compound X bind/transport metal Y?"):
1. Load `references/evidence-classification.md` **before** answering — it defines the three-tier evidence framework (direct / extrapolation / unknown) and lists common generalization traps.
2. Search separately for (a) direct experimental data on the specific compound, (b) data on structural analogues, (c) and flag which is which in the answer.

## Plugin Metadata

- Version: 1.0.2
- Author: OpenAI
- Source: https://github.com/openai/plugins/tree/main/plugins/life-science-research
