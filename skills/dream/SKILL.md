---
name: dream
description: "一键把某个 profile 里没有仓库归属的本地 skill 批量收编进包仓库：枚举（脚本）→ 判断每条归哪个包、与哪个已有技能交叉（JEV 在就优先用 JEV，否则派分类子代理）→ 迁移 → 整包重装回 profile。**全程无人值守**（不问人、不等人；判不出来的行留并列进汇报）。不属于本 skill 的：单个 skill 的收编（→ recruit-learning-in-profile）、装/更/卸的机制（→ install-/update-/remove-hermes-skills）、跨 profile 补齐（→ maintain-hermes-profile-skill-parity）、一轮会话自己的收获（→ recruit-learning-in-session）。触发：「一键收编」「无人值守地收编」「把 local 里的技能批量迁到包仓库」「sweep profile skills into packs」「扫一遍这个 profile 的本地技能」"
---

# 批量收编一个 profile 的本地 skill

一条命令启动，**全程无人值守**（不问人、不等人）：交付是一张按判据自动决议的归位表 + 每一行落在包仓库里、
并从远端重新装回 profile。它不新增机制：单个 skill 的五阶段流程（定位 / 评估 / 迁移 / 安装 / 退役）归
`recruit-learning-in-profile`，重叠审计的方法归 `maintain-hermes-skills`，安装与退役的工具归
`install-` / `update-` / `remove-hermes-skills`。本 skill 独占的是**批次**：一次枚举、一次判断、一次按规则决议、
按包并发、一次整包重装。

**为什么必须有这个 skill（而不是把单条流程跑 N 遍）**：单条流程在每个 skill 前要一次 `clarify`，129 条
就是 129 次询问；而批次能一次算完、一次按同一套规则决议。代价是**每行的判断质量不能靠主 agent 一个人兜**——
所以下面这张分工表是硬约束，不是建议。

## Agent 分工（本 skill 的主体，先读这张表）

| 阶段 | 谁做 | 为什么非它不可 | 明确不许 |
|---|---|---|---|
| S1 枚举 | **主 agent 跑 `scripts/sweep-plan.py scan`** | 129 个候选手抄必错；判官输入必须是**脚本产物**（凭记忆转写的题面曾逐条 10/10 与源文件不同，整轮结论作废） | 不读技能正文、不判断归属 |
| S2 路由 | **JEV**（一次请求多题）；无 key → **分类子代理**，每 10–15 条一个 | 判断要独立视角：主 agent 刚枚举完，对「这条像哪个包」已有先入之见；JEV 只看 name+desc，比子代理更快更省 | 子代理只写自己的 `verdicts-task-N.jsonl`，不写包、不装、不起后台进程 |
| S3 交叉审计 | **每条「落点=已有技能」的行一个子代理** | 只有它能 grep 正文、给出接收侧 `file:line` 证明 already-there / net-new；JEV 从没看过正文 | 不改任何文件；只出两张清单 + 一个建议 |
| S4 自动决议 | **主 agent 跑规则**（见「无人值守」一节） | 无人值守下没有闸口：规则把「明确归位」与「拿不准」分开 | 不问人、不等人；拿不准的行不写包 |
| S5 写入 | **每个目标包一个 writer 子代理**，包内串行、跨包并行 | 同一 clone 里两个 writer 会互相踩 README、生成段与提交；跨包并行没有共享文件 | 不许 `git add -A`、不许后台进程、不许碰本包之外的路径、不许替别人提交在途文件 |
| S6 验证 | **一条与所有 writer 不同的验证子代理** | 「自己写自己验」有乐观偏差；回读要有人复核 plan 的每一行 | 只读：`diff -rq` / `check` / lock / 脚本实跑 |
| S7 整包重装 | **主 agent 跑脚本生成的命令** | 命令由 lock 证据生成、条数与代价要在眼前 | 不装本批没改动的包 |
| S8 退役与汇报 | **主 agent** | 删除是最后一步，且必须等回读 | 回读没通过不许删 |
| S9 全库去重 + 无类目归位 | **主 agent 跑 `scripts/sweep-plan.py dedupe --fix-no-category`** | 804 个副本手工比对必错；去重判据是脚本产物（filecmp + 旧名检测）；无类目归位只能挪进该 profile 已有类目 | 不先 `--dry-run`、不备份就删；给无类目技能硬造类目 |

