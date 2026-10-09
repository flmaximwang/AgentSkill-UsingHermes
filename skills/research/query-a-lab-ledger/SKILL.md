---
name: query-a-lab-ledger
description: "Use when 编号/图谱名/管号要落到台账实体那一行（只读 Dolt 台账查询）。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [lab-records, ledger, dolt, identity-resolution, aliases, read-only, reporting]
    related_skills: [sequence-file-formats, co-write-a-shared-repo]
---

# query-a-lab-ledger —— 标记 → 台账那一行（只读）

用户的台账（库存编号 / 实体 / 管 / 盒位）在 vault 之外的 Dolt 库里，不是 Excel。用户要的回答永远是
**整条链**：这个标记定义的是哪个对象、它承载哪个构建体、有哪些管、在哪、状态是什么。

## When to Use

- 给一个标记（库存编号 `05PL06C3`、图谱文件名 `05PL070H-pZET038-0212`、构建体码 `05PR06-2.0@2`、
  设计码 `0506-2.2@2`、管号 `05PL06C3-01-FL1`、内部测序名 / `.dna` 内部 UUID）问「这是哪个质粒 / 哪个构建体」。
- 用户问「图谱能不能唯一映射到台账实体」「后续检索时链条能不能快速拿到」——后半句问的是**这条链有没有单入口**。
- 需要先确认台账里到底有哪些对象、某个视图/规则是怎么写的。

**不属于**：改台账（建实体 / 建管 / 盒位 / 合并定义、批量改写法）→ 台账管理类技能；文件目录 ↔ 实体的
核对审计 → 映射审计类技能；管号 → 盒位 → 产生链 → 日志 UID 的溯源 → 产生链类技能。本条**只读**，且只到**定义层**。
问**这套服务本身**（一共几个库 / 数据目录在哪 / 某个库怎么 push 到 remote / 怎么备份 / 恢复要带什么）
→ 读 `references/zsqlab-ledger-service.md`：那里讲拓扑与「把库搬出去」的实测做法，不改变本条的查询口径。

## Step 1 · 连上并自省（先看有什么，别先写查询）

```bash
dolt --host 127.0.0.1 --port 13308 --no-tls sql -q \
  "SELECT TABLE_NAME, TABLE_TYPE FROM information_schema.tables WHERE table_schema='<db>' ORDER BY TABLE_TYPE, TABLE_NAME;" -r csv
```

- **不要加 `-u root`**：服务器未配该用户口令时会停在 `Enter password:`，非交互下报
  `Failed to parse credentials: operation not supported by device` —— 读起来像权限/连接故障，其实是多传了一个 flag。
  不带 `-u` 直接进（本机实测 `dolt --host … --port … --no-tls sql` 即可）。
- **`\G` 不是 `-q` 的合法语法**（解析器在 `\` 处报 `syntax error`）。宽表用 **`-r vertical`** 看，脚本里解析用 `-r csv`。
- 输出分两类：`BASE TABLE`（事实）与 `VIEW`（**已经设计好的检索路径**）。先看视图清单再决定要不要自己 JOIN。

## Step 2 · 先读视图定义，别重造

```bash
dolt --host 127.0.0.1 --port 13308 --no-tls sql -q "USE <db>; SHOW CREATE VIEW <view>;" -r vertical
```

台账里的视图往往已经把「定义 → 承载的构建体 → 全部管 → 盒位 → 库存状态」串好了（实测一个
`v_entity_chain` 就把这些一次给全）。**读它的定义再决定用不用它** —— 自己重新拼三张表既慢，又容易和视图口径分叉
（同一个库里可以并存两代视图，名字像全表 ≠ 口径一致）。

## Step 3 · 把标记归到身份通道，并联搜

身份不是一个字段，是**多通道**：名称 / 别名 / 文件名 / 编号 / 构建体码 / 设计码 / UUID。查询必须并联这几列，
**不能只比 `name`**：

```sql
USE <db>;
SELECT c.entity_kind, c.name, p.file_name AS map_file, c.aliases,
       c.design_key, c.construct, c.stocks, c.stock_status
FROM v_entity_chain c
LEFT JOIN entity_plasmids p ON p.entity_uuid = c.entity_uuid
WHERE c.name      LIKE '%<M>%'
   OR c.aliases   LIKE '%<M>%'
   OR c.construct LIKE '%<M>%'
   OR c.stocks    LIKE '%<M>%'
   OR p.file_name LIKE '%<M>%';
