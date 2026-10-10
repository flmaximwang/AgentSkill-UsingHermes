# 路由盲测账 · manage-global-heartbeat（原名 scan-heartbeat-sessions）

本技能的三轮 description 路由盲测（2026-10-10）。口径见 `skill-routing-blind-test`：候选**只给
description 前 57 字符**，两名判官互不相见、只读同一份判官输入、逐条选一个 skill 或 `none`；
**新增 skill** 时必须跑一轮（旧题逐字冻结重放，只把候选列表加长）。

| 轮次 | 名字 | 题数（旧/新） | 臂 A 旧题 | 臂 B 旧题 | 新能力 | 诱饵 | 旧题被抢 | 结论 |
|---|---|---|---|---|---|---|---|---|
| r6 | `scan-heartbeat-sessions`（首版，只读） | 59（54/5） | 35/54 | 40/54 | 4/4 | 1/1 | 0 条 | 定版 |
| r7 | 同名（加写侧 + 第 2 条诱饵） | 63（54/9） | 36/54 | 38/54 | 7/7 | 2/2 | 0 条 | 过渡产物（改名在跑轮途中，见下） |
| r8 | `manage-global-heartbeat`（改名后） | 63（54/9） | 38/54 | **39/54** | **7/7** | **2/2** | **0 条** | **定版** |

臂别：A / C 判官读臂 A（候选**不含**本技能），B / D 读臂 B（含）。四名判官各写 63 行 `P<n>|<skill>`，
打分只认落盘文件（`docs/routing-blind-tests/`）。

## r8 · 定版（当前名字）

```
blind-prompts-r8-manage-global-heartbeat.json    63 条题面（旧题 54 + 新题 9）+ 两臂候选集合
blind-key-r8-manage-global-heartbeat.json        金标（不进判官通道）
judge-input-r8-manage-global-heartbeat-{A,B}.txt 臂 A 50 候选 / 臂 B 51 候选
blind-judge{A,B,C,D}-r8-manage-global-heartbeat.txt
blind-roundr8-manage-global-heartbeat-score.txt
```

```bash
python3 -B docs/routing-blind-tests/make-blind-round.py --round r8-manage-global-heartbeat \
        --new-skill manage-global-heartbeat --decoy-ids 5,9 \
        --decoy-pick-map "manage-global-heartbeat#5=maintain-hermes-gateway,manage-global-heartbeat#9=hermes-session-routing-forensics"
python3 -B docs/routing-blind-tests/score-blind.py --round r8-manage-global-heartbeat \
        --new-skill manage-global-heartbeat
```

新题 7 条正例 = 4 条读侧（列出/扫/一览表/烧 token）+ 3 条写侧（clear 某条、从会话外停、改间隔）；
2 条诱饵答案不同（网关活体 → `maintain-hermes-gateway`；心跳消息进错线程 → `hermes-session-routing-forensics`），
所以用 `skill#id=answer` 逐条给（生成器为此加了这条支持）。

三道自检过：候选覆盖 ✓ · 截断口径 ✓ · 旧题逐字命中且一句一次 ✓。

## 接受的代价（写下来，下一轮别再当缺陷处理）

- **臂 A 里本技能的 8 条正例被两判官判成 `none`**（r6 时是落到 `hermes-session-routing-forensics`）——
  候选表里没有它、又没有明显更像的兄弟时，判官会说「都不合适」。这正是我们要的行为：**不该硬塞给兄弟**。
- **两条诱饵在 r7/r8 都是 2/2** ⇒ 头里的「heartbeat」没有抢走网关活体那一类题，也没有抢走
  「心跳消息投错了线程」那类题（后者属 `hermes-session-routing-forensics`），两条边界都是硬的。
- **旧题残差 15 条（臂 B, r8）全部落在既有兄弟之间**：`dream ↔ recruit-learning-in-profile`、
  `install-* ↔ remove-* ↔ update-*`、`maintain-hermes-*` 互串 —— 与 r5/r6 同一族，不由本技能引入。
- 臂 B 旧题比臂 A 高 1 条（39 vs 38）：候选表多一个名字会移动少数模糊题的落点，按既有口径算判官噪声。

## r6 / r7 · 旧名期

r6 是首版（只读，59 题，`--decoy-ids 5 --decoy-pick maintain-hermes-gateway`）；r7 是加写侧后、
**改名指令到达时正在跑**的那一轮 —— 判官看到的是旧名 `scan-heartbeat-sessions`，结论（旧题 38/54、
新能力 7/7、诱饵 2/2、抢 0）与 r8 一致，但它不是当前名字的记录，**保留作过渡产物**，不作为定版依据。
改名（`manage-global-heartbeat`）后按惯例重跑成 r8。

## 基线快照

旧题集 = 当时 `skills/*/test-prompts.json` 去重后的 54 条（**会随别人新增 skill 变化**），所以
「39/54」只在 2026-10-10 可复现；判据是**抢题 0 条 + 新能力 7/7 + 诱饵 2/2**，不是绝对分数。

本轮候选根是**软链镜像**（`/tmp/hb-blind/skills`），排除了 `skills/sipoon-codegraph-index`（没有 YAML
frontmatter ⇒ 生成器判「没有可读的 description」并整轮拒件）。它本来就当不了候选；补 frontmatter 是另一件事。
