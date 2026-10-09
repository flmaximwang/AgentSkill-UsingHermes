---
name: ledger-record-reconciliation
description: "Use when reconciling IDs/maps or 校验 log vs the ledger."
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [lab-records, sample-management, inventory, dolt, reconciliation, protein-engineering]
    related_skills: [manage-inventory-for-protein-engineering, manage-logs, trace-sample-provenance, dolt-sql-server-ops]
---

# 实验记录 ↔ 样本台账对账（编号 → stock_uid，并把差异写回）

## When to Use

- 用户要「审查日志 / 记录里提到的**每一个**样品、产物编号是否已经落进台账」。
- 用户说「**校验 log**」/「核对这批记录」（他的原话常常就三个字）：记录本身对不对 —— 字段齐不齐、标识符与台账对不对得上、正文是不是还停在「进行中」—— 走下面的**记录（log）对账：三线核对**。
- 用户报的编号在台账里查不到：前缀不同（`PL`/`PT`/`PP` 写成 `PR`）、批号不同、只有码没有批号。
- 要**把对账结果写回**（改记录 frontmatter、改台账 `notes`/`aliases`、补记录）时 —— 写回的两条义务（留痕、猜测日志）在本 skill。
- 要审的是一批**文件/图谱**（`SnapGene/**/*.dna`、`*.prot` 这类设计文件）能不能**一对一**映射到库里的 entity（用户问「能否唯一映射」）—— 同一种对账手艺，见下一节。

相邻（受保护，只读引用）：台账结构 / 加管 / 约束 → `manage-inventory-for-protein-engineering`；vault 记录读法与类型词表 → `manage-logs`；跨源取证 → `trace-sample-provenance`；连 server / 重建 → `dolt-sql-server-ops`。本 skill 只装这几者未覆盖的一层：**对账与写回口径**。

## 五条口径（用户已定，先于任何实现）

1. **`stock_uid` 是主键**，历史 / 别的写法进 `aliases` 列（每张 `stock_*` 表一列）+ `v_alias_map(stock_kind, stock_uid, aliases)` 视图供反查；一个 uid 一行、多个别名用 `;` 分隔。
2. **批号不同 ⇒ 不同 `stock_uid`**，即使实体完全相同：别把 02 批并进 01 管，也别把跨批的写法写成 alias。
3. **多支管共享一个 entity 是常态**（`stock_*.entity_uuid` 多对一）：实体有 uuid（按名字派生的 uuid5）、管有 uid；同一实体下 01 / 02 批各一支 uid 是正常形态。
4. 记录里出现、源表没有的码 ⇒ **建 entity（uuid5）+ 同名 uid 的管行**（生成器里用 `EXTRA_*` 清单追加）；**不推断改名、不拿前缀最像的管顶替**。有些码**既是 entity 又是 stock**。
5. **无解就标位置未知**：派生列 `location_status = IF(box IS NULL,'存储位置未知',CONCAT_WS('_',box,`row`,col))`；未解析项在生成器里记账（`ALIAS_UNRESOLVED`）+ `checks` 一条 INFO 规则数它。**不发明 uid、不挂不确定的 alias**。**「已知」与「未知」必须分开报**：盒图给了坐标就是已知、可直接补录；只有占位符（`#N/A`/`?`/`-`/`/`）或空才是未知。

详细配方（alias 列 / `v_alias_map` / 派生列 / `EXTRA_*` 形态）、证据链反例、留痕与猜测日志模板、多 agent 审查的分批与复测口径 → `references/identity-reconciliation.md`。

## Workflow

**Step 1 · 圈定记录清单**（输入：一个课题；输出：要审的记录路径列表）
用 `search_files (target='files')` 列该课题 vault 的 `Logs/<年>/<月>/<日>/<Type>-<NNN>/`（老一代 vault 是 `Records/<bucket>/(YYYY.MM.DD) <标题>/`）；活库在 `/Users/org_zsqlab/Obsidian/`，归档全本在 NAS `ORG_ZSQLab_Bucket`（同名 `.txt` 占位 ≠ 空）。

**Step 2 · 抽编号**（输入：记录正文 + frontmatter；输出：去重编号表）
frontmatter 的 `material` / `product` / `purification-id` 是一手 join 面；正文里的 `[Material:: …]`、表格、`条目标识` 也要抓。**每条编号记下它出现在哪条记录、哪个字段** —— 报缺口时这是唯一依据。

