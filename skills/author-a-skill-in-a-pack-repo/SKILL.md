---
name: author-a-skill-in-a-pack-repo
description: "在 AgentSkill-* 包仓库里新建/改写 skill 时用（证据先行→扫描闸→装完回读）。"
---

# 在用户的包仓库里写一个 skill（`flmaximwang/AgentSkill-*`）

## When to Use（触发与边界）

- 触发：用户说「构建一个 <仓库> 中的 skill：<名字>」「在 AgentSkill-<X> 里加一个 skill」「把这条 skill 的某节补齐/改写」，或直接给出**判据清单式**需求（「审查 X 是否满足 1…5」）。
  —— 判据清单本身就是任务书：**先把每条判据落成「记录侧看哪个键 / 下游侧查哪张表」，再动手写**。
- 前提判据：这个 skill 的 **source of truth 是用户的某个包仓库**，改内容要动 clone、再由 hub 分发回 profile。
- 不属于：把 profile 里**已存在**的 skill 迁进仓库（→ `install-hermes-skill-from-a-profile`）；装/更新/卸载的机制与适配器细节（→ `install-hermes-skills` / `update-hermes-skills` / `remove-hermes-skills`）；同一 clone 有并发写者时的提交与推送细则（→ `co-write-a-shared-repo`，本 skill 只给该场景下的**决议**）；通用 skill 内容打磨与 eval 迭代（→ `skill-creator`）。

## 流程

**Step 1 · 认门**（输入：仓库名；输出：clone 路径 + 分支 + 并发状况）
`git -C <clone> fetch --quiet && git status --short && git log --oneline -3 origin/main`，并读该仓库 README 的「索引 / 安装 loop / 现有 `## skills/<x>` 正文节」——你要沿用它的形状。
**这套仓库经常有别的会话在同一个 clone 里写**：`?? skills/<别的名字>/`、被改过的 README、`docs/` 里别人的产物都当在途工作，一个字都不要动。

**Step 2 · 证据先行**（输入：判据清单；输出：可实现的字段/命令/阈值）
先把这门活的**真实产物**读一遍，判据里的每个名词都落到实况：条目文件的真实 frontmatter 键名、模板与视图（`Templates/**`、`*.base`）、下游库的表名/列名（`SHOW TABLES` / `DESCRIBE` 实测）、再跑一次存量数据量出基线。
**判据的词表必须能分开「源头没写」与「下游查不到/没建」**（本用户明确要求）：前者是记录侧缺口，后者是下游缺库或缺行——用两个不同的结论词，报告里不许互相代替。
**第三类「空」也要有自己的词：本机压根没有那份数据**（目录只剩 0 字节 `.txt` 占位、全本在 NAS 归档）——「本机索引不到」不能被读成「没有这件事」。
同理，凡要求「每一步都给出某个标识符」的判据，先在实况里确认那个标识符处处存在；某一步本来就缺它时，如实写「该处没有这个字段」，**不要拿形近的东西代替**（拿目录名冒充日志 UID 就是这一类的错）。
完成标准：能说出每个字段名/命令出自哪个文件或哪次实测输出；说不出来的回去再读，不要凭想象设计 schema。

**Step 3 · 写产物**（输入：判据；输出：一个可装的 skill 目录）
沿用该仓库的既定形状：`skills/<name>/SKILL.md`（正文中文，字段/列名/程序名保留英文）+ `references/<topic>.md`（按主题、≤2–3 个，不建日期文件）+ `scripts/<name>.py`（**真能跑**：argparse + 默认值与单位 + 有意义的退出码；SKILL.md 里给一条可直接复制的命令行）+ `test-prompts.json`（真实 prompt + expected，含与相邻 skill 的分界）。
- SKILL.md 节次沿用兄弟 skill：When to Use / Workflow 的 Step N / 检查点 / 黑名单 / 实测基线 / Support files。
- **实测基线写进 SKILL.md 当校准点**（例：「对 15 份记录跑一遍：✅37 ⚠️18 ❌19 ➖1」），并标明它属于哪个实例、不是通用常量。
  **基线是快照，不是验收线**：活数据（台账库、vault）会被别的会话随时增删 —— 实测同一份 SKILL.md 里写的行数当天下午就变（119→121）。
  写「当时测到 N 行」+ 测量时刻；长流程**收尾时重测一遍**，变了就改口径（那是一次带 `fact_fix` 说明的提交，不是顺手抹掉）。
