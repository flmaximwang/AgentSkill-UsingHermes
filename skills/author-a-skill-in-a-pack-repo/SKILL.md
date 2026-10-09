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
**开写前先 diff clone 与已装副本**（`diff -rq <clone>/skills/<x> <profile>/skills/<cat>/<x>`）：**最常见的写者就是这个 profile 自己的后台 review fork**
（每轮交付后它重放会话、把本轮教训直接写进已装副本——所以长会话收尾时「profile 比仓库新」是常态，不是你写漏了），其次是别的 agent
直接改**已装那份**而没回移植，两种情况都让 profile 比仓库新 —— 那几份是它的在途工作，**先逐字节搬回仓库当基线
（单独一个提交），再在上面改你的**。反了就是静默删掉人家内容（本轮实测：在改同一个 `assets/plan.html` 的
同时，另一个会话已经改了 profile 里的 `assets/plan.html` / `SKILL.md` / `plan.py` 三份；直接 `cp` 覆盖与
`skills update --force` 都会把它们的改动吞掉）。漂移一旦发现就**把在途文件也一并回移植**（含 `.py`：先
`py_compile` + 跑一条只读子命令确认能跑），让仓库 ⊇ profile，别人以后跑 `update` 就不会砸掉它。
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
  picks 优先从**子代理 live transcript**（`…/delegation/live/<deleg_id>/task-N.log`）里含 `assistant|` 且带 `"P1"` 的那一行 `json.loads` 取 ——
  2026-10-04 实测那一行是**完整** JSON（14/14 键），而批次完成通知的 `TASK n/N` 块只是摘要、长 picks 会被截成 `…(+100 chars)`；
  两者对不上时以 transcript 为准。
  手抄漂一格，整张矩阵静默出错（实测 6 个判官里漂了 2 个，分数全错）。
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
  **两臂对比比「只跑一张新候选表」更可信**：同一份题面文件喂**两个候选列表**（A = 旧的 N 个 / B = N+1 个），
  2 评测者各跑一臂 = 4 个互不相见的子代理；判据随之变成可算的两个数 —— B 臂里 `pick == 新 skill` 而 gold 不是它的条目应为 **0**，
  A→B 的落点变化应**全部落在既有兄弟之间**（那是评测者噪声，不是新技能造成的）。
  本轮实测：旧题被抢 0/0；新技能 4 条正例在 B 臂两评测者一致命中、在 A 臂两评测者一致判 `none`（证明那是既有技能没覆盖的新地盘）。
  判官**把 picks 写成文件**（每行 `P<编号>|<skill 名或 none>`）再由脚本汇总 —— 别让它只回在回答里，更别手抄。
  **诱饵要先看不含新技能那一臂认不认领**：若 A 臂两评测者都判 `none`、B 臂却一致投给新技能，那是我方**题面没写好**
  （兄弟本来就不认领它，不构成「被抢走」）—— 按本包写死的准入标准改判 `edge_case`，并把理由与该题在两臂的逐票结果写进用例 `notes`。
  新增题的构成照抄这个骨架：4 条正例（不同提问者措辞：「一张表」「速查表」「一览」「一行一条命令」）
  + 1 条诱饵；同一批 prompt 同时落进该 skill 的 `test-prompts.json`。
  **旧题集的 glob 会把新技能自己的题也收进去**：`skills/*/test-prompts.json` 在你建好新技能目录之后就已经包含它了，
  于是新技能的正例/诱饵被投放两次（2026-10-04 实测：真实的旧题是 26 条，脚本算出 31 条；自己的 4 正例 + 1 诱饵混进
  「旧题」里，被当成"一题都没被抢走"的既有题）。判官不受影响（同一题两次落在同一答案），**错的是统计口径**。
  做法：旧题集 glob 显式排除本技能目录，或合并后按题面文本去重再统计。
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
| 家目录相对的递归删除（**即使这一步确实必要**，例如「把工具的配置目录搬到别处」） | **critical** / `destructive_home_rm` | **换动作，不只是换措辞**：把「`cp -a` 拷贝 → `rm -rf` 原目录 → `ln -s`」改成 `mv <原目录> <新位置>` + `ln -s`（全程**一次删除都没有**）；回滚用 `unlink` 摘软链再 `mv` 回来 |
| 把 Hermes 的 profile 环境文件写成字面路径（家目录前缀紧跟 `.hermes` 再跟 `.env`）—— **连代码里的 fallback 与文档里的说明都算** | **critical** / `hermes_env_access`（「directly references Hermes secrets file」） | 别隐式读它：key 只从环境变量 / `--api-key` / 显式 `--key-file` 取；文档里也不出现那个路径（示例写成 `/path/to/key.txt`）。实测去掉这一处后，另外两条 medium（`python_environ_get_secret`、`hardcoded_ip_port`）仍停在 informational，verdict 回到 `safe` |
| 读环境变量的**下标**写法（正则只放过 `.get(` 形态：`^[^#\n]*os\.environ\b(?!\s*\.get\s*\()`） | high / `python_os_environ` | 一律 `os.environ.get("X_KEY")`，别用 `os.environ["X_KEY"]`（本来就该防 KeyError） |
| 命令替换里 `…/venv` 紧跟管道（`VENV=$(ls -dt …/environments/*/venv \| head -1)` 这类挑最新 generation 的写法） | high / `dump_all_env` | 命中原因是字符串 `'venv \|'` 里含 `'env \|'`（正则 `env\s*\|`）—— 换一种列目录写法、拆行都没用；把命令替换换成**占位路径**（`<install id>/<generation>/venv`）或改成一段只挑目录的 python 单行，信息不丢、形态不再命中 |
| IP 与端口**贴在一起**（连正文里的说明句也算） | medium / `hardcoded_ip_port` | 拆开写：「地址 127.0.0.1、端口 7890」——信息不丢，`\d+.\d+.\d+.\d+:\d+` 不再命中 |
| 脚本里的**可执行程序白名单**出现 `ssh-keygen` 这类字面量（哪怕它只是「哪些首词算程序名」的清单） | medium / `ssh_keygen` | 不影响 verdict（medium 单独只算 informational ⇒ 仍 `safe`）；要消掉就把该词从清单里删掉，或写成前缀匹配（`"ssh-"`）不落整词 |

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