**Step 3 · 逐个核对**（输入：编号；输出：命中行或「未命中 + 理由」）
```bash
dolt --host 127.0.0.1 --port 13308 --no-tls sql -q "USE <库>; SELECT stock_uid,stock_kind,entity_name,aliases FROM v_stock_all WHERE stock_uid='<id>' OR aliases LIKE '%<id>%' OR entity_name LIKE '%<token>%';"
```
`row` 是保留字要反引号；视图里 `entity_uid_map` 的列叫 `entity_name`（**没有** `name`）。先 `SHOW DATABASES` 确认该课题有没有库 —— 0 行 ≠ 不存在。

**Step 4 · 复测所有否定结论**（输入：subagent 的 `in_stock: false`；输出：父 agent 亲自验过的「库里确实没有」）
多 agent 分工时（如 34 条记录 9/9/9/7 分 4 批、每个 agent 只读、输出 JSON 到 `scratch/audit-batch-N.json`），子 agent 的未命中是**自报**：实测出过「拿最近似前缀当命中/当依据」这类错结论。父 agent 必须自己跑一遍否定项。

**Step 5 · 归类**（输入：核对结果；输出：三类清单）
**在库 / 应为 stock 但未入库 / 非 stock 体系**。第三类包括设计码、纯化批号、数据归档号（`CRGnnn`/`TEMnnn`）、模板测试码（`WFLTE-…`）、别的课题编号 —— **不算缺口，报缺口前先剔出去**。

**Step 6 · 处置与写回**（输入：三类清单 + 用户口径；输出：台账改动 + 记录留痕）
- 前缀笔误 ⇒ 把旧写法挂成正确管的 alias，并改记录字段；
- 批号不同 ⇒ 另立 uid（实体可共用），记录**保持该批自己的编号**；
- 无原始来源记录 ⇒ 补一条**猜测日志**（见下）；
- 每条改动都在记录末尾加**留痕**；
- 台账改动：改生成器 → 重跑（重建前先确认脚本不会 `DROP DATABASE`，那会清空 `dolt_log`）→ `CALL DOLT_ADD('-A'); CALL DOLT_COMMIT('-m', …)`；
- 汇报用 4 段式（要什么 / 做了什么 / 每项改动的效果 / 待办），数字与实测输出照贴。

## 写回的两条义务

**① 校正必须留痕，不静默改写**（记录是原始证据）。记录末尾追加：

```
> [!note] 台账校正留痕（<YYYY-MM-DD>）
> 原文写作 `<旧写法>`；该标注在 `<库名>` 台账里登记为 alias，指向正确的 `stock_uid` `<新 uid>`。<依据一句话>
> 旧写法保留在 Dolt（`<库名>.stock_<族>.aliases`，视图 `v_alias_map`），本记录的编号已改为 <新 uid>。
```

**② 只在「任何源都查不到原始记录」时才补猜测日志**（仍受「用户没要求就别往 vault 写」约束）：新建一条记录（类型取该库词表，如 `StrainTransformation`），归档到**最早引用日**，正文首块用 `> [!warning] 猜测日志（<日期> 补记，非原始记录）` 写明：在哪些源里查过（vault 全库 grep + 飞书 base 全部表逐叶子扫）、口径、猜测内容、日期依据、台账侧同步了哪一列。记录里 **`material` = 源管、`product` = 目标管**；下游记录的留痕里用**完整路径 wiki 链接**指回它（同级记录大量重名，basename 会解析到别的记录）。

## 对账的另一半：文件/图谱 → entity 唯一映射

问法：「这批图谱能不能全部映射到现在的 entity？」→ 先写死**口径优先级**并逐条打印，再分类报数，最后才谈修数据。

1. **口径优先级**：① 文件名首段的编号（`^\d{2}PL[A-Z0-9]{3,4}$`）→ `aliases` 的编号段（去前导 `*`，取第一个 `-` 前）；② 第二段的名称 → **宽容解析** `(backbone, 条码, u 号)` 再比 `name`（容忍磁盘 `pEGFP001-p1.3.2_s1.2_r2_b32032_u0001` ↔ 表里 `pEGFP001-1_2_2_32032_0001`，也把 `pET040` 当 `pZET040` 笔误）；③ 设计码 `0506-x.y@z` → 构建体 `05PR06-x.y@z` → 该构建体挂的质粒。
2. **两个口径给出不同唯一解 ⇒ 报冲突，不擅自挑一个**（那正是要人定的地方）；无候选 ⇒ 报无解，**不改文件名、不猜前缀**去凑匹配。
3. **同名两行 entity 是根因、不是细节**：库里同一质粒有 `<id>-01-FL1` 与 `*<id>-02-FL1` 两条 entity 时，凡是靠编号/名称命中的文件都变多解 —— 修法是 **entity 按序列去重**（合并一行，两个编号都进 `aliases`），`stock_uid` 仍各自保留（批号不同不共用的是 uid，不是 entity）。
4. 交付形态：一个可复跑脚本（`--json-out` 明细，退出码 0=全唯一 / 1=有待处理）+ 一份报告，把每类文件逐条列名（多解 / 冲突 / 无解），并为每类写**根因**（重复 entity / 构建体↔质粒连接与文件名不一致 / 表里没有这些行）。

