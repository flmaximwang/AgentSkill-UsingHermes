# Handing the session's gaps to darwin-skill

Phase 3 of `recruit-learning-in-session`. Phase 1 produced findings with receipts and a `dimension_hint`; this
file turns them into a `darwin-skill` run that is *about this session* rather than about the skill in the
abstract, and keeps the result inside this pack's conventions.

Contents: §1 which optimiser · §2 what Phase 1 gives darwin · §3 where to run it and what it writes ·
§4 the run · §5 when darwin's rules lose to this pack's · §6 reading the result · §7 the run is not done
until the profile has it

## §1 Which optimiser

**`darwin-skill`.** The user's stated preference is darwin-skill > skillopt, and the reason is structural
rather than aesthetic: darwin's ratchet is *paired within-judge comparison* with git as the memory, which
is the only gate in either skill that survives being wrong; skillopt's validation gate is a score delta on
a task suite you would have to build first (JSONL train/val splits, `scripts/skillopt.py init`), and the
unit it optimises is the skill text against *newly invented* tasks. This phase's whole input is the
session's real, already-failed prompts — darwin consumes test prompts directly, skillopt wants train/val
files.

Take `skillopt` only when darwin is missing or the finding is a **contract** problem (the skill's output
format is wrong for the consumer, so the fix is a small edit validated against a fixed task suite). Do not
run both on one skill in one pass: two ratchets over the same text make the result unattributable.

## §2 What Phase 1 gives darwin, and where each piece lands

| Phase 1 output | darwin slot |
|---|---|
| the session's real user prompts (verbatim, corrections included) | **Phase 0.5** test prompts → `<skill>/test-prompts.json`, field `prompt` + `expected` |
| `dimension_hint` per finding | **Phase 2 Step 1** the dimension to fix this round (one dimension per round) |
| `cost: user-correction` findings, in rank order | the order of rounds; highest cost first |
| `gap_class: missing-failure-branch` | dim3 — write it as the pack's three-column form: 触发条件 / 一线修复 / 仍失败兜底 |
| a receipt that a claim in the skill is false | dim5 — the judge-catching-a-fabrication case below is the precedent |
| `no_coverage` entries | *not* darwin's input: a finding with no skill is a new skill or a new reference, decided in Phase 2 |

Two rules that keep this honest:

- **`expected` is written from the session, not invented.** The session shows what the user wanted and
  what they had to say to get it; `expected` states that outcome. Precedent from this user's own repo —
  `AgentSkill-ObsidianManagement/skills/organize-obsidian-notes/test-prompts.json` is three real prompts
  with a paragraph of `expected` each, and the run against them is what produced that skill's later fixes.
- **A finding whose receipt you could not verify in §6 of the mining reference does not become a test
  prompt.** Optimising against an unverified claim bakes the misreading into the skill.

## §3 Where to run it, and which artifacts belong to the skill

Run it against the **clone**, with the skill dir at `skills/<name>/`. Two paths matter, and the user has
already settled both by precedent:

- **`test-prompts.json` and the result card are part of the skill**, committed in the pack repo.
  Measured: `skills/organize-obsidian-notes/` is tracked with `test-prompts.json` and
  `assets/darwin-card-20260930.png`, and the hub lock's `files` list for that skill includes both — so they
  install with the skill and the package stays self-describing.
- **`results.tsv` belongs to the darwin installation, not to the skill.** Measured precedent:
  `~/.hermes/profiles/software-development/skills/darwin-skill/results.tsv`. Writing it into a *hub-installed*
  skill dir is the shape to avoid: it leaves that copy "locally edited", after which `hermes skills update`
  skips it forever (`update-hermes-skills`) — the same trap that a `test-prompts.json` dropped into an
  installed copy by hand would set.
- Regenerating the structure tree after the run is mandatory, because the new files change it —
  `python3 scripts/auto-generate-skill-structure.py <name>`, then `verify-skill-package.py`.
- darwin's own paths are Claude-Code-shaped (`.claude/skills/*/SKILL.md`, `.claude/skills/darwin-skill/results.tsv`).
  Override them: the skill dir given to darwin is `<abs>/skills/<name>`, and `results.tsv` goes under the
  darwin skill's own directory, as in the precedent above.