- 描述的前 57 字符必须自足：触发词放最前，排除条款（「不属于本 skill 的…」）排在信号列表**之前**。
  **改头部不能靠推演——必须盲测复核**：57 字符窗口是硬的，塞进新钩子就会挤掉旧钩子，
  被挤掉的触发词对应的 prompt 会**静默转投最像的兄弟 skill**（本轮实测：新增「多峰逐峰」后，
  「逐帧归一化」被挤出窗口，两条原本命中的 prompt 两票都落到判据 sibling 上）。
  做法：把本类目现有 skill 的 description 都截到前 57 字符做成候选表 → **两个独立评测者**（`delegate_task`，
  交错题面、不带正负标签）各判一遍同一套 prompt → 对着金标落分矩阵。
  **题序与 picks 一律解析，不许手抄**：判官回的 `P1…Pn` 是**它自己**乱序下的编号，脱离那次调用发给它的题序就没有意义，
  而题序只存在于**你那条 `delegate_task` 调用的参数**里 —— `messages.tool_calls` 里
  `json.loads(call['function']['arguments'])['tasks'][i]['context']`，按行抓 `P<k> <题面>`，再用金标的题面文本映回 prompt id；
  picks 从**批次完成通知**的 `TASK n/N` 块里 `json.loads` 取。子代理 live log 会把 kickoff 截断成 `…(+N chars)`、
  子会话行只存 goal —— **没有第二份来源**；手抄漂一格，整张矩阵静默出错（实测 6 个判官里漂了 2 个，分数全错）。
  **把「现版头部」也当一个 arm（基线臂）**：既有的家族抢词只有在基线臂里才分得出来，别把它们记到新头的账上；
  基线臂同样漏的题属于别的 skill 的头部问题，另开一轮，不并进这一轮。
  **打分按组给，取舍按可复现定**：题面分「原有触发词 / 新能力 / 兄弟干扰项」三组分别统计 —— 总分接近时只有
  **新能力组**是有意义的比较（实测三臂总分 25/35/34，而新能力组 0/8、7/8、5/8）；语义双关题（答案本就一半一半，
  例如问句里点了「更新 / force」这类属于 sibling 的词）单列成「接受的代价」，不为它特化头部。
- **新增一个 skill（不是改头部）时的路由重测**：把旧题集**逐字冻结重放**（题面与编号一字不改、金标同一份），
  只把候选列表加长，再补新技能自己的正例**和一个兄弟诱饵**——诱饵题面里要**故意出现新技能的关键词**
  （实测：「我照速查表敲了 git annex drop，它报 unsafe…」，正确答案却是 drop 那个 skill），
  它测的正是新头会不会因为一个词就抢题。判据是**既有技能一题都没被抢走**（旧题只该留下同一批老残差），
  而不是只看新技能命中；两判官一致＝定版，别开第二轮。
  新增题的构成照抄这个骨架：4 条正例（不同提问者措辞：「一张表」「速查表」「一览」「一行一条命令」）
  + 1 条诱饵；同一批 prompt 同时落进该 skill 的 `test-prompts.json`。
- 本机专属值（路径、端口、主机）进 references，脚本用**可覆盖的默认值**（`--vault/--host/--port`），正文只写默认值 + 可覆盖。

**Step 4 · 跑通再推**（输入：skill 目录；输出：真实输出 + 扫描 verdict）
先实跑自己的脚本：单份 / 批量 / 故意造失败（改坏一份**副本**验证退出码），把真实输出（不是想象的样例）贴进报告与 references。
**关键数字要用独立方法复核，不能只信自己脚本的自述**：换一条解析/统计路径再数一遍（例：用 `search_files` 数出的「含目标语法的行」集合 vs 解析器取到的行集合，差集应**全部落在已知应忽略的区域**，如代码块内）；抽样用 `search_files`（`target='files'`）到盘上核实「报缺失的东西真不存在」；同一产物跑两次 `diff` 确认确定性（集合/字典迭代顺序会让输出抖动 ⇒ 关键集合显式排序）。两边不一致时先查自己的解析器。再预测扫描 verdict：

