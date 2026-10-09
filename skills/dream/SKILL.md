---
name: dream
description: "一键把某个 profile 里没有仓库归属的本地 skill 批量收编进包仓库：枚举（脚本）→ 判断每条归哪个包、与哪个已有技能交叉（JEV 在就优先用 JEV，否则派分类子代理）→ 迁移 → 整包重装回 profile。不属于本 skill 的：单个 skill 的收编（→ recruit-learning-in-profile）、装/更/卸的机制（→ install-/update-/remove-hermes-skills）、跨 profile 补齐（→ maintain-hermes-profile-skill-parity）、一轮会话自己的收获（→ recruit-learning-in-session）。触发：「一键收编」「把 local 里的技能批量迁到包仓库」「sweep profile skills into packs」「扫一遍这个 profile 的本地技能」"
---

# 批量收编一个 profile 的本地 skill

一条命令启动，交付是一张**用户批准过的归位表** + 每一行落在包仓库里、并从远端重新装回 profile。它不新增
机制：单个 skill 的五阶段流程（定位 / 评估 / 迁移 / 安装 / 退役）归 `recruit-learning-in-profile`，重叠审计
的方法归 `maintain-hermes-skills`，安装与退役的工具归 `install-` / `update-` / `remove-hermes-skills`。
本 skill 独占的是**批次**：一次枚举、一次判断、一次批准、按包并发、一次整包重装。

**为什么必须有这个 skill（而不是把单条流程跑 N 遍）**：单条流程在每个 skill 前要一次 `clarify`，129 条
就是 129 次询问；而批次能一次算完、一次拍板。代价是**每行的判断质量不能靠主 agent 一个人兜**——所以下面
这张分工表是硬约束，不是建议。

## Agent 分工（本 skill 的主体，先读这张表）

| 阶段 | 谁做 | 为什么非它不可 | 明确不许 |
|---|---|---|---|
| S1 枚举 | **主 agent 跑 `scripts/sweep-plan.py scan`** | 129 个候选手抄必错；判官输入必须是**脚本产物**（凭记忆转写的题面曾逐条 10/10 与源文件不同，整轮结论作废） | 不读技能正文、不判断归属 |
| S2 路由 | **JEV**（一次请求多题）；无 key → **分类子代理**，每 10–15 条一个 | 判断要独立视角：主 agent 刚枚举完，对「这条像哪个包」已有先入之见；JEV 只看 name+desc，比子代理更快更省 | 子代理只写自己的 `verdicts-task-N.jsonl`，不写包、不装、不起后台进程 |
| S3 交叉审计 | **每条「落点=已有技能」的行一个子代理** | 只有它能 grep 正文、给出接收侧 `file:line` 证明 already-there / net-new；JEV 从没看过正文 | 不改任何文件；只出两张清单 + 一个建议 |
| S4 决定表 | **主 agent + 用户** | 落点是用户的口径（「这条该不该进包」他一句话拍板），agent 推不出来 | 未获批准前不写任何包、不删任何副本 |
| S5 写入 | **每个目标包一个 writer 子代理**，包内串行、跨包并行 | 同一 clone 里两个 writer 会互相踩 README、生成段与提交；跨包并行没有共享文件 | 不许 `git add -A`、不许后台进程、不许碰本包之外的路径、不许替别人提交在途文件 |
| S6 验证 | **一条与所有 writer 不同的验证子代理** | 「自己写自己验」有乐观偏差；回读要有人复核 plan 的每一行 | 只读：`diff -rq` / `check` / lock / 脚本实跑 |
| S7 整包重装 | **主 agent 跑脚本生成的命令** | 命令由 lock 证据生成、条数与代价要在眼前 | 不装本批没改动的包 |
| S8 退役与汇报 | **主 agent** | 删除是最后一步，且必须等回读 | 回读没通过不许删 |
| S9 全库去重 | **主 agent 跑 `scripts/sweep-plan.py dedupe`** | 804 个副本手工比对必错；去重判据是脚本产物（filecmp + 旧名检测） | 不先 `--dry-run`、不备份就删 |