并发上限 10：>10 个包时按包分波（每波 ≤10 个 writer），别一次全派。所有子代理**前台跑完即结束**——子代理起
后台进程会把完成通知的会话路由 pin 到子代理身上，人面会话被顶掉（本机上游未修的坑）。子代理不能提问，
**主 agent 也不提问**：本 skill 没有任何用户闸口，S5/S6 只认 S4 规则产出的那份 plan。

每条子代理任务书怎么写、必须回哪几件收据：`references/dream-agent-roster.md`。
JEV 的题面、分块与判读：`references/dream-jev-routing.md`。

## 无人值守（本 skill 的唯一模式）

一条批次从枚举跑到整包重装，中间**不问人、不等人、不发要点选的表单**：所有判断落到下面这张表，跑完把汇报贴出来。
「没判出来」不是停下来问的理由，但**v2 也不再是「留本地」**：每条候选都必须有落点，没判完就回 S2 重判那一条。

| 情形 | 自动动作 |
|---|---|
| 判官一致（同一行 ≥2 份 verdicts 同落点）、落点是可用包 | 写入该包（进 S5） |
| 落点=包内已有技能、且交叉审计给出了 net-new 清单 | 按 net-new 折进那条技能（already there 的部分丢掉） |
| 置信低 / 判官分歧 / verdicts 缺失 / `no_category` 但给不出目标类目 | **v2 没有「留本地」**：这一行是**没判完** → 补一次判官重判；仍拿不准就在汇报里单列一行（写明缺哪条判据），**不进包、也不删它的副本** |
| 落点是**新包**（`dest.kind:"new"`） | **不建仓库**（对外可见的持久动作）→ 进汇报「拟建」段，等有人在的一次会话点名再做（S5 那段只在点名时才执行） |
| 上游有独立仓库的技能（见 S1 那一条） | 照常给落点、进包，但**汇报里单列**「该从上游装回」段（给出标识符），由用户决定改走 `install` |
| 退役（删本地副本）/ 整包重装（S7） | 回读全绿 + `tar czf` 备份落盘之后自动执行 |

汇报即交付（四段：枚举数 · 判定表 · 每行的证据 · ≤3 条要人拍板的事）。要人拍板的那些**不阻塞本批次**：
要建的仓库已经在「拟建」段里列清楚，下次有人在时说一句就能做；回读通过的行已经装回 profile 了。
**交付验收**：表里不许出现没有落点的行，也不许出现只凭名称/类目/profile 得出的落点——出现一条就得重判。

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
- ⚠️ **看着像 `local`、但该从上游装回的一类：上游有独立仓库的技能**——目录里带 `_meta.json` / `skill-card.md`
  （ClawHub 记号）、正文头部自报 `GitHub: <url>`、或正文里写着 `.claude/skills/<名>/` 这类上游自带的路径。
  它现在没有 lock 往往只是被手工拷进来过。实测 2026-10-10：`darwin-skill` 上游是 `alchaincyf/darwin-skill`。
  **v2 没有「留本地」这个答案**（`__stay_local__` 已废除，见 S2），所以这类行照样要有落点：判官照常判一个包、
  `why` 以 `upstream:<owner>/<repo>` 开头，主 agent 在汇报里把这类行**单列一段**「该从上游装回
  （本次先并入 <包>；改走 `hermes skills install <owner>/<repo>/…` 由用户定）」。

产出（全在 `--out` 里）：`inventory.tsv`（全表）、`judge-input.json`（**冻结**的候选表：id / skill / category /
`path` 与 `skill_md` 绝对路径 / `refs` 清单 / 正文字节数——判官拿它去读**全文**）、
`judge-input-bodies.json`（同一批，另把正文内联，给只会看文本的判官）、
`packs.json`（每个目录：路径 / 三段式标识符 / 分支 / 技能清单 / 本 profile 已装的成员与类目 / 是否空壳 / 是否可路由）、
`answer-space.json`（**判官的落点空间**：全部目录名 + 按轴分好的 `tool_dirs`/`topic_dirs` + `routable` 名单 +
两条新包命名式）、`pack-index.txt`（可路由包的各条 `category/name: desc`）。脚本自报 counts，先核一遍再往下走。