```bash
~/.hermes/hermes-agent/venv/bin/python3 - <<'PY'
import sys; sys.path.insert(0, '<hermes-agent 绝对路径>')
from pathlib import Path; from tools import skills_guard as sg
r = sg.scan_skill(Path('<skill 目录>'), source='skills-sh/<owner>/<repo>')
print(r.verdict, r.summary)
for f in r.findings: print(f.severity, f.pattern_id, f.file, f.line)
PY
```

`safe` 才推（medium findings 不影响）；`caution` 多半是正文里出现了 **home 相对的字面路径**（ssh 配置/密钥文件名）或**提权词**——改成描述式表述即可，被替换的原文留在 source 抓取物里。

**实测命中的五类形态与逐条改写方式**（2026-10-02，一个网络类 skill 首轮拿到 `dangerous`：1 critical + 5 high；改写后只剩 2 条 medium `python_subprocess`，设计一字未改）：

| 命中形态 | 级别 / pattern_id | 改写成 |
|---|---|---|
| SSH 公钥清单那个**文件名**（字面量写出来就命中） | **critical** / `ssh_backdoor` | 用官方机制代替：`ssh-copy-id -i "<公钥路径>" <user>@<host>`（顺带避开「SFTP 子系统关闭 ⇒ scp 失败」那个坑） |
| 家目录前缀**紧跟** ssh 配置目录（`~/` 与 `.ssh` 连写、`$HOME/` 与 `.ssh` 连写） | high / `ssh_dir_access` | 去掉家目录前缀，只写 `.ssh/config` |
| 裸词形式的提权命令（**含逐字引用厂商输出里那道前缀**） | high / `sudo_usage` | 写「提权 / 以 root 执行」；引用时只保留命令本身，前缀改成说明句 |
| 通配监听地址带端口 | high / `bind_all_interfaces` | 「22 与 5001 都在通配地址上监听」 |
| 字面 IP 带端口 | medium / `hardcoded_ip_port` | `NAS=<地址>` + `"https://$NAS:5001/"`：变量形式保留可复制性，不再命中 |

保留路径、警告与命令，只去掉「长得像那个动作」的形态——把整条警告删掉是更贵的错。

**先看判级这一层，再决定改不改**：判级与严重度一一对应 —— `critical → dangerous`、`high → caution`、`medium/low 单独只算 informational（safe）`。
所以 `dangerous` 就是**硬拦**：来源是 `community` / `trusted`（包仓库的常态）时**任何 flag 都覆盖不了**，`--force` 也不行，
这个 revision 在 hub 上**永远装不上**。症状是 `hermes skills install` 回一句
「the security scan found N high-risk pattern(s) … even with --force」——**N 是全部 finding 的条数，不是 high 的条数**，别被这句话误导成"要消掉 N 条"。
唯一出路是按命中行改文字 → 重新提交推送 → 再装一次。

**扫描器不读意图**：「千万别执行 X」的警告行只要长得像 X 就照样命中。`critical` 里最容易踩的是
家目录相对的递归删除（正文写出一条 `rm -rf` + 家目录路径的句子，**哪怕整句在说「绝对不要」**）与 pipe-to-shell；
改写成**陈述式**——保留路径与警告、去掉动词/管道形态（例：「Never delete the managed runtime tree (the directory `~/.hermes/node`)」），
别把整条警告删掉。逐条改写的手册：`install-hermes-skills` → `references/install-hermes-skills-scan-gate.md`。

**medium 不等于要改**：实测一个「子进程调 dolt + 正文写 `127.0.0.1:13308` + 报错提示 `pip install pyyaml`」的 skill 拿到 3 条 medium（`hardcoded_ip_port` / `python_subprocess` / `unpinned_pip_install`）仍是 `safe` —— 这三类是本机只读工具的正常形态，不必为了消告警改设计；同理 `shell_rc_mod`（正文提到 shell 启动文件）与 `unpinned_npm_install`（`npm install -g` 不钉版本）各若干条也仍是 `safe`。

