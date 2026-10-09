# zsqlab 台账对象地图（快照口径 —— 用前先按 SKILL.md Step 1 重取自省）

台账在 vault 之外的 Dolt 数据目录 `/Users/org_zsqlab/Dolt`，服务 `127.0.0.1:13308`。库名 = 课题号
（`zsqlab05` / `zsqlab08` / `zsqlab10` / `plasmid-backbone` …）。**数字与列都会随改库变**，本文件是地图不是常量。

## 连接

```bash
dolt --host 127.0.0.1 --port 13308 --no-tls sql -q "<SQL>" -r csv       # 脚本解析用
dolt --host 127.0.0.1 --port 13308 --no-tls sql -q "<SQL>" -r vertical  # 看宽表 / 看视图定义
```
不加 `-u`（会去要口令并在非交互下失败）；`\G` 不可用，宽表一律 `-r vertical`。

## 三层标识（谁是谁）

| 层 | 形如 | 主键 | 落在 |
|---|---|---|---|
| 定义（质粒 / 构建体） | `pZET039-p1.3.2_s1.1_r3_b35071_u0002`；编号 `05PL06C3`；构建体码 `05PR06-3.0@3` | `entity_uuid` | `entity_plasmids` / `entity_constructs` 的 `name` / `aliases` |
| 实例（管） | `05PL06C3-01-FL1`（编号-批号-保管人） | `stock_uid` | `stock_*` + `stock_registry`（盒位在此） |
| 盒位 | `WFL-05-01` + row `A` + col `2` | `UNIQUE(box,row,col)` | `box_registry` |

判据一句话：**带批号的永远是实例，不带批号的才是定义。** 多条管共享一个 entity 是常态（多对一）。

## 视图各给什么（实测口径）

| 视图 | 给什么 |
|---|---|
| `v_entity_chain` | **单入口**：一行一个实体（质粒 + 构建体合 118 行），含 `name` / `aliases` / `design_key`(`系列-主体-改造-载体(骨架)`)/ `construct` / `stocks` / `positions` / `stock_status`（`在库` / `存储位置未知` / `无库存管`）/ `source`。查标记先用它 |
| `v_stock_all` | 实例层全量：`stock_uid` / `stock_kind` / `box,row,col` / `slot_label` / `location_status` / `entity_uuid` / `entity_name` / 类型列 / `batch` / `aliases` |
| `entity_uid_map` | 实体 UUID ↔ 实体名 ↔ 它的管（笔记 frontmatter 里常只有 UUID，从这里退回管号） |
| `stock_uid_map` | 管号 → 盒位 / 状态 / 实体（`v_stock_all` 的整齐版） |
| `v_alias_map` | `(stock_kind, stock_uid, aliases)` —— 用 `aliases LIKE '%<旧码>%'` 反查实例侧旧写法 |
| `v_marker_code` / `marker_lookup` | 取号脚手架（月份 × 日期 → 两字母标记码；原 Excel Helper 映射） |
| `v_box_layout` | 盒位网格（含空位），对齐原 Excel 的 Box Layout 公式 |
| `v_entity_nameless` / `v_uuid_orphans` / `v_uid_dupes` / `checks` | 体检：无名实体 / 悬空实体 / 重复 uid / 规则逐条 PASS-FAIL |

事实表：`entity_registry`（全部实体）/ `entity_plasmids` / `entity_constructs` / `stock_registry`（盒位登记）/
`stock_plasmids` / `stock_proteins` / `stock_bacteria` / `box_registry` / `marker_lookup`。

## 身份通道与填充率（这是「链快不快」的瓶颈所在）

| 通道 | 列 | 实测填充 | 影响 |
|---|---|---|---|
| 编号 / 别名 | `entity_plasmids.aliases` | 63/63 | 编号、构建体码、旧命名、`.dna` 内部 UUID、内部测序名都在这 |
| 名称 | `entity_plasmids.name` | 51/63 | 剩下 12 条无名（早世代 / 对照），只比 name 会漏 |
| 图谱文件名 | `entity_plasmids.file_name` | 51/63 | 同上；另有定义只剩 aliases 里的旧写法 |
| 构建体侧别名 | `entity_constructs.aliases` | **1/55** | 构建体码查不回**构建体**实体（只能从质粒侧 aliases 命中）—— 关键卡点 |

`entity_constructs` 的 `name` 存在**两种范式混装**：设计码形 `05PR06-2.0@1`（`series/body/version`
齐全、`design_key` 有值）与磁盘字母组形 `05PR06B2`（三段全空、`design_key` 为空串）。按 `design_key`
反查会**静默漏**掉后者 —— 反查前先看这一列的空值率。

## 一条能打穿所有通道的模板

```sql
USE <db>;
SELECT c.entity_kind, c.name, p.file_name AS map_file, c.aliases,
       c.design_key, c.construct, c.stocks, c.stock_status
FROM v_entity_chain c
LEFT JOIN entity_plasmids p ON p.entity_uuid = c.entity_uuid
WHERE c.name LIKE '%<M>%' OR c.aliases LIKE '%<M>%'
   OR c.construct LIKE '%<M>%' OR c.stocks LIKE '%<M>%'
   OR p.file_name LIKE '%<M>%';
```

实测三例：编号 → 1 行（`aliases` 里同时留着旧写法与旧条码）；旧图谱文件名（`070H`）→ 1 行（`name` 为空，
全靠 `aliases` 命中）；构建体码 → **2 行**（质粒 + 构建体，是答案不是歧义）。