🔴 **没有类目层的 local skill 一条都不许留**（用户要求）：`skills/<名字>/SKILL.md` 直接躺在 skills/ 下就是形状
缺口 —— `hermes skills list` 的 category 列是空白，谁也说不清它属于哪一族。本机实测 **50 条**（default 16 +
五个 profile 34，其中几条还是「技能占着类目名」）。脚本把它们标 `no_category=true` 并在汇总里单独报数，
判官对这类行**必须同时给出目标类目**。

🔴 **落点空间是 `~/Documents/AgentSkill/` 下的全部 `AgentSkill-*` 目录名**（v2，2026-10-10 用户改口径）：本机
实测 **291** 个（274 个 `AgentSkill-Using<工具>` + 17 个主题包）。`routable`（有 remote + 本机真有 `SKILL.md`，
实测约 31 个）**只决定这个落点以后能不能 `install` 回来，不限制它能否当落点**：空壳目录由 writer 在写入前
`gh repo create <name> --private`（幂等，已存在则复用）或 `git remote set-url` 补上 remote。脚本把全部目录名、
按轴分好的两组、以及 `routable` 名单写进 `answer-space.json`——**判官的候选空间就是它**，`merge` 会拒收
指向名单之外的 `repo`。
**但这不等于「没有包就留本地」**（v2 根本没有这个答案）：值得复用却没有可合并的包时，落点是**新建一个包**
（两轴命名与判据见 S2，做法见 S5）。

## S2 · 路由判断（两轴先判；JEV 优先，无 key 走子代理）

**第一步是二选一，不是挑名字**：这条技能的**主语**是「某个软件/工具」（PyMOL、ATSAS、BioXTASRAW、Dolt、
git-annex、ComfyUI、Zotero、Discord、Obsidian、VSCode、OBS、Bilibili …）还是「一类任务/学科/项目」（主题）？
先答这一句，再在对应轴里挑落点：

- **工具轴** → `AgentSkill-Using<软件名>`：274 个存量名里挑；**本机没有这个工具**才新造 `AgentSkill-Using<X>`。
- **主题轴** → 17 个存量主题名里挑（AgentEvolution / AgentOrchestration / CloudDrive / CodeExplain / DoingSAXS /
  HoldingConversations / JobHunt / LabProject / ObsidianManagement / PlasmidEngineer / ProteinDesign /
  QuantInvestment / SoftwareDev / StructuredResponse / TravelGuide / WatchingVideo / WebInspection）；都不合适才
  新造主题名，且**主题名要少、同类合并**（一主题一包）。
`answer-space.json` 的 `tool_dirs` / `topic_dirs` 就是这两组的现成清单（脚本产出，别手抄）。

**三段问法**（一段一问，不许合成一段）：

1. **轴** —— 主语是工具还是主题？（二选一）
2. **落点** —— 该轴里哪个目录名？（`answer-space.json` 的 `dirs`；要新包就答 `new` 并给轴与名字）
3. **落点技能** —— 落点是已有目录时，并入它已有的哪条技能（从 `pack-index.txt` 抄），还是 `__new__`。

每条 verdict 一行 JSONL（`verdicts-jev.jsonl` / `verdicts-task-N.jsonl`）：

```json
{"id":"P12","dest":{"kind":"existing","repo":"AgentSkill-UsingGit","dest_skill":"__new__","action":"move"},
 "why":"…","evidence":"正文原句：「…」或 file:line","confidence":0.82,"source":"agent"}
{"id":"P13","dest":{"kind":"new","axis":"tool","topic":"Jev","personal":false,
 "boundary":"不吃 Cline/Cursor 这类编辑器的接入"},
 "why":"…","evidence":"…","confidence":0.8,"source":"agent"}
```

- `kind:"existing"`：`repo` 必须是 `answer-space.json` 里出现过的**目录名**；`dest_skill` 必须是那条目录**已有**
  的技能名或 `__new__`（脚本拿 `packs.json` 的技能清单核对，编出来的名字当场拒收）；`action` ∈
  `move` / `merge` / `strengthen`。
