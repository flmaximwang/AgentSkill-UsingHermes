# Sourcing job postings and scoring them against this user's profile

Companion to SKILL.md Step 10. Use when the task is "find the relevant postings, judge my match, record
it in the vault" — the pattern the user repeats whenever new openings appear.

## 1. Getting the JD text (China) without a login

| Source | URL pattern | What it gives |
|---|---|---|
| BOSS直聘 posting | `https://www.zhipin.com/job_detail/<jobId>.html` | **public 职位描述 block**; `jobId` is the trailing token of any share link (`m.zhipin.com/mpa/html/weijd/weijd-job/<jobId>?...`) |
| BOSS直聘 company | `/gongsi/job/<id>.html`, `/companys/<id>.html` | often renders "0 在招职位" for anonymous visitors — a rendering artifact, NOT evidence the company stopped hiring |
| 高校/科研机构 | `gaoxiaojob.com/announcement/detail/<id>.html`, `.../job/detail/<id>.html` | full institute ad with 岗位职责 + 任职要求 + 福利 |
| 智源社区 repost | `hub.baai.ac.cn/view/<id>` | institute/company calls reposted verbatim; frequently the most complete copy |
| 研究组 ads | `boshijob.com/article/...` | group-level (研究组) postings the institute board misses |
| Company site | `/<company>/join`, `/careers` | the roles a company actually staffs (often not the ones on job boards) |
| 猎聘 company page | `liepin.com/company/<id>` | a company's whole posting set + salary band |
| Overseas | `job-boards.greenhouse.io/<co>/jobs/<id>`, `compbiojobs.com`, `builtinsf.com` | full JD incl. salary range |

Rules that save a round trip:

- **Read the public page before asking for credentials.** Only the tail ("登录查看完整内容") is gated —
  the 职位描述 block is public. If a section is missing, ask the user for that one section; they are
  usually already logged in. Never take a password or an SMS code through chat.
- A mobile share link is not a page to open — map it to the canonical posting URL.
- Transient blocks (rate limits, "IP 存在异常行为") expire; retry the canonical URL later instead of
  concluding the platform is unreadable.
- Cross-check title vs content. The same company posts both an ML-research role and a design/deployment
  role under near-identical titles; the tags list often reveals which side the posting is on.

## 2. The five-dimension match score

| Field | Weight | "5" means | "1" means |
|---|:--:|---|---|
| 领域/工具链 `mDomain` | 25 | the JD's tool list matches what the user actually runs (AF3/Boltz-2/MPNN/Rosetta/RPXDock/MASTER) | tools/domain outside their stack (e.g. antibody humanization, MD) |
| 湿实验 `mWetlab` | 15 | the JD *values* wet-lab literacy (design↔bench hand-off, reading experiment results) | bench work **is** the job content → respect the "no pure wet lab" boundary and exclude regardless of score |
| 工程化/编排 `mEng` | 20 | what the JD asks for is at the user's current reach (scripts, Linux) | container + workflow engine + scheduler + production-grade code required now |
| 闭环案例 `mClosure` | 25 | no closed-loop case required | a verifiable design→build→measure→redesign case is stated as a requirement |
| 硬门槛 `mThreshold` | 15 | degree/experience comfortable ("博士期间课题可计入") | paper quotas, 3–5 years, or model training as must-have |

`score = (25·领域 + 15·湿实验 + 20·工程化 + 25·闭环 + 15·门槛) / 5`, max 100.
Buckets: `≥78 A·优先` / `68–77 B·可投` / `<68 C·暂缓`; a manual 否决 reason field forces **C·排除**
without distorting the score — keep the score honest and the decision separate.

Discipline:

- Every dimension carries **one quoted JD clause as evidence**; a score with no clause is an opinion.
- Label the composite as *your* judgment, not the employer's, and invite the user to dispute rows.
- Score the whole batch, then read the **per-dimension averages** — a systematically low dimension
  (usually 闭环 or 工程化) is the actionable finding, not the ranking.

## 3. Reading the gate that decides everything: is AI a must-have or a preference?

Bucket every posting into one of four, quoting the line:

| Bucket | Wording | Verdict for this user |
|---|---|---|
| must-have training | "对机器学习/深度学习理论有深入了解", "在 LLM 和 diffusion model 领域有深入研究并有相关项目经历", "精通 PyTorch" | out of scope (boundary: no algorithm development) |
| preferred | "熟悉 AI 在蛋白/大分子设计中的应用", "深度学习经验者优先", "具备生信算法开发经验和 AI 基础研究者优先" | in scope — the real gate is something else |
| tool-use only | "熟练使用 RFdiffusion/ProteinMPNN/Boltz2/BoltzGen/Rosetta", "能从结构、能量与机制解释设计决策，而非仅调用现成工具" | the archetype to aim at |
| ML handed to another team | "与机器学习算法团队配合完成蛋白质设计项目", "与算法及工程团队协作", "与 AI/ML 团队协作" | strongest evidence that design ≠ model work |

Report the **counts** across the batch. That number is the answer to "我没有任何 AI 项目经验，还能竞争吗" —
together with a correction: tool-**orchestration** experience (using AI tools inside a design pipeline,
judging whether outputs are trustworthy) *is* "AI project experience" in the sense employers mean; what
the user lacks is model **training** experience, which only a minority of postings demand.

## 4. The four real gates (what actually blocks this candidate)

| Gate | How it shows up in JDs |
|---|---|
| a verifiable closed loop | institute JDs state it outright ("至少 1 项可核验的『设计—实验验证—迭代』案例") |
| workflow engineering | container (Docker/Singularity) + workflow engine (Nextflow/Snakemake) + Git + scheduler (Slurm/K8s) + HPC, listed line by line |
| paper count | 研究组/副研究员 ads: first-author ≥5 SCI |
| years of engineering experience | company agent/platform roles: 3–5 years |

Say plainly that title-level prestige gates essentially never appear, and that none of the four requires
learning PyTorch. This is the sentence that resolves the user's recurring "AI 门槛" anxiety.

## 5. Deliverable shape

- One note per posting (fields in frontmatter incl. the five scores, platform-verified JD excerpt, the
  dimension table with quoted evidence, 缺口, 行动) under a library folder in the job-search vault.
- A `.base` over those notes (build recipe in the `obsidian-bases` skill) with views per question: all by
  score, by region, top bucket, dimension spread, excluded-with-reason, still-to-verify.
- A hub note embedding the base + a short "key regularities" section (gate counts, the real gates, where the
  best-fit organizations cluster — typically the compute × wet-lab dual-platform companies).
- When the user's question was "can I compete?", write the answer as its own note in the vault's 能力评估
  folder: a table of the competing profiles and this user's evidence-backed differentiators, a *short*
  honest list of what they still lose on, and the two or three things to build before graduating.
- Report the row count against what was asked, and list the 待核实 rows as next actions rather than
  presenting partial coverage as complete.
