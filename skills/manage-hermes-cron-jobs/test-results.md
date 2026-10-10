# 路由盲测账 · manage-hermes-cron-jobs

本技能的 description 路由盲测（2026-10-10，收编进本包的当天）。口径见 `skill-routing-blind-test`：候选**只给
description 前 57 字符**，两名判官互不相见、只读同一份判官输入、逐条选一个 skill 或 `none`；**新增 skill**
时必须跑一轮（旧题逐字冻结重放，只把候选列表加长）。

| 轮次 | 名字 | 题数（旧/新） | 臂 A 旧题 | 臂 B 旧题 | 新能力 | 诱饵 | 旧题被抢 | 结论 |
|---|---|---|---|---|---|---|---|---|
| r9 | `manage-hermes-cron-jobs`（首版） | 68（63/5） | 46/63 | 44/63 | **4/4** | **1/1** | **0 条** | **定版** |

臂别：A / C 判官读臂 A（候选**不含**本技能，52 个），B / D 读臂 B（含，53 个）。四名判官各写 68 行
`P<n>|<skill>`，打分只认落盘文件（`docs/routing-blind-tests/`）。

## r9 · 定版

```
blind-prompts-r9-manage-hermes-cron-jobs.json    68 条题面（旧题 63 + 新题 5）+ 两臂候选集合
blind-key-r9-manage-hermes-cron-jobs.json        金标（不进判官通道）
judge-input-r9-manage-hermes-cron-jobs-{A,B}.txt 臂 A 52 候选 / 臂 B 53 候选
blind-judge{A,B,C,D}-r9-manage-hermes-cron-jobs.txt
blind-roundr9-manage-hermes-cron-jobs-score.txt
```

```bash
python3 -B docs/routing-blind-tests/make-blind-round.py --round r9-manage-hermes-cron-jobs \
        --new-skill manage-hermes-cron-jobs --decoy-ids 5 --decoy-pick hermes-session-routing-forensics
python3 -B docs/routing-blind-tests/score-blind.py --round r9-manage-hermes-cron-jobs \
        --new-skill manage-hermes-cron-jobs
```

新题 4 条正例 = 改投递目标 / 把单个 job 钉到另一个模型 / fire 失败按层排查 / 列全部 job 与健康字段；
1 条诱饵的正确答案是 `hermes-session-routing-forensics`（题面里出现「dream 定时任务派出的子代理」，问的却是
会话被 `session_switch` 顶掉 —— 路由归属，不是 job 本身）。

三道自检过：候选覆盖 ✓ · 截断口径 ✓ · 旧题逐字命中且一句一次 ✓。

## 接受的代价（写下来，下一轮别再当缺陷处理）

- **臂 A 里本技能的 4 条正例被两判官一致判成 `none`**（P21/P38/P59/P62）——候选表里没有它，判官不硬塞兄弟，
  这正是要的行为。臂 B 里这 4 条 4/4 判给本技能，`none` 全部消失：臂间对照里那 4 条 `none → 本技能` **不是抢题**，
  是本技能接住了自己。
- **诱饵 2/2 两臂一致** ⇒ 头里的「定时任务」没有抢走路由类题；边界（job 自身 vs 会话路由）是硬的。
- **旧题残差（臂 B 19 条、臂 A 17 条）全部落在既有兄弟之间**：`recruit-learning-in-profile ↔ dream ↔
  maintain-hermes-skills`、`install-/update-/remove-hermes-skills`、`maintain-hermes-gateway ↔
  maintain-hermes-desktop-app`、`leave-and-rejoin-a-discord-thread ↔ maintain-hermes-gateway` —— 与 r5/r6/r8
  同一族，**不由本技能引入**（臂 A 同题同错可证）。
- 臂 B 旧题比臂 A 低 2 条（44 vs 46）：候选表多一个名字会移动少数模糊题的落点，按既有口径算判官噪声。
- `score-blind.py` **退出码 1 属正常**：它给任一臂的每一处 ✗ 都计数（含臂 A 里按设计必 ✗ 的新能力），
  不代表本轮有问题；判据是**旧题被抢 0 条 + 新能力 4/4 + 诱饵 1/1**。

## 基线快照

旧题集 = 当时 `skills/*/test-prompts.json` 去重后的 63 条（**会随别人新增 skill 变化**），所以「44/63」只在
2026-10-10 可复现；判据是**抢题 0 条 + 新能力 4/4 + 诱饵 1/1**，不是绝对分数。

本轮跑之前修掉了一个挡闸的既有缺陷：`skills/sipoon-codegraph-index/SKILL.md` 整份没有 YAML frontmatter
（候选覆盖自检判「没有可读的 description」并整轮拒件 —— r8 当时是用软链镜像把它排除掉的）。补 frontmatter
后它进候选表（52/53 而非 51/52），生成器不再需要绕路。
