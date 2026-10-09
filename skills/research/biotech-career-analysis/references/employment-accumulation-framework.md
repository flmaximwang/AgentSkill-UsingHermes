# Employment-Accumulation Framework ("which first job builds toward the goal?")

Use when a graduating life-science PhD asks which job to take, or asks that a first job
"accumulate" toward a longer-term goal. The deliverable is a *job-choice* framework, not a
venture plan (see SKILL.md Step 7.0 for the horizon gate).

## 1. Define the assets before scoring employers

The standard is not employer prestige; it is which durable assets the years buy:

| Asset | Content | Delivered by |
|:--:|------|------|
| **A1 closed loop** | one complete design→express→purify→characterize→conclusion case, owned by the user | wet-lab-dominant roles, CRO/CDMO |
| **A2 method & interface skill** | modular/interface design — geometry constraints + interface energetics | de novo / assembly-oriented groups |
| **A3 industrial platform** | pipeline engineering, data回流, DBTL, automation | platform/techbio companies |
| **A4 product & customer view** | who pays, what the pain is, what a deliverable looks like | customer-facing/交付 roles |
| **A5 network & ecosystem position** | future co-founders, users, funding access | depends on the company's ecosystem |
| **A6 demonstrable credit** | finished case, first-author preprint, reusable tool/spec doc | any role, but only if produced deliberately |

Diagnostic: a role that gives only A1 or only A3 is a *station*, not a destination. The best first
job hands over A1 + A3 together.

## 2. Archetype scoring (fill in per market, keep the column meaning)

| Archetype | Typical employers | A1 | A2 | A3 | A4 | A5 | A6 |
|------|------|:--:|:--:|:--:|:--:|:--:|:--:|
| Platform-company bridge role (dry-wet) | full-stack AI protein-design platforms | high | mid-high | **high** | mid-high | mid | high |
| Methodology group (research) | top de novo/assembly labs | mid | **highest** | mid | low | high (academic) | high (papers) |
| CRO / CDMO protein engineering | large CROs, protein-service shops | **highest** | low | mid | mid | mid | mid |
| Pharma computational + wet role | large pharma / biotech | mid-high | low | mid-high | mid | mid | mid |
| Pure algorithm / AIDD | AI drug-discovery teams | — | — | — | — | — | — |

The last row is a **不要投** row: JDs for these require training models (PyTorch/Python,
transformer/diffusion experience) and directly contradict a user who ruled out algorithm
development.

Trade-off to state plainly:
- Platform company → product and industrial process, shallower personal loop, may be pulled into
  pure computation.
- CRO → the deepest loop training, essentially no method or product exposure.
- Methodology group → method + academic credit, near-zero industrial experience.
- Pharma → stability, but computation and wet lab are often split across teams (weak A2).

## 2b. Decompose an archetype into sub-roles before scoring it

A row such as "methodology group (research)" hides three different jobs with three different gates.
Split it and score the sub-roles — the user's boundary usually kills one of them, not the whole row:

| Sub-role | What it does | Technical gate |
|:--:|------|:--:|
| algorithm / model development | trains and iterates generative or geometric models | **high** (PyTorch, GPU, distributed training) |
| **design & tool orchestration** | wraps existing tools (structure prediction, inverse folding, docking, design) into reproducible pipelines; decides what goes to the bench; owns the prediction→experiment hand-off | **mid-low** (scripting Python, HPC, workflow orchestration) |
| experimental validation & characterization | expression, purification, structure determination, binding/stability assays | low / none |

The middle tier is a real hired archetype with its own titles (Protein Design Scientist — Agentic/Workflow;
Computational Protein Design Scientist; Model-Driven Design Scientist; 蛋白质计算设计岗; AI蛋白设计科学家).
Requirement buckets read out of real postings:

| Posting type | Requirement buckets that decide the fit |
|------|------|
| **Design-orchestration scientist** | orchestrate protein language models / structure predictors / scoring tools into (semi-)automated pipelines; close the loop with the wet lab; **production-quality Python**; workflow orchestration a plus; call PLMs for scoring/representation — **not** train them; understand how predictions connect to wet-lab validation |
| Comparable senior design posts (pharma / techbio) | "technical fluency" **using** AlphaFold / Rosetta / PyRosetta / RFdiffusion / ProteinMPNN; ability to work **with** AI/ML teams on Python-based workflows; integrate computational outputs with experimental validation (library generation, screening, directed evolution) |
| **Avoid — same companies, different job** | "ML Research Engineer" / "ML Scientist" (3+ years training models in PyTorch, CUDA, distributed training) and C++ tooling postings on the same board |

Channels specific to this tier — these postings often never reach local job platforms: the domain
community's own jobs board (e.g. Rosetta Commons), its training workshop (a 1-day workflow course aimed
at people with tool exposure but limited project experience; membership status decides whether it is
covered or paid), and company career pages on Greenhouse/Ashby.

Gap list for a tool-native candidate entering this tier — all non-algorithm: refactor the existing
pipeline from notebooks/scripts into a modular package (config, tests, versioning); one real workflow
orchestration example (Snakemake / Nextflow or equivalent); call a protein language model for scoring and
compare against the user's own experimental data; interface energetics (interface score, ddG, shape
complementarity); and write up the "which prediction metrics did/didn't match experiment" case.

When the user also refuses pure wet lab, the orchestration tier is the *entire* remaining space — say that
explicitly, and note that the closed loop (A1) must then be produced as a side deliverable rather than
inherited from the job.

## 3. Station plan

| Station | Timing | Choose | Purpose |
|:--:|------|------|------|
| 1 | graduation → +3 yr | platform company (preferred) or CRO (fallback) | A1 or A3+A4, plus a loop the user personally closed |
| 2 | +3 → +5 yr | fill what station 1 lacked (deepen the loop, or move to platform/methodology) | no asset still missing |
| 3 | +5 yr onward | venture / owning the product | only now |

Rule to repeat to the user: **do not try to solve the endgame in the first job.** Station 1 only has
to produce a closed loop plus real industrial-process exposure; those are prerequisites for
everything later.

## 4. Preparation while still enrolled

| Priority | Action | Asset |
|:--:|------|------|
| P0 | close out one minimal loop (1–2 modules + one measurable function) | A1 — decides which archetypes are even reachable |
| P1 | abstract the in-progress project into a "modules / interfaces / assembly operators / validation rules" spec doc | A2 + A6 |
| P1 | first-author paper or preprint | A6 |
| P2 | working knowledge of automation/DBTL and high-throughput screening vocabulary | A3 entry ticket |
| do not | PyTorch / model training | contradicts the user's boundary unless the target is a pure algorithm role |

## 5. Interview narrative template

Do not say "I'm working on X and still optimizing it". Say, in three cited beats:

1. **Pipeline orchestration** — "I maintain a parametric design pipeline through N versions, each
   with reproducible directory layout and data archiving."
2. **Interface constraints and validation** — "I abstracted the coordination geometry into
   transferable parameters from a statistics-over-natural-structures dataset, and used clash
   scanning plus burial analysis as assembly-feasibility criteria (no-clash ≠ a real binding site)."
3. **Both dry and wet** — "I expressed, purified and imaged my own designs."

Keys: pipeline orchestration / geometric constraints and validation / dry and wet hands-on.
Caveat: present an open project as *process*; never assert the loop was closed.

## 6. Channels

Reuse the evidence verdicts in SKILL.md: broad applications + alumni/internal referral carry the
case studies; conference-booth cold contact does not. See also
`references/china-ai-bio-employer-landscape.md` for employer inventories.

## 7. Where the output goes

The user's job-hunting vault is a separate Obsidian vault with fixed sections (01 职业测评,
02 目标公司, 03 岗位方向, 04 能力评估, 05 能力提升, 06 投递追踪, 07 面试). Write analyses into the
matching section, label the note by horizon, cross-link with `[[wikilinks]]`, and back up before
editing any existing note.
