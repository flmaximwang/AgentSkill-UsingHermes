---
name: biotech-career-analysis
description: >-
  Evaluate career paths for life-science PhDs transitioning to industry.
  Matches actual skill sets (not degrees/titles) to real job market data
  with concrete salary ranges, company listings, and honest gap analysis.
---

# Biotech Career Analysis

## When to trigger

Use this skill when a user with a life-science PhD (or equivalent) asks about industry career paths, job types, salary expectations, or which roles match their background.

## Core methodology

### Step 1 — Map actual skills (not just degree/department)
Categorize the user's skills into three tiers:

| Tier | Description | Examples |
|------|-------------|----------|
| **Core expertise** | Skills they can lead with | Protein expression, purification, characterization assays |
| **Tool usage** | They deploy/run, not develop | Rosetta, AlphaFold, ProteinMPNN, RFdiffusion — as a user |
| **Gap area** | Skills they explicitly lack | Algorithm development, Python/PyTorch, ML, proteomics |

> **CRITICAL DISTINCTION**: Distinguish **tool deployment** (running existing software, interpreting results) from **tool/algorithm development** (writing Python/PyTorch, training models, publishing at NeurIPS/ICML). These are two completely different career tracks with different salary bands and job titles. Mixing them up produces wrong advice.

### Step 2 — The "干湿闭环" reality check
Many life-science PhDs (especially in protein design) ask about "dry-wet loop" roles that combine computation and experiment.

| Level | Dry-wet loop demand | Reality |
|-------|-------------------|--------|
| Fresh PhD entry-level | **Low** | Large companies split computing and wet lab into separate teams |
| Senior/Principal (8+ yr) | **Medium** | Some roles emerge that bridge groups |
| Small startup (< 50 people) | **Higher** | Need generalists, but high risk |
| CRO protein services | **Low** (pure execution) | Formulaic, clear workflow |

**Honest framing**: If the user is a fresh PhD, the "dry-wet loop" is not a standalone job title. It is a **differentiator** within a wet-lab role — being the person on the protein team who can talk to the computational group and interpret their outputs.

### Step 3 — Search for real postings
Search 猎聘, BOSS直聘, 智联 for actual salary data and job descriptions by role type, not by what sounds interesting. Key search terms:

- **Protein scientist track**: `蛋白质工程`, `蛋白科学家`, `蛋白质高级研究员`, `蛋白表达纯化`
- **CMC track**: `CMC科学家`, `工艺开发`, `蛋白纯化工艺`
- **Avoid**: `AIDD`, `AI科学家`, `计算化学家`, `算法研究员` — these require development skills

### Step 4 — Present with layered specificity

**Tiered format (proven effective):**

1. **Salary panorama table** — by direction, entry-level and mid-career
2. **Concrete job listings** — company, location, salary, requirements
3. **Corrected priorities** — after considering user's feedback, re-rank
4. **Actionable advice** — which titles to search, which to avoid, how to position in interviews

### Step 5 — Always include "不要投" section
List job titles that sound related but are actually mismatched. This is the most valued part of the analysis because it prevents wasted applications.

### Step 6 — Accept correction and re-research
If the user points out a mismatch (e.g. "those jobs require algorithm development, not deployment"), **do not defend the original analysis**. Instead:
1. Thank them for the correction
2. Re-search with corrected keywords
3. Present a revised analysis that addresses the mismatch
4. Acknowledge the gap honestly

### Step 7 — Career-path analysis toward a stated long-term goal

When the user states an ultimate goal ("design proteins like drawing CAD", "build X"), do NOT
jump to job titles. Run this sequence:

0. **Gate on the planning horizon FIRST.** A stated long-term goal is *input* to the next
   decision, not a mandate to plan the endgame. Establish which decision is actually on the table
   now: (a) the next job after graduation, (b) positioning over the following 3–5 years, or
   (c) launching/owning the venture. Deliver that level only and keep the deeper analysis as a
   labeled background note — handing someone a product/funding plan when they asked which job to
   take reads as not listening, however good the plan is.
   Label every note you write by horizon (`现在做什么` / `3–5 年` / `长期愿景`) and cross-link them;
   when the user corrects the horizon, retitle and demote the deep note rather than deleting it.

