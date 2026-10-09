# Protein-Design Field Boundaries, Standardization Workarounds, and Support Channels

Condensed, cited notes for judging (a) whether a protein-design direction is feasible and
(b) where money, users and co-founders actually come from. Re-verify funding figures before
quoting them as current — rounds move.

## 1. What is already deliverable (and under what caveat)

| Capability | Reported figure | Source |
|------|------|------|
| Monomer generation for a specified topology, *in silico* | ~42% and ~54% in-silico success for two target folds | RFdiffusion, Nature 623 (2023) |
| Binder design, *experimental* hit rate | ~7–35% (RFdiffusion), ~10–100% (BindCraft), 16% de novo antibody hit rate (one closed model) | Structure 33(10) (2025) review |
| Binder design at real scale via a third-party validation lab | 1,320 designs / 16 targets → 26.8% binders | vendor case study |
| Enzyme active-site scaffolding | 41/41 benchmark sites scaffolded; active clones within <96 sequences | RFdiffusion2, Nat. Methods (2025) |
| Enzyme activity from designed scaffolds | 90% of designs active across 37 backbones | Nature 649 (2026) |

## 2. What is still unsolved (do not promise these)

- **Catalytic efficiency remains low**, so enzyme designs "require costly experimental optimization
  and high-throughput screening to be industrially viable" (Nature 649, 2026).
- **High-barrier catalysis**, and **switches/nanomachines integrating binding + conformational change
  + catalysis**, are named as open methods challenges (Nature 652, 2026 review).
- Sequence→structure relationships for folding, assembly and stabilization are not fully understood;
  β-rich designs are harder (aggregation); energy-function quality is still the main obstacle.
- Designed-but-failed is the norm: independent evaluations report failures from low recombinant
  expression, non-specific binding, or undetectable affinity — so "looks good in silico" is not a
  deliverable.

**Implication for advice**: "arbitrary design of a functional monomer with a specified geometry" is
*not* a solved, push-button problem. Do not tell a user it is easy, and do not tell them it is
hopeless — see §3 for how the field itself routes around it.

## 3. The field's own workaround is standardization (= the CAD answer)

| Workaround | Source |
|------|------|
| Standardized, extendable protein building blocks | Nature 627, 898–904 (2024) |
| Bond-centric modular design: regular coordination geometries + tailorable bonding interfaces, instead of arbitrary monomers | Nat. Mater. 24, 1644–1652 (2025) |
| Rigid junction libraries (tens of thousands of structurally unique junctions between repeat proteins) | PNAS 117(16) (2020) |
| Library-based "CAD-like" assembly: user draws a target shape, an algorithm searches a discrete block library | Elfin UI |
| Structure assembly from natural substructures (SEWING etc.) | Rosetta design applications |
| Explicit statement that complex machines can be built **without mastering de novo design** of flexible structures | artificial protein walker, Nat. Nanotech. (2026) |

So a design-platform thesis should be stated as: **standard-parts library (including the user's own
modules) + interface/assembly grammar + geometric & energetic validation + experimental loop**,
where "arbitrary" applies to *arrangement and combination*, not to monomer internal geometry.
Residual risks to name: library coverage, ddG/interface-prediction accuracy, validation throughput,
and whether a functional module still works once reassembled (context/allostery effects).

## 4. Who is building what (positioning matters more than the label)

| Player type | Product shape | Note |
|------|------|------|
| Cloud-lab / validation-as-a-service for protein designers | submit designs by web/API, automated wet lab returns data; community competitions as demand engine | validates that "someone else runs the experiments" is a real market; also the cheapest exposure platform for a newcomer |
| Scientist-facing protein-engineering SaaS | model + curated library rounds sold as software subscription | ML-engineer framing, not geometry/CAD framing |
| Foundation-model / generative-biologics startups | programmable-biology models sold via partnership | competes on model layer; combined raises are large |
| Chinese full-stack "dry-wet loop" agents | conversational agent + in-house automation + third-party lab dispatch; tens of产业化 projects delivered | closest existing analogue to "let everyone design proteins" — but the interaction paradigm is *ask in natural language*, not *draw/assemble* |
| Protocol/standard layer | a verifiable language for biological protocols as the interface between AI and the bench | most leverage, hardest to own |
| Incumbent CAD-for-molecules | modelling GUI + collaboration platform + Python API; licensing plus internal pipeline | proves the software-licence business model; its protein/enzyme stack is weaker than its small-molecule stack |

Gap to point at: **every existing platform is "state a request → get sequences".** None offers constrained,
parametric, editable *assembly* — no constraints/history tree/interference checking. That is the seam.

## 5. Support channels: what has evidence behind it

| Supporter | What they screen on | Evidence-backed channel |
|------|------|------|
| Technical co-founder | is the blueprint concrete and worth 3 years | same-school/same-lab engineering circles (documented: co-founding teams assembled entirely from one institution's circle); open-source contributors; competition teammates |
| Academic/technical endorser | is the method defensible | the user's own PI and lab (documented: an academic lab spun a company with a lab PhD as CTO); a complementary PI paired with a commercial founder |
| First users | does it solve one real problem | public competition/data platforms with open leaderboards; labmates and collaborators |
| Early funding | team + insight + early data | accelerators with published terms and equity thresholds; alumni investment funds that invest in their own alumni; strategic industry capital that supplies capability (automation, synthesis) alongside cash; government talent/project programs and provincial startup competitions |

**Evidence boundary**: no success cases were found for cold outreach (conference chat, sending
papers to strangers) leading to a co-founder, investor or offer in this domain. The pattern is
**existing-network + structured program**, identical to the job-search conclusion. Therefore the
sequencing advice is: build something showable first, then approach — and say the low expected rate
out loud instead of writing a warm-sounding script.