并发上限 10：>10 个包时按包分波（每波 ≤10 个 writer），别一次全派。所有子代理**前台跑完即结束**——子代理起
后台进程会把完成通知的会话路由 pin 到子代理身上，人面会话被顶掉（本机上游未修的坑）。子代理不能提问，所以
**所有用户闸口都留在主 agent**（S4 一次批准覆盖全批，S5/S6 只认那一份批准过的 plan）。

每条子代理任务书怎么写、必须回哪几件收据：`references/dream-agent-roster.md`。
JEV 的题面、分块与判读：`references/dream-jev-routing.md`。

## S1 · 枚举（主 agent，一条命令）

```bash
~/.hermes/hermes-agent/venv/bin/python3 -B \
  skills/dream/scripts/sweep-plan.py scan \
  --profile <profile> --packs-root ~/Documents/AgentSkill --out <scratch>/sweep-<date>
```

三种容器（`hub` / `bundled` / `local`）只有 `local` 是候选，判据是 lock 与 manifest，不是目录名：

- `hub` — 名字是 `<profile>/skills/.hub/lock.json` 的键 ⇒ 已有仓库与更新路径，跳过。
- `bundled` — 名字在 `<profile>/skills/.bundled_manifest` 里 ⇒ Hermes 自带的种子，不属于用户，跳过。
- `local` — 两者都不是 ⇒ 没有 lock 条目、没有 source of truth、没有生命周期 ⇒ 候选。

产出（全在 `--out` 里）：`inventory.tsv`（全表）、`judge-input.json`（**冻结**的候选表，name+desc）、
`packs.json`（每个包：路径 / 三段式标识符 / 分支 / 技能清单 / 本 profile 已装的成员与类目 / 是否空壳）、
`pack-index.txt`（各包 `category/name: desc`）。脚本自报 counts，先核一遍再往下走。

🔴 **没有类目层的 local skill 一条都不许留**（用户要求）：`skills/<名字>/SKILL.md` 直接躺在 skills/ 下就是形状
缺口 —— `hermes skills list` 的 category 列是空白，谁也说不清它属于哪一族。本机实测 **50 条**（default 16 +
五个 profile 34，其中几条还是「技能占着类目名」）。脚本把它们标 `no_category=true` 并在汇总里单独报数，
判官对这类行**必须同时给出目标类目**。

🔴 **落点空间是「非空壳且本机真有 SKILL.md」的包**，不是 `~/Documents/AgentSkill/` 下的全部目录：实测
285 个 `AgentSkill-*` 里只有 **27** 个能当落点，258 个是只有 `.git`、没有 `SKILL.md` 的半成品壳（其中多数
连 remote 都没有）。脚本把它们标 `empty` 并从判官候选里剔掉；`merge` 会拒收指向空壳的判定。
**但这不等于「没有包就留本地」**：值得复用却没有可合并的包时，落点是**新建一个包**（判据与做法见 S2 末与 S5）。

## S2 · 路由判断（JEV 优先）

1. **探活**：`$HERMES_HOME/.env` 里有没有 `TYPESAFE_API_KEY`（`grep -c`，不回显值），再打一次探针看 HTTP
   状态；代理端口不通表现为超时，别误判成 key 失效。
2. **JEV 在** → 把 `judge-input.json` 的每条按 `choice` 出题（选项 = 27 个包 + `__stay_local__`），
   第二层问落点技能（该包已有技能名 + `__new__`）；state 里放 `pack-index.txt`。一条请求里多题并行，
   按 token 预算分块。落 `verdicts-jev.jsonl`，**每条记下回复里的 `model` 字段**才算真机答案。
3. **JEV 不在**（无 key / 探针非 200 / 429 退避两次仍失败）→ 派分类子代理：每 10–15 条一个，任务书只让它
   `read_file` 那两个脚本产物，逐条写 `P<k>|<包名或 __stay_local__>`，落盘 `verdicts-task-N.jsonl`。
4. **标注纪律**：只有带 `model` 字段的算 JEV；子代理/人工填的一律 `source: agent`，报告里两组数字分开写，
   不许混着当「JEV 的效果」。
