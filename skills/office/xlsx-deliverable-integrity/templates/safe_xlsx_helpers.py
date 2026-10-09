"""openpyxl 安全写入 helper —— 复制到项目里用，别每次重新推导。

这三条规则里，前两条是**已证实的**报错成因，第三条只是一致性卫生：
  1. 空白文本写 None（写 "" 会产出 <c ... t="inlineStr" /> 畸形单元格）—— 已证实
  2. 文本不得以 = + - @ 开头（openpyxl 会当成公式，写成非法 <f>）—— 已证实，且最隐蔽
  3. 冻结窗格要同时重置 selection（否则 activeCell 落在冻结区内）—— 卫生项，别当根因追

为什么第 1、2 条最难查：openpyxl 读回来仍然显示成正常文本，读回复算根本发现不了。

交付前记得跑本技能自带的结构门禁：
    python3 <skill_dir>/scripts/check_xlsx_parts.py 产出.xlsx
"""
from __future__ import annotations

_FORMULA_HEADS = {"=": "＝", "+": "＋", "-": "－", "@": "＠"}


def t(value):
    """文本单元格唯一出口：空白→None；公式领头字符→全角。

    >>> t("")            # None（不生成单元格）
    >>> t("= 现金 + 存款")  # "＝ 现金 + 存款"（不再是公式）
    >>> t("可用资金 = 现金")  # 原样（首字符不是公式领头）
    """
    if value is None:
        return None
    text = str(value)
    if text.strip() == "":
        return None
    head = text[:1]
    if head in _FORMULA_HEADS:
        return _FORMULA_HEADS[head] + text[1:]
    return text


def freeze(ws, ref="A2"):
    """冻结窗格 + 把 selection 修正到冻结区之外（不要直接用 ws.freeze_panes）。

    一致性卫生：openpyxl 默认写出 activeCell 落在冻结区内的 selection。孤立测试表明
    它单独存在时 Excel 仍能打开，所以修它是为了干净，不是“修好报错”。
    """
    from openpyxl.worksheet.views import Selection

    ws.freeze_panes = ref
    ws.sheet_view.selection = [Selection(pane="bottomLeft", activeCell=ref, sqref=ref)]


def num(value):
    """数值单元格：Decimal/None/字符串都要能安全落到 float 或 None。"""
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def append_row(ws, row, numeric_cols=()):
    """按列写一行：numeric_cols 里的列走 num()，其余走 t()。

    不要绕开这个函数直接 ws.append([...]) —— 空串/公式领头文本就是这么漏进去的。
    """
    cells = []
    for idx, value in enumerate(row, start=1):
        cells.append(num(value) if idx in numeric_cols else t(value))
    ws.append(cells)
    return cells