细节（名称宽容解析写法、四类判定定义、脚本骨架、实跑到的数字样例）→ `references/file-artifact-mapping-audit.md`。

## 记录（log）对账：三线核对 —— 结构 → 台账 → 协议模板

用户说「校验 log」时，只跑结构审查（frontmatter 的键 / 类型 / 正则）会漏掉最要紧的错位：标识符与台账不符、缺的键没人点出来、实验做完了正文还写着「进行中」。三条线走完再报。

1. **结构线**：跑受保护 skill `audit-logs` 的脚本（`scripts/audit_logs.py --config <log-audit.json>`，只读）。
2. **台账线**：记录里每个标识符都**回读台账**，不采信正文自述、也不采信记忆 ——
   - 管：`stock_plasmids` / `stock_bacteria` 的 `stock_uid, box, row, col`（或视图 `v_stock_all`）；
   - 实体 uuid：`entity_plasmids.entity_uuid`（**列名是 `entity_uuid` 不是 `uuid`**；写成 `uuid` 报 `column "uuid" could not be found in any table in scope`），与记录 frontmatter 里的 `plasmid-uuid` **逐字**比；
   - 实体名：`LEFT JOIN entity_constructs c ON p.construct_uuid = c.entity_uuid` 取 `c.name`，与记录标题逐字比；顺带核 `bacterial_resistance`（Kan 平板之类是下游先决条件）；
   - 连接：库名是 server `--data-dir` 的**目录名**（`zsqlab_10_gammaPFD-Fiber_2026.06.25`），**不是**短代号 `zsqlab10` —— 先 `SHOW DATABASES;`；命令必须带 `--no-tls`，缺了会去交互要密码，在非交互下以 `Failed to parse credentials: operation not supported by device` 失败。
