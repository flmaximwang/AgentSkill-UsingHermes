#!/usr/bin/env python3
"""结构门禁：检查 .xlsx 是否会被 Excel 判为「部分内容有问题，是否让我们尽量尝试恢复？」。

用法: python3 check_xlsx_parts.py 产出.xlsx [更多.xlsx ...]
退出码: 0 = 全部通过；1 = 有问题；2 = 用法错误

只依赖标准库。检查项：
  1 zip 完好
  2 每个 .xml 是合法 XML
  3 无畸形空单元格（openpyxl 写空字符串会产出 `<c ... t="inlineStr" />`，缺 <is>）
  4 无公式单元格（= 开头的文本会被 openpyxl 当成公式，非法公式会让 Excel 报错）
  5 每个 part 都在 [Content_Types].xml 里声明
  6 工作表引用的 r:id 在其 _rels 里存在
  7 冻结窗格与 selection 一致（activeCell 不能落在冻结区内）
"""
from __future__ import annotations

import re
import sys
import zipfile
from xml.etree import ElementTree

SHEET_RE = re.compile(r"^xl/worksheets/sheet\d+\.xml$")
EMPTY_INLINE_RE = re.compile(r'<c [^>]*t="inlineStr"[^>]*/>')
FORMULA_RE = re.compile(r"<f[ >][^<]*</f>")
PANE_RE = re.compile(r'<pane ySplit="(\d+)"[^>]*state="frozen"')
SELECTION_RE = re.compile(r"<selection[^>]*/>")
ACTIVE_RE = re.compile(r'activeCell="[A-Z]+(\d+)"')
RID_RE = re.compile(r'r:id="(rId\d+)"')
REL_ID_RE = re.compile(r'Id="(rId\d+)"')
PART_NAME_RE = re.compile(r'PartName="([^"]+)"')
EXT_RE = re.compile(r'Extension="([^"]+)"')


def check(path: str) -> list[str]:
    issues: list[str] = []
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        broken = zf.testzip()
        if broken:
            issues.append(f"zip 条目损坏：{broken}")

        for name in sorted(names):
            if not name.endswith(".xml"):
                continue
            try:
                ElementTree.fromstring(zf.read(name))
            except Exception as exc:  # noqa: BLE001
                issues.append(f"{name} 不是合法 XML：{exc}")

        for name in sorted(n for n in names if SHEET_RE.match(n)):
            text = zf.read(name).decode("utf-8", errors="replace")

            bad_cells = EMPTY_INLINE_RE.findall(text)
            if bad_cells:
                issues.append(f"{name}: {len(bad_cells)} 个畸形空单元格"
                              f'（t="inlineStr" 缺 <is>）—— 空白应写 None，不要写 ""')

            formulas = FORMULA_RE.findall(text)
            if formulas:
                issues.append(f"{name}: {len(formulas)} 个公式单元格（很可能是 = 开头的文本"
                              f"被当成公式）：{formulas[0][:60]}")

            pane = PANE_RE.search(text)
            if pane:
                ysplit = int(pane.group(1))
                for sel in SELECTION_RE.findall(text):
                    active = ACTIVE_RE.search(sel)
                    if active and int(active.group(1)) <= ysplit:
                        issues.append(f"{name}: 冻结窗格 ySplit={ysplit}，但 selection 的 activeCell"
                                      f"落在冻结区内（{sel}）")

            refs = set(RID_RE.findall(text))
            if refs:
                rels = f"xl/worksheets/_rels/{name.rsplit('/', 1)[-1]}.rels"
                rels_text = zf.read(rels).decode("utf-8", errors="replace") if rels in names else ""
                missing = sorted(refs - set(REL_ID_RE.findall(rels_text)))
                if missing:
                    issues.append(f"{name}: 引用了不存在的 r:id {missing}（缺 {rels}）")

        if "[Content_Types].xml" in names:
            ct = zf.read("[Content_Types].xml").decode("utf-8", errors="replace")
            declared = set(PART_NAME_RE.findall(ct))
            exts = set(EXT_RE.findall(ct))
            for name in sorted(names):
                if name.endswith(".rels") or "/_rels/" in name or name == "[Content_Types].xml":
                    continue
                if f"/{name}" in declared or name.rsplit(".", 1)[-1] in exts:
                    continue
                issues.append(f"{name} 未在 [Content_Types].xml 中声明")
    return issues


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    failed = 0
    for path in argv[1:]:
        issues = check(path)
        print(f"{path}: " + ("通过" if not issues else f"{len(issues)} 个问题"))
        for item in issues:
            print(f"  - {item}")
        failed += 1 if issues else 0
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