- `kind:"new"`：`axis` ∈ `tool|topic`、`topic` 非空、**`boundary` 必填**（这个包**不吃**什么）、`personal` 布尔。
  脚本按 `AgentSkill-Using<topic>` / `AgentSkill-<topic>` 命名；归一化（小写、去连字符下划线空格）后撞上已有
  目录名 → **复用那个仓库**（不建孪生目录）；**同一 topic 的多条合并进一个包**。
- **`personal:true` 且该 topic 只有 1 条** → 私人仓库，S5 才 `gh repo create --private`，汇报里单列。

🔴 **本版没有 `__stay_local__`**：judge-input 不再出现它，`merge` 收到一律**拒收**（exit 4，文案点明本版禁止
stay local）。每条候选都必须有落点——判不出来不是「留本地」，是**没判完**。

🔴 **严禁偷懒判法**（用户 2026-10-10 原话：「不能有机械、偷懒、不基于 skill 内容的判断（简单从名称提取关键词、
简单根据 profile 合并等都属于偷懒行为）」）：

1. **判官必须读 SKILL.md 全文**（含正文点名的 `references/` 段），不许只看 `name` / `description` / `category`；
2. **每个落点必须回一条正文证据**（正文原句，或 `file:line`）——`evidence` 空的 verdict 视为没判；
3. **禁止按类目批量套模板**（`obsidian/*` 全进 `ObsidianManagement`、profile 私有 ⇒ `AgentSkill-Private-<Profile>`
   这类映射已被用户明确驳回）：**每条独立判**，同类目下不同技能可以落不同包，允许新包只吃 1 条。

新建包的两条判据都要满足：① 讲的是**一类任务的通用方法**（认的是工具名或学科主题，正文里没有某个 profile 的
私有数据路径 / 表名 / 项目名当主语）；② 现有落点里没有一条覆盖它（S3 审计的 already there 为空或近乎为空）。
**本机已有同名半成品目录（有 `.git`、无 `SKILL.md`）就直接用那个仓库名**，没有才新建仓库。

**走哪条路**：① **探活** `$HERMES_HOME/.env` 里有没有 `TYPESAFE_API_KEY`（`grep -c`，不回显值），再打一次
探针；**探针返回 451**（`Typesafe is not available in your region`，2026-10-11 本机实测就是）与超时同样算
「不可用」，直接走子代理，别重试到超时。② **JEV 在** → 把 `judge-input-bodies.json`（正文内联的那份）当
`state` 分块出题，落 `verdicts-jev.jsonl`，**每条记下回复里的 `model` 字段**才算真机答案。③ **JEV 不在**
（无 key / 探针非 200 / 451 / 429 退避两次仍失败）→ 派分类子代理：**每 8–12 条一个**（判官要读全文，一条比
只给 name+desc 贵得多），任务书只让它 `read_file` 指到的那几份产物，落 `verdicts-task-N.jsonl`。
④ **标注纪律**：只有带 `model` 字段的算 JEV；子代理/人工填的一律 `source: agent`，两组数字分开写，不许混着
当「JEV 的效果」。

判据：`merge` 的覆盖率必须是 100%（有未判定或被拒收的行就 exit 4），且没有任何 `dest.repo` 落在
`answer-space.json` 之外。

## S3 · 交叉审计（只跑「落点=已有技能」的行）

「迁移」不是移动文件。落点是某个包里的**已有技能**时，先证明它与那条技能重叠在哪：派一个子代理读源
skill 整个目录 + 接收技能整个目录，按 claim（表头 / 实测数字 / 命令旗标 / 源路径）逐条 grep，产出**两张
清单**（already there 带接收侧 `file:line` / net-new）和一个建议：`merge`（把净值折进去）/ `new`（净值和
边界都不同，另起一条）/ `strengthen`（重叠少但话题相邻 ⇒ 在两边头部各加一句界限声明）。方法归
`maintain-hermes-skills-overlap-and-merge.md`，本 skill 只规定**先证明再动手**这个顺序。

## S4 · 自动决议（无人值守）

```bash
… sweep-plan.py merge --dir <scratch>/sweep-<date> --profile <profile>
```

