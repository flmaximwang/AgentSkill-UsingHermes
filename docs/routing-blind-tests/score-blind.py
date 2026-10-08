#!/usr/bin/env python3
"""给一轮路由盲测打分：判官文件 + 金标 → 逐题矩阵 + 分组统计。

    python3 docs/routing-blind-tests/score-blind.py --round r1

判官文件（`blind-judge*-<round>.txt`）每行 `P<n>|<skill 名或 none>`。
臂别由文件名里的末位字母决定：A/C → 臂 A（候选不含新技能），B/D → 臂 B（含）。同一臂的两份互相对照，
两份逐题一致即视作定版证据（`skill-routing-blind-test` 的口径）。

判据：
  should_trigger       pick == owner
  should_not_trigger   pick != owner（且若给了 expect_pick，另记 pick 是否落在正确答案上）

分组：`旧题(既有触发词)` / `新能力(本轮新技能的正例)` / `兄弟干扰项(诱饵)` —— 总分接近时只有「新能力组」的差异
是有意义的比较。退出码：0 全部按判据通过 · 1 有失败题 · 2 找不到输入。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

LINE = re.compile(r"^(P\d+)\s*\|\s*(\S+)\s*$")


def read_judge(path: pathlib.Path) -> dict[str, str]:
    picks: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = LINE.match(raw.strip())
        if match:
            picks[match.group(1)] = match.group(2)
    return picks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True)
    ap.add_argument("--dir", default="docs/routing-blind-tests")
    ap.add_argument("--new-skill", default="maintain-hermes-models")
    args = ap.parse_args()

    base = pathlib.Path(args.dir).resolve()
    key = json.loads((base / ("blind-key-%s.json" % args.round)).read_text(encoding="utf-8"))
    prompts = json.loads((base / ("blind-prompts-%s.json" % args.round)).read_text(encoding="utf-8"))
    order = [p["id"] for p in prompts["prompts"]]
    text_of = {p["id"]: p["prompt"] for p in prompts["prompts"]}

    judges = {}
    for path in sorted(base.glob("blind-judge*%s.txt" % args.round)):
        match = re.match(r"blind-judge([A-Z])-", path.stem)
        letter = match.group(1) if match else "?"
        arm = "A" if letter in "AC" else "B"
        judges.setdefault(arm, []).append((path.name, read_judge(path)))
    if not judges:
        print("找不到任何 blind-judge*-%s.txt" % args.round, file=sys.stderr)
        return 2

    out: list[str] = []
    failed = 0
    for arm in sorted(judges):
        names = [n for n, _ in judges[arm]]
        out.append("=== 臂 %s（%s） ===" % (arm, ", ".join(names)))
        agree = {pid: len({p.get(pid, "-") for _, p in judges[arm]}) == 1 for pid in order}
        groups: dict[str, list[int]] = {"旧题": [0, 0], "新能力": [0, 0], "兄弟干扰项": [0, 0]}
        out.append("%-4s %-18s %-30s %-30s %s" % ("题", "kind", "owner / 正确 pick", "判官 picks", "结"))
        for pid in order:
            item = key[pid]
            picks = [p.get(pid, "-") for _, p in judges[arm]]
            if item["kind"] == "should_trigger":
                ok = all(p == item["owner"] for p in picks)
                group = "新能力" if item["owner"] == args.new_skill else "旧题"
                want = item["owner"]
            else:
                ok = all(p != item["owner"] for p in picks)
                group = "兄弟干扰项"
                want = "%s（不该）→ %s" % (item["owner"], item.get("expect_pick", "?"))
            groups[group][0] += 1
            if ok:
                groups[group][1] += 1
            else:
                failed += 1
            note = "" if agree[pid] else "  (两判官不一致)"
            if item["kind"] != "should_trigger" and item.get("expect_pick"):
                landed = [p for p in picks if p == item["expect_pick"]]
                note += "  [落在正确答案上的判官：%d/%d]" % (len(landed), len(picks))
            out.append("%-4s %-18s %-30s %-30s %s%s" % (
                pid, item["kind"], want, ",".join(picks), "✓" if ok else "✗", note))
            if not ok:
                out.append("     题面：%s" % text_of[pid][:90])
        out.append("分组：%s" % " · ".join(
            "%s %d/%d" % (g, v[1], v[0]) for g, v in groups.items()))
        out.append("")

    # 臂间对照：旧题在 B 臂里是否被新技能吃掉
    if "A" in judges and "B" in judges:
        a = judges["A"][0][1]
        b = judges["B"][0][1]
        stolen = [pid for pid in order
                  if key[pid]["owner"] != args.new_skill
                  and key[pid]["kind"] == "should_trigger"
                  and a.get(pid) != args.new_skill and b.get(pid) == args.new_skill]
        moved = [pid for pid in order if a.get(pid) != b.get(pid)]
        out.append("=== 臂间对照（各取第一份判官） ===")
        out.append("旧题被新技能抢走：%d 条 %s" % (len(stolen), stolen or ""))
        out.append("A→B 落点变化的题：%d 条 %s（应全部落在既有兄弟之间 = 判官噪声）" % (len(moved), moved or ""))
        for pid in moved:
            out.append("  %s  %s → %s   题面：%s" % (pid, a.get(pid), b.get(pid), text_of[pid][:60]))

    report = "\n".join(out)
    (base / ("blind-round%s-score.txt" % args.round)).write_text(report + "\n", encoding="utf-8")
    print(report)
    print("\n报告已写：%s" % (base / ("blind-round%s-score.txt" % args.round)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
