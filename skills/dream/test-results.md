# 路由盲测账 · dream

> **改名说明（2026-10-09）**：本 skill 原名 `recruit-profile-skills-in-batch`，现名 `dream`。下面 r5 那轮的产物与复跑命令
> 保留旧名 —— 它们记的是当时真跑的东西，按包规「记录不改」。改名后的定版账是 r6。

## 结论

**定版（2026-10-09，轮次 `r5-recruit-batch`）。** 判据是包的准入标准：新增一个 skill 后**既有技能一题都没被
抢走**（旧题被新技能抢走 0 条），同时新能力自己 4/4 命中、诱饵题没被抢过来。

| 指标 | 结果 |
|---|---|
| 臂 B 新能力（本技能的 4 条正例） | **4/4**（两名判官逐题一致） |
| 诱饵题（P39，正确答案是 `recruit-learning-in-profile`） | **1/1**（两臂四判官一致投给兄弟，没投给本技能） |
| 旧题被新技能抢走 | **0 条** |
| 臂 B 旧题 | 41/57（老残差，见下） |
| 候选 | 臂 A 24 个 / 臂 B 25 个；题面 62 条（旧题 57 + 新题 5，含 1 条诱饵） |

## 本技能的 5 条题与逐判官结果

| 题号 | 类型 | 题面（截） | 臂 A 判官 1 | 臂 A 判官 2 | 臂 B 判官 1 | 臂 B 判官 2 |
|---|---|---|---|---|---|---|
| P8 | 正例 | 这个 profile 里攒了一大堆没有仓库归属的本地 skill，你帮我一次性扫一遍…别一条条问我 | 兄弟 | 兄弟 | **本技能** | **本技能** |
| P25 | 正例 | sweep this profile's un-homed skills into their pack repos… | 兄弟 | 兄弟 | **本技能** | **本技能** |
| P38 | 正例 | 有一百多条本地技能要归位，每条先判断归哪个包、跟包里哪条技能哪儿交叉，然后迁过去再装回来 | 兄弟 | 兄弟 | **本技能** | **本技能** |
| P40 | 正例 | 我想一键把 default 里的 local 技能批量收编进包仓库，收完再把那个包装回 profile | 兄弟 | 兄弟 | **本技能** | **本技能** |
| P39 | 诱饵 | 我 profile 里刚学到的一个新技能，想把它收进对应的包仓库，以后好维护 | 兄弟 | 兄弟 | 兄弟 | 兄弟 |

（「兄弟」= `recruit-learning-in-profile`。四份落盘 picks：`blind-judge{A,B,C,D}-r5-recruit-batch.txt`，
A/C 为臂 A、B/D 为臂 B。）

## 接受的代价（写清楚，下一轮别重踩）

- **本技能与 `recruit-learning-in-profile` 是相邻的，判别的唯一信号是「一批 vs 一条」。** 臂 A 里两名判官把
  4 条正例**全部**判给了单条流程（不是 `none`）——说明话题词（profile / 包仓库 / 收编 / 迁移）两边一样，
  只有「一次性扫一遍 / 一百多条 / 批量 / 一键」把它分开。**这几个词不许从 description 的前 57 字符里挪走**，
  改写头部时按 `docs/routing-blind-tests/` 的口径重跑一轮。
- 诱饵题（单条收编）四判官一致判给兄弟：这是本技能**不该抢**的题，也是它与单条流程的边界证明。
- 旧题 41/57 的残差里，P11 / P12 / P21 / P34 / P46 是**兄弟之间的老噪声**（两臂就已在
  `maintain-hermes-skills`、`recruit-learning-in-profile`、`update-hermes-skills`、`maintain-hermes-gateway`
  之间摇摆），与本技能的头部无关，不并进本轮结论。

## 复跑

```bash
cd ~/Documents/AgentSkill/AgentSkill-UsingHermes
python3 -B docs/routing-blind-tests/make-blind-round.py --round r5-recruit-batch \
    --new-skill recruit-profile-skills-in-batch --decoy-ids 5 --decoy-pick recruit-learning-in-profile
# 再派 2 名判官 × 2 个候选臂（四个互不相见的子代理），只读对应的 judge-input-<轮次>-{A,B}.txt、
# 逐行 `P<n>|<skill 名或 none>` 落盘 blind-judge{A..D}-<轮次>.txt（子代理前台跑完即结束）
python3 -B docs/routing-blind-tests/score-blind.py --round r5-recruit-batch \
    --new-skill recruit-profile-skills-in-batch
```
