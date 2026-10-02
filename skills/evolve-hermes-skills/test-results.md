# evolve-hermes-skills — description-head blind tests

The router sees only a skill's **name** plus the first **57 characters** of its description
(`agent/skill_utils.py` `SKILL_PROMPT_DESC_LIMIT`). Every hook added to that window is paid for by
something pushed out of it, so a head change is decided by a blind test, never by reasoning about it.

## Round 1 — 2026-10-02: does a reconcile hook fit?

**Question.** `update-hermes-skills` is one-directional (a pushed revision → the profile); judging a
profile copy that has *drifted ahead* of its pack clone now belongs to this skill (see § *Reconciling a
drifted installed copy* in `references/evolve-hermes-skills-routing.md`). Can that capability be put in
the 57-char window without pushing out the existing session-harvest triggers?

**Method.** 3 arms × 2 independent judges (`delegate_task` subagents, each blind: the candidate table is
the only input, prompts per judge in a different shuffled order, no positive/negative labels, gold held by
the author). 20 prompts: 5 existing triggers, 4 reconcile scenarios, 11 sibling distractors. Scoring =
single pick per prompt against gold; a prompt counts only if the judge names the gold skill.

| arm | evolve head (the visible 57) |
|---|---|
| A | `Harvest one finished session into skill edits. Mines the ` |
| B | `Evolve skills from a session, and reconcile a copy drifte` |
| C | `会话结束后把教训沉淀进 skill；并把 profile 副本与仓库 clone 的漂移 reconcile（判该` |

### Per-judge score

| judge | total | harvest (1-5) | reconcile (6-9) | siblings (10-20) |
|---|---|---|---|---|
| A1 | 12/20 | 3/5 | 0/4 | 9/11 |
| A2 | 13/20 | 5/5 | 0/4 | 8/11 |
| B1 | 20/20 | 5/5 | 4/4 | 11/11 |
| B2 | 15/20 | 4/5 | 3/4 | 8/11 |
| C1 | 14/20 | 5/5 | 1/4 | 8/11 |
| C2 | 20/20 | 5/5 | 4/4 | 11/11 |

### Per-arm

