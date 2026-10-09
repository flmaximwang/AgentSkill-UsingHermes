# Excel「发现…中的部分内容有问题，是否让我们尽量尝试恢复？」排查手册

## 为什么只有 Excel 能判定

Excel 的 OOXML 校验比 LibreOffice、pandas、WPS 严格。同一条命令（`soffice --headless
--convert-to xlsx`、`pd.read_excel`、openpyxl 读回）全部通过，Excel 仍可能弹修复提示。
交付验收标准是「用户双击能打开」时，只能由用户点的结果作准；代理工具只作参考。

## XML 级只读排查（解包看，不必打开 Excel）

```bash
unzip -l out.xlsx                                              # 包结构
unzip -p out.xlsx xl/worksheets/sheet1.xml | grep -o '<f[ >][^<]*</f>'                # 公式单元格
unzip -p out.xlsx xl/worksheets/sheet1.xml | grep -o '<c [^>]*t="inlineStr"[^>]*/>'  # 畸形空单元格
unzip -p out.xlsx xl/worksheets/sheet1.xml | grep -o '<pane[^>]*>\|<selection[^>]*>'  # 冻结/选区
for f in $(unzip -Z1 out.xlsx | grep '\.xml$'); do unzip -p out.xlsx "$f" | xmllint --noout - ; done
```

只读对照技巧：找机器上 Excel/WPS 自己生成的文件当基准（`unzip -l` 看它有哪些 part、`<selection>`
怎么写、`docProps/app.xml` 的 AppVersion 格式）—— 用用户自己的文件当基准，比凭记忆猜靠得住。
典型差异：Excel 原生文件有 `xl/sharedStrings.xml`，openpyxl 从不生成（字符串一律内联）。

## 成因清单：2 类已证实 + 1 类仅一致性缺陷

下面第 1、2 类由用户在 Excel 里双击的结果证实；第 3 类只有 XML 层面的不一致，**未经证实会触发
修复提示**。排序就是排查顺序：先查内容级（1、2），再考虑结构级。

### 1. 畸形空的内联字符串单元格
`cell.value = ""` / `ws.append(["", …])` → `<c r="M437" t="inlineStr" />`。
`t="inlineStr"` 必须带 `<is>` 子元素，自闭合就是畸形 part。**空白一律写 `None`。**

### 2. 文本被当成公式（最隐蔽，最容易被误判成别的原因）
`ws.append(["可用资金", "= 库存现金 + 银行存款（可随时支取）"])` →
`<c r="H9" s="6"><f> 库存现金 + 银行存款（可随时支取）</f><v /></c>`
—— 公式体是中文说明（非法公式）、缓存值为空。只有解包搜 `<f>` 才看得见：
`data_only=True` 读回来仍显示为普通文本，因此 读回复算/交叉验证都发现不了它。
修：文本首字符不以 `=` `+` `-` `@` 开头（或在写入 helper 里换成全角 `＝ ＋ － ＠`）。

### 3. 冻结窗格与 selection 不一致（**仅一致性缺陷，未证实会触发修复提示**）
`ws.freeze_panes = "A2"` → `<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>`
`<selection pane="bottomLeft" activeCell="A1" sqref="A1"/>`：activeCell 在冻结区内，却声明在
bottomLeft 下半区。Excel 自己写的是 activeCell 位于下半区（行号 > ySplit）。修：设完冻结后把
`ws.sheet_view.selection` 重置为 `[Selection(pane="bottomLeft", activeCell="A2", sqref="A2")]`。
**但它不是报错成因**：单独拿「裸数据 + 这种不一致冻结」造文件让用户双击，Excel 正常打开。
它与报错并存时不要判它死刑 —— 回去查第 1、2 类（优先搜 `<f>`）。

## 对照法（bisect）定位：步骤与陷阱

1. 用**真实数据**造最小文件，一次只加一个特性：裸数据 → +自动筛选 → +冻结 → +样式 →
   +多工作表/中文表名 → +完整数据。
2. **对照组必须包含出问题的那段内容**：真实文件里元凶在第 9 行的长说明，对照组只抄前 6 行，
   于是「全都正常」，把方向带偏一整轮。造对照组要抄到出问题的行。
3. 让用户各双击一次、只报哪几个失败；让他在**测试文件**上点一次修复，Excel 的「修复记录」
   通常直接指名坏在哪个 part。
4. **拿到用户结果前不下结论**；讲「证据 + 假设」，不讲「根因已确认」。

## 兜底手段：LibreOffice 重存洗包（不是对因下药）

```bash
soffice --headless -env:UserInstallation=file:///tmp/lo_profile --convert-to xlsx --outdir /tmp out.xlsx
# 再把 /tmp/out.xlsx 移回原处
```

- 作用：第三方引擎重写包，产出 `xl/sharedStrings.xml`、完整字体定义、Excel 形态的 docProps。
- **它不是可靠修法**：曾经「洗」过仍然报错，真正病灶是公式单元格。所以先修具体写法，再考虑洗包。
- 用就必须带前后校验：洗包前后各读回复算一次，两份结果必须逐字相同，不同即拒绝交付。

## 交付纪律

- 不用「LibreOffice/pandas 能打开」宣称修好了；只有用户双击的结果算数。
- 不在用户验证前宣布根因。汇报时分清「已证实的成因」与「顺手修的卫生项」，不把卫生项（冻结
  selection、洗包、内联字符串）当根因讲给用户。
- 不 `pkill` / `open -a` / AppleScript 操作用户的办公软件来跑自己的测试；只做只读检查。
- 结构门禁不过就不交付。
