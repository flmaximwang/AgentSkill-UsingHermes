# 编号身份对账：记录侧编号 ↔ 台账里的管（详细配方）

## 1 · `aliases` 列 + `v_alias_map` 视图

- 每张 `stock_*` 表加一列 `aliases varchar(255)`（放 `notes` 后面），多个别名用 `;` 分隔；`entity_*` 表也可有同名列（构建体码 → 构建体实体）。
- 反查视图：

  ```sql
  CREATE VIEW v_alias_map AS
  SELECT 'bacteria' AS stock_kind, stock_uid, aliases FROM stock_bacteria WHERE aliases IS NOT NULL
  UNION ALL SELECT 'plasmid', stock_uid, aliases FROM stock_plasmids WHERE aliases IS NOT NULL
  UNION ALL SELECT 'protein', stock_uid, aliases FROM stock_proteins WHERE aliases IS NOT NULL
  ORDER BY stock_kind, stock_uid;
  ```

- 生成器里把映射写成一个显式字典（`ALIASES = {<正确 uid>: [<历史写法>, …]}`），重跑可复现；未解析项另写 `ALIAS_UNRESOLVED = {<记录侧码>: <为什么不能解析>}`，配一条 `checks` INFO 规则数它的条数（解析掉了自然归零）。
- `checks` 里再配一条 INFO「带 alias 的管」，让每次重建都能看出对账状态。

## 2 · 派生列 `location_status`

```sql
IF(s.box IS NULL, '存储位置未知', CONCAT_WS('_', s.box, s.`row`, s.col)) AS location_status
```

`v_stock_all` 的每个 UNION 分支都要带上这一列（列数必须对齐）。好处：位置状态是**算出来的**，不需要人去填「未知」二字；`checks` 里「存储位置未知的管」直接 `COUNT(*) WHERE box IS NULL`。

## 3 · 证据链：alias 目标怎么定

1. 记录侧写的是设计码（`0506-2.1@2`、`05BD06-2.0@2(pZET038)-01-FL1`）⇒ 先把它翻成「质粒名」：`p<backbone>-p<ver>_s<sel>_r<round>_b<bin>_u<unit>`；`r1` = 设计 1.0、`s1.1_r2` = 2.1、`s1.2_r2` = 另一组字母、`_RL` 之类后缀是变体。
2. 再用质粒名去库里找管（`entity_name LIKE '%<质粒名片段>%'`），必要时用 `SnapGene/Constructs/*.prot` 文件名交叉（文件名里就是「构建体码 + 质粒名」的配对）。
3. 若两支管带着**同一个选择**（前缀高度相似）⇒ 用上游表的 `使用菌种` / 该批纯化编号交叉定位，不要按前缀挑。
4. 记录侧码与推导出的实体名不一致时（源表字段推不出那组「字母组」命名）⇒ **不挂 alias**，把码本身建成 entity + 同 uid 的管行（见下）。

## 4 · 「既是 entity 又是 stock」的码

记录里出现、源表没有的「字母组」码（如 `05PR06B2`）：

- 建 entity：生成器加进 `EXTRA_CONSTRUCTS`（uuid5 由名字派生，`entity_constructs` 一行，`series`/`body`/`version` 留 NULL，`file_name` 写该码本身）；
- 建管：生成器加进 `EXTRA_PROTEINS` / `EXTRA_BACTERIA`（uid 就是该码本身、`batch` 可 NULL、`notes` 写「存储位置未知」）；
- 这样「编号即 uid」，记录文本不用改，两边都查得到。

管表补登记的通用形状：

```python
EXTRA_BACTERIA = [dict(alias='05STA6A2-02-FL1', plasmid_alias='05PL06A2-01-FL1', batch='02',
                       strain='BL21(DE3)', notes='存储位置未知；来源 05STA6A2-01-FL1（使用 01 管，猜测日志 …）')]
```

两个实现坑（实测）：

