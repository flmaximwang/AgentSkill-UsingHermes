# 路由盲测账（diagnose-a-failed-hermes-update）

口径照 `skill-routing-blind-test`：候选 description **只给前 57 字符**，两名独立判官只读同一份判官输入、
逐条选 skill。两个候选臂喂**同一份 52 条题面**：

- **臂 A** = 既有 22 个 skill（本技能不在候选列表里 —— 这是本轮之前的实况）
- **臂 B** = 加进本技能的 23 个

每臂两名判官（共 4 个子代理，互不相见），判官把 `P<n>|<skill 名或 none>` 逐行落盘。
金标：旧题 47 条（各自 `test-prompts.json` 的 owner）+ 本技能 4 条正例 + 1 条兄弟诱饵
（题面故意写「Desktop 刚更新完」，正确答案 `maintain-hermes-desktop-app`）。

## r4-diagnose-update（2026-10-08，定版）

| 项 | 臂 A（22 候选） | 臂 B（23 候选） |
|---|---|---|
| 本技能 4 条正例 | 0/4（被最近的兄弟认领：`maintain-hermes-desktop-app` ×2 / `maintain-hermes-gateway` / `update-hermes-skills` 与 `none` 各一票） | **4/4（两名判官逐条一致命中）** |
| 既有 47 题 | 33/47 | 32/47 |
| 诱饵 1 条 | 1/1 | 1/1 |
| 两判官逐题一致 | 45/52 | 45/52 |
| 旧题被本技能抢走 | — | **0 条** |

臂间对照（各取第一份判官）：A→B 落点变化 9 条，其中 **4 条是本技能那 4 条正例**
（`maintain-hermes-desktop-app` / `maintain-hermes-gateway` / `maintain-hermes-desktop-app` / `update-hermes-skills`
→ 本技能）—— 这是本轮要测的新能力；其余 5 条（P15 / P23 / P40 / P49 / P51）全落在既有兄弟之间，
是判官噪声（本技能一次都没被选中）。

**定版判据**：既有题 0 条被抢走 + 本技能 4 条正例在两判官逐题一致命中 + 诱饵在两臂都稳定落在正确兄弟上
（而不是「两臂都不认领」）⇒ 两判官一致，不开第二轮。

## 已知残差（不是本技能的问题，不并进本轮账）

臂 B 里 15 条既有题没命中：P7 / P24 / P45（`install-a-hermes-plugin`）、P8（`remove-a-hermes-plugin`）、
P9（`leave-and-rejoin-a-discord-thread`）、P11（`hermes-session-routing-forensics`）、P17 / P20 / P39
（`maintain-hermes-skills`）、P22 / P23（`recruit-learning-in-profile`）、P40（`recruit-learning-in-session`）、
P49（`install-hermes-skills`）、P50（`maintain-hermes-models`）、P51（`author-a-skill-in-a-pack-repo`）——
都是各自头部的口径问题，要另开一轮，不记在本轮账上。

## 本轮产物

```
blind-prompts-r4-diagnose-update.json        52 条题面（含 owner / kind / expect_pick）+ 两个候选臂
blind-key-r4-diagnose-update.json            金标（不进判官通道）
judge-input-r4-diagnose-update-A.txt         判官输入：臂 A（22 候选）
judge-input-r4-diagnose-update-B.txt         判官输入：臂 B（23 候选）
blind-judge{A,B,C,D}-r4-diagnose-update.txt  四名判官的落盘 picks（A/C = 臂 A，B/D = 臂 B）
blind-roundr4-diagnose-update-score.txt      逐题矩阵 + 分组统计 + 臂间对照
```

## 轮次名要带自己的技能名

这个 clone 里常有别的会话并发写，**裸 `rN` 会互相覆盖**：生成器按 `--round` 拼文件名，谁后跑谁覆盖谁，
而且覆盖是静默的（2026-10-08 实测：另一个会话的 r3 生成件被我用同一个轮次名覆盖，补救过程与判据见
`docs/routing-blind-tests/NOTE-2026-10-08-r3-输入被并发会话覆盖并重建.md`）。所以本轮用
`r4-diagnose-update` 这种带技能名的轮次号。
