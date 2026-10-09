---
name: md-docx-writeback
description: Use when writing an edited .md back into a .docx form.
version: 1.0.0
metadata:
  hermes:
    tags: [docx, markdown, roundtrip, forms, verification]
    category: productivity
    related_skills: [docx]
---

# md → docx 写回（保留原版式）

## When to Use

用户维护一份 md 草稿 + 一份机构下发的 docx 表格（机时申请、基金申请书等），要求
"把 md 写回 docx"。md 是内容源，docx 必须保留原有字体/字号/页边距/留白。
不要用 `docx_create.py` 从零生成——那会丢掉母本版式。

## Procedure

1. **先读两边**。`docx_read.py f.docx --text` 拿到 docx 现状；`read_file` 读 md（用户可能
   已改过，不要用上下文里的旧副本）。用 `docx_read.py f.docx --structure` 确认段落数、有无表格。
2. **找版式母本段**。用 python-docx 打印每段的 `pPr` 与首个 run 的 `rPr`，按 `w:sz` 归类：
   中文表格常见 sz=24(12pt) 章节标题、sz=21(10.5pt) 正文、空段（只有 pPr/rPr）。
   至少取三个模板：标题段、正文段、空段。
3. **确认真正的歧义再动手**。典型两问：md 里的图片行要不要嵌图；docx 模板自带的
   说明文字（如"申请300kv电镜需提供…"）md 里没有时是否保留。用 clarify 一次问完。
4. **重建 body**。删掉 body 下所有 `w:p`（保留 `w:sectPr`），按 md 顺序用
   `doc.add_paragraph()`（python-docx 自动插在 sectPr 之前）新建段落，把母本段落的
   `pPr`/`rPr` deepcopy 进去，单个 run 承载整段文字（`w:t` 加 `xml:space="preserve"`，
   否则首尾空格/全角空格被吞）。空行只当段落分隔，不产生空段；章节标题前补 3 个空段
   与母本留白一致。
5. **图片**：单独一段居中（`WD_ALIGN_PARAGRAPH.CENTER` + `run.add_picture(path, width=Cm(...))`），
   图注另起一段居中，放在图**下方**。图宽按版心算：`pgSz.w - pgMar.left - pgMar.right`（twips/567 ≈ cm）。
6. **先备份再覆盖**：`backup/<stem>.backup-YYYY.MM.DD-HHMM.docx`。
7. **验证**（缺一不可）：
   - 逐块比对：把 md 解析成块序列（图片行展开成 图片段+图注段），与 docx 非空段文本
     一一对齐，打印差异——比抽样肉眼可靠。
   - `docx_validate.py out.docx` → `ok: true`；`unzip -l` 确认 `word/media/` 图片张数。
   - 版式目检：`soffice --headless --convert-to pdf` → `pdftoppm -r 90 -png` →
     `vision_analyze` 看每页（图片是否居中、图注是否紧贴其图下方、有无错配/多余空行）。

## 现成脚本

`scripts/md2docx.py`（本 skill 自带）：`python md2docx.py --md x.md --template x.docx --out x.docx`。
默认 `--img-width-cm 10.0`，默认先备份到 `backup/`，`--no-backup` 可关。

## Pitfalls

- **绝不写死母本段序号**：脚本的输出会被下一次运行当母本，段落序号会漂移（曾经因此把
  “空段”模板取成了正文段，15 个分节空段全变成重复正文，段数 51→66）。按 `w:sz`
  自动识别模板段（最大字号=标题、其余最常见字号=正文、无 run 无图=空段）。
  重新写回前先数段：非空段数 == md 内容块数（图片行算 2 段），对不上就是模板取错了。
- **出错先回滚**：备份目录里存着上一次的输出，`cp -p backup/<stem>.backup-<stamp>.docx <stem>.docx`
  即可回滚，别在坏文件上继续跑（会污染下一轮的母本）。
- **python-docx 没装**：新建 venv 时 lxml 常因网络中断失败，改用
  `uv pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple python-docx lxml`。
- **skill 名 docx 有歧义**：本机 `office/docx` 与 `productivity/docx` 同名，
  `skill_view('docx')` 会拒绝，必须写 `productivity/docx`。
- **`pPr` 子元素顺序**：手插 `w:jc` 要排在 `w:rPr` 之前，否则 Word 报错；
  用 `paragraph.alignment = ...` 让 python-docx 处理顺序。
- **md 里非 `##` 的小节标题**（如"（一）…"）在 md 中无加粗标记，写回时按正文字号，
  不要自作主张加粗/放大——与 md 不一致就是错的。
- **旧的导出 PDF 会过期**：docx 更新后旧 PDF 仍指向上一版内容，报告时提醒用户重新导出。