**索引 / 速查表型 skill（把同包内容汇成一张表）要额外多一道「命令出处闸」**：脚本抽出表里的每个命令锚点，
在同包某个 skill 里找出处。口径**只到子命令一级**（`annex unused`、`git rm`、`git-annex fix`），
参数里的占位符（`<file>`、`<KEY>`）不参与比对——同包各 skill 写的是自己的实测路径，逐字比对必然假失败。
另给两条二级证据：man 页写法（`git-annex-unannex.mdwn`）与独立反引号 token（`` `dropkey` ``）——
同包对少数破坏性 plumbing 命令就是这种写法，只认一级会把 **skill 自己的措辞**判成无出处
（实测首轮 `annex dropkey` / `annex unannex` 就是这么被报出来的，查证后是判据太严、不是无出处）。
同一脚本顺带核实「每行末尾指向的主题 skill」目录存在（拿 `→ \`名字\`` 与表格首格反引号名当引用集，别用
「长得像 slug」的启发式——`git-annex-shell` 这类会假命中）。两种故障注入都要真跑：捏造子命令、幽灵 skill 名。

**Step 5 · 提交（只按 pathspec）**（输出：一条只含你这个 skill 的提交）
`git add skills/<name>` → 复核 `git diff --cached --stat` → `git commit`。**不要 `-A`、不要顺手带别的东西**（细则见 `co-write-a-shared-repo`）。
改仓库里被跟踪的数据/配置类文件（`test-prompts.json` 这类）时**沿用原有缩进与键序**：
用 `json.dump(..., indent=2)` 重写一个原本 2 空格缩进的文件，得到的提交是整文件重排、真改动只有一行，
评审时看不出来（本会话踩过一次，只能再补一个"回到原缩进"的提交）。

**Step 6 · 推送**（输出：远端 tip == 你的提交）
`git fetch && git push origin HEAD:main`，推完 `git log --oneline -1 origin/main` 确认是自己的 sha。不想捎上别人的在途提交就用 `git push origin <你的 sha>:main`（远端已前进会被安全拒绝，不会静默带上人家的提交）。

**Step 7 · 安装 + 回读**（输出：三件证据）
```bash
hermes --profile <目标 profile> skills install "<owner>/<repo>/skills/<name>" --category <类目> -y
diff -rq <clone>/skills/<name> <profile>/skills/<类目>/<name>    # 应为空
hermes --profile <目标 profile> skills check                      # 应报 up_to_date
python3 <profile>/skills/<类目>/<name>/scripts/<name>.py <一个真实输入>   # 从装好的那份再跑一次
```
- **`--profile` 是全局前置 flag**：`hermes --profile X skills install …`。`hermes skills install --help` 里**没有** `--profile`，别去找子命令参数。
- **同一个 skill 的第二轮改动走 `update` 而不是重装**：`hermes --profile <目标 profile> skills update <name>`，然后照样 `diff -rq` + `check` 回读；只以「装过了」结案，会留下一个旧副本。
- **跑过脚本的安装副本会被判成「本地已改」**：在副本目录里以模块方式导入/跑过脚本会留下 `__pycache__/`，hub 就报「kept your local edits」并跳过更新。修法：先删副本里的 `__pycache__` 再 `update`（实测即通过）——磁盘上的内容其实没被改动。
- **`update` 是单向的**（已推送的修订 → profile），推不出去。回读时 `diff -rq` 若显示安装副本里有 clone 没有的内容（别的会话直接改过安装目录），那是**先判后并**的漂移：逐字节回移植进 clone → pathspec 提交推送 → 再 `update --force`（此时仍会报「kept your local edits」——跳过判据是**记录的哈希**，与两棵树现在是否已相同无关）；顺序反了就是静默删掉别人那份内容。归属与五步走见 evolve 流程。
- **`hermes skills list` 的 Name 列会截断**（显示成 `maintain-hermes-mem…`）：拿完整技能名 grep 它**零命中**，看起来像「根本没装上」。回读以 `diff -rq` 与 `.hub/lock.json` 为准（有 `install_path` + `source_revision` 才算真装上）；要 grep 列表就 grep **名字前缀**，或直接读 lock。
- **`hermes skills check` 一次只吃一个名字**：`hermes skills check a b c` 直接报 `unrecognized arguments`，
  要核查多个就逐个跑（或只跑刚交付的那个）。
