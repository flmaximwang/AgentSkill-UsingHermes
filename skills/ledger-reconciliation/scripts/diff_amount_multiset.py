#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按「纯金额多重集」比对某账户某期的流水与分录，找出真正的净差来源。

用法（cwd = 项目根）：
    env -u PYTHONPATH /Applications/Accountancy/bin/python \
        <此脚本> 2026-07 "中国银行借记卡-3572（郑玉丽）"

为什么不能带日期：跨日期的同笔（提现到账、退款延迟入账、跨月）在「日期+金额」比对下会同时出现在
「缺」和「多」两侧，看着像两处问题，其实金额层面是平的 —— 顺着它查会一路查偏。

输出：记账多 / 记账少 两张清单，按（金额, 方向）计数。
    单边（只在一侧出现）的金额就是待解释的真差；两侧同额成对的多半是合并付款/退款对，不是问题。

只读：它只打印，不写任何账本或流水。
"""
from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())

from Scripts import paths  # noqa: E402
from Scripts.books import book, period_of  # noqa: E402
from Scripts.money import money  # noqa: E402
from Scripts.parsers import normalize_dir  # noqa: E402
from Scripts.rules import load_map, load_yaml  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    period, acct = sys.argv[1], sys.argv[2]

    records, errors, per_file, dups = normalize_dir(paths.RUNNING_ACCOUNT_DIR)
    cfg, rules = load_map("Config/account_map.yaml")
    coa_raw = load_yaml("Config/chart_of_accounts.yaml")
    coa = {str(i["code"]): i for g in coa_raw.get("accounts", {}).values() for i in g}
    res = book(records, cfg, rules, coa, duplicates=dups)

    flow, booked = Counter(), Counter()
    for r in records:
        if r.get("账户") == acct and period_of(r.get("日期")) == period:
            d = "+" if r["收支"] == "in" else ("-" if r["收支"] == "out" else "o")
            flow[(str(money(r["金额"])), d)] += 1

    for e in res["entries"]:
        if (e.get("凭证日期") or "")[:7] != period:
            continue
        for ln in e["行"]:
            if (ln.get("明细") or "") != acct:
                continue
            if float(ln.get("借方金额") or 0) > 0:
                booked[(str(money(ln["借方金额"])), "+")] += 1
            if float(ln.get("贷方金额") or 0) > 0:
                booked[(str(money(ln["贷方金额"])), "-")] += 1

    extra, miss = booked - flow, flow - booked
    print(f"{period} {acct}：流水 {sum(flow.values())} 条 / 记账 {sum(booked.values())} 条")
    print("  --- 记账多（金额层面）---")
    for (amt, d), n in sorted(extra.items()):
        print(f"    {n}× {d}{amt}")
    print("  --- 记账少（金额层面）---")
    for (amt, d), n in sorted(miss.items()):
        print(f"    {n}× {d}{amt}")

    both = {k for k in extra if k in miss}
    if both:
        print("  --- 两侧同额成对（合并付款/退款对，通常不是问题）---")
        for amt, d in sorted(both):
            print(f"    {d}{amt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
