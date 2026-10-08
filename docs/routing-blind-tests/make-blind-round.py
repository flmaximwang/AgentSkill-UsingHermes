#!/usr/bin/env python3
"""生成一轮 skill 路由盲测的判官输入（两个候选表臂 A/B）+ 金标，顺手做完三道自检。

    python3 docs/routing-blind-tests/make-blind-round.py --round r1 \
        --new-skill maintain-hermes-models --decoy-ids 5 --decoy-pick maintain-hermes-profiles

判官输入里**只有候选列表与题面**，没有金标（金标写进 blind-key-<round>.json，不进判官通道）。

三道自检（任一不过即非零退出、不写输出）：
  1. 候选表覆盖 `skills/*/SKILL.md` 全集（臂 B = 全集；臂 A = 全集去掉新技能）——漏一个已装技能时
     诱饵题没有正确归属，判官只能投给最像的那个，表上看像「新头抢了诱饵」，真因是列表坏了。
  2. 候选的截断口径与磁盘一致：逐个回读 SKILL.md 的 frontmatter，断言写入的 `description[:57]` == 磁盘值。
  3. 旧题逐字命中：每道旧题在生成的文件里按原文出现恰好一次（人手转写会让题面与金标错配，分数全假）。
     并顺带按题面文本去重：`skills/*/test-prompts.json` 的 glob 会把新技能自己的题也收进来，不去重就会
     把它投两次、被统计成「既有题」。

题面与金标分放两个文件；判官输出的编号就是本文件里的 `P<编号>`，因此解析不依赖判官的书写顺序。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import sys

DESC = re.compile(r"^description:[ \t]*(.+?)[ \t]*$", re.M)
WINDOW = 57


def read_desc(skill_dir: pathlib.Path) -> str:
    """frontmatter 里的 description（本机包里既有双引号写法也有裸写法，两种都吃）。"""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = DESC.search(text)
    if not match:
        return ""
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True, help="轮次名，进文件名（r1 / r2 …）")
    ap.add_argument("--skills-root", default="skills")
    ap.add_argument("--new-skill", required=True, help="本轮新增的 skill 名")
    ap.add_argument("--decoy-ids", default="", help="新技能 test-prompts 里属于诱饵的 id（逗号分隔）")
    ap.add_argument("--decoy-pick", default="", help="诱饵题的正确答案（某个既有 skill 名）")
    ap.add_argument("--out-dir", default="docs/routing-blind-tests")
    ap.add_argument("--seed", type=int, default=20261008, help="题序打乱的固定种子（可复现）")
    args = ap.parse_args()

    root = pathlib.Path(args.skills_root).resolve()
    out = pathlib.Path(args.out_dir).resolve()
    decoy_ids = {int(x) for x in args.decoy_ids.split(",") if x.strip()}

    all_skills = sorted(d.name for d in root.iterdir() if d.is_dir() and (d / "SKILL.md").is_file())
    problems: list[str] = []
    if args.new_skill not in all_skills:
        problems.append("新技能 %s 不在 skills 根下" % args.new_skill)
    descs = {name: read_desc(root / name) for name in all_skills}
    for name, desc in descs.items():
        if not desc:
            problems.append("skills/%s/SKILL.md 没有可读的 description" % name)

    # 题面：旧题（每个既有 skill 的 test-prompts.json）+ 本轮新题（新技能自己的），按题面文本去重
    prompts: list[dict] = []
    seen: dict[str, str] = {}
    for name in all_skills:
        if name == args.new_skill:
            continue
        path = root / name / "test-prompts.json"
        if not path.is_file():
            continue
        for pos, entry in enumerate(json.loads(path.read_text(encoding="utf-8")), start=1):
            text = " ".join(str(entry["prompt"]).split())
            if text in seen:
                problems.append("题面重复（%s 与 %s）：%s" % (seen[text], name, text[:40]))
                continue
            seen[text] = name
            prompts.append({"prompt": text, "owner": name, "kind": "should_trigger",
                            "origin": "%s#%s" % (name, entry.get("id", pos))})

    new_path = root / args.new_skill / "test-prompts.json"
    new_prompts: list[dict] = []
    for entry in json.loads(new_path.read_text(encoding="utf-8")):
        text = " ".join(str(entry["prompt"]).split())
        if text in seen:
            problems.append("新题与既有题重复：%s" % text[:40])
            continue
        seen[text] = args.new_skill
        if entry["id"] in decoy_ids:
            item = {"prompt": text, "owner": args.new_skill, "kind": "should_not_trigger",
                    "expect_pick": args.decoy_pick, "origin": "%s#%s" % (args.new_skill, entry["id"])}
        else:
            item = {"prompt": text, "owner": args.new_skill, "kind": "should_trigger",
                    "origin": "%s#%s" % (args.new_skill, entry["id"])}
        new_prompts.append(item)
        prompts.append(item)

    if len(new_prompts) != 5:
        problems.append("新题应为 4 正例 + 1 诱饵（拿到 %d 条）" % len(new_prompts))

    random.Random(args.seed).shuffle(prompts)
    for i, item in enumerate(prompts, start=1):
        item["id"] = "P%d" % i

    def candidates(with_new: bool) -> list[str]:
        names = [n for n in all_skills if with_new or n != args.new_skill]
        if with_new and args.new_skill not in names:
            names.append(args.new_skill)
        return names

    # 自检 1：候选表覆盖全集
    for arm, with_new in (("A", False), ("B", True)):
        wanted = set(all_skills) - set() if with_new else set(all_skills) - {args.new_skill}
        got = set(candidates(with_new))
        if wanted - got:
            problems.append("臂 %s 候选表缺：%s" % (arm, sorted(wanted - got)))
        if not with_new and args.new_skill in got:
            problems.append("臂 A 不该含新技能")

    if problems:
        print("自检未通过，未写任何输出：")
        for p in problems:
            print("  -", p)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    key = {item["id"]: {k: item[k] for k in ("owner", "kind", "expect_pick", "origin") if k in item}
           for item in prompts}
    (out / ("blind-key-%s.json" % args.round)).write_text(
        json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    header = (
        "你是一名 skill 路由判官。下面第一段是候选 skill 列表（只有名字与 description 的前 57 字符），\n"
        "第二段是一批**用户提问**。请为每一条提问选出「最该被触发的那个 skill」。\n\n"
        "规则：\n"
        "- 只能从候选列表里挑一个名字，或写 none（表示这批候选里都不合适）。\n"
        "- 只按语义判断；提问里出现某个词不等于该选同名的 skill。\n"
        "- 每条只给一个答案，不确定时给最接近的那个，不要跳过任何一条。\n"
        "- 编号照抄题面里的 `P<n>`。\n"
        "- 除本文件外不要读任何其它文件、不要翻技能目录。\n"
    )
    for arm, with_new in (("A", False), ("B", True)):
        names = candidates(with_new)
        lines = [header, "\n## 候选 skill（%d 个）\n" % len(names)]
        for i, name in enumerate(names, start=1):
            lines.append("%d. %s — %s…\n" % (i, name, descs[name][:WINDOW]))
        lines.append("\n## 提问（%d 条）\n" % len(prompts))
        for item in prompts:
            lines.append("%s %s\n" % (item["id"], item["prompt"]))
        lines.append(
            "\n## 输出\n"
            "把答案写成每行 `P<n>|<skill 名或 none>`（n 用题面里的编号），写进你被指定的输出文件，\n"
            "并在回答里原样重复这份清单。最后一行写 DONE。\n"
        )
        path = out / ("judge-input-%s-%s.txt" % (args.round, arm))
        path.write_text("".join(lines), encoding="utf-8")

    # 自检 2/3（写完再回读核对）
    for arm in ("A", "B"):
        text = (out / ("judge-input-%s-%s.txt" % (args.round, arm))).read_text(encoding="utf-8")
        names = candidates(arm == "B")
        for name in names:
            window = "%s — %s…" % (name, descs[name][:WINDOW])
            if window not in text:
                problems.append("臂 %s：候选 %s 的截断口径与磁盘不一致" % (arm, name))
        for item in prompts:
            if text.count("%s %s\n" % (item["id"], item["prompt"])) != 1:
                problems.append("臂 %s：题 %s 没有逐字出现且只出现一次" % (arm, item["id"]))
        numbered = re.findall(r"^(P\d+) ", text, re.M)
        if len(numbered) != len(prompts):
            problems.append("臂 %s：题面编号数 %d != 题数 %d" % (arm, len(numbered), len(prompts)))

    if problems:
        print("回读自检未通过：")
        for p in problems:
            print("  -", p)
        return 1

    old = sum(1 for i in prompts if i["origin"].split("#")[0] != args.new_skill)
    (out / ("blind-prompts-%s.json" % args.round)).write_text(
        json.dumps({"round": args.round, "seed": args.seed, "skills": all_skills,
                    "prompts": prompts}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("臂 A 候选 %d 个 / 臂 B 候选 %d 个 / 题面 %d 条（旧题 %d + 新题 %d，其中诱饵 %d）"
          % (len(candidates(False)), len(candidates(True)), len(prompts), old, len(new_prompts), len(decoy_ids)))
    print("金标：%s" % (out / ("blind-key-%s.json" % args.round)))
    print("判官输入：%s / %s" % (out / ("judge-input-%s-A.txt" % args.round),
                                 out / ("judge-input-%s-B.txt" % args.round)))
    print("三道自检：候选覆盖 ✓ · 截断口径 ✓ · 旧题逐字命中且一句一次 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