- **lock 里各条的 `source_revision` 混合是正常态**（每次只重装动过的那个）：实测同一类目 11 条里躺着 5 个不同提交，
  而 `check` 按内容判、全部 `up_to_date` —— 别把「revision 不一致」当成漂移去回移植。
- **`hermes skills check` 不带名字会把 90+ 个技能逐个对远端核**（实测 300 s 跑不完）——回读只查刚装的那个：`hermes skills check <name>`（输出 `up_to_date` 即可），别为了「跑一遍 check」把一次交付卡死。
- **别信 `Updated N skill(s).` 这句收尾行**：扫描被拒时它照打不误。真相是三件回读再加一件：`diff -rq` 空、`check` = `up_to_date`、**`.hub/lock.json` 里的 `source_revision` == 仓库 HEAD**。
- `--category` **只在安装时读**：换类目 = 卸载 + 带 `--category` 重装。
- 目标 profile 与类目查 `references/author-a-skill-in-a-pack-repo-pack-repos.md`（快照，以 `git remote -v` 与 `.hub/lock.json` 为准）。

**Step 8 · README 与汇报**（输出：索引 + 4 段式）
索引四处：Features 一行、索引表一行、安装 loop 里加名字、外加一段 `## skills/<name>`（触发、判据、可复制命令、实测基线）。
**若 README 里还有别人未提交的段落**：不要提交它（会把对方半成品连同「指向尚未进 git 的目录」的链接一起发布）——你的几处留在工作区，报告里列为待办。
汇报 4 段式：要什么 / 做了什么（commit 号、pin 的 sha、扫描 verdict）/ **每项结论对应的证据**（实测数字、真实报错原文、命令输出）/ **要你拍板的决策点**。
- 第 4 段写成**决策点**，不是问句清单：≤3 条，每条三句——要你定什么 / 为什么只能你定（那是我拿不到的事实）/ 我的建议 + 代价。
  用户会直接反问「那你要我做什么决策呢？」：**收尾反复抛「要不要我做 <某件只读的事>」不是决策，是噪音**。
- **只把「动用户数据 / 定口径」的事留给他**：只读的核查、清单、对照表自己做掉再报（把「我先出个清单？」换成清单本身），
  决策点只留「改谁的记录 / 动哪个源 / 收哪个值」。
- 值分两类就分两类报：「**有原文逐字依据的（我已直接写/准备写）**」与「**推断出来的（等你一句话）**」——
  混在一起报，他会以为整批都要他判，决策点就被淹掉了。

## 检查点

| 触发 | 动作 |
|---|---|
| 要写 / 改 / 删**用户数据侧**的东西（vault 笔记、协议、台账表、模板） | STOP：那是被审对象、不是交付物；先问用户（各自的检查点在对应 skill 里）。**获授权之后仍受「补录四条」约束**（见坑）——授权的是「可以动」，不是「可以推断」 |
| 想把别人的未提交文件「顺手」一起提交 | STOP：只按 pathspec；README 类索引文件按 Step 8 决议 |
| 想让某项判据「过」而去补下游数据 | STOP：判据是量尺不是改造目标，补数据要用户点头 |
| 批量跑真实数据超过十几份 | 分块跑，别一次灌一大份输出 |

## 坑（规则 + 机制）

