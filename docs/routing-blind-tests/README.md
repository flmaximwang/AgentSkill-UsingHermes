# 路由盲测账（AgentSkill-UsingHermes）

本目录存本包每一轮 description 路由盲测的 **五件套 + 打分报告 + 生成/打分脚本**。口径见 skill
`skill-routing-blind-test`：候选 description 只给**前 57 字符**，两名独立判官只读同一份判官输入、逐条选
skill；**新增一个 skill** 时必须跑一轮（旧题逐字冻结重放，只把候选列表加长）。

## 怎么跑一轮

```bash
# 1) 生成判官输入（两个候选臂）+ 金标；三道自检（候选覆盖 / 截断口径 / 旧题逐字命中）不过就不落文件
python3 -B docs/routing-blind-tests/make-blind-round.py --round r2 --new-skill <名> \
        --decoy-ids 5 --decoy-pick <正确答案>

# 2) 发 2 个判官 × 2 个候选臂（delegate_task，四个互不相见的子代理）。任务书里写死三件事：
#    只读 judge-input-r2-A.txt（或 -B.txt，一次 read_file，禁读技能目录）；逐行 `P<n>|<skill 名或 none>`
#    写进 blind-judge{A..D}-r2.txt；回答里原样重复（被截断也没关系，以落盘文件为准）。

# 3) 打分 → blind-roundr2-score.txt
python3 -B docs/routing-blind-tests/score-blind.py --round r2
```

臂别由判官文件名的末位字母决定：**A / C = 臂 A**（候选不含新技能），**B / D = 臂 B**（含）。

## 轮次表

| 轮次 | 日期 | 新技能 | 臂 B 新能力 | 臂 B 旧题 | 诱饵 | 旧题被新技能抢走 | 结论 | 账 |
|---|---|---|---|---|---|---|---|---|
| r1 | 2026-10-08 | maintain-hermes-models | 4/4 | 23/31 | 1/1 | 0 条 | 定版 | `skills/maintain-hermes-models/test-results.md` |

## 本目录实测的口径坑

- **两个脚本必须从仓库根跑**：`--skills-root` / `--dir` 都是仓库根相对路径，在 `docs/routing-blind-tests/`
  里跑会去找 `docs/routing-blind-tests/skills` 并以 `FileNotFoundError` 结束。
- **兄弟 skill 的 `test-prompts.json` 有两种形状**：一部分带 `id`，一部分没有（生成器用位置序兜底）。
  改别人的题面文件不是本目录的事，绕过去就行。
- **生成器按题面文本去重**：`skills/*/test-prompts.json` 的 glob 在建好新技能目录之后就已经包含它自己的题，
  不去重就会把新题投两次、被统计成「既有题」（判官结论不受影响，错的是统计口径）。
- **判官必须落盘**：批次完成摘要把长 picks 截成 `…(+100 chars)`、live transcript 也会截，只有
  `write_file` 出来的那份是完整的 —— 打分只认落盘文件。
- **诱饵题的 `expect_pick` 写错会让正确的 pick 看起来像错的**：修正只能在**打分前**做，并在轮次说明里写清
  「只改语义标注，题面 / 题号 / 判官 picks 一字未动」；事后改金标就是移动球门。

## r1 的文件清单

```
blind-prompts-r1.json      36 条题面（含 owner / kind / expect_pick）+ 两个候选臂的候选集合
blind-key-r1.json          金标（不进判官通道）
judge-input-r1-A.txt       判官输入：臂 A（19 候选）
judge-input-r1-B.txt       判官输入：臂 B（20 候选）
blind-judgeA-r1.txt        判官 1（臂 A）
blind-judgeB-r1.txt        判官 2（臂 B）
blind-judgeC-r1.txt        判官 3（臂 A）
blind-judgeD-r1.txt        判官 4（臂 B）
blind-roundr1-score.txt    逐题矩阵 + 分组统计 + 臂间对照
make-blind-round.py        生成器（含三道自检）
score-blind.py             打分器
```
