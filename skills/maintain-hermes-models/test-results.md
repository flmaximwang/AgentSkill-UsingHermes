# 路由盲测账（maintain-hermes-models）

口径照 `skill-routing-blind-test`：候选 description **只给前 57 字符**，两名独立判官只读同一份判官输入、
逐条选 skill。两个候选臂喂**同一份 36 条题面**：

- **臂 A** = 既有 19 个 skill（新技能不在候选列表里 —— 这是本轮之前的实况）
- **臂 B** = 加进新技能的 20 个

每臂两名判官（共 4 个子代理，互不相见），判官把 `P<n>|<skill 名或 none>` 逐行落盘。
金标：旧题 31 条（各自 `test-prompts.json` 的 owner）+ 新技能 4 条正例 + 1 条兄弟诱饵。

## r1（2026-10-08，定版）

| 项 | 臂 A（19 候选） | 臂 B（20 候选） |
|---|---|---|
| 新技能 4 条正例 | 0/4（被最近的兄弟认领：maintain-hermes-profile / maintain-hermes-profiles） | **4/4（两名判官逐条一致命中）** |
| 既有 31 题 | 24/31 | 23/31 |
| 诱饵 1 条 | 1/1 | 1/1 |
| 两判官逐题一致 | 32/36 | 32/36 |
| 旧题被新技能抢走 | — | **0 条** |

- **准入判据成立**：既有技能一题都没被新技能抢走；新技能自己的 4 条正例（「全库换模型」「单个 profile 换
  模型」「切完怎么证明真在用」「Model 列变 `--` 是不是写坏了」）在 B 臂两判官一致命中，在 A 臂一致落到
  兄弟 —— 说明这块地盘此前没有技能专门覆盖。
- **A→B 落点变化 7 条**：4 条是本轮新技能的正例（P4 / P24 / P27 / P30），另 3 条（P6 / P17 / P23）落在
  既有兄弟之间 —— 两臂用的是不同判官，这一部分属判官噪声，不是新头部造成的。
- **接受的代价（既有残差，不并进本轮）**：7 条旧题在**两臂都错**，是**它们**头部的问题，按口径另开一轮 ——
  P2（hermes-session-routing-forensics）、P6 / P10 / P26（maintain-hermes-skills ↔ evolve-hermes-skills）、
  P15（leave-and-rejoin-a-discord-thread ↔ maintain-hermes-gateway）、P16 / P17
  （install-hermes-skill-from-a-profile ↔ update- / evolve-hermes-skills）。
- **诱饵题的 expect_pick 在打分前修正过一次**：题面里出现「模型的 provider」但正确答案是
  `maintain-hermes-gateway`（两位判官一致给出），原先写的 `maintain-hermes-profiles` 是错的。只改语义
  标注 —— **题面 / 题号 / 判官 picks 一字未动**，`blind-prompts-r1.json` 与 `blind-key-r1.json` 各只有
  一行差异（`expect_pick`）。
- **定版**：两判官逐题一致、准入判据成立，**不开第二轮**。

五件套与逐题矩阵：`docs/routing-blind-tests/`（`blind-prompts-r1.json` / `blind-key-r1.json` /
`judge-input-r1-A.txt` / `judge-input-r1-B.txt` / `blind-judge{A,B,C,D}-r1.txt` /
`blind-roundr1-score.txt`）。

复跑（从仓库根执行；判官得另发）：

```bash
python3 -B docs/routing-blind-tests/make-blind-round.py --round r2 --new-skill <新技能> \
        --decoy-ids 5 --decoy-pick <正确答案>
python3 -B docs/routing-blind-tests/score-blind.py --round r2