5. **新建包**：判官在「27 个包 + `__stay_local__`」之外还有第三个去处 —— `__new_pack__`。**两条判据都要满足**
   才准新建：① 这条技能讲的是**一类任务的通用方法**（认的是工具名或学科主题，正文里没有某个 profile 的私有
   数据路径 / 表名 / 项目名当主语）；② 现有落点包里没有一条覆盖它（S3 审计的 already there 为空或近乎为空）。
   满足 → 落点是新包，包名按 `AgentSkill-<工具名|主题>`；**本机已有同名半成品目录（有 `.git`、无 `SKILL.md`）
   就直接用那个仓库名**，没有才新建仓库。不满足（尤其只关某个 profile 的流程或记录）→ 留本地，不为它建包。

判据：`merge` 的覆盖率必须是 100%（有未判定的行就 exit 4），且没有任何 `dest_pack` 落在非落点包上。

## S3 · 交叉审计（只跑「落点=已有技能」的行）

「迁移」不是移动文件。落点是某个包里的**已有技能**时，先证明它与那条技能重叠在哪：派一个子代理读源
skill 整个目录 + 接收技能整个目录，按 claim（表头 / 实测数字 / 命令旗标 / 源路径）逐条 grep，产出**两张
清单**（already there 带接收侧 `file:line` / net-new）和一个建议：`merge`（把净值折进去）/ `new`（净值和
边界都不同，另起一条）/ `strengthen`（重叠少但话题相邻 ⇒ 在两边头部各加一句界限声明）。方法归
`maintain-hermes-skills-overlap-and-merge.md`，本 skill 只规定**先证明再动手**这个顺序。

## S4 · 决定表 → 一次闸口

```bash
… sweep-plan.py merge --dir <scratch>/sweep-<date> --profile <profile>
```

`plan.md` 按目标包分组，`install-cmds.sh` 是 S7 的命令清单（脚本按 lock 证据生成，**不执行**）。主 agent 把
plan 汇成一段话贴进回复，**四类分开报**：① 明确归位（判官一致）② 待定（低置信 / JEV 缺失 / 判给空壳）
③ 建议留本地 ④ **拟新建的包**；另把**没有类目**的行单列：迁移型的写清它落进包的哪个类目，
留本地型的写清建议挪进哪个**现有**类目（没有合适的就报「需要新类目」，别硬塞）（给出拟用的仓库名、它要吃几条、为什么现有 27 个包都不合适 —— 建仓库是对外
可见的持久动作，单独获批，别混在①里）。🔴 **STOP 等用户一句话**——决策点写在回复里，不做成要点选的表单题
（表单会挂在那里等超时）。

## S5 · 写入（每包一个 writer 子代理）

writer 的五步，全在这一条包里做完：① `git fetch` + `git status`，**profile 副本比仓库新时先逐字节回移植**
（那是别的会话在途的工作，单独一个提交）；② 按包形状写（frontmatter 只留 `name` + `description`、
references 用 `<skill>-<topic>.md`、正文末尾带那两行 Generated by Scripts 注释标记）；③ 包内脚本依赖按
`../../<兄弟技能>/scripts/` 定位；④ `auto-generate-skill-structure.py <name>` →
`verify-skill-package.py skills/<name>` → 预测扫描 verdict（非 `safe` 先按 `install-hermes-skills-scan-gate.md`
改写，`dangerous` 的 revision 在 hub 上永远装不上）；⑤ `git add skills/<name>`（pathspec）→ commit →
`git push origin <sha>:main`。

writer 必须回：commit sha、推出去的 sha、扫描 verdict、`git diff --cached --stat`。
**一次跑不完就在每条技能上各自提交**：长活被截断时，已提交的那些就是可回读的成果，不用从头再来。

**本批若含「没有类目」而留本地的行，writer 顺手补齐形状**：`mv skills/<名字> skills/<类目>/<名字>`
（没有 lock 条目，`mv` 即可；动完跑一次 `hermes skills list` 确认那一行的 category 不再是空白）。

**落点是新包时，writer 的活多一步：先把仓库建起来**（获批之后才动）——`gh repo create <owner>/<name> --private
--description "…"` → **立刻把 remote 换成 SSH**（`git remote set-url origin git@github.com:<owner>/<name>.git`；
`gh` 建出来是 https，裸 push 会卡在凭据提示直到超时）→ **README 是交付物的一部分**（索引表 + 三段式安装命令 +
「当前状态：装 / 不装」那一段，照同族包的 README 写）→ 按 `skills/<name>/SKILL.md` 布局写第一条技能 →
**首推之前必须扫出 `safe`**：这一个 revision 决定这个包以后还能不能被装上。

