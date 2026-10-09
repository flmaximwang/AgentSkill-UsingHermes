---
name: xlsx-deliverable-integrity
description: "Use when generating .xlsx that Excel must open cleanly."
---

# xlsx 交付完整性（openpyxl → Excel）

**LibreOffice 能打开、pandas 能读到、WPS 正常 —— 完全不能证明 Excel 不会报错。** Excel 的 OOXML
校验严格得多，这是本技能存在的全部理由。当验收标准是「用户双击能打开、不弹修复提示」时，
**Excel 本体是唯一 oracle**，其他工具只是参考。

（读写/公式重算/格式保留的常规做法见 bundled `xlsx` 技能；本技能只管「交出去的文件能不能被
Excel 接受」以及验证纪律。）

## 步骤

1. **写入时守三条死规矩**，并把它们封成单一出口（一个写文本的 helper + 一个冻结的 helper），
   否则散在各处必然漏。可直接复制 `templates/safe_xlsx_helpers.py`（`t()` 处理空白与公式领头
   字符、`freeze()` 处理冻结、`append_row()` 强制所有单元格走这两个出口）：
   - **空白文本写 `None`，绝不写 `""`**：openpyxl 把 `""` 写成 `<c r="A1" t="inlineStr" />`
     （自闭合、缺必需的 `<is>` 子元素）→ 畸形 part。
   - **不要让文本以 `=` / `+` / `-` / `@` 开头**：openpyxl 会当**公式**写成
     `<c r="H9"><f> 库存现金 + …</f><v /></c>` —— 非法公式 + 空缓存值。说明文字改成
     `"可用资金 = 库存现金 + …"` 这种名称开头的写法，或写单元格时把首字符换全角 `＝ ＋ － ＠`。
   - **不要直接 `ws.freeze_panes = "A2"`**（一致性卫生，**不是**已证实的报错成因）：它会写出
     `<selection pane="bottomLeft" activeCell="A1" …/>` —— activeCell 落在冻结区内却声称在下半区；
     Excel 自己生成的文件里 activeCell 在下半区。设完冻结后把 `ws.sheet_view.selection` 重置到下半区。
     但别把它当根因追：孤立测过「裸数据 + 冻结」的文件，Excel **能**正常双击打开。
2. **交付前跑结构门禁**（纯 stdlib）：
   ```bash
   python3 scripts/check_xlsx_parts.py 产出.xlsx
   ```
   查：zip 完好 / 每个 part 合法 XML / 无畸形空单元格 / **无公式单元格** / 每个 part 在
   `[Content_Types].xml` 声明 / 工作表 `r:id` 引用在 `_rels` 中存在 / 冻结窗格与 selection 一致。
   **不通过就不交付** —— 宁可失败，也不交一个 Excel 打不开的文件。
3. **交叉验证数字**：写出后读回复算，保证「只改包结构、不改数字」。若用 LibreOffice 重存洗包，
   洗包前后必须逐字相同，不同就拒绝交付（洗包只是兜底，不是对因下药）。
4. **把「能不能打开」的判定交给用户**：给他 2~3 个最小对照文件让他双击，而不是自己开他的 GUI 应用。
5. 用户报错时走对照法（下），**拿到他的结果再下结论**。

## 用户报错时的对照法（bisect）

- **先内容、后结构**：解包搜 `<f>`（公式单元格）与 `t="inlineStr" />`（畸形空单元格）—— 内容级缺陷
  优先怀疑；冻结、内联字符串、字体/docProps、sharedStrings 缺失等结构差异都只是嫌疑，实测多能正常
  打开。按嫌疑轻重排序而不是按「看起来可疑」排序，否则白耗一整轮。
- 取**真实数据**造最小文件，一次只加一个特性：裸数据 → +筛选 → +冻结 → +样式 → +多工作表/中文表名
  → +**出问题的那段内容**。
- **对照组必须包含出问题的那段内容**：真实文件里元凶在第 9 行的长说明文字，对照组只抄前 6 行，
  于是「全都正常」、方向被带偏一整轮。说明/备注/尾部行最容易藏元凶。
- 让用户各双击一次，只报哪几个失败；更快的一步是让他在**测试文件**上点一次修复，
  Excel 的「修复记录」通常直接指名坏在哪个 part。
- **拿到用户结果之前，只讲证据与假设，不宣布根因。** 用户明确反对「在我验证前就下结论」。

## 绝不碰用户的 GUI 应用

- 不 `pkill` 用户的 Excel/办公软件；不 `open -a` 他们的应用来做自己的测试；不用 AppleScript
  改他们的 `display alerts`。这些会关掉他们未保存的文件、并静默关掉他们的告警。
- 需要 GUI 侧证据时：造文件交给用户点，自己只做**只读**检查（诊断日志、md5 比对、`~$*` 锁文件、
  解包看 part）。
- 也不要把「我这边能开」当成「修好了」。

## XML 级只读排查（快速定位）

```bash
unzip -l out.xlsx                                                                      # 包结构
unzip -p out.xlsx xl/worksheets/sheet1.xml | grep -o '<f[ >][^<]*</f>'                # 公式单元格（不该有）
unzip -p out.xlsx xl/worksheets/sheet1.xml | grep -o '<c [^>]*t="inlineStr"[^>]*/>'  # 畸形空单元格
unzip -p out.xlsx xl/worksheets/sheet1.xml | grep -o '<pane[^>]*>\|<selection[^>]*>'  # 冻结/选区
```

拿机器上 **Excel/WPS 自己生成的文件当基准**（看它有哪些 part、`<selection>` 怎么写）——比凭记忆猜靠得住。

深度说明（三类成因的机制、洗包兜底的前后校验、只读基准对照）见 `references/excel-repair-prompt.md`。