- **判据里的名词必须来自实况**：字段名错一个（`samples` / `product`、`protocol` / `protocols`）就会在真数据上给出相反结论。机制：同一课题常有**两代记录**并存，承载同一语义的键名不同——先认代际，再判字段。
- **不要只读一半就下结论**：产物常只出现在正文（「保存为 `<编号>`」）而不在 frontmatter——正文出现算**证据**、不算**标注**，结论仍是未过，但要在证据里列出候选编号。
- **frontmatter 缺键 ≠ 事实缺失：记录之间的链接常写在正文的 URI 参数里。** 引用以
  `obsidian://adv-uri?vault=…&uid=<uuid>` 或 `[显示名](obsidian://…)` 的形式出现在正文（实测：纯化记录的上游培养记录
  就写在这句话里，frontmatter 一个键都没有）。所以「追链 / 补字段」的第一步是
  `grep -oE 'uid=[0-9a-fA-F-]{36}' <记录>` 扫一遍正文，把每个 uid 回索引解析成「哪条记录、什么类型」，
  再回下游核实命中——这一步把「只能靠日期猜上游」变成「有原文可引」。同一件事的反面：**不要把「frontmatter 没有这个键」
  答成「这件事不存在」**。
- **获授权补录用户数据时，仍然只写「原文逐字出现」的值。四条：** ① 值必须来自这条记录自己的正文（「保存为 `<X>`」、
  链接参数里的 `uid=…`）；**推断出来的值**（排除法定的上游记录、按日期对上的批次）逐条问、不写；
  ② 一次改动一条提交，信息里写明「后期补录 + 依据原句」——他要的可追溯性就是 git 历史，不是事后解释；
  ③ 新值沿用**该记录既有写法**（同一文件里下划线/连字符别混），不要顺手改成下游库的规范写法；
  ④ 写前 `git status` 干净、写后 `git diff --stat` 只该有你新增的那几行。
  机制：补录把「当时的记录」与「现在的理解」混进同一份证据里，唯一能把两者分开的就是提交信息 + 值必须是原文。
- **编号要归一化后再查下游**：连字符 / 下划线在人工录入里高频互换；查询按「原样 / `_`→`-` / `-`→`_`」三试，命中时报「归一化命中」，并回引下游键值（盒位/实体名）当证据。
- **两个来源同时给出时要比对是否自洽**（例：`[[名字]]` 指 A、UID 指 B）：不自洽判「不完整」并写明该改成哪个，不要挑一个当答案。
- **扫描 verdict 要在 push 前拿到**：推完才发现 caution 就得再补一个提交，pin 出来的 sha 也随之改变。
- **仓库 clone 里也会被跑出 `__pycache__/`**（以模块方式 `import` 过脚本就会有）：`git add skills/<name>` 会把该目录下**所有**未跟踪文件一并带走，所以 add 之后看一眼 `git diff --cached --stat` / `git status --short`，别让编译缓存进包（包里只该有 SKILL.md / references / scripts / test-prompts.json）。
- **示例输出与基线数字必须实跑**：一个凭印象写的样例被抓住，整份 skill 就失信了。
- **不要给「备选方案」清单**：某条正路被堵时找官方机制（官方字段 / flag / 上游改动）把它打通，并明说绕路代价。
- **57 字符窗口里要写「提问者会说的那个词」，不是「你给这个话题起的名字」**：
  三轮盲测里两处**一致错**都是这个毛病——我方的命名是「不可逆操作」「`init` 参数」，
  而提问者说的是「这么做会不会丢数据」「仓库建好后哪些设置改不了」；判别信号落在窗口之外，
  判官就顺着话题词（`.git/annex`、"数据存哪"）投给了兄弟技能。
  改法＝把提问者的口语词搬进窗口，正式命名留在窗口之后（实测：改两处头部后，
  同一批 30 题从「各错 2/30 + 一致错 1」变成**两个判官 30/30、picks 逐题完全一致**）。
- **逐字引文的包要加一道「引文回校验」**：把每个 `>` 引文切成 ≥6 词的片段回语料做子串比对
  （空白归一化、wiki 链接按显示文本展开），`…`/`[...]` 必须显式标省略。
  实测这一关抓出两处真实失真——**一处把句子首字母大写了、一处少引了原文一行却没标省略**；
  只靠人眼复读是发现不了的。它和扫描闸、盲测并列，是 doc 类包交付前的第三道闸。
