---
name: user-document-deliverables
description: "Use when the user asks for a 文档/报告/待办 instead of chat."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [reporting, deliverables, documents, pdf, pandoc, cjk, user-preferences]
    related_skills: [agent-to-agent-handoff]
---

# Delivering an answer as a document

The 4-section chat summary (要什么 / 做了什么 / 效果 / 待办) is governed by the user's own
`respond-to-requirements` skill. **This skill owns the other container**: what to do when the answer is a
list he has to work through — decisions, pending items, a comparison — and chat is the wrong shape.

## When to Use

- 「把待办 / 这一堆整理成一个文档发给我」「给我一份文件 / 清单 / 报告」, or any ask for one deliverable
  rather than a reply.
- The answer contains items someone must decide or act on: pending decisions, a migration checklist, a
  plan comparison.
- He answers a report of yours with 「我看不到你说的 X」 — the items existed only inside a document he was
  never holding.

## Choose the container before writing

- Chat: one question at a time, conclusion first, a few sentences. A set of items is **not** a chat
  answer — it is a file.
- Do not send the list in chat *and* attach it. Attach the file; keep the chat message to the decisions
  and the single reply each one needs.
- **A visual or interactive deliverable needs a text companion.** A graph, an HTML panel or a rendered
  figure cannot be quoted, diffed or grepped, and he reads text faster than he reads a picture — ship the
  structured text beside it, never the picture alone: 口径 (the command that produced it) → item/node
  table → per-row detail with source line numbers → what is missing / not done → next step.
- Write the file beside the work it describes (repo root, project dir), give the path in the message,
  and say whether it is committed — do not silently commit or silently leave it untracked.
- Name it with the project and a date (`PENDING-DECISIONS-YYYY.MM.DD.md`) so a later round can supersede it.

## Make it self-contained

- **No coordinates into documents he has not read.** "§8.1" / "item 7 of the checklist" only work for
  whoever has that file open; he usually has none, and a decision list he cannot see is a missing
  deliverable. Restate every item.
- Per item, in this order: the fact as you measured it (paths, ids, HTTP codes, commit hashes) → why it
  needs him → the options with the cost of each, recommended one first and marked → **回什么就能推进**.
- Numbers must be the ones you measured, not ones inherited from another agent's brief; when the brief
  disagrees with the live source, that disagreement is its own section (素材 vs 实测) — it is what the
  reviewer of the work checks.
- Prefer 2–3 options with explicit costs over a menu of five. He is choosing between costs.
- Name items in human words (`仓库要不要改名`), never by a number.

## Skeleton that works

1. Header: title, date, one line of context (who produced what and why the document exists), one line
   saying every item ends with the reply that unblocks it.
2. **A. Decisions only he can make** — one block per decision.
3. **B. Process items** you can act on with one word.
4. **C. Discrepancies** vs the brief or vs earlier numbers, as 素材 vs 实测 pairs.
5. **D. What is already finished**, so he can spot-check.

Copyable skeleton: `templates/pending-decisions.md`.

## Render it (CJK-safe PDF, verified)

```bash
pandoc DOC.md -o DOC.pdf --pdf-engine=xelatex -V documentclass=article -V geometry:margin=1.8cm \
  -V mainfont="PingFang SC" -V CJKmainfont="PingFang SC"
```

- Set **both** `mainfont` and `CJKmainfont`; with a Latin mainfont the CJK glyphs and arrows drop out.
- Treat every `Missing character: There is no …` line on pandoc's stderr as a defect and replace that
  character: PingFang SC has no glyph for `⇒` (U+21D2) — use `→`. Regenerate until the count is 0.
- One blank line between a bold label and the bullet list under it, or pandoc swallows the list into the
  paragraph and the layout reads as run-on prose.
- Wide multi-column tables overflow the page; for content with long cells use labeled bullets.
- Verify before sending: `pdfinfo DOC.pdf | grep Pages`, then rasterize a page
  (`pdftoppm -png -f 2 -l 2 -r 90 DOC.pdf /tmp/pg`) and **look at the image** — column overflow and
  overlapping rows never appear in a text-only check. Fix and re-render; never ship a page you have not seen.
- Send it as `MEDIA:/abs/path/DOC.pdf` and give the `.md` path too (he annotates the source); offer
  another format instead of guessing it.

## Pitfalls

- **A sectioned report as the whole answer gets a 「看不懂」 round trip.** When the material is a list of
  items, ship the file first and keep chat to the decisions.
- **Do not reference your own document by section number in chat.** The number is a coordinate inside the
  file; the chat message needs the content.
- **A todo framed as "waiting on user" is not actionable.** Frame each as the reply that unblocks it
  (「回『改名』我就做」), so one word moves the work.
- **Do not hand over options with no position.** Mark a recommendation and its cost; a neutral menu reads
  as not having done the analysis.
- **The document the user reads is not the reviewer's brief.** Keep another agent's checklist language out
  of it; where their numbers disagree with yours, show both rather than silently picking one.