```

- **先量各列的填充率，再决定信哪个键**：实测 `entity_plasmids` 的 `name` 与 `file_name` 各 51/63、`aliases` 63/63
  —— 只按 name 比会**静默漏掉**那 12 条无名定义与早世代记录。填充率用 `SUM(col IS NOT NULL AND col<>'')` 逐列跑一遍。
- 别名串按 `;` 拆开逐段试，**不要按 `-` 切**（编号本身带 `-`）；同一个编号要同时试「带后缀旧写法」与
  「去批号/保管人的首段」两种粒度（`05PL070H-pZET038-0212` ↔ `05PL0611` ↔ `05PL0611-01-FL1`）。
- 设计码（`0506-2.2@2`）先归一成构建体码（`05PR06-2.2@2`）再查；`pET040` / `pZET040` 这类骨架笔误要在比对侧容忍。

## Step 4 · 判「几行是答案、几行是歧义」

- **两行常常就是正确答案**：定义层（不带批号）与实例层（带批号）各一行 —— 一个构建体码同时命中「质粒定义」
  与「构建体定义」是设计成这样的（构建体码写在质粒的 `aliases` 里）。**不要把它报成歧义**。
- 真正的歧义是**同一层级里两条候选**（同一编号两行定义）。这时报「多解 + 候选清单」，
  **绝不挑一个当答案**；并点名该状态在台账 `checks` 里是哪条规则负责发现。

## Step 5 · 报「链」，不报「一个值」

一次给出该行的 **name / aliases / design_key / 承载的构建体 / 全部管号 / 盒位 / 库存状态**。
用户问的是「链条能不能快速拿到」——只回一个名字等于没回。

派生出来的三个汇报规矩（都是被用户纠正过的）：

- **别堆标记串**：提案或结论里出现一长串编号时，用户会直接说「我对不上你的描述链条」。改用**角色名**叙述
  （「定义那一行」/「管那一行」），并**原样贴出**涉及的行（`name` / `aliases` / `source` 各一行），
  最后问一个**一个词能回答**的问题。
- **数字给现场值并注明是快照**：台账是活的，别的会话随时加管；同一库同一天复测就会变。引用时写「当场测到 N 行」，
  不要把 N 写成验收线。
- **卡点要指名到通道**：说清「哪个身份通道是空的、因此哪类标记现在查得慢」，并给一条可直接粘的查询模板 ——
  这比「已经改好了」有用得多。

## Step 6 · 交付

- 结论 + 卡点 + 查询模板，先结论后细节。要留成可复用资产时，落到共享 pack 仓库的 `docs/` 并 commit；
  **只按 pathspec 暂存自己的文件**，别把别的会话的未跟踪文件一起带走（多写者共用一个 clone 时尤其如此）。
- 只读到底：查出来的东西要写进 vault 或登记进台账之前**先问用户**。

## Pitfalls

- **能查 `information_schema.tables` / `columns` 与 `SHOW CREATE VIEW` 就不要靠 grep 文件猜 schema** —— 猜出来的列名与视图口径不可信。
- **「别名命中」不等于「编号命中」**：命中的是哪一列就写哪一列 —— 这一条决定了这个标记是**定义级**还是**实例级**，
  两者含义不同，混写会把实例当定义。
- **别为了让映射成立而放宽判据**（去掉前缀、模糊数字、按长度对齐）：无解就报无解。身份变更的唯一硬证据是
  **全序列/全字段逐字节相同**，长度相同、编号相同、手写标注都不算。
- 观察到的库结构会随改库而变：先跑 Step 1 重取，不要把上一次的清单当常量。

## References

| 文件 | 承担什么 |
|---|---|
| `references/zsqlab-ledger-objects.md` | 本机 zsqlab 台账的对象地图（表 / 视图各给什么、身份通道与填充率、已知卡点），**快照口径**，用前先重取自省 |
| `references/zsqlab-ledger-service.md` | 台账这套 Dolt 服务的拓扑（多库容器、数据目录、服务器进程）与 push/remote/backup 的实测做法：per-库 remote、服务器在跑也能 CLI push、Git 仓库当 remote 的前置与 refs、推到 NAS 的 `ssh://` remote（目标目录先存在、远端 dolt 用 `DOLT_SSH_EXEC_PATH` 指、别放进同步 share）、备份要一并带走的配置 |