`plan.md` 按落点分组（新包 / 复用已有目录 / 已有包三类），`resolved.json` 是逐行的机器可读决议，
`install-cmds.sh` 是 S7 的命令清单（脚本按 lock 证据生成，**不执行**）。主 agent 按「无人值守」一节的规则
**逐行决议、不等人**：明确归位的直接进 S5。汇报里分开写：① 明确归位 ② **拟新建的包**（只报不建）
③ **判官判了新包但归一化后撞上已有目录 → 复用**（单列，因为它改的是既有仓库）④ 上游自有仓库的行
（单列，见 S1）；另把**没有类目**的行单列：写清它落进包的哪个类目，或该挪进哪个**现有**类目
（没有合适的就写「需要新类目」，不硬塞）。要人拍板的事写进汇报即可，**不许停在那里等**——批次一路跑到 S8 才收尾。

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

**落点是新包时，writer 的活多一步：先把仓库建起来**——`gh repo create <owner>/<name> --private
--description "…"`（幂等：已存在就复用，退 1 时先 `gh repo view <owner>/<name>` 确认它真在）→ **立刻把 remote
换成 SSH**（`git remote set-url origin git@github.com:<owner>/<name>.git`；`gh` 建出来是 https，裸 push 会卡在
凭据提示直到超时）→ **README 是交付物的一部分**（索引表 + 三段式安装命令 +「当前状态：装 / 不装」那一段，
照同族包的 README 写）→ 按 `skills/<name>/SKILL.md` 布局写第一条技能 → **首推之前必须扫出 `safe`**：这一个
revision 决定这个包以后还能不能被装上。
**无人值守下 S4 照常产出这类行（v2 取消了「留本地」，判官的 `dest.kind:"new"` 就是落点）**，但**建仓库这一步
仍只在这次调用被点名要建包时才做**：名字先落进汇报的「拟建」段，用户点名后再建。

## S6 · 独立验证（一条只读子代理）

对 `plan.md` 的**每一行**核一遍，逐行 PASS/FAIL：交付的目录在 clone 里存在且与计划一致 ·
`git log --oneline -1 origin/main` 就是 writer 报的 sha · `hermes skills check <name>` = `up_to_date` ·
`diff -rq <clone>/skills/<name> <profile>/skills/<类目>/<name>` 为空 · `.hub/lock.json` 里
`installed.<裸名>.metadata.source_revision` == 仓库 HEAD · 从**装好的那份**用 `python3 -B` 跑一次脚本。
FAIL 的行回 S5 修，不静默放过。

## S7 · 整包重装（主 agent）

```bash
sh <scratch>/sweep-<date>/install-cmds.sh     # 先数一遍条数写进汇报：一包 20 行 = 20 个 prompt 行，是代价
```

先 `install` 新成员，再 `update` 改动过的与**本包既有成员**（整包重装）。回读三件（同 S6 的判据）。

- `--profile` 是**全局前置 flag**（`hermes --profile X skills install …`），子命令里没有这个参数。
- `hermes skills check` 一次只吃一个名字；不带名字会把 90+ 个技能逐个对远端核，卡死一次交付。
- `hermes skills list` 的 Name 列会截断 ⇒ 用完整名 grep 它零命中，回读以 `diff -rq` 与 lock 为准。
- 别信收尾那句 `Updated N skill(s).`（扫描被拒时照打）；装了脚本的副本要用 `python3 -B` 跑，否则
  `__pycache__` 会让 `update` 报「kept your local edits」。
- 安装到**同一个类目**时会就地替换掉原来的 lockless 副本 —— 那是目标态（一个名字一个目录），不是少了一步。

## S8 · 退役与汇报

退役**只在回读通过之后**（这是自动闸，不是人闸）：先 `tar czf` 备份并把备份路径写进汇报，lockless 的直接删目录，
hub 装的走 `hermes skills uninstall <裸名>`；回读有 FAIL 的行先修，修不动的那行跳过（副本不删）。最后汇报四段：
枚举数（local/hub/bundled）· 判定表 · **每行对应的证据**（sha / verdict / diff / check 原文）· ≤3 条要人拍板的事
（每条：要你定什么 / 为什么只能你定 / 我的建议与代价）——不等人回话，本批次到此结束。