1. **Define the goal before planning it.** Decompose the vague goal into separable capability
   layers and state which layer the user actually means. Example (protein design): L1 图纸语言 =
   module geometry + interface constraints; L2 装配引擎 = search/generate + interference & energy
   checks; L3 加工车间 = build and measure. A slogan like "CAD" bundles all three — the user
   normally wants to *be* the architect, not the engine author.
2. **Name the two roles the goal implies**: engine author (writes the algorithms) vs design
   architect (defines the standard parts and the fit/assembly rules). Then say which one the
   user's stated boundary (通常 "不做算法开发") allows. In mature CAD the highest-value people
   define parts and fit rules, not kernels — this reframing is the most useful single output of
   the analysis, because it converts "I can't write models" from a disqualifier into a role split.
3. **Map the user's EXISTING work onto that vocabulary** (see the evidence rule below). Users
   routinely do not recognize their own work as the asset it is — show them which of their past
   actions were already instances of the goal (e.g. parameterizing a cofactor geometry = writing a
   fit-tolerance table; a docking hard constraint on terminal distance = reserving an interface
   tolerance for a connector).
4. **Ground the field with citable sources**: one recent review + 3–5 primary papers, each with
   journal + year. Use them to answer two questions — is the user's direction already solved
   (→ help them pick a different seam) or still open (→ the open window is why their taste is an
   asset)? Quote the paper that shows the frontier is still unsolved, and the one that shows the
   obvious approach is already commoditized.
5. **Asset/gap table, then a 3-phase path** (in-program → next role → two exits), naming concrete
   target teams/institutions matched by skill continuity (whose tooling the user already uses).