## §4 The run

```
Phase 0.5   write <skill>/test-prompts.json from the session's prompts; show it to the user, confirm
Phase 1     baseline: 9-dim rubric + the dimension scores; the absolute total is triage only
Phase 2     one round = one dimension = one edit = one commit (message: "optimize <skill>: <summary>")
            gate: 3 independent judges, each reading before AND after in the SAME call, majority decides
            keep / revert; the absolute-score delta never does
Phase 3     summary; the result card renders from templates/result-card.html via scripts/screenshot.mjs
```

Measuring it the way darwin's own table wants: `eval_mode` = `paired` for the gate, `full_test` when
subagents actually ran the prompts, `dry_run` when they did not — and **a mostly-`dry_run` run must be
labelled as such in the report**, since dim8 carries weight 23 and a dry run leaves it invented.

Two constraints of darwin's that Phase 1 output will strain, with the resolution:

- **`MAX_ROUNDS` (3) and "one dimension per round"** can be too few when the session produced findings in
  four dimensions. Do not widen the round to fit — drop to the top 3 by cost and queue the rest; darwin's
  own break-on-diminishing-returns rule says the fourth round is usually redundant anyway.
- **The 150%-size guard** assumes a finished skill. The measured precedent is a case where it did not
  apply (a baseline that was a truncated 17-line draft); if this session's skill is similarly incomplete,
  say so explicitly in the run's summary instead of silently exceeding the guard.

## §5 When darwin's rules lose to this pack's

The pack's authoring conventions (`maintain-hermes-skills/references/maintain-hermes-skills-authoring-conventions.md`)
are what make a skill installable and loadable here, so they outrank darwin's general constraints when the
two conflict:

| Darwin says | This pack says | Follow |
|---|---|---|
| "不引入新依赖 — do not add scripts/references" | depth belongs in prefixed references, routed from the body | the pack: add the reference, add its route row, regenerate the tree |
| body can grow to 150% of the original | body under ~200 lines; references carry the depth | the pack: move the growth into a reference |
| skills live in `.claude/skills/*` | `$HERMES_HOME/skills/**`, installed from a repo | the pack: run on the clone, deliver through the hub |
| English or Chinese as the skill's own language | English prose, source-language evidence verbatim | the pack |
| "尊重花叔风格" for wording | imperative, why-first prose; no filler | the pack's prose rules, and darwin's dim7 penalty for filler (说白了 / 换句话说 / 首先其次综上) still applies |

Darwin's **runtime-neutrality gate is not a conflict** — it is a gate both sides agree on. Run its red-flag
scan before the first edit, and fix any hit that is instructional (a hardcoded `~/.claude/skills/<x>` path,
"在 Claude Code 里") as the round's P0, because this pack ships to any skills-compatible runtime.

## §6 Reading the result

- **`keep`** — the majority of paired judges said after ≥ before. Nothing else to check at this point except
  that the edit stayed inside the pack's conventions (§5).
- **`revert`** — take it as information, not failure: the dimension was not the real problem. Put the
  finding back on the Phase 2 ladder as a *droppable* item and report which dimension was tried and
  reverted; a revert with its reason recorded is worth more to the next run than a silent drop.
- **A tie** — darwin's own rule is "见好就收"; two consecutive slight/tie rounds end the run.
- **A judge catching a fabrication** — the highest-value outcome of the whole phase. The precedent in this
  user's repo: a judge found the skill claiming a `polyphone-review` feature the script did not have, and
  the fix was to *implement it*, not to delete the sentence. When the receipt already exists in the session,
  do the same: make the skill true rather than quieter.

## §7 The run is not done until the profile has it

Phase 3's edits live in the clone. Delivery is §3 of the routing reference: generator → verify → commit →
push `main` → `hermes skills update <name>` → read back `up_to_date`. Then, and only then, the report to the
user can say the session's lessons are live — with the commit ref, the update output, and the one line
saying which of them is *not* done (findings queued, reference not reached, dimension reverted).