## S9 · 全库去重 + 无类目归位（主 agent，一条命令）

S7 整包重装后，profile 里可能还残留大量与包同名的 local 副本（实测 2026-10-09：583 个相同 + 84 个有路径修复）。
这一步把它们清掉，让 profile 里只剩「包没有的」和「hub 装的」。同时把没有类目层的 local skill 挪进现有类目。

```bash
~/.hermes/hermes-agent/venv/bin/python3 -B \
  skills/dream/scripts/sweep-plan.py dedupe \
  --profile all --packs-root ~/Documents/AgentSkill \
  --fix-no-category \
  --backup ~/.hermes/backups/dream-dedupe-$(date +%Y-%m-%d)
```

去重三种情况：
- **SKILL.md 相同** → 直接删 local（包是 source of truth）
- **SKILL.md 不同，local 有旧 profile 路径引用** → 先回移植到包，再删 local
- **SKILL.md 不同，无路径修复** → 包更新，直接删 local

无类目归位（`--fix-no-category`）：
- 候选类目**只能是该 profile 自己已有的类目**
- 按技能名关键词匹配现有类目；匹配不上就报「需要新类目」，**不自动归入 misc**
- 主 agent 看到报告后判断：是真需要新类目（如 `mcp-server-integration` → 新建 `mcp-server-integration/` 类目），还是归入 `misc/` 兜底
- 实测 2026-10-10：default 15 条无类目，13 条进已有类目，2 条报告需要新类目

🔴 **`not_in_pack > 0` 是硬错误（exit 5）**：v2 的判据是 **local 必须为 0**——还有 local skill 没有任何仓库归属，
就说明这批没做完，不许当一句脚注收尾（用户 2026-10-10 改口径）。确实要先收尾再加 `--allow-not-in-pack`
（它只是把硬错误降级成警告，不改变事实）。

🔴 **先 `--dry-run` 看一遍**，确认数字合理再真跑。备份在 `--backup` 指定的目录。

## 检查点

| 触发 | 动作 |
|---|---|
| 判官分歧 / 置信低 / verdicts 缺失 / `no_category` 但给不出目标类目 | **v2 没有「留本地」**：这是**没判完**，补一次判官重判那一条；仍拿不准就在汇报里单列（写明缺哪条判据），**不进包也不删副本** |
| 判官只凭 name / description 就下了落点（`evidence` 空） | 那条 verdict 不算数：把它连同 `skill_md` 路径退回判官，要求读全文 + 回一条正文原句 |
| 落点是**新包** | 只报不建：包名与 boundary 进汇报「拟建」段（建仓库是对外可见动作，等有人在的一次会话点名） |
| 候选 > 30 条 | 分块跑 JEV / 分波派子代理，别一次灌进一个上下文 |
| 扫描 verdict 非 `safe` | 按手册改写形态再扫；仍 `dangerous` 的那条**不推**，跳过并写进汇报 |
| 想 `git add -A` / 想顺手带上别人的在途文件 | 只按 pathspec |
| 想把子代理填的选项当 JEV 结论 | 标 `source: agent`，两组数字分开报 |
| 回读没过 | 先修；修不动就跳过那一行并写进汇报，**不删它的副本** |

## 反例（不要做的事）

- **不要问人、不要等人**：本 skill 是无人值守的 —— 判不完就在汇报里单列（写明缺哪条判据），别用 `clarify`、
  别写「等你批准」、别发要点选的表单（表单会挂在那里等超时）。

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
  50 条）。迁移型的随装回落进包的类目；确实留本地的当场 `mv` 进现有类目，别只报不修。
- **🚫 判官不许机械 / 偷懒判**（用户 2026-10-10 原话：「不能有机械、偷懒、不基于 skill 内容的判断（简单从名称
  提取关键词、简单根据 profile 合并等都属于偷懒行为）」）——就这三条，逐条都要在 verdict 里能验：
  ① 只看 `name` / `description` / `category` 就下结论（**必须读 SKILL.md 全文**——judge-input 已经给了
  `skill_md` 绝对路径与 `refs` 清单，没有借口）；
  ② 落点没有正文证据（**每条必须回一条正文原句或 `file:line`**）；
  ③ **按类目批量套模板**（`obsidian/*` 全进 `ObsidianManagement`、profile 私有 →
  `AgentSkill-Private-<Profile>` 这类映射本会话已被用户明确驳回）。**每条独立判**：同类目下不同技能可以落
  不同包，新包只吃 1 条也允许，不为凑整齐牺牲判断。新增包同样受这一条的约束：它要么认工具名、要么认主题，
  不能是「这个 profile 的杂项」这种垃圾抽屉。