- **描述头部的每轮盲测都要落盘，含"接受的代价"**：最多调 2–3 轮即停；同分时取**两评测者逐题完全一致**的那版
  （可复现优先于分数漂亮），把逐题矩阵、金标、以及"哪几条正面稳定漏给哪个 sibling、为什么是取舍不是缺陷"
  写进该 skill 的 `test-results.md`，并把轮次记到仓库 README 的盲测表。只写"改好了"看不出代价，下一轮还会重踩。
- **技能目录里新增"给人看的"产物（图/README/表）时，交付前把它打开看一眼**：
  图里某格没有可画的数据时，绘图库画出来是**空轴**（自动量程给 ±0.05），声称"这格有 Rg/I0/MW"就会失真；
  无数据的格显式写 no data。本轮这条缺陷**是看图看出来的**，读代码/看日志都不会暴露。

- **同一个包里的技能互相依赖，用「同类目兄弟目录」定位，不要拷代码**：被依赖的脚本按
  `<本技能>/../../<兄弟技能>/scripts/<x>.py` 找（hub 安装后形状不变），并给一个显式覆盖参数（`--find-stock <路径>`）
  + 找不到时**明说找过哪些路径**、把那一半结论判成「无法判定」并给出专属退出码。**两处都要实测**：
  clone 里跑一次、hub 安装到 profile 后再从安装那份跑一次（本次实测两次都自动定位到正确的 find_stock.py）。
- **切分 CLI 输出的标记前必须补一个换行**：用 `echo "###MARKER"` 切段时，前一段若是 JSON（`tailscale status --json` 这类）就没有结尾换行，标记会被**粘到最后一行上**——那一段 `json.loads` 静默失败、下一个段的 key 直接消失，输出看着"字段全空"却毫无报错。写 `printf '\n###MARKER\n'` 即可（本轮实测踩过，症状是 `TUN: ?`）。
- **包内脚本不要依赖环境里的 `python3` 有第三方包**：同一台机器上，前台登录 shell 的 `python3` 与后台/非登录 shell
  解析到的 `python3` 可能不是同一个（实测前台是自带 PyYAML 的 3.9、后台落到没装 yaml 的 homebrew python3，
  脚本直接 `ImportError` 退出）⇒ 要么自带一个只吃目标子集的兜底解析器，要么在文档与命令里写死解释器路径；
  并且**在后台/非登录 shell 里也跑一遍**再交付。兜底解析器要用「与主解析器在真实语料上逐键对比」来证明等价
  （实测 1453 份记录里 40 份有差异，全部落在视图插件键与时间类型键上，本技能读的键 0 差异）。
- **委托出去的那一次调用，连接类错误一律先退避重试再判「不可用」**：子进程 / CLI 报 `failed to connect` /
  `connection refused` / `connection reset` / `can't assign requested address` 时，按 3 s、6 s 退避重试两次，
  仍失败才落「无法判定」，并在报告里注明「已重试 N 次」。机制：这类报错多半是**本机态**（临时端口被 TIME_WAIT 占满、
  服务刚重启），不是被委托方坏了 —— 判据是**换一条路径直连同一服务**（直接 `dolt … -q "SHOW DATABASES;"`、`curl`）能通
  而子进程报连接错，就该重试。一次批量里几十次子进程调用最容易触发；把瞬断写成「下游没有这一条 / 没建库」是最贵的错。
- **`--all` 的基线每轮放宽抽取规则都要重跑并肉眼读输出**：只改正则不动口径，计数看着正常、内容已经错了。
  本轮实测的四类误报：「取 5~8 合并」的分数区间、试剂名（`20Tris.5CHAPS.0.5Arg`）、
  指向记录的链接显示名（`[2026.06.26.001](obsidian://…uid=…)`，要连显示名一起遮罩、把 uid 当上游）、
  比例（`1:1000`）；这四类都是读真实输出才发现的，不是想出来的。
- **交付前造一个合成语料把「成功路径」也跑通**：单份 / 批量 / 故意造失败（坏路径、坏参数、缺依赖）**之外**，
  还要造一份最小 vault 让主判据拿到最高结论（本次合成一个 zsqlab99 假 vault，跑出 `✅ 全链可溯` 与退出码 0），
  否则「只有失败样例」的分支等于没验。
