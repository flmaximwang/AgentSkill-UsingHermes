---
name: obsidian-snippet
description: Create and manage Obsidian Snippets (碎片笔记) — chronological micro-notes with Dataview-based cross-referencing. Covers location convention, template fields, parents/abstract/keywords best practices, and Templater automation.
---

# Obsidian Snippet 创建指南

## 概览

Snippets 是时间线碎片笔记，按 **年/月/日/时间戳** 组织在 `📝 Snippets/` 下。每个 snippet 携带结构化 frontmatter（tags、parents、abstract、keywords、references），通过 Dataview 实现跨笔记检索。

## Snippet 的定位

- **与 MEMOS 笔记的关系**：MEMOS 是"主条目"（如一个蛋白质、一个基因的完整记录），Snippet 是对应某个主条目的碎片笔记（如一个实验条件、一个结晶方法）。通过 `parents` 字段关联。
- **何时用 Snippet**：当一个事实性信息不构成一个独立大笔记，而是一段可被搜索的摘要/备注时。
- **不是 Snippet**：完整的方法论、综述性笔记 → `📚 Literatures/` 或 `🗂️ Classifications/`。

## 模板

模板文件：`🌏 Public/📝 Snippets/_Snippets.md`

```yaml
---
aliases:
tags:
  - Snippets
parents:
  - "[[关联的 MEMOS 笔记]]"    # 必填，链接到对应的主条目
abstract:                      # 必填，一句话摘要
keywords:                      # 可空，数组，用于 Dataview 检索
references:                    # 可空，文献链接
---
```

模板字段说明：

| 字段 | 必填？ | 说明 |
|------|--------|------|
| `aliases` | 可选 | 别名 |
| `tags` | 固定 | 必须为 `Snippets`（Dataview 检索依据） |
| `parents` | **推荐** | 链接到关联的主笔记（如 `[[β₂-Adrenergic Receptor (β2AR-T4L)]]`）。Snippet 通过此字段与 MEMOS 或其他笔记建立双向关联。多条用数组 |
| `abstract` | **推荐** | 一句话摘要，在 Dataview 表格中显示 |
| `keywords` | 可选 | 关键词数组，供 Dataview 中的关键词匹配查询跨 snippet 检索 |
| `references` | 可选 | 关联的文献笔记（`[[Author (Year) Journal]]`），用于元绑定输入 |

### 正文

正文直接书写摘要内容。对于简单 snippet，可删除模板中的 `You may delete this section...` 提示。结构化字段通过 sections 管理：

```
# REFERENCES

\`\`\`meta-bind
INPUT[list:references]
\`\`\`

# RELATED NOTES
（可留空，也可放内部链接）
```

## 存储位置

路径格式：`🌏 Public/📝 Snippets/{YYYY}/{YYYY.MM}/{YYYY.MM.DD}/{YYYY.MM.DD_HH.MM.SS}/`

```
📝 Snippets/
├── + Snippets.md          ← 文件夹笔记
├── _Snippets.md           ← 模板
├── % Snippets.base        ← Dataview 视图
├── Snippets.base          ← Dataview 表格
├── 2026/
│   └── 2026.06/
│       └── 2026.06.12/
│           └── 2026.06.12_20.08.00/
│               └── 2026.06.12_20.08.00.md
```

- 路径按 **UTC+8 北京时间** 的创建时间决定
- 最内层文件夹以精确到秒的时间戳命名
- `.md` 文件名与文件夹名一致

## 工作流程

### 1. 手动创建

1. 进入 `🌏 Public/📝 Snippets/` 下的对应日期路径
2. 如果当前日期的路径不存在，创建 `YYYY/YYYY.MM/YYYY.MM.DD/YYYY.MM.DD_HH.MM.SS/` 目录
3. 在该目录下创建 `YYYY.MM.DD_HH.MM.SS.md` 文件
4. 使用 `_Snippets.md` 模板作为起点
5. 填入 frontmatter（尤其 `parents` 和 `abstract`）
6. 写入正文内容

### 2. Hermes Agent 创建（当前工作流）

当用户要求创建 Snippet 时：

1. **Scope check**: Each distinct topic gets its own Snippet file. Do NOT combine multiple topics (e.g. conductivity measurement + protein overview + axial ligand analysis) into one note. The user will correct you to split them.
2. 确定关联的 MEMOS 笔记（`parents` 指向的文件）
3. 按当前时间确定日期路径，每个 topic 使用独立的 timestamp（递增秒数避免重复）
4. 使用 `_Snippets.md` 模板格式创建文件
5. 确保各字段填写完整

### 3. Templater 自动化

在任意笔记中运行 `@Templater SnippetCollection` 模板（位于 `⚙️ Scripts/Templater/`），会提示输入关键词，然后生成一个 Dataview 查询块，汇总匹配这些关键词的 snippet：

~~~
```dataview
TABLE abstract AS Abstracts, references AS References FROM #Snippets
WHERE icontains(keywords, "keyword1")
OR contains(parents, this.file.link)
```
~~~

## 常见陷阱

1. **合并多个 topic 到一个文件**：用户明确要求"每个主题一个 Snippet"，不要将对话中的多个讨论点合并写入同一个 Snippet 文件。而是各自分配独立 timestamp，各写一个文件。
2. **parents 必须用双链引用格式**：`"[[笔记名]]"`（YAML 中需要双引号括起来防止解析错误）
3. **tags 必须为 `Snippets`**：这是 Dataview 过滤的固定 tag，错写会导致 snippet 不会被查询到
4. **keywords 是 Dataview 索引字段**：用 `icontains()` 做大小写不敏感匹配，写关键词时考虑别人搜索时可能用的词
5. **references 用 `[[...]]` 格式**：链接到 `📚 Literatures/` 下的文献笔记，不是裸 URL
6. **abstract 不宜过长**：控制在 50-80 字，因为 Dataview 表格列宽有限

## 与 MEMOS 的交互

Snippet 通过 `parents` 链接回 MEMOS 笔记。MEMOS 端的 `% Memos @ Proteins.base`（或其他 MEMOS 的 .base 文件）中通常包含 Dataview 查询：

~~~
```dataview
TABLE abstract AS Abstracts, references AS References FROM #Snippets
WHERE icontains(keywords, "...") or contains(parents, this.file.link)
```
~~~

这使得在 MEMOS 笔记中即可查询到所有相关的 snippet。

## 相关文件

| 文件 | 用途 |
|------|------|
| `📝 Snippets/_Snippets.md` | 单个 snippet 的模板 |
| `📝 Snippets/% Snippets.base` | Snippets 文件夹的 Dataview 视图配置 |
| `📝 Snippets/Snippets.base` | Snippets 文件夹的 Dataview 表格配置 |
| `⚙️ Scripts/Templater/@Templater SnippetCollection.md` | 跨笔记关键词查询的 Templater 脚本 |