## S6 · 独立验证（一条只读子代理）

对 `plan.md` 的**每一行**核一遍，逐行 PASS/FAIL：交付的目录在 clone 里存在且与计划一致 ·
`git log --oneline -1 origin/main` 就是 writer 报的 sha · `hermes skills check <name>` = `up_to_date` ·
`diff -rq <clone>/skills/<name> <profile>/skills/<类目>/<name>` 为空 · `.hub/lock.json` 里
`installed.<裸名>.metadata.source_revision` == 仓库 HEAD · 从**装好的那份**用 `python3 -B` 跑一次脚本。
FAIL 的行回 S5 修，不静默放过。

## S7 · 整包重装（主 agent）

```bash
sh <scratch>/sweep-<date>/install-cmds.sh     # 先给用户看条数：一包 20 行 = 20 个 prompt 行，是代价
```

先 `install` 新成员，再 `update` 改动过的与**本包既有成员**（整包重装）。回读三件（同 S6 的判据）。

- `--profile` 是**全局前置 flag**（`hermes --profile X skills install …`），子命令里没有这个参数。
- `hermes skills check` 一次只吃一个名字；不带名字会把 90+ 个技能逐个对远端核，卡死一次交付。
- `hermes skills list` 的 Name 列会截断 ⇒ 用完整名 grep 它零命中，回读以 `diff -rq` 与 lock 为准。
- 别信收尾那句 `Updated N skill(s).`（扫描被拒时照打）；装了脚本的副本要用 `python3 -B` 跑，否则
  `__pycache__` 会让 `update` 报「kept your local edits」。
- 安装到**同一个类目**时会就地替换掉原来的 lockless 副本 —— 那是目标态（一个名字一个目录），不是少了一步。

## S8 · 退役与汇报

退役**只在回读通过之后**：先 `tar czf` 备份并说明备份在哪，lockless 的直接删目录，hub 装的走
`hermes skills uninstall <裸名>`。最后汇报四段：枚举数（local/hub/bundled）· 判定表 · **每行对应的证据**（sha /
verdict / diff / check 原文）· ≤3 条决策点（每条：要你定什么 / 为什么只能你定 / 我的建议与代价）。

## S9 · 全库去重（主 agent，一条命令）

S7 整包重装后，profile 里可能还残留大量与包同名的 local 副本（实测 2026-10-09：583 个相同 + 84 个有路径修复）。
这一步把它们清掉，让 profile 里只剩「包没有的」和「hub 装的」。

```bash
~/.hermes/hermes-agent/venv/bin/python3 -B \
  skills/dream/scripts/sweep-plan.py dedupe \
  --profile all --packs-root ~/Documents/AgentSkill \
  --backup ~/.hermes/backups/dream-dedupe-$(date +%Y-%m-%d)
```

三种情况：
- **SKILL.md 相同** → 直接删 local（包是 source of truth）
- **SKILL.md 不同，local 有旧 profile 路径引用** → 先回移植到包，再删 local
- **SKILL.md 不同，无路径修复** → 包更新，直接删 local

🔴 **先 `--dry-run` 看一遍**，确认数字合理再真跑。备份在 `--backup` 指定的目录。

## 检查点

| 触发 | 动作 |
|---|---|
| 要写任何包、建任何仓库、删任何副本 | 🔴 STOP：先出 plan + 命令条数，等用户一句话 |
| 候选 > 30 条 | 分块跑 JEV / 分波派子代理，别一次灌进一个上下文 |
| 扫描 verdict 非 `safe` | 🔴 STOP：按手册改写形态再推，`dangerous` 不可覆盖 |
| 想 `git add -A` / 想顺手带上别人的在途文件 | 🔴 STOP：只按 pathspec |
| 想把子代理填的选项当 JEV 结论 | 🔴 STOP：标 `source: agent`，两组数字分开报 |
| 回读没过就想删副本 | 🔴 STOP：先修，删是最后一步 |

## 反例（不要做的事）

