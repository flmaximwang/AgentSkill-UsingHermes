---
name: obsidian-qa-discussion
description: Record multi-turn technical Q&A discussions as structured Obsidian notes under CLC classification.
platforms: [macos, linux, windows]
---

# Recording Q&A Discussions into Obsidian

When the user asks a series of deep "why" questions on a technical topic and then asks to save the discussion into the Obsidian vault.

## Trigger

User asks to save a technical discussion into the Obsidian vault. **Two distinct trigger patterns produce different output formats:**

| Trigger phrasing | Expected output format |
|-----------------|----------------------|
| "把讨论记录/归纳总结到 Obsidian" / "存成笔记" | **Q&A transcript** — numbered sections matching the reasoning chain |
| "先整理一下" / "把这个内容整理成笔记" / simply "整理" | **Knowledge reference note** — encyclopedia-style sections (definition, mechanism, experiments, applications, etc.), NOT a dialog replay |

**Key distinction**: "整理" implies the user wants a polished, reusable reference — not a verbatim record of the conversation flow. Reading "整理一下" and writing a Q&A transcript is a mistake.

## Workflow

### Phase 0: Determine note type from trigger

Before anything else, classify the user's request:

- **"整理一下" / "整理成笔记"** → Knowledge reference note. Skip Phase 1's Q&A-specific advice and go straight to Phase 2 (CLC classification). Structure as an encyclopedia article, not a dialog transcript.
- **"把讨论记录到 Obsidian" / "记录讨论"** → Q&A transcript. Follow the full workflow including Phase 1's structured answer pattern.

### Phase 1: Provide structured answers during discussion

When the user asks a chain of deep questions:

- Start with the **core principle**, then build upward
- Use **comparison tables** and **math formulas** when relevant
- Trace back to **first principles** (user's learning style: they ask "why" recursively)
- Offer to show a **real image/visual aid** when one exists

### Phase 1b: Deep explanatory techniques for "why" chains

When the user follows up a first answer with deeper "why" questions (e.g., "热压为什么是向内的", "辐射压究竟是什么"), use multi-level layered answers:

- **Multi-level explanation**: Give the SAME phenomenon at different abstraction layers — phenomenological formula (what), field-theoretic definition (how), microscopic mechanism (why). Example for "radiation pressure": (1) P~2I/c from photon momentum, (2) Maxwell stress tensor ⟨T_rr⟩, (3) ponderomotive force F_p∝-∇E². This satisfies the "why → why → why" chain without repeating yourself.

- **Energy budget reasoning**: Use back-of-envelope calculations when a claim seems counterintuitive ("why doesn't it explode?" → show P_th ∝ R⁻⁵ scaling). This builds trust through quantitative intuition.

- **Geometrical ASCII diagrams**: Draw the system's force balance in ASCII (spherical shell, arrows for inward/outward forces) when spatial reasoning is essential. This resolves confusion faster than prose alone.

- **Historical evidence timeline**: When asked "how did scientists figure this out," present a chronological evidence chain (1955 Kapitza → 1969 Dawson & Jones → 1990s PIC → 2014 spectrum → 2016 Wu → 2026 SIOM). This gives the answer narrative structure and shows convergence from multiple independent lines.

- **Analogy to familiar systems**: Compare to well-understood systems (stars, soap bubbles, balloons, tokamaks) when explaining force balance, but always note where the analogy breaks.

- **Fiction-vs-science comparison**: When the user asks about a fictional representation (Liu Cixin's macro electron, etc.), present a side-by-side comparison table and evaluate the fiction on scientific grounds. This both satisfies curiosity and reinforces the correct physics.

> See `references/electromagnetic-soliton-deep-dive.md` for a worked example of all six techniques on a single "why" chain.

### Phase 1b: Deep follow-up Q&A after note creation

When the user continues asking deep "why" questions AFTER the note has already been created (knowledge-reference or Q&A):

- Assess whether the new material warrants a **note update**: did the follow-up uncover significantly missing content (e.g. a key mechanism not explained), or was it just elaboration on what's already covered?
- If update warranted → append new sections or enrich existing ones. Use `patch` for targeted insertions.
- If update not warranted → offer to save separately or note in your reply that the content is covered already.
- **Don't update if it's just a deeper explanation of already-documented points** — the user may be using the existing note as a reference while learning, not asking for expansion.

### Phase 2: Locate the CLC classification

Before writing to Obsidian:

1. Search the vault's `🗂️ Classifications/` for existing notes on the topic
2. Search for CLC-code folder names (e.g., `O657.33`, `TP18`)
3. Check `<vault_root>/README.md` for CLC rules
4. Search the web (clcindex.com) if the code is uncertain

**Key rule**: CLC subclasses are FLAT at the `🗂️ Classifications/` root.

### Phase 3: Structure the note

**Two format branches** — choose based on Phase 0:

#### Branch A: Q&A transcript format

```markdown
---
aliases: Topic Keywords
tags: 
date created: YYYY-MM-DD
---

# Topic Title

Brief context paragraph.

## 1️⃣ First question/theme

Core answer with key insight. Use comparison tables when applicable.

## 2️⃣ Next question/theme

...

## Summary

Concluding comparison table or one-paragraph synthesis.

## 相关笔记

- [[Existing Note 1]]
```

#### Branch B: Knowledge reference note format (from "整理一下")

```markdown
---
aliases: [别称, English]
tags: [Memos/Physics (or appropriate domain tag)]
parents: [[Parent CLC Folder]]
abstract: One-sentence summary of the concept.
keywords: [keyword1, keyword2]
---

# Title

## 背景

Lay the foundation — what broader context this concept fits into.

## 定义

Precise definition with boundary conditions.

## 产生机制 / 工作原理

Break down the physics/mechanism step by step. Use comparison tables, math formulas.

## 关键实验 / 证据

If recent experimental results exist, summarize in a table: parameters, values, significance.

## 应用前景 / 与用户领域的关联

What's the practical relevance? Explicitly note if there is **no direct connection** to the user's domain (protein design, biochemistry).

## 参考文献

- Source papers, news releases, DOI links

## 相关笔记

- [[Existing Note 1]]
```

**Key differences from Q&A format**:
- Frontmatter includes `abstract` and `keywords` fields
- Sections are thematic (Background / Definition / Mechanism / Evidence), not dialog-sequence-based
- "Related to your field" section is labeled explicitly, including a clear "no connection" statement when warranted
- Each section is self-contained — the note should be understandable without reading the conversation history
- **Science Q&A additions (Branch B)**: if the original question was poorly posed, include an explicit "澄清后的核心问题" section (why the original is flawed + the reframed version) as the note's first content section; when evidence strength varies across the table, add a one-line evidence legend (e.g. ★★★ direct causal / ★★ functional / ★ correlative) above the comparison table. Match the vault's existing note conventions (e.g. `RNA.md`-style minimal frontmatter: aliases + dates) when placing a concept note inside an established CLC subtree — don't force the full template.

### Phase 4: Handle media

1. Search for a public-domain or freely licensed image (Wikimedia Commons, etc.)
2. Download it to the **same directory as the note** (use PNG format)
3. Reference it with `![[filename.png]]`
4. **Fallback**: Wikimedia CDN may block curl — try the `thumb/...` PNG preview URL or use a browser screenshot

### Phase 5: Update cross-links

1. **Backup first** — `cp target.md target.md.bak` before any edit
2. **Folder note** — add `[[New Note]]` to the folder's root `.md` file
3. **Parent/related notes** — add `[[New Note]]` to directly related subtopic notes
4. Use `patch` for targeted edits

### Phase 6: Verify

- `ls` the note directory → confirm all files
- `read_file` the folder note → verify links
- `read_file` related notes → verify links

## Format conventions (user preferences)

### Branch A: Q&A transcript format

| Element | Convention |
|---------|-----------|
| Sections | Numbered with emoji: `## 1️⃣`, `## 2️⃣` |
| Comparisons | Side-by-side tables with clear column headers |
| Math | $$ LaTeX $$ for formulas |
| Key insights | Bold or callout blocks |
| Summary | Final comparison table wrapping up all points |
| Frontmatter | `aliases:`, `tags:`, `date created:` |
| Images | `![[filename.png]]` embed, placed in same directory |

### Branch B: Knowledge reference note format

| Element | Convention |
|---------|-----------|
| Sections | Thematic headings (背景 / 定义 / 机制 / 关键实验 / 应用前景) |
| Frontmatter | `aliases:`, `tags:`, `parents:`, `abstract:`, `keywords:` |
| Field relevance | Explicit section — include "no direct connection" disclaimer when true |
| Comparisons | Tables with clear column headers |
| Math | $$ LaTeX $$ for formulas |
| Images | `![[filename.png]]` embed where available |
| References | Numbered or bulleted list with DOI links and news-report URLs |

## Pitfalls

- **Don't cram all Q&A into one mega-section** — each distinct question needs its own section
- **Don't write without checking vault first** — CLC code may already exist with related notes
- **Don't skip the image** — user values visual aids
- **Don't use SVG embeds** — not reliably rendered in Obsidian; convert to PNG
- **Don't forget .bak** — vault modifications need recovery options
- **Don't assume a CLC code** — always verify by searching the vault
- **Don't use Q&A transcript format when user says "整理一下"** — this is the most common mistake. "整理" demands a polished, self-contained reference note, not a dialog replay.
- **Don't create a knowledge note that requires conversation history to understand** — each section must be self-contained.