6. **Market reality check (mandatory).** Before recommending a direction, verify it exists as a
   *paid job title*. If it does not, say so and repackage: which buyer problem does this capability
   solve? (e.g. modular protein assembly has no job title anywhere, but "rigid-interface fusion
   instead of linkers" sells as enzyme/binder engineering.)
7. **Timeline checkpoints** as a table (time → deliverable → pass/fail criterion), plus a
   risk/fallback table for the most likely way the plan dies.
8. **Say what NOT to learn.** Protecting the user's stated boundary ("don't pick up PyTorch — it
   drags you into the track you ruled out") is worth as much as the positive plan.

### Step 8 — When the real question is "which job do I take next?"

This is the most common form of the task, and it is not a strategy question. Answer it with the
asset framework, not with the vision:

- Score candidate job archetypes by the durable assets they hand the user, never by employer
  prestige: **A1** a closed design→build→measure loop / **A2** method & interface skill /
  **A3** industrial platform & workflow / **A4** product + customer understanding /
  **A5** network & ecosystem position / **A6** demonstrable credit (finished case, paper, reusable tool).
- Rule: **the first job must not be an attempt at the endgame.** It needs two things only — a case
  the user personally closed out, and time inside a real industrial process. Say this explicitly;
  people skip station one.
- Give stations (first → second → third) in which each station fills the asset the previous one
  lacked, and name what each archetype does NOT give (platform company: product view, shallower
  loop; CRO: deepest loop, no method or product; methodology group: method + academic credit, no
  industrial process; pure-algorithm roles: excluded by the user's boundary).
- Translate the unfinished project into industry language for interviews (pipeline orchestration →
  interface constraints and validation → both dry and wet hands-on). Frame an open project as
  process; never claim a closed loop.
- Scoring table, station plan and narrative template: `references/employment-accumulation-framework.md`.

### Step 9 — When the objection is "that category needs skills I refuse to build"

The question arrives as a self-diagnosis ("per your categories I only fit X, but X needs AI mastery to be
competitive"). Do not argue from the category label — decompose it:

1. **Split the category into sub-roles ordered by technical gate.** For research/methodology and platform
   teams the split that works is: (a) algorithm/model development (training, PyTorch, GPU);
   (b) **design & tool orchestration** (wrap existing tools into reproducible pipelines, decide what goes
   to the bench, own the prediction→experiment hand-off); (c) experimental validation & characterization.
2. **Read 3–5 real JDs and bucket every requirement into those tiers.** One hard posting must never define
   a category's barrier — postings whose title contains "AI" routinely list wet-lab technique as the core
   requirement and programming as 加分项. Show the user the quoted line.
3. **Match the user's boundary against the sub-role, not the category.** Refusing algorithm development
   still leaves tiers (b) and (c) open; refusing pure wet lab as well leaves (b) only.
4. **Name the tier in the vocabulary employers use**, give its archetype JD, its requirement buckets, and
   its *own* channels (community job board + that community's training workshop) — these postings often
   never reach local job platforms.
5. **State the honest fork and let the user choose**: working *inside* a methodology team (no model
   training needed) vs *leading* methodology (algorithm skill is the price of the microphone). Ask which;
   do not decide for them.

Sub-role table, verbatim JD buckets and tier channels: `references/employment-accumulation-framework.md` §2b.

### Step 10 — Score a batch of postings and hand back a queryable table

When the request is "检索所有相关岗位 → 看匹配度 → 记录到 vault"（or the vault should hold a
continuously-updated posting inventory）:

1. **Get the JD text first.** Public pages carry the whole 职位描述 block in China; only the tail is
   login-gated. URL patterns per platform: `references/job-posting-sourcing-and-scoring.md` §1.
2. **Score every posting on five dimensions** — 领域/工具链 25, 湿实验 15, 工程化 20, 闭环案例 25,
   硬门槛 15 — one quoted JD clause as evidence per dimension. Weights encode this user's profile:
   闭环案例 is heavy because an unfinished portfolio is the real bottleneck; 工程化 is scored on what
   the user can currently reach, not on how hard the job is.
3. **Bucket each posting by the AI gate** rather than by its title: must-have training / preferred /
   tool-use only / ML explicitly handed to another team. Then report the **count** across the batch.
4. **Keep excluded postings as rows** with a 否决 reason (paper count, years, PyTorch must-have,
   pure wet lab) instead of dropping them silently — the exclusion list is the part that saves the
   user time, and it must stay visible when the criteria change.
5. **Deliver as one note per posting + a `.base` + a hub note** (build recipe: `obsidian-bases` skill),
   then report the row count against what was asked and list what is still 待核实.

Scoring model, gates, URL patterns, deliverable shape:
`references/job-posting-sourcing-and-scoring.md`.

## Standing user boundaries (re-check, then apply to every recommendation)

Hard filters the user set. A plan that violates one is wrong however attractive it looks.

- **No algorithm / model-development roles.** Tool deployment, orchestration and interpretation are in
  scope; training/fine-tuning models, PyTorch, CUDA, distributed training are not. Do not list PyTorch as
  a gap to close unless the user changed this boundary in the current session.
- **No pure wet-lab roles.** Even when a wet-lab-dominant job is the fastest route to closing the loop
  (A1), this user rejects it as a detour away from the design side. Prefer the design/orchestration tier
  and treat the closed loop as a deliverable to be produced alongside the job, not as the job's content.
- **Academic posts must pass three tests** before being recommended: high PI output (近5年通讯作者论文数,
  output trend, first-author distribution across the group's students); controllable intensity (contract
  type + group structure, confirmed by asking two current/former members three fixed questions); and
  thought-content — reject groups where the work is 80% hands rather than head.
  Rubric and detection signals: `references/academic-lab-screening.md`.
- **Carry stated exclusions forward as exclusions**, with the user's reason, so a later session does not
  reintroduce them ("no pure wet lab" ⇒ CRO/CDMO and characterization-only rows are dead).
- **Region is 待确认 until the user states it in the current session** — never default to a country or city
  derived from older notes.

## Style rules for this user
- Direct, data-backed, concise
- Use tables for comparison — always include salary ranges and company names
- Be brutally honest about gaps; don't soften realities
- Separate "this fits you" from "this sounds related but doesn't fit"
- Provide specific job postings (company + location + salary) not generalities

## Pitfalls

- **❌ Recommending AIDD jobs to protein scientists**: AIDD/计算化学 roles require Python, PyTorch, ML model training. Protein design tool deployment does not qualify.
- **❌ Overselling "干湿闭环"**: At entry level this is a differentiator, not a primary role. Senior-level cross-functional roles exist but require 8+ years.
- **❌ Ignoring city salary differences**: Shanghai (88万 median) vs Shenzhen (72万) vs smaller cities — factor into recommendation.
- **❌ Treating academia postdoc as equivalent**: Institutes like SIAT/SMART pay 23-30k/month which is significantly less than industry entry-level.
- **❌ Recommending "蛋白质组学" (proteomics) roles**: Different field from protein design/engineering. Proteomics = mass spec based protein ID/quantification.
- **❌ Asserting skills the user never claimed**: assessment notes written from background inference ("大概率掌握 SPR/BLI", "北大+CAS 所以英语好") are worse than blank — they inflate the resume and collapse in the interview. Rebuild every claim from a named artifact or mark it ❌ (not done) / ❓ (unverified). See the skill-evidence rule below.
- **❌ Recommending a direction that has no job title behind it**: run the market reality check (Step 7.6) before writing the plan, and say plainly when the answer is "no such post exists".
- **❌ Trusting a company's "base city" from search snippets**: same-name unrelated companies exist (e.g. 杭州晶泰电子科技 ≠ 晶泰科技). Verify 工商全称 + 注册地址 before listing a company as having a base in a city, distinguish a subsidiary/research center from the parent brand, and keep the negative findings ("X/ Y/ Z have no base there") — they save the user the most time.
- **❌ Answering the endgame question instead of the next decision**: when a user describes a long-term
  ambition, the actionable request is usually the next career step; a venture/strategy plan they
  cannot act on now wastes the answer and signals you weren't listening. Fix the horizon first (Step 7.0).
- **❌ Reusing a stored profile field without re-confirming it**: location, enrollment stage and
  institution live in memory AND in narrative notes, and drift silently. An unconfirmed field is
  reported as 待确认 — never asserted, and never used as a default region or stage for the advice.
- **❌ Over-claiming the state of the field when judging a direction's feasibility**: before telling a
  user a design problem is "basically solved" or "impossible", pull the numbers (success rates,
  what still requires heavy screening) and cite them. Field-boundary notes with figures and
  citations: `references/protein-design-field-boundaries.md`.
- **❌ Letting the hardest JD in a category define the category's barrier**: one posting demanding PyTorch
  is not evidence that an entire archetype requires model development — the same company often hires both
  an ML-research role and a design-orchestration role under similar wording. Read 3–5 JDs and bucket each
  requirement by sub-role before telling the user what they cannot do (Step 9). At batch scale, report the
  count ("training is a must-have in N of M postings, all of them in directions you already excluded") and
  name the gate that actually blocks — closed loop, workflow engineering, paper count, years. That count,
  not an opinion about competitiveness, is the answer to "我有可能和其他应聘者竞争吗？" (Step 10).
- **❌ Re-offering a role type the user already excluded**: once a boundary is stated, the matching
  archetype rows are dead for this user. Drop them from the next table instead of presenting them again
  as options.
- **❌ Assuming a citation's phrasing means what the title says**: verify what a paper/tool actually does
  rather than the impression its abstract or name gives — the same discipline that applies to JDs applies
  to literature (read the Methods bucket, not the title).
- **❌ Letting a platform login wall end the research**: a company's job-list page can render "0 在招职位"
  for anonymous visitors, and a mobile share link opens an app-install page — while the JD itself is public
  at the platform's canonical posting URL (`https://www.zhipin.com/job_detail/<jobId>.html`, where `<jobId>`
  is the trailing token of the share link). Map the link and read it before asking the user for credentials
  or declaring the posting unreadable; when only the "登录查看完整内容" tail is missing, ask for that one
  section. Never accept a password or an SMS code through chat — codes go through the browser vault's code
  channel.

---

## 🏢 Company-level analysis for job seekers

Once the user knows their direction, they need to evaluate individual companies. Use this three-step workflow:

### Step 1 — Website "Business" page (3 min)
- What category is the company? CRO / CDMO / AI-CRO / AI-Biotech / tools & reagents
- What is its core technology platform (one sentence)?
- Where does revenue actually come from?

### Step 2 — Job postings (5 min)
Search 猎聘/BOSS直聘/公司官网:
- Are there roles matching the user's skill set? (protein engineering, protein purification)
- What tech stack is listed? (Python, Rosetta, AlphaFold, SPR)
- Are job numbers growing or shrinking? Recent postings?
- **This is the strongest signal** — a company's hiring tells you what they actually do day-to-day.

### Step 3 — Read one deep-dive article (10 min)
Search "XXX 公司 深度分析 招股书":
- Does actual business match website claims? (Often they differ — e.g. 晶泰科技 presents as AI-biotech but is actually AI-CRO)
- Who are the customers? (big pharma vs small biotech)
- Who are competitors?
- Financial health: profitable or burning cash?

### Decision
Combine all three signals to answer: worth applying to? What angle to emphasize in the interview?

> Full methodology with examples is in `references/company-analysis-for-job-seekers.md`
> City-level employer inventories and how to build/verify them: `references/china-ai-bio-employer-landscape.md`

---

## ⚠️ Evidence rule for advice about behaviors

**NEVER prescribe social behaviors** (how to network, what to say at a booth, follow-up scripts, "提供价值" templates) without first searching for actual success-case posts from people who have done it.

**Why**: Career networking advice "sounds right" but is often idealized. This session found:
- Conference booth → WeChat → job offer: **zero case studies found** in Chinese biotech
- Sharing a paper with a potential employer: **zero case studies found**
- In contrast, direct resume submission (海投) and internal referral via alumni: **multiple case studies**

**Procedure when user asks about networking/cold-contact:**
1. Search for actual experiences from similar-background people in the target industry
2. If no success cases found, say so explicitly and downgrade the advice level
3. Default to the empirically supported path (standard job application channels) rather than social strategies
4. If prescribing a social strategy, state its expected success rate as "low / medium / unknown" based on evidence found
5. The same standard governs founder/supporter/funding questions ("how do I find co-founders,
   backers, first users?"). Evidence-backed channels are peer/alumni networks and *structured*
   programs — accelerators with published terms, public competitions with open leaderboards,
   government talent/project programs, strategic industry capital that brings capability as well
   as money. Cold outreach to strangers has no documented cases in this domain either, and
   flattering the user's ambition is not a substitute for evidence. Sequence rule: make something
   showable (a spec doc, a demo, first experimental data) BEFORE approaching people — every one of
   these channels screens on artifacts, not on intent.
   Channel evidence table: `references/protein-design-field-boundaries.md`.

## Pitfalls (additions)

- **❌ Writing polished networking scripts without evidence**: The "conference booth → WeChat → follow-up" script works in Silicon Valley tech. In Chinese biotech, no evidence was found that this produces interviews. Default to direct applications, not social strategies.
- **❌ Recommending "provide value" as follow-up**: Sending a paper/article to a potential employer contact has no documented success cases in biotech. Avoid this as primary advice.

## ⚠️ Evidence rule for claims about the user's own skills

Before writing anything about what the user can do, read their actual work products: lab-vault
experiment logs, design/analysis repos (`pipelines/*/README.md`, `design_summary.*`, `synthesis_summary.*`),
protocol notes, git history. Then:

- Every skill line carries a named artifact next to it, or it is marked ❌ (not done) / ❓ (unverified).
- Separate three states and never blur them: **designed** / **experimentally validated** / **never got working**.
  A project that did not close out is real evidence of the tool chain, but must be labeled unfinished.
- The real headline of such a profile is often the gap itself ("no end-to-end completed project");
  say it in the first line of the assessment rather than burying it in a table.
- When identity or experience changes, sweep the WHOLE vault for stale tokens of the old version —
  degree, institution, graduation year, location habits appear in narrative notes too, not only in
  the profile block (`grep -E '北大|生化所|博士|毕业|日本'`), then fix every hit.
- Re-confirm volatile profile fields at the START of every session (current institution and group,
  enrollment stage and expected graduation year, city/region, whether a stated role boundary still
  holds). Treat both memory and the vault as possibly stale; a field the user did not state in this
  session is 待确认, never asserted. Carrying a stale location or stage into advice contaminates every
  recommendation and burns trust fast.
- An identity/experience correction is a TWO-STORE fix in one pass: purge it from memory AND grep the
  whole vault, back up before each edit (`cp f "f.bak.$(date +%Y%m%d%H%M)"`, timestamped so an
  existing `.bak` is never clobbered), then re-grep and confirm zero live matches (exclude backups
  via `file_glob`) before reporting done. Also fix the derived notes (job-archetype rows, soft-skill
  rows, region-specific sections), not just the profile block.
- Assessment files that were previously written from inference must be explicitly superseded
  ("旧版为推测式盘点，已废止") instead of silently edited, so the user can tell what changed.

## Verification
- For each claimed salary range, cite source (search result, compensation report, or job posting)
- For each recommended role, confirm the job posting does NOT require algorithm development skills
- Always double-check the distinction between "使用部署" and "开发" in the JD
- For social/behavioral advice, verify against actual case studies from the target industry/region