- **不要给「备选方案」清单**：判据不过就修判据，正路被堵就找官方机制并说明代价。

## 实测基线（2026-10-11 02:1x，default profile，本机）

```
[sweep-plan] profile=/Users/maxim/.hermes skills=261 local=99 hub=151 bundled=11
[sweep-plan] packs=290 routable=33 placeholder=257 pack_skills=408 pack_index_est_tokens~37190
[sweep-plan] dest_space=290 个目录名（tool 273 + topic 17）
[sweep-plan] no_category=1
[sweep-plan] candidates=99 judge_input 62253 B bodies 1322501 B      （scan 全程 12 s）
```

- **判官输入 62 kb，内联正文那份 1.32 MB**（99 条 × 平均 13 kb，最长的一条 90 kb）：这是 v2「必须读全文」的
  直接代价，也是它换来判断质量的地方。判落点那一轮只能**一批 3–5 条**，别整份塞进一次请求。
- **落点空间 290 个目录名，只有 33 个 `routable`**（有 remote + 有 `SKILL.md`）：能当落点的远比能 install 的多，
  这正是 v2 取消「空壳不能当落点」的原因——空壳由 writer 补 remote。
- **`.git` 是文件（不是目录）的目录不是包**：那是别的 clone 的 worktree，名字再像 `AgentSkill-*` 也不算落点
  （2026-10-11 实测：本会话自己的 `AgentSkill-UsingHermes.dream-nostay` 就出现在 `routable` 名单里，
  脚本已按这条过滤掉）。
- 落点空间的 33 个可路由包里，有几个**没有 remote**（`AgentSkill-HoldingConversations` / `UsingAstra` /
  `UsingEagle` 一类）：能收内容，但装回 profile 要 MANUAL，这类行要在汇报里显式列出。
- 99 条候选里 `.archive/` 下的退役件不计（脚本跳过 `.archive`）：那是退役落点，不是候选。
- **基线是快照，而且同一天就会变**：本节的数字在 2026-10-10 是 `skills=262 local=99 hub=152 packs=288
  routable=30 pack_skills=214`，02:00 前是 `291/34/596`，02:1x 就是上面的 `290/33/408`——别的会话在同一个
  `~/Documents/AgentSkill/` 下推提交、增删 skill 都会动这些数。**收尾时重测一遍并把数字改掉**（带一条说明的
  提交），别把上一轮的数字当验收线。

## Support files

| 文件 | 承担什么 |
|---|---|
| `references/dream-agent-roster.md` | 五种子代理任务书（逐字可抄）、并发与分波、每类必须回的收据、「子代理不许起后台进程」的原因 |
| `references/dream-jev-routing.md` | JEV 题面模板（两轴 + 三段问法）、分块、`dest` 的两种形状与 `source` 标注、451/超时时的降级路径 |
| `scripts/sweep-plan.py` | `scan`（枚举 + 冻结判官输入（含 `skill_md` 路径与内联正文）+ `answer-space.json`）、`merge`（`dest` 校验 → `plan.md` / `resolved.json` / `install-cmds.sh`）、`dedupe`（S9 去重 + 无类目归位，`not_in_pack` 是 exit 5 硬错误）；`--self-test` 跑一个抛掉即弃的三容器样例、9 个拒收分支、复用/合包两个决议分支、以及 dedupe 的 exit 5 |

## Skill Structure

<!-- Generated by Scripts -->

```
dream/
├── SKILL.md  (363 lines)
├── test-prompts.json  (32 lines)
├── test-results.md  (53 lines)
├── references/
│   ├── dream-agent-roster.md  (142 lines)
│   └── dream-jev-routing.md  (123 lines)
└── scripts/
    └── sweep-plan.py  (908 lines)
```

<!-- Generated by Scripts -->
