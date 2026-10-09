# 图谱/设计文件 → entity 唯一映射审查

适用：`SnapGene/Plasmids/*.dna`（质粒图谱）、`SnapGene/Constructs/*.prot`（构建体序列）这类设计文件，问「能不能一对一映射到库里的 entity」。

## 先定口径，再报数

「唯一映射」不是自明的 —— 同一批文件用不同键会得出不同结论。把口径写进脚本 docstring 并逐条打印，再报数。

| 优先 | 键 | 取法 | 命中面 |
|---|---|---|---|
| ① | 编号 | 文件名首段匹配 `^\d{2}PL[A-Z0-9]{3,4}$` → `aliases` 去掉前导 `*`、取第一个 `-` 前 | 库存编号就是台账主键，最强 |
| ② | 名称 | 第二段质粒名 → `name` | 命名体系两套时要宽容解析 |
| ③ | 设计码 | `0506-x.y@z` → 构建体 `05PR06-x.y@z` → 该构建体挂的质粒 | 文件按构建体码命名时的唯一出路 |

**宽容名称解析**（磁盘名与表里名两套写法）：

```python
def name_parts(name):
    name = (name or "").replace("pET040", "pZET040")          # 磁盘笔误
    backbone = re.match(r"(p[A-Za-z]+\d*)", name).group(1).lower()
    barcode = re.search(r"(\d{4,5})", name).group(1)          # 42285 / 32032 …
    base = name.replace("_RL", "")                            # 变体后缀
    unum = re.search(r"u0*(\d{2,4})$", base) or re.search(r"_0*(\d{3,4})$", base)
    sel = re.search(r"s(\d+)\.(\d+)", name)                   # s1.1 / s1.2
    rnd = re.search(r"r0*(\d+)", name)                        # r1..r5
```

键 = `(backbone, barcode, unum)`；不够时退到 `(backbone, sel, rnd)`。**别只用条码**：`b30279_u0003` 在 pZET038/039/040/WGD002 四个骨架下各有一支，只用条码会一次性把甲文件匹配到四个实体（把 MULTI 当「多解」报出去，全是假的）。

## 四类判定

| 判定 | 含义 | 处置 |
|---|---|---|
| UNIQUE | 恰一个候选 | 过 |
| AMBIGUOUS | 同一键下 ≥ 2 候选 | 先查是不是**同名两行 entity**（`<id>-01-FL1` 与 `*<id>-02-FL1`）—— 根因是实体没按序列去重 |
| CONFLICT | 两个口径各给出唯一解、但互不相同 | **不擅自选**，列两个候选交人定 |
| UNMAPPED | 无候选 | 分清：表里没这行（要建）/ 命名体系不同 / 根本不该映射（连接子片段、非图谱导出） |

报 CONFLICT 的典型来源是 **「构建体 ↔ 质粒」连接与磁盘文件名不一致**（库里由源表字段推导，磁盘按实际操作命名），以及 `_RL` 这类变体后缀归属不确定。

## 脚本骨架

- 只读 Dolt（`SELECT entity_uuid,name,aliases,construct_uuid FROM entity_plasmids` + `entity_constructs`），建三个索引：编号 / 名称 / 构建体→质粒（`plas_by_construct[construct_uuid]`）。**别忘了 `construct_uuid` 也要 SELECT** —— 口径③ 靠它，漏了就整批 UNMAPPED。
- 结果写成 `[dict(kind,file,id,name_token,state,via,targets,target_names,construct)]`，`--json-out` 落明细，stdout 只印汇总 + 异常清单。
- 退出码：0 = 全部唯一；1 = 有待处理（这样 CI/复跑能当门禁用）。
- 落 `Migration/<YYYY.MM.DD>.<NNN>/{README.md,audit_*.py}`，README 里写清口径、四类计数、每类逐条文件 + 根因 + 待用户裁决的三个问题。

## 实跑样例（一个课题，`.dna` 66 + `.prot` 9）

```
dna : 共 66 -> UNIQUE 40, AMBIGUOUS 11, CONFLICT 3, UNMAPPED 12
prot: 共 9  -> UNIQUE 8,  AMBIGUOUS 0,  CONFLICT 0, UNMAPPED 1
结论：48/75 唯一映射，27 项待处理
```

- AMBIGUOUS 11 全部来自同名两行 entity（01/02 两批质粒制备各建了一行）。
- CONFLICT 3 = 名称口径 vs 设计码口径指向不同管（含 `…_RL` 变体）。
- UNMAPPED 12 = 早世代质粒（源表里根本没有这些行）、库盒对照质粒（有槽位行但无 entity）、缺号的 `05PL06D5`、命名异常的 `05PL07xx` 三个、非质粒的 `Linker`、以及一个 `.prot` 对应的构建体在库里不存在。

## 不要做什么

- **不要为了凑「100% 唯一」改文件名、改库里的 name、或猜最像的前缀** —— 命名不一致本身就是要报的发现。
- **不要把「无候选」都归成一类**：没这行 ≠ 命名体系不同 ≠ 不该映射，三者修法完全不同。
- **不要在报告里只给总数**：要逐条列文件名，否则用户没法裁。