3. **协议模板线**：该类记录的 frontmatter 键集应对齐**该协议的运行参数模板** `Protocols/<协议>/<协议>.md` 的 frontmatter（实测 `化学转化` 模板 = `plasmid-stock-uid` `plasmid-mass-ng` `chemical-competent` `chemical-competent-volume-ul` `bacteria-stock-uid`）。**模板里有、记录里空的键 = 缺的口述参数**：逐条列出等用户给数，不替他填，也不用旧记录的数值当默认。记录里标注「换算」的量用工具复算（`plasmid-mass-ng` = 浓度 × 上样体积）—— 目测等于没核。
4. **报告分两类，混着报就是错**：
   - **记录缺陷** —— 键在但空；正文停在「（…进行中）」而实验已完成；标识符与台账不符；`highlight`/`keywords` 空；只带 `Protocols/<协议>` tag 却没有 `protocols:` 字段。协议页的联动 base 读的是 **frontmatter 字段**不是 tag（实测 `Protocols to Logs` = `file.tags.contains("Logs")` AND (`list(protocol)` / `list(protocols)` 含 `this.file` 或 `this.note["UID"]`），`Logs to Protocols` 同理）⇒ 只带 tag 的记录在协议页看不到。
   - **配置 / 口径误报** —— 审查配置的正则或必带清单比该 vault 的约定窄（实测：`tags` 正则 `^Logs$` 会把 vault 约定内的 `Protocols/<协议名>` 判成「列表项不匹配」）。误报**不许靠改记录、也不许偷偷改配置**消掉：两类分开列，问用户改哪边。
5. **产出物还没登记就写「尚无」**：转化 / 纯化的产物管要等挑克隆、收样才存在 —— 报缺口时给「尚无」+ 计划号位（哪个盒哪排有空位、下一个 uid 是什么），**不要替还不存在的管插行**（会凭空造出假库存，台账立刻与盒子对不上）；等用户把管拿来做实了再插 `stock_registry` + `stock_<族>` + 盒图三处，并把 uid 回填到记录的 `bacterial-stock-uid` 之类字段。

## 台账内部对账：盒图 ↔ stock 表（源侧的同一门手艺）

问法：「盒图（`Box Table`）/ 记录里有的管，台账里到底有没有？位置是什么？」四次**只读**集合比对就能答完，与上面两节共用同一套键列口径：

1. **键集双向差**：`Box Table` 的**非 Trash** UID 集 ⟷ 各 `* Stocks` 表的 UID 集。两类差额分开报：**有槽位、无 stock 行**（管在盒图上、从未登记 ⇒ 要补录，位置直接从 `Box Table` 取）与**有 stock 行、无槽位**（登记了但盒图没位置 ⇒ 位置未知）。先自检：两类 stock 表的 UID 集互不相交（同一枚 UID 不该既是质粒又是菌）。
2. **槽位冲突**：同一 `(box,row,col)` 挂着两枚 UID ⇒ 源侧冲突，不能直接进 `UNIQUE(box,row,col)`，先摆给用户。
3. **`Trash` 槽位不是脏数据**：台账用 `Box = Trash` + `Row/Col = -` 记**故意废弃**（实测 4 支质粒如此）—— 别当错误清掉，也别去"修"它。
4. **占位符全集 = 位置未知**：`#N/A` / `?` / `-` / `/` / 空；这类行**不要**拿盒图坐标替它填。

- 报缺口时写清**位置是已知还是未知**：盒图给了坐标就是已知（可直接补录成带槽位的行），只有占位符才是未知；混成一句"位置未知"是错的。
- 补录走**独立的增量脚本**，不要混进建库脚本：它是审查结论、要能单独回退；同时在 vault 侧留一条审查记录。
- 补录时实体解析不出来就 `entity_uuid = NULL`、位置照实写——不造实体、不造序列。

**跨多个仓库批量做这一族活儿时**：把清单落到 **vault 之外**的一个文件（`- [ ]` / `- [x]`，**每库一节**，行尾补日期；连同"口径速查"一起写进去，免得每库重新推导），做完一项勾一项；**逐个仓库做完就汇报、确认后再动下一个**，不要一口气全量改完再报。

## 🚫 不要做什么

- **不要发明 uid / 位置 / 实体名去补空**：源表缺就记 NULL + 「存储位置未知」并记账。
- **不要拿前缀最像的管顶替**（同一选择下的两支管前缀高度相似，前缀相似度不是证据）；alias 目标只靠「设计码 ↔ 质粒名 ↔ 管 + 上游表用量/使用菌种」的证据链。
- **不要在推导名与记录里的码不一致时硬挂 alias** —— 宁可不挂、留未解析项。
- **不要把「非 stock 体系」的编号（设计码 / 批号 / 归档号 / 测试码）报成台账缺口**。
- **键列一律按表头名解析，绝不写死列字母**。列序会在副本之间、乃至同一本薄的不同 sheet 之间漂移；症状是同一张表在不同副本 / 不同读法下数出的行数对不上（实测同一份 `Box Table` 一份数出 77 行、另一份 73 行，纯是因为键列被写死成 D 列，而两边的 UID 列分别是 E 与 A）。先用表头行找列号，找不到就抛，别退回默认列。
- **冲突副本（`X.xlsx` ↔ `X (已自动还原).xlsx`）不按文件名 / mtime / 大小判**：两份各自逐 sheet 逐格 diff；若差异只是**列序整体错位**，再做**记录级比对**（按键列读成 `{UID: (box,row,col)}` 比键集与映射）—— 键集与映射完全一致时两份是同一本台账、**取哪份结果一致**，此时才按"列序与同薄其它表一致 / 更新的那份"选；键集或映射不一致就是真冲突，摆给用户。
- **不要只查一边就说「没有原始记录」**：vault 全部记录 + base 全部表都要查；base 导出 JSON 不要按猜的键路径索引（会静默返回 0 条）。归档侧（NAS）不可达时把结论标成**「未验证」**，不要写成「没有记录」。
- **不要用 UID 前缀反推课题、也不要用盒子前缀反推实体归属**：老台账里常装着**别的课题的实体/管**（实测：某库 UID 是 `01PL0201` / `01STA201-02`，盒子却是 `WFL-38-01`；另一库的 `Lookup` 里实体全属于 08），同一本薄还可能混两种 UID 写法（`01xx…` 与 `YYMMDD-N-M` 并存）。归属只能走解析链。
- **不要静默改写记录 frontmatter 而不留痕**；也不要为了「闭环」把推断出的链路写成原始记录。

## Support files

| 文件 | 承担什么 |
|---|---|
| `references/identity-reconciliation.md` | alias 列 / `v_alias_map` / `location_status` 配方、证据链反例、留痕与猜测日志模板全文、多 agent 审查分批与复测口径 |
| `references/file-artifact-mapping-audit.md` | 图谱/设计文件 → entity 的唯一映射审查：口径优先级、宽容名称解析、四类判定（唯一 / 多解 / 口径冲突 / 无解）与常见根因 |