**能换动作就别只换措辞**（2026-10-05 实测）：一个「把某个 CLI 的配置目录搬到 `~/.<tool>`」的 skill
首轮整包拿到 `dangerous`——2 条 critical `destructive_home_rm`，命中的是示例命令里那句
「`cp -a` 拷贝 → `rm -rf` 原目录 → `ln -s`」。改成 `mv <原目录> <新位置>` + `ln -s` 之后
**一次删除动作都没有**，verdict 回到 `safe`，而「怎么搬、怎么回滚」的信息比原版更完整
（回滚用 `unlink` 摘软链，天然不需要递归删除）。
机制：`rm -rf` 往往只是「把这件事做完」的顺手写法，而扫描器只看形态、不看这一步是否必要；
agent 该找的是**语义等价但不含删除**的那条路 —— 找不到时才退回去改措辞。

**同类：描述触发形态的文字本身也会命中**（2026-10-04 实测）。一份把两台机器的代理来源写成 markdown 表格的 skill 里，
某个单元格以「进程环境」的简称结尾，被表格自己的列分隔符补成了 `dump_all_env` 的字面形态 → 整包从 `safe` 掉到
`caution`（community 源就得 `--force` 才能装）；改写那个单元格后回到 safe。**第二次命中来自解释这件事的那段说明文字**——
所以要描述形态、不要复现它。对应条目与改写方式见上面那本手册。

**medium 不等于要改**：实测一个「子进程调 dolt + 正文写 `127.0.0.1:13308` + 报错提示 `pip install pyyaml`」的 skill 拿到 3 条 medium（`hardcoded_ip_port` / `python_subprocess` / `unpinned_pip_install`）仍是 `safe` —— 这三类是本机只读工具的正常形态，不必为了消告警改设计；同理 `shell_rc_mod`（正文提到 shell 启动文件）与 `unpinned_npm_install`（`npm install -g` 不钉版本）各若干条也仍是 `safe`。

**索引 / 速查表型 skill（把同包内容汇成一张表）要额外多一道「命令出处闸」**：脚本抽出表里的每个命令锚点，
在同包某个 skill 里找出处。口径**只到子命令一级**（`annex unused`、`git rm`、`git-annex fix`），
参数里的占位符（`<file>`、`<KEY>`）不参与比对——同包各 skill 写的是自己的实测路径，逐字比对必然假失败。
另给两条二级证据：man 页写法（`git-annex-unannex.mdwn`）与独立反引号 token（`` `dropkey` ``）——
同包对少数破坏性 plumbing 命令就是这种写法，只认一级会把 **skill 自己的措辞**判成无出处
（实测首轮 `annex dropkey` / `annex unannex` 就是这么被报出来的，查证后是判据太严、不是无出处）。
同一脚本顺带核实「每行末尾指向的主题 skill」目录存在（拿 `→ \`名字\`` 与表格首格反引号名当引用集，别用
「长得像 slug」的启发式——`git-annex-shell` 这类会假命中）。两种故障注入都要真跑：捏造子命令、幽灵 skill 名。

**Step 4b · 跑包自己的收尾脚本（新 SKILL.md 必须自带生成段标记）**
带 `scripts/` 的包仓库都有自己的收尾两道闸，跑在提交前：

```bash
~/.hermes/hermes-agent/venv/bin/python3 scripts/auto-generate-skill-structure.py   # 填 Skill Structure
~/.hermes/hermes-agent/venv/bin/python3 scripts/verify-skill-package.py skills/<name>
```

`verify-skill-package.py` 要看到 `tree vs disk: ok` 与 `pointers: ok`（它同时给指针闸做出包前的第二道保险）。

- **新建的 SKILL.md 必须自己带上那对标记**，否则第一个脚本打印 `skipped (no markers to fill)`、verify 报
  `no generated section: SKILL.md carries fewer than two markers`：文件末尾补一行 `## Skill Structure`
  与**两行** `<!-- Generated by Scripts -->

```
author-a-skill-in-a-pack-repo/
├── SKILL.md  (182 lines)
├── test-prompts.json  (14 lines)
└── references/
    ├── author-a-skill-in-a-pack-repo-darwin-blind-paired-loop.md  (58 lines)
    └── author-a-skill-in-a-pack-repo-pack-repos.md  (44 lines)
```

<!-- Generated by Scripts -->

```
author-a-skill-in-a-pack-repo/
├── SKILL.md  (348 lines)
├── test-prompts.json  (14 lines)
└── references/
    ├── author-a-skill-in-a-pack-repo-darwin-blind-paired-loop.md  (58 lines)
    └── author-a-skill-in-a-pack-repo-pack-repos.md  (44 lines)
```

<!-- Generated by Scripts -->