- **不要在 SKILL.md 正文里写出那对 Generated-by-Scripts 注释的原文**：生成段脚本按文本找分隔符，正文里
  出现一次，它就把从那里到文件末尾整段当成自己的区段**覆盖掉**（本 skill 第一版就被吃掉半篇：S5 后半 +
  S6/S7/S8 + 检查点 + 反例 + 基线 + Support files 全没了，而 `verify-skill-package.py` 照样报 tree/pointers
  全绿）。要提它时写「两行 Generated by Scripts 注释标记」，不要写那串 HTML 注释本身；改完 `grep -c '^## '`
  数一遍小节数再看生成段有没有把它吃短。
- **不要把 N 个候选一次塞进一个子代理**：上下文爆掉、判断质量崩，还违背「一个包一个 writer」的边界。
- **不要同一个包派两个 writer**：README、生成段、提交会互相踩，合并出来的历史看不出谁覆盖了谁。
- **不要用 `mv` 当迁移**：包是 source of truth，profile 副本只在回读之后退役。
- **不要凭记忆转写判官题面**：题面必须是 `judge-input.json` 的产物，判官只读那一个文件、一次 `read_file`。
- **不要跳过扫描闸直接 push**：`dangerous` 的 revision 在 hub 上永远装不上，`--force` 也覆盖不了。
- **不要在写完后由同一个上下文自己验**：自评有乐观偏差，验证必须是另一条子代理。
- **路由盲测只测得到 description 的前 57 字符**：判官输入里每个候选只有「名字 + description 头 57 字」，
  所以**正文里补一句转指对路由毫无影响**（本轮实测：给 `organize-batch-saxs-dataset` 正文补了转指，
  抢题数一动不动）。要收窄边界只有两条路：改**描述头**（把吸题的词挪出去）或改**题面/gold**（题面缺上下文
  的弱 gold 会一直被别人抢，臂 A 里连它自己的主人都不认领）。改完必须重跑同一轮复核，别只看 diff。
- **不要留下没有类目的 local skill**：`skills/<名字>/` 直接躺在 skills/ 下，category 列空白（本机实测
  50 条）。迁移型的随装回落进包的类目；留本地型的当场 `mv` 进现有类目，别只报不修。
- **不要为「只关某个 profile 的记录或流程」建包**：新包只吃通用方法（S2 第 5 条两条判据都要满足）。
- **不要给「备选方案」清单**：判据不过就修判据，正路被堵就找官方机制并说明代价。

## 实测基线（2026-10-09，default profile，本机）

```
[sweep-plan] profile=/Users/maxim/.hermes skills=292 local=149 hub=132 bundled=11
[sweep-plan] packs=285 routable=27 placeholder=258 pack_skills=164 pack_index_est_tokens~18775
[sweep-plan] candidates=149 judge-input.json 44526 B   （scan 全程 21 s）
```

- 落点空间的 27 个包里，3 个**没有 remote**（`AgentSkill-HoldingConversations` / `UsingAstra` / `UsingEagle`）：
  能收内容，但装不回来（没有三段式标识符）——这类行要在 S4 显式报给用户。
- 149 条候选里 `.archive/` 下的退役件不计（脚本跳过 `.archive`）：那是退役落点，不是候选。
- 基线是快照：库与 profile 每天在变，收尾时要重测一遍并把数字改掉（带一条说明的提交）。

## Support files

| 文件 | 承担什么 |
|---|---|
| `references/dream-agent-roster.md` | 五种子代理任务书（逐字可抄）、并发与分波、每类必须回的收据、「子代理不许起后台进程」的原因 |
| `references/dream-jev-routing.md` | JEV 题面模板、两层走树、token 预算分块、判读与 `source` 标注、无 key 时的降级路径 |
| `scripts/sweep-plan.py` | `scan`（枚举 + 冻结判官输入 + 包索引）与 `merge`（判定 → plan.md + install-cmds.sh）；`--self-test` 跑一个抛掉即弃的三容器样例与 4 个拒收分支 |

## Skill Structure

<!-- Generated by Scripts -->

```
dream/
├── SKILL.md  (226 lines)
├── test-prompts.json  (27 lines)
├── test-results.md  (53 lines)
├── references/
│   ├── dream-agent-roster.md  (123 lines)
│   └── dream-jev-routing.md  (90 lines)
└── scripts/
    └── sweep-plan.py  (437 lines)
```

<!-- Generated by Scripts -->
