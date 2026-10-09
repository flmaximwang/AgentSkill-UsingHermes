---
name: lab-vault-experiment-records
description: Search and summarize lab logs in zsqlab lab vaults (zsqlab01/08/10/11); add Records/Logs entries.
---

# Lab Vault Experiment Records (zsqlab01 + zsqlab08 + zsqlab11)

Use when the user asks to search, summarize, or write lab logs / experiment records in a
zsqlab lab vault:
- `~/Downloads/zsqlab01_hNCAM-Binder_2024.09.06/` (hNCAM-binder project — dated
  `Records/<range-id>/(YYYY-MM-DD) Title/` folders, plus `QAs/` Q&A summary notes)
- `/Users/org_zsqlab/Obsidian/zsqlab08_EcBfr-Mirror_2026.04.17/` (README title "zsqlab1 — 实验记录库")
- `/Users/org_zsqlab/Obsidian/zsqlab10_gammaPFD-Fiber_2026.06.25/` (γPFD heme-nanowire project — same Records/Logs/Projects/Protocols layout as zsqlab08; key logs: TEM-001, Purification-00x, BacterialCulture)
- `/Users/org_zsqlab/Obsidian/zsqlab11_OmcZ-FollowUp_2026.06.24/` (OmcZ follow-up project — DIFFERENT structure, see `references/zsqlab11-vault.md`)
- Design repos carry AA sequences for MW computation: `~/Repositories/zsqlab08_EcBfr-Mirror/design_summary.csv`, `~/Repositories/zsqlab10_gammaPFD/design_summary.tsv` (columns ID/Alias/AA Sequence); alias like `8.1.4` = construct name, e.g. sample `08BD01-8.1.4`

These are DIFFERENT vaults from the user's personal vault (`$OBSIDIAN_VAULT_PATH`) — never default to the wrong one.

## Vault structure (read root README.md first)

| Folder | Purpose |
|--------|---------|
| `Records/` | Experiment records — dated entries, sample analyses, data processing |
| `Logs/` | Raw per-experiment logs (structure below) |
| `Projects/` | Project docs |
| `Protocols/` | SOPs |
| `Dashboard/Rules/工作规范.md` | Doc conventions (dataview-table style for Notice-type docs) |

**zsqlab11 (OmcZ follow-up) has a DIFFERENT layout** — no `Projects/`, flat OR directory
Logs, `meta-bind-js-view` highlight blocks, `_Logs2Protocols.base` embed. Full format,
frontmatter schema, naming, protocol UIDs, and the M72_HLF1 recipe: `references/zsqlab11-vault.md`.

## Log path convention: log names are DIRECTORIES

A log path like `Logs/2026/07/28/Purification-001` is a **directory**, not a file. The note is
`Logs/2026/07/28/Purification-001/Purification-001.md`. Each log dir contains:
`<LogName>.md` + `assets/` (embedded images) + `workspace/` (analysis scripts + raw data).
When the user gives a log path without the trailing `.md`, append `/<LogName>.md`.
(zsqlab11 ALSO accepts flat `Logs/YYYY/MM/DD/<LogName>.md` for simple culture logs.)

## Pitfall: read_file misdetects valid UTF-8 .md as binary (hit 3× in one session)

Notes like `TEM-001.md`, `SampleMerge-001.md`, `Dashboard/Rules/工作规范.md` come back from
`read_file` as "Binary file - cannot display as text" even though `file` says "Unicode text,
UTF-8". Do NOT trust that error and do NOT try `iconv -f UTF-16` (produces mojibake). Read with:

```bash
python3 -c "print(open('<abs path>', encoding='utf-8').read())"
```

Same pitfall confirmed in zsqlab11 (`Purification-001.md`, `工作规范.md`) and zsqlab01
(`(2024-12-12) Preparation of pZcD-NCAM...md`). In zsqlab01 the file `file(1)` reported
"Unicode text, UTF-8" yet `read_file` still said binary — always fall back to python, never
`iconv -f UTF-16` (mojibake) and never conclude the file is corrupt.

## Pitfall: empty record folders ≠ missing records (rsync in progress)

A vault freshly copied via rsync from NAS can show record folders as EMPTY DIRECTORIES
while the transfer is still running. Do NOT report "no records found" from empty folders —
the user WILL correct you ("等同步完成再…"). This happened on zsqlab01: first pass found
40/69 record folders empty and 0 content matches for `293|HEK`; after rsync finished only
2/69 were empty and 34 matching .md files appeared.

Verification before concluding "not found":
1. Check sync completeness: count record folders with ≥1 .md vs empty
   (`for d in Records/<range>/*/; do find "$d" -name '*.md' | grep -v @eaDir | wc -l; done`).
   If a large fraction are empty, ask the user whether the sync finished.
