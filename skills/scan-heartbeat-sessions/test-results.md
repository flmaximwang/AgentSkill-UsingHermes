# 路由盲测账 · r6-scan-heartbeat-sessions

新增 `scan-heartbeat-sessions` 这一轮的 description 路由盲测（2026-10-10）。口径见
`skill-routing-blind-test`（候选只给 description 前 57 字符；两名判官互不相见、只读同一份判官输入）。

## 五件套

```
blind-prompts-r6-scan-heartbeat-sessions.json   59 条题面（旧题 54 + 新题 5）+ 两臂候选集合
blind-key-r6-scan-heartbeat-sessions.json       金标（不进判官通道）
judge-input-r6-scan-heartbeat-sessions-A.txt    臂 A：50 个候选（不含本技能）
judge-input-r6-scan-heartbeat-sessions-B.txt    臂 B：51 个候选（含本技能）
blind-judgeA|B|C|D-r6-scan-heartbeat-sessions.txt  四名判官，各写 59 行 `P<n>|<skill>`
blind-roundr6-scan-heartbeat-sessions-score.txt 逐题矩阵 + 分组统计 + 臂间对照
```

生成 / 打分（从仓库根跑；`--new-skill` 必须写，打分器默认值是别的技能）：

```bash
python3 -B docs/routing-blind-tests/make-blind-round.py --round r6-scan-heartbeat-sessions \
        --new-skill scan-heartbeat-sessions --decoy-ids 5 --decoy-pick maintain-hermes-gateway
python3 -B docs/routing-blind-tests/score-blind.py --round r6-scan-heartbeat-sessions \
        --new-skill scan-heartbeat-sessions
```

三道自检过：候选覆盖 ✓ · 截断口径 ✓ · 旧题逐字命中且一句一次 ✓（去重 0 条）。

**本轮候选根是软链镜像**（`/tmp/hb-blind/skills`），排除了 `skills/sipoon-codegraph-index` ——
它没有 YAML frontmatter（全文以 `# 标题` 开头），生成器直接判「没有可读的 description」并拒件。
它本来就当不了候选；修它（补 frontmatter）是另一件事，本轮不动别人的在途件。

## 结果

| 臂 | 旧题 | 新能力 | 兄弟干扰项（诱饵） |
|---|---|---|---|
| A（不含本技能） | 35/54 | 0/4 | 1/1 |
| B（含本技能） | 40/54 | **4/4** | 1/1 |

**旧题被新技能抢走：0 条** ⇒ 定版。

## 接受的代价（写下来，下一轮别再当缺陷处理）

- **本技能的 4 条正例在两臂里都进题，臂 A 里一致落到 `hermes-session-routing-forensics`**（两判官都这么投）。
  那是候选里最像的兄弟——「对话/session 层面的事」而不是「这件事本身」——候选缺本技能时的必然落点，
  不是头部缺陷。臂 B 里 4/4 命中本技能（两判官逐题一致）。
- **诱饵（「网关目录里 gateway.heartbeat 一直在更新，能说明网关还活着吗？」）两臂两判官全部判给
  `maintain-hermes-gateway`** ⇒ 头里的「heartbeat」没有把网关活体那一类题抢过来，这条边界是硬的。
- **旧题残差 14 条**（臂 B）全部落在既有兄弟之间：`dream ↔ recruit-learning-in-profile` 一族 6 条
  （r5 起就在）、`install-* ↔ remove-* ↔ maintain-*` 一族、`maintain-hermes-models ↔ maintain-hermes-gateway`。
  臂间落点变化的 13 条里，除本技能那 4 条正例，其余 9 条同样是兄弟之间的判官噪声 —— 不由本技能引入。
- 臂 B 旧题比臂 A 高 5 条（40 vs 35）：候选表多一个名字会改变判官对少数模糊题的落点（同一批题、不同判官），
  按上一轮的口径这属于判官噪声，不并进本技能的账。

## 基线快照

本轮的旧题集 = 当时 `skills/*/test-prompts.json` 去重后的 54 条（**会随别人新增 skill 变化**，
所以「40/54」只在 2026-10-10 这一天可复现；判据是**抢题 0 条**，不是绝对分数）。
