---
name: study-exercises
category: research
description: Generate practice exercises from book chapter or paper PDFs.
---

# Study Exercises from Book Chapters (习题生成)

Maxim reads textbooks chapter-by-chapter (e.g. Ligand-Binding Basics, Carey 2026) and asks for exercises per chapter ("对第X章出习题，A-B页"). Deliverable: a complete, answer-keyed exercise set in Chinese, with **verified coverage of the chapter's knowledge points** — he WILL ask how you know it's complete.

## Workflow

1. **Locate the source first in Zotero MCP** (rule: 具体文献先查 Zotero). Search by author surname only (e.g. `Carey`), get item key, check for attached notes (`zotero_get_notes`) — they may contain prior study context.

2. **Extract the chapter text.** PDFs from Wiley often fail `read_file` with `NeedsOcrError` on the first page even when later pages have a text layer. Don't give up: use `pdftotext -f <first> -l <last> -layout <pdf> /tmp/chX.txt` (poppler, already installed at /opt/homebrew/bin). Always extract the exact page range the user gave. Page numbers in the PDF ≠ book page numbers (e.g. PDF 25–47 = book pp. 10–32) — note the mapping in your reply. Confirm extraction with `head`.

3. **Read the ENTIRE chapter** before writing exercises (chunked `read_file`, ~300 lines each). Skipping the tail = missing knowledge points (in ch2 the tail had stoichiometric titration, molar-ratio determination, activity).

4. **Verify coverage before finalizing** (the key step Maxim probes):
   - Programmatically extract the chapter's own structure: section headings, equations (Eq n), text boxes (Text Box n.n), thought experiments, figures (Fig n.n). Use `scripts/extract_chapter_structure.py` on the pdftotext output.
   - Build a **coverage matrix**: every extracted knowledge block → exercise number(s), status ✅/⚠️.
   - Gap analysis: unassigned/weak blocks get new questions appended as a **supplemental group (F1, F2, …)** — never renumber the original groups.
   - Report the matrix in the reply, with honest gaps. Distinguish genuine knowledge gaps from merely illustrative content (e.g. a structural figure with no quantitative content).

5. **Format the exercise set**:
   - Chinese, grouped by cognitive type: A 概念辨析 / B 推导题 / C 计算题 / D 图形与实验设计 / E 综合思考, then a full 答案与解析 section.
   - Math in LaTeX ($...$) — desktop app renders it. Use the book's own numbers (Kd = 100 μM, [At] = 600 μM, RT ≈ 2.48 kJ/mol at 298 K) and its equation references (Eq 8, Text Box 2.4).
   - Step-by-step derivations with all algebra shown (Maxim: 步骤式, concrete numbers, no hand-waving; verify arithmetic — ν=0.909, quadratic [AH]=500 μM, ΔG°=−28.5 kJ/mol).
   - Include the book's own Thought Experiments as questions.

## Pitfalls

- **Never claim "complete coverage" without the matrix.** Maxim asks "你如何确认覆盖完整?" — the programmatic structure extraction + matrix IS the answer. Present evidence, not assertion.
- `NeedsOcrError` on PDF page 1 does NOT mean the whole PDF is scanned — later pages usually have text; `pdftotext -f -l` on the requested range works.
- Long outputs get truncated mid-answer-key. If truncated, continue exactly where you stopped — do not restart or repeat.
- When closing coverage gaps, append a new group (F…); renumbering A–E breaks cross-references the user is following.
- Distinguish molar ratio vs stoichiometry and monomer vs dimer unit conventions when writing calculations — the book (Carey ch2) is emphatic about these and Maxim checks definitions precisely.
- Zotero search: keep query short (author only); long queries return nothing.

## Support files

- `scripts/extract_chapter_structure.py` — regex extractor for chapter structure (headings, equations, text boxes, thought experiments, figures) from pdftotext output; feeds the coverage matrix.