2. Loose search patterns like `293` match dates/filenames (e.g. `Pasted Image ..._293.jpg`,
   `2024-10-09`), giving false-positive hits — use strict patterns
   (`HEK293|Expi293|293T|FreeStyle`) for content, and match folder NAMES for topic discovery.
3. Search strategy that worked on zsqlab01: read root README → list `Records/` subfolders
   (folder titles like `(2025-05-06) Preparation of hNCAM-TGP from 293 cells` are the best
   topic index) → read the main `.md` per folder → follow `obsidian://adv-uri` links in
   `## DESIGN` sections to predecessor records → cross-check `QAs/` summaries for overview.

## Pitfall: Synology @eaDir + @SynoResource artifacts pollute vault searches

NAS-shared vaults carry `@eaDir/` shadow dirs and `@SynoResource`/`@SynoEAStream` sidecar
files next to EVERY file, which flood `search_files` results (first listing was 50/50 junk).
Always filter: `grep -v "@eaDir"` in terminal pipelines, and exclude `@eaDir` paths when
listing files. `file_glob: "*.md"` alone does NOT remove them — @eaDir copies of .md files
exist too.

## Record format (Records/)

`Records/<title>-<date>.md`: frontmatter `tags: Records` + `keywords:`. Typical structure:
- `## Why do you start this project?` — motivation + linked evidence notes with `(UID)`
- `## How will this project go?` — planned steps, linked logs with `(UID)`
- `## 实验记录` — the summarized record (one subsection per log)

Log frontmatter carries `UID:` (used in cross-links as `[[LogName]] (UID)`), `highlight:`,
`keywords:`, `archive-id:` (e.g. `0016224/P103/2026.07.31`), `protocols:`.

## Summarize-logs-into-record workflow (validated 2026-08-04)

1. Read the target Records file FIRST (user may have edited it since your last change).
2. Resolve each log path: it's a directory → read `<dir>/<LogName>.md`.
3. If read_file calls it binary → `python3 -c` fallback (above).
4. **Backup before modifying**: `cp "<file>" "<file>.bak"` in the same directory (vault convention).
5. `patch` the record: keep existing Why/How sections, append `## 实验记录` with one subsection
   per log in **chronological execution order** (user preference: Step 1 → Step 2 → …, not
   principle-based summaries).
6. Per-log subsection: link `[[Logs/YYYY/MM/DD/Name/Name|Name]] (UID)`, archive-id in backticks,
   numbered procedure steps, results, sample tables copied verbatim from the log.
7. Re-read the full file after patching; check for omissions and trailing artifacts (a stray
   `- ` at EOF survived from the original — clean it). Extend frontmatter `keywords` to match
   new content (e.g. added `heme binding`, `TEM`).

## Adding a NEW Log (zsqlab11 workflow, validated 2026-08-08)

1. Locate the source session FIRST (`session_search`) — Logs are often created from a
   discussion/design session, not just wet-lab execution.
2. Decide flat vs directory form by looking at sibling logs (assets → directory).
3. Generate a fresh lowercase UUID: `uuidgen | tr 'A-Z' 'a-z'`.
4. Copy the sibling's frontmatter schema + the meta-bind-js-view highlight block VERBATIM.
5. Link protocols via `protocols:` frontmatter (UID + wikilink) and embed `![[_Logs2Protocols.base]]`.
6. Re-read the file after writing; verify the `Logs.base` 日期 formula resolves
   (`file.path.split("/").slice(1,4).join(".")` → YYYY.MM.DD from the path).

## zsqlab08 Bases data model (BacterialCulture → Purification)

- BacterialCulture notes: `UID`, `production-culture-volume-ml` (number, e.g. 1000), tag `Pipelines/Bacterial-Culture/AIM-01`.
- Purification notes: `culture-pellet-source` = the source culture's UID as a BARE STRING (`2e57f15b-…`); `culture-pellet-original-volume-ml` = QUOTED string (`"500"`).
- `%Culture2Purification%.base` embedded in each culture note lists that culture's purifications (filter: `Logs` tag AND `note["culture-pellet-source"].contains(this.note["UID"])`).
- `Logs/Bacterial Culture.base` = one row per culture, with per-row formula columns (culture time spans, total volume).
- Dataview IS installed (Calender.md / Dashboard.md / Bacteria.md use it) — use dataviewjs for cross-note rollups Bases formulas cannot do (see the `obsidian-bases` skill's `references/bases-formulas.md`).
- Some purifications have empty `culture-pellet-source` (e.g. Purification-001) — treat the relationship as sparse; match on UID, never assume completeness.

## Style rules

- Keep the user's original language (Chinese content stays Chinese).
- Preserve exact units/spelling from logs (µl, 30 µM, 413 nm, Capto Core 700).
- Match the nearest existing sibling doc's format; don't force the Rules template onto
  plain Records/Logs.
