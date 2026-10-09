# zsqlab11 Vault (OmcZ Follow-Up) — Structure & Log Format

Second lab vault, **different structure from zsqlab08**. Validated 2026-08-08 while adding
`ExpressionOptimization-001` from the MR-1 expression-condition session.

Vault root: `/Users/org_zsqlab/Obsidian/zsqlab11_OmcZ-FollowUp_2026.06.24/`
README: "项目 11：跟进项目 04，重点关注 OmcZ，需要得到足够的确定性"

## Key differences vs zsqlab08

| zsqlab08 | zsqlab11 |
|---|---|
| has `Projects/` | NO `Projects/` — has `Protocols/` (General/ + Specific/) |
| Records/ holds dated entries | Records/ is minimal (Records.md + templates/) |
| Logs all directory-form | Logs can be **flat file** OR directory (see below) |
| archive-id like `0016224/P103/2026.07.31` | archive-id like `null//2026.07.28` |

Other root dirs: `Dashboard/` (Calender, Notices, Rules/工作规范.md), `Tasks/`,
`Templates/`, `Lookup-11.xlsx` (sample/protocol lookup), `SnapGene/`, `Backup/`, `Pipelines/`.

## Log path convention — TWO forms

1. **Directory form** (logs with assets/protocols): `Logs/2026/07/22/StrainTransformation-001/StrainTransformation-001.md`
   with `assets/` next to the .md (Purification-001 also has `samples.canvas`).
2. **Flat file form** (simple culture logs): `Logs/2026/08/04/BacterialCulture-001.md`

Logs.base date formula: `file.path.split("/").slice(1,4).join(".")` → `Logs/2026/08/08/...`
displays as **2026.08.08**. So the YYYY/MM/DD path segments are mandatory.

## Log frontmatter (copy the sibling's schema)

```yaml
cssclasses:
  - a4-page
  - metadata-label-width-20em
UID: <uuid4 lowercase — use `uuidgen | tr 'A-Z' 'a-z'`>
tags:
  - Logs
highlight:            # list of 1-line summaries — rendered by meta-bind block
keywords:             # list
archive-id:           # empty until archived
bacteria-uid: 1126GO02
antibiotic: Gen, 10 ug/ml
seed-culture-broth: LB
seed-culture-volume-ml: "50"
seed-culture-flask: 100 ml 带挡板锥形瓶
seed-culture-temperature-℃: "30"
seed-culture-rotation-speed-rpm: "218"
production-culture-broth: M72_HLF1
production-culture-inoculation-volume-ml: "6"
production-culture-volume-ml: "600"
production-culture-flask: 2 L 带挡板锥形瓶
production-culture-temperature-℃: "30"
production-culture-rotation-speed-1-rpm: "218"
production-culture-rotation-speed-2-rpm: "88"
protocols:
  - <protocol UID>
  - "[[Purification & Characterization of OmcZ - S1.V1]]"
```

Optional culture fields: `culture-pellet-source: <UID of the culture log>`,
`culture-pellet-original-volume-ml`.

## Body template (every Log carries these blocks)

```markdown
# <Title>

```meta-bind-js-view
{highlight} as highlight
---
let highlight = context.bound.highlight;
if (!Array.isArray(highlight)) {
return "";
}

if (highlight.length === 0) {
return "";
}

// 直接返回处理结果
return highlight
.map((value, index) => `(${index + 1}) ${value}`)
.join("\n");
```

> **Keywords**: `VIEW[{keywords}][text]`

## Procedures / experiment sections

## Protocols

![[_Logs2Protocols.base]]
```

Copy the meta-bind-js-view block VERBATIM from an existing log — it renders `highlight:`
frontmatter as numbered lines.

## Naming convention

`<ExperimentType>-NNN` (counter per type): `PlasmidConstruction-001`, `StrainTransformation-001`,
`BacterialCulture-001`, `Purification-001`, `ExpressionOptimization-001`.

## Pitfall: same read_file-binary misdetection as zsqlab08

`Purification-001.md`, `工作规范.md` etc. come back from read_file as "Binary file". Use the
python3 fallback (see umbrella SKILL.md).

## Key protocol UIDs (link via `protocols:` frontmatter)

- `a7066159-acff-4e04-94fd-b0934ba75eb2` = **Purification & Characterization of OmcZ - S1.V1**
  (MR-1 expression + purification SOP; contains M72_HLF1 recipe, see below)
- `907d6bc3-cdcd-4c99-89f3-3d93895af959` = MR-1 Transformation (electroporation SOP)

## M72_HLF1 medium (from the OmcZ S1.V1 protocol; Lockwood et al. 2018)

- Stock A (1 L): 15 g casein digest peptone + 5 g soya peptone + 5 g NaCl; autoclave 600 ml/bottle
- Stock B (filter-sterilized): 400 mM HEPES + 400 mM sodium lactate + 600 mM sodium fumarate,
  pH 7.8 (NaOH)
- Use: 600 ml Stock A + 30 ml Stock B → final ≈ **19 mM HEPES / 19 mM lactate / 28.6 mM fumarate**
  (= the published M72 recipe 20/30 mM level, see recombinant-protein-expression skill refs)

## Logs.base views

- `Logs/Logs.base` — 总览 (grouped by 日期 formula), 进行中 (archive-id empty)
- `_Part_LogsChecker.base` — duplicate-name check
- `_Logs2Protocols.base` — linked-protocol table (embedded at the bottom of every Log)