| arm | total | reconcile | reconcile minus #7 (see costs) |
|---|---|---|---|
| A | 12+13 = **25/40** | 0/4 + 0/4 = 0/8 | 0/6 (clean, minus #7) |
| B | 20+15 = **35/40** | 4/4 + 3/4 = 7/8 | 6/6 (clean, minus #7) |
| C | 14+20 = **34/40** | 1/4 + 4/4 = 5/8 | 4/6 (clean, minus #7) |

### Per-prompt matrix

| # | prompt | gold | group | A1 | A2 | B1 | B2 | C1 | C2 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 把这轮会话的教训存进 skill | `evolve-hermes-skills` | harvest | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | evolve the skills | `evolve-hermes-skills` | harvest | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | 分析这次会话里我调用过的 skill | `evolve-hermes-skills` | harvest | ❌`none` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | curator 这轮新建了哪些 skill | `evolve-hermes-skills` | harvest | ❌`maintain-hermes-skills` | ✅ | ✅ | ❌`maintain-hermes-skills` | ✅ | ✅ |
| 5 | 看看流程有什么 skill 没覆盖的 | `evolve-hermes-skills` | harvest | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 6 | profile 里的 skill 被改过了，跟仓库那份不一样，判断该不该保留 | `evolve-hermes-skills` | reconcile | ❌`update-hermes-skills` | ❌`update-hermes-skills` | ✅ | ✅ | ✅ | ✅ |
| 7 | 安装副本比 clone 新，更新前要不要直接 force 掉 | `evolve-hermes-skills` | reconcile | ❌`update-hermes-skills` | ❌`update-hermes-skills` | ✅ | ❌`update-hermes-skills` | ❌`update-hermes-skills` | ✅ |
| 8 | 本地优化了某个 skill，怎么同时维护仓库和 profile 两份 | `evolve-hermes-skills` | reconcile | ❌`update-hermes-skills` | ❌`update-hermes-skills` | ✅ | ✅ | ❌`update-hermes-skills` | ✅ |
| 9 | diff -rq 显示安装副本里有仓库没有的段落，这算优化还是脏改 | `evolve-hermes-skills` | reconcile | ❌`update-hermes-skills` | ❌`update-hermes-skills` | ✅ | ✅ | ❌`update-hermes-skills` | ✅ |
| 10 | 把 archify 这个 skill 装到 rdm-assistance 这个 profile 里 | `install-hermes-skills` | sibling | ✅ | ❌`install-hermes-skill-from-a-profile` | ✅ | ❌`install-hermes-skill-from-a-profile` | ❌`install-hermes-skill-from-a-profile` | ✅ |
| 11 | profile 里冒出来一个新技能，没有仓库也没有 lock 条目，怎么处理 | `install-hermes-skill-from-a-profile` | sibling | ❌`maintain-hermes-skills` | ❌`maintain-hermes-skills` | ✅ | ❌`maintain-hermes-skills` | ❌`maintain-hermes-skills` | ✅ |
| 12 | hermes skills check 报 update_available，怎么更新 | `update-hermes-skills` | sibling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 13 | 把这个 skill 从 hermes 类目换到 saxs 类目 | `install-hermes-skills` | sibling | ❌`maintain-hermes-skills` | ❌`maintain-hermes-skills` | ✅ | ❌`maintain-hermes-skills` | ❌`maintain-hermes-skills` | ✅ |
| 14 | 在 AgentSkill-DoingSAXS 仓库里加一个 skill | `author-a-skill-in-a-pack-repo` | sibling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 15 | 别的 bot 有这个 skill 而我没有，怎么补齐 | `maintain-hermes-profile-skill-parity` | sibling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 16 | 把 profile 里的几个技能删掉 | `remove-hermes-skills` | sibling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 17 | 新建一个 profile | `maintain-hermes-profiles` | sibling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 18 | hub 安装的 skill 显示了 2 张卡片 | `maintain-hermes-skill-cards` | sibling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 19 | 更新完 skill 后，跑着的会话什么时候能生效 | `update-hermes-skills` | sibling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 20 | 从别人的技能仓库里读一份索引表，不要安装 | `load-external-skill-index` | sibling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Verdict

**Adopt B** — `Evolve skills from a session, and reconcile a copy drifted from its pack repo.` It is the
only arm that never systematically misses: A scores 0/8 on the new reconcile prompts (every judge sent
all four to `update-hermes-skills`), B 7/8 and 6/6 once the ambiguous #7 is excluded, C 5/8 and 4/6. B
also keeps the harvest triggers (9/10 against A's 8/10) and produced the round's only perfect judge run.
C keeps the old triggers perfectly (10/10) but leaks three of the four reconcile prompts in one judge —
under this pack's rule (reproducible over prettier) B's cleaner new-capability profile wins over C's
1-point-lower total.

## Accepted costs — what still leaks, and why the head cannot fix it

- **#7 「安装副本比 clone 新，更新前要不要直接 force 掉」** is genuinely two-headed: it names the update
  step, so half the judges hand it to `update-hermes-skills`. Kept as-is in gold (the *judgment* is this
  skill's) and accepted as a coin-flip rather than special-cased — no head can own both readings.
- **#10 / #11 / #13 leak to siblings in every arm, including A** — pre-existing three-way rivalry between
  `install-hermes-skills` (`Install Hermes skills from GitHub, skills.sh, ClawHub and`),
  `install-hermes-skill-from-a-profile` (`Install a skill that exists only inside a Hermes profile`) and
  `maintain-hermes-skills` (`Manage the skills inside a Hermes profile — where they co`). Not caused by,
  and not fixable from, this skill's head: it needs a separate round over those three heads.
- **#4 「curator 这轮新建了哪些 skill」** survived in 3 of 6 judges; it is named later in the description
  than the window reaches, so it routes by inference. Accepted.

## Reproduce

Round 1 raw assets (gold, arm tables, authoritative per-judge prompt order parsed from the author's own
`delegate_task` call, and the scored picks): `~/.hermes/cache/scratch/blindtest-{gold,arms,trueorder,scored}.json`.
Re-running means rebuilding the three arm tables from this file, dispatching 2 fresh judges per arm with
`delegate_task` (blind, shuffled, no labels), then scoring the returned `results` against the gold column
above.