- **动手前先 `git fetch` 看别人是否已经推了你正要依赖的东西**：本次依赖的同包技能是另一个会话在同一 clone 里
  刚提交并安装到目标 profile 的 —— 拉一下才发现依赖当场可用、不必自造兜底；推送仍用 `git push origin <你的 sha>:main`。
- **改/优化包里某个 skill 前，先查有没有别的 skill 在消费它的接口**：`grep -rn "<你的脚本名>" skills/ README.md`，
  并读那个 skill 的 coupling 文档（同包 skill 之间会有契约：按 key 名取 `hits[].stock`、按退出码分流）。
  机制：**只改文档是安全的，顺手改脚本输出格式会静默打断人家**（对方没有任何信号，直到它下次跑）。
  所以优化一个被依赖的 skill 时，把改动限制在 SKILL.md；改完**核对契约的 key 集合**（`--json` 取 `sorted(keys())` 与 coupling 文档逐个比），
  而不是只跑自己的用例。
- **新建包仓库后立刻把 remote 换成 SSH**：`gh repo create --source=. --remote=origin --push` 建出来的是
  **HTTPS** remote（`https://github.com/…`），而本机既有包仓库一律是 `git@github.com:…`（`git remote -v` 实测）。
  用户明确要求过 SSH。做法：建完 `git remote set-url origin git@github.com:<owner>/<repo>.git`，
  再用 `git fetch` + `ssh -T git@github.com` 各验一次凭据；别等到下次推送才发现。
- **回读时不要把命令接 `| tail -1`**：`hermes skills check` 的最后一行是空行/表格边框，`tail -1` 会把它
  吞成空字符串，看起来像「没输出=没装上」。用 `grep -ivE '^\s*$|^[╭╮╰╯│─]'` 滤掉边框再取结论
  （实测判据是那句 `0 update(s) available across 1 checked skill(s)`）；同理 lock 条目的 `source` 字段
  写的是适配器名（`skills.sh`）而不是仓库名，按仓库名去 grep lock 会零命中。
- **别把一个 gate 的通过当成「都查过了」——先问它扫的是什么形态**：UsingGitAnnex 的引文闸
  （`verify-quotes.py`）只数**每行以 `>` 开头的块引用**，行内 `*"…"*` 引文它看不见 —— 于是
  `cheatsheet-for-git-annex-pipelines` 在那张表里恒为 `0 fragments`、总数还报 `529/529 全过`，
  而它正文正引着官方原话（2026-10-04 实测）。两条规则：**任何你声称 verbatim 的引用都写成 `>` 块引用**
  （行内写法不在闸的覆盖里）；**闸报的 `0` 先当成「这个闸看不到」而不是「没有」**，并把闸自己的口径读出来
  ——它在数哪些行、语料是哪个快照（评论页不在 `source/` 快照里时，那段引文从构造上就进不了闸，
  只能回 wiki 源手动核对）。

## Support files

| 文件 | 承担什么 |
|---|---|
| `references/author-a-skill-in-a-pack-repo-pack-repos.md` | 各包仓库 → 默认分支 / 类目 / 目标 profile / 当下是否已安装的速查（快照；以 `git remote -v` 与 `.hub/lock.json` 为准） |
| `references/author-a-skill-in-a-pack-repo-darwin-blind-paired-loop.md` | 在本机把一个包 skill 跑一轮 darwin 优化：账本行格式、dim8 实测的设计（冻结副本）、paired 盲测的随机 A/B 与判词格式、结果卡片两个坑、收尾回读顺序 |

## Skill Structure

<!-- Generated by Scripts -->

```
author-a-skill-in-a-pack-repo/
├── SKILL.md  (263 lines)
├── test-prompts.json  (14 lines)
└── references/
    ├── author-a-skill-in-a-pack-repo-darwin-blind-paired-loop.md  (58 lines)
    └── author-a-skill-in-a-pack-repo-pack-repos.md  (41 lines)
```

<!-- Generated by Scripts -->
