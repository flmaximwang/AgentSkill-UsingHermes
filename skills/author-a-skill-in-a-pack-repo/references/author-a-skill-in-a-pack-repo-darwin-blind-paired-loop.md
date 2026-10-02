# 在本机把一个包 skill 跑一轮 darwin 优化

上游理论（9 维 rubric、棘轮、HL-1…4）在 darwin-skill 自己的 SKILL.md 里 —— **那份是 hub 安装的、不要改**（跑它留下的
`results.tsv` 已经让该副本被判成「本地已改」）。这里只写它没写、而本机必须知道的部分。

## 1. 账本

- 位置：`~/.hermes/skills/agent-evolution/darwin-skill/results.tsv` —— darwin **自己的安装目录**，不是 `.claude/skills/…`。
  往它写一行 = 该副本从此被 hub 判成「本地已改」⇒ 以后 `hermes skills update darwin-skill` 要 `--force`。
- 列：`timestamp / commit / skill / old_score / new_score / status / dimension / note / eval_mode`。
  paired 行的 `new_score` 栏记**投票比数**（`3-0 better`），`status` 取 `keep | revert | baseline | fact_fix`，
  `eval_mode` 取 `paired | full_test | dry_run`。
- **只追加、不重排**：它是流水账。rebase/改名换了 sha 就把那一行的 sha 补正 —— 别留指向不存在 commit 的账。
- 每轮**一个维度**，`note` 里写清改了哪一节、judge 的原话裁断、体积变化；自审抓到的事实错误单开一行 `fact_fix`。

## 2. dim8 实测（带 skill vs 不带 skill）

- 设计：2 条最典型 prompt × 两臂 = 4 个 `delegate_task` 子 agent，一次批量发出。
- **带 skill 那一臂指向 skill 目录的冻结副本**：`cp -R skills/<name> <scratch>/<name>-baseline` 并记 sha256。
  测评期间你还要继续改真目录 —— 子 agent 读到半改状态，这一轮结果就作废。
- 两臂的 prompt 必须逐字相同；带 skill 臂额外告诉它「先读这份 SKILL.md 并严格照做」，并要它在答复末尾
  贴出「实际跑了哪些命令 + 关键输出原文行」，否则你只能拿到自述、没法判口径对不对。
- **判读不要预设「带 skill 赢」**：语料小的时候，对照组靠暴力枚举也能查到同样答案，甚至挖得更深
  （它会去读生成器源码，找到别名是迁移时人工硬编码的）。带 skill 的真实收益通常在三处：**口径**
  （命中列 / 弱产出 / 三种「空」都写对）、**时耗与调用数**（实测 25 s/8 calls vs 275 s/22 calls）、**不跑偏**。
  dim8 就按这三条打分，不是按「答没答对」。

## 3. paired 盲测（keep/revert 的唯一依据）

- 先把两版**落成静态文件**：`git show <sha>:skills/<name>/SKILL.md > A.md`（另一版 `> B.md`），给子 agent **文件路径**。
  不要给它 commit 号 —— 它会 `git log` 看出谁新谁旧，盲测就没了。
- **随机 A/B 映射**（判官 1、3 用「新作 = A」，判官 2 用「新作 = B」），自己留一张映射表还原票数。
  **映射表要机器可读，并且从生成它的那次调用里取回**（`messages.tool_calls` → 那次 `delegate_task` 的 `tasks[i]`），
  不要事后凭记忆补：判官答的 A/B 是**它自己那一版**的标签，脱离映射表毫无意义，映射漂一格就会把 `keep` 读成 `revert`。
  同一个判官在**一次 call 内**读两版 —— 判据是同尺比较，不是各打绝对分。
- 判官约束写死四条：只读那两份文件；**不许跑脚本**；**不许碰 git / 仓库**；不许因为「更长 / 更新」定优。
  末行严格输出 `VERDICT: A|B|tie | margin: clear|slight | reason: <一短句>`，方便机械还原映射。
- N 取奇数、默认 3，**一批发完**（一次 `delegate_task` 的多个 task 属同一个 completion unit）；多数决 keep/revert。
- 收工判据：多数判 `margin=slight` / `tie` **连续两轮**，或达 `MAX_ROUNDS`（默认 3）→ 进 Phase 3，**不要为凑轮数硬改**。
  报告里列出剩余短板与加权缺口，并说明「再加 1 轮 / 探索性重写」仍然是摆在桌上的选项。
- 判官的裁决会被「两版只差 N 行」这种局面逼成 `slight` —— 那不是失败，是**该停的信号**。

## 4. 结果卡片

- 模板 `~/.hermes/skills/agent-evolution/darwin-skill/templates/result-card.html`，用 `data-field="…"` 占位，正则替换即可。
- **坑一：「N 维度全景」那个网格是硬编码格子 + 模板自带的数字**（旧 8 维布局）。用 9 维 rubric 时必须换成 9 格、
  并把每个数字换成自己的真实分 —— 否则卡片上印的是**模板里别的 skill 的分数**，会被读成你的评估结果。
  **交付前必须打开图看一眼**（这一条只能靠看图发现，读代码看不出来）。
- **坑二：`scripts/screenshot.mjs` 依赖 playwright**（本机没装）。改用系统 Chrome 无头截图：
  `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --hide-scrollbars --window-size=980,1560 --screenshot=<out.png> "file://<card.html>"`
  （stderr 会喷两条 `task_policy_set … invalid argument`，无害）。

## 5. 收尾顺序（缺一件都不算完）

`git rebase origin/main`（或先确认 `HEAD~N == origin/main`）→ ff 合并 `main` → `git push origin main` →
`hermes --profile <p> skills update <name>` → `diff -rq` clone↔profile 应为空 + `skills check` 报 `up_to_date` +
**从装好的那份再跑一次脚本**。
装前先删安装副本里的 `__pycache__`（跑过脚本就会有），否则 update 会误报「本地已改」。