- **追加清单要放对位置**：`bacteria = bacteria + EXTRA_BACTERIA` 放在 `dedupe()` 之前或之后，决定它是否参与去重口径 —— 选一种并写清。
- **构建体归并要用「质粒 → 构建体」全量映射**：构建体名可能由多个质粒共享（`constructs.setdefault` 只留第一条），按「构建体 → 某一支质粒」反查质粒名会拿错对象。要按质粒名给构建体挂 alias，就先建 `plasmid_name → construct` 映射再聚合。

## 5 · 记录侧留痕模板（全文）

```
> [!note] 台账校正留痕（<YYYY-MM-DD>）
> 原文写作 `<旧写法>`；该标注在 `<库名>` 台账里登记为 alias，指向正确的 `stock_uid` `<新 uid>`。<依据一句话>
> 旧写法保留在 Dolt（`<库名>.stock_<族>.aliases`，视图 `v_alias_map`），本记录的编号已改为 <新 uid>。
```

批号不同的情形单独写清，例如：「原文写作 `05STA6A2-02-FL1`（批次 02）。批号不同不共用 stock_uid：02 批已另立一支管（batch 02，实体同 01 管），存储位置未知；01 管保留 alias …。本记录的 material 用的就是本支管编号，不改。」并追加一行指向后补的猜测日志。

## 6 · 猜测日志模板（全文）

```
> [!warning] 猜测日志（<YYYY-MM-DD> 补记，非原始记录）
> **为什么补记**：<编号> 出现在 <下游记录> 的 material 字段；但 vault 全部记录 + 飞书 `<base 名>` 全部 25 张表（含细菌库存、培养、转化）里都没有该批的原始记录 —— grep 只命中 01 批。
> **口径**：没有原始记录时补记一条猜测日志，并标记为使用 01 管。
> **猜测内容**：02 批由 01 管 `<uid>`（<strain>；<质粒名>）划线 / 扩培而来，用于 <下游记录日期> 的纯化。
> **日期**：真实日期未知，按最早引用日（<YYYY-MM-DD>）归档。
> **台账同步**：Dolt `<库名>.stock_bacteria` 里 `<uid>` 的 `notes` 已记「来源 <源 uid>（猜测）」。
> **关联记录**：[[Logs/2025/10/07/Purification-001/Purification-001|Purification-001（2025-10-07，用该管纯化）]]
> **审查依据**：<审查报告路径>
```

- frontmatter 照该 vault 的记录模板（`UID` / `tags: [Records, Logs]` / `cssclasses` / `parents` / `highlight` / `keywords` / `archive-id` / `contributors` / `material` / `product`）；类型标在**目录名**（`StrainTransformation-001`），`material` = 源管、`product` = 目标管。
- 目录里建 `assets/` 与 `workspace/data/`（空目录放 `.gitkeep` 才进 git）。

## 7 · 多 agent 审查的分批与复测

- 分批：34 条记录 → 4 批（9/9/9/7），每批一个只读 subagent，提示里写死「抽**每一个**样品 / 产物编号」+「输出 JSON（`id, kind, mentioned_in[], in_stock, stock_row, note`）到 `scratch/audit-batch-N.json`」。
- 父 agent：合并去重 → 亲自复测全部 `in_stock:false` → 归类三类 → 落一份 md（总览 + 逐条事实 + 复测数字）。
- **子 agent 的否定结论一定要复测**：实测出过「最近似前缀」当作依据、以及把设计码/批号当缺口两类错误。
- 报告里给出**可复核的硬数字**（管总数、alias 条数、位置未知条数、`checks` 的 PASS/INFO 分布），而不是「已全部核对」。

## 8 · 查源备忘（实测）

- 飞书 `常规实验管理-<NN>.base` 转出的 JSON 是**每张表一个 item 的列表**，字段值埋在 `schema.data.recordMap.<recId>.<fldId>.value[].text` 之类的嵌套里：**不要按 `tables` / `records` 之类猜的键路径索引**（会静默返回 0 条，把「搜不到」误读成「没有」）。用 `trace-sample-provenance` 的 `scripts/feishu_base_dump.py`，或自己写递归遍历收集 `路径 → 叶子值`，再在叶子上 grep 目标编号。
- 证明「某批没有原始记录」要**两边都查**：vault 全部记录 grep + base 全部表逐叶子扫；只查一边不算。
