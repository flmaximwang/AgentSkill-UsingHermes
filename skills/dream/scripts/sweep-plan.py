#!/usr/bin/env python3
"""Enumerate a profile's un-homed skills and every local skill pack, then fold judge verdicts into a plan.

The deterministic half of `dream`. Two subcommands:

    # 1. scan — what is local-only in this profile, what packs exist, frozen judge input
    python3 -B sweep-plan.py scan --profile default --packs-root ~/Documents/AgentSkill \
        --out ~/.hermes/cache/scratch/sweep-2026-10-09 --self-test     # --self-test runs a throwaway tree

    # 2. merge — judge verdicts (JSONL) -> plan.md + install-cmds.sh
    python3 -B sweep-plan.py merge --dir <the same --out> --profile default

Neither subcommand writes to a profile, a pack or git: `scan` is read-only, `merge` writes only inside --out.

Run it with the venv interpreter (it needs pyyaml, for the same reason load-external-skill-index does —
`description: >-` must be resolved as YAML, not regexed):
    ~/.hermes/hermes-agent/venv/bin/python3

Classification is the three kinds this pack already names, and only the third is a candidate:
    hub-installed   name is a key in <profile>/skills/.hub/lock.json     -> skip (repo + update path)
    bundled         name is a line in <profile>/skills/.bundled_manifest -> skip (Hermes' own seed)
    profile-local   neither -> CANDIDATE (no lock entry, no source of truth, no lifecycle)

## v2 · 判官要读全文，答案空间是全部 AgentSkill-* 目录（2026-10-10 用户改口径）

- `judge-input.json` 每条带 `path` / `skill_md` / `refs`，判官**必须读 SKILL.md 全文**（只说 name+desc
  就是偷懒判法，用户已驳回）；`judge-input-bodies.json` 把正文内联，给只会看文本的判官（JEV）用。
- 答案空间分两轴先判：`{kind:"new", axis:"tool"|"topic", topic, personal, boundary}` 会落到
  `AgentSkill-Using<Topic>` / `AgentSkill-<Topic>`，归一化后撞上已有目录名就**复用那个仓库**；
  多条同 topic **合并进一个包**。`existing` 的 `repo` 可以是 `~/Documents/AgentSkill` 下**任一**
  `AgentSkill-*` 目录名（`routable` 只决定能不能 install 回来，不限制能否当落点）。
- **没有 `__stay_local__`**：判官输出里出现它一律拒收（exit 4）——每条都必须有落点。

Exit codes: 0 ok | 2 no candidates, no packs, or missing sibling | 3 profile not found | 4 verdict coverage < 100%
            or a rejected verdict (stay-local / unknown dest / non-string dest fields) | 5 local skills left outside every pack
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
from typing import NoReturn

HERMES_HOME = pathlib.Path(os.environ.get("HERMES_HOME") or pathlib.Path.home() / ".hermes")
SKIP_DIRS = {".hub", ".git", ".archive", "__pycache__", "quarantine", ".trash"}
# The sibling that already owns frontmatter parsing (YAML, not regex) and the pack index format.
PARSER_SKILL = "load-external-skill-index"
STAY_LOCAL, UNJUDGED = "__stay_local__", "__unjudged__"
ACTIONS = ("move", "merge", "strengthen")
TOOL_PREFIX, TOPIC_PREFIX = "AgentSkill-Using", "AgentSkill-"


def norm(s: str) -> str:
    """Uniquification key: lowercase, hyphens/underscores/spaces dropped (用户 2026-10-10 定的口径)."""
    return "".join(ch for ch in s.lower() if ch not in "-_ ")


def pack_name_for(axis: str, topic: str) -> str:
    """The script only uniquifies — naming policy is exactly these two formulas, nothing cleverer.

    The topic is slugged into something a git remote can carry (no spaces/punctuation); two candidates naming
    the same topic in different styles then land on the same repo name (and on the same normalized key).
    """
    slug = "".join(ch for ch in topic.strip() if ch.isalnum() or ch in "-_") or "Unnamed"
    return (TOOL_PREFIX if axis == "tool" else TOPIC_PREFIX) + slug



def die(code: int, msg: str) -> NoReturn:
    print(f"[sweep-plan] {msg}", file=sys.stderr)
    raise SystemExit(code)


def profile_root(profile: str) -> pathlib.Path:
    root = HERMES_HOME if profile in ("", "default") else HERMES_HOME / "profiles" / profile
    if not (root / "skills").is_dir():
        die(3, f"no skills tree under {root} — profile {profile!r} not found")
    return root


def load_parser(override: str = "") -> tuple:
    """Import the sibling skill-index.py. Never copy its frontmatter parser: the YAML trap is real."""
    here = pathlib.Path(__file__).resolve()
    cands = [pathlib.Path(override).expanduser()] if override else [
        here.parents[2] / PARSER_SKILL / "scripts" / "skill-index.py",          # repo / installed layout
        here.parents[2].parent / PARSER_SKILL / "scripts" / "skill-index.py",   # one level up, defensive
    ]
    for p in cands:
        if p.is_file():
            spec = importlib.util.spec_from_file_location("_sweep_sibling_index", p)
            if spec is None or spec.loader is None:
                die(2, f"cannot load parser module from {p}")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod, p
    die(2, "sibling parser not found; looked at: " + ", ".join(str(c) for c in cands)
           + f" — install {PARSER_SKILL} beside this skill, or pass --parser-script")


def parse_fm(mod: object, path: pathlib.Path) -> dict:
    try:
        fm = mod.frontmatter(path)          # type: ignore[attr-defined]
    except ImportError:
        die(2, "pyyaml missing in this interpreter — run with ~/.hermes/hermes-agent/venv/bin/python3")
    return fm if isinstance(fm, dict) else {}


def git(repo: pathlib.Path, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"<git failed: {exc}>"
    return out.stdout.strip() if out.returncode == 0 else f"<git error: {out.stderr.strip()[:80]}>"


def identifier(remote: str) -> str:
    """git@github.com:owner/repo.git | https://github.com/owner/repo -> owner/repo ('' when unknown)."""
    r = remote.strip()
    if not r or r.startswith("<"):
        return ""
    r = r.removesuffix(".git").rstrip("/")
    r = r.split(":", 1)[1] if r.startswith("git@") else r
    parts = [p for p in r.split("/") if p and "github.com" not in p]
    return "/".join(parts[-2:]) if len(parts) >= 2 else ""


def walk_skill_dirs(skills_root: pathlib.Path) -> list:
    """<cat>/<name>/SKILL.md, plus a plugin's <cat>/<sub>/<name>/SKILL.md; hidden/archive dirs skipped."""
    found = []
    for md in sorted(skills_root.rglob("SKILL.md")):
        rel = md.relative_to(skills_root).parts
        if len(rel) > 4 or any(p in SKIP_DIRS or p.startswith(".") for p in rel[:-1]):
            continue
        found.append(md)
    return found


def read_lock(root: pathlib.Path) -> dict:
    p = root / "skills" / ".hub" / "lock.json"
    if not p.is_file():
        return {}
    try:
        return (json.loads(p.read_text(encoding="utf-8")) or {}).get("installed", {}) or {}
    except (json.JSONDecodeError, OSError):
        die(2, f"unreadable lock file: {p}")


def read_bundled(root: pathlib.Path) -> set:
    p = root / "skills" / ".bundled_manifest"
    if not p.is_file():
        return set()
    return {ln.split(":", 1)[0].strip() for ln in p.read_text(encoding="utf-8", errors="replace").splitlines()
            if ":" in ln}


def cmd_scan(args) -> int:
    root = profile_root(args.profile)
    mod, parser_path = load_parser(args.parser_script)
    lock, bundled = read_lock(root), read_bundled(root)
    skills_root = root / "skills"
    rows = []
    for md in walk_skill_dirs(skills_root):
        rel = md.relative_to(skills_root)
        fm = parse_fm(mod, md)
        name = str(fm.get("name") or rel.parts[-2]).strip()
        kind = "hub" if name in lock else ("bundled" if name in bundled else "local")
        # 形状缺口：<名字>/SKILL.md 直接躺在 skills/ 下 = 没有类目层（用户要求不存在这种 local skill）
        no_cat = len(rel.parts) == 2
        rows.append(dict(kind=kind, category=("(无类目)" if no_cat else rel.parts[0]), name=name,
                         no_category=no_cat, dir=str(rel.parent), _md=md,
                         desc=" ".join(str(fm.get("description") or "").split()), bytes=md.stat().st_size))
    rows.sort(key=lambda r: (r["kind"] != "local", r["category"], r["name"]))
    local = [r for r in rows if r["kind"] == "local"]
    if not local:
        die(2, f"no profile-local skills in {root} — nothing to recruit")

    packs = []
    for pack in sorted(pathlib.Path(args.packs_root).expanduser().glob("AgentSkill-*")):
        if not pack.is_dir():
            continue
        # A linked worktree of some other clone has `.git` as a FILE, not a directory: its name looks exactly
        # like a pack but pushing there is not what a destination means (measured 2026-10-11: this session's own
        # `AgentSkill-UsingHermes.dream-nostay` worktree showed up as a routable destination).
        if (pack / ".git").is_file():
            continue
        pk_skills_dir = pack / "skills"
        remote = git(pack, "remote", "get-url", "origin")
        installed = {n: str(v.get("install_path", "")) for n, v in lock.items()
                     if pack.name in str(v.get("identifier", "")) or pack.name in str(v.get("metadata", {}).get("repo_url", ""))}
        # Every SKILL.md under skills/, at whatever depth the pack lays its categories out.
        skills = sorted({md.parent.name for md in walk_skill_dirs(pk_skills_dir)}) if pk_skills_dir.is_dir() else []
        packs.append(dict(repo=pack.name, path=str(pack), identifier=identifier(remote), remote=remote,
                          has_git=(pack / ".git").exists(),
                          branch=git(pack, "branch", "--show-current"), skills=skills,
                          # An `AgentSkill-*` directory with no SKILL.md anywhere is a placeholder: it is a
                          # legal DESTINATION (the writer creates the repo) but can never be installed back.
                          empty=not skills and not (pack / "SKILL.md").is_file(),
                          installed=installed,
                          categories=sorted({p.split("/")[0] for p in installed.values() if p})))
    if not packs:
        die(2, f"no AgentSkill-* checkout under {args.packs_root}")
    routable = [p for p in packs if not p["empty"]]
    if not routable:
        die(2, f"every AgentSkill-* under {args.packs_root} is a placeholder (no SKILL.md) — "
               "there is no pack index to route against")

    out = pathlib.Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    (out / "inventory.tsv").write_text(
        "kind\tcategory\tname\tno_category\tdir\tdesc\n" + "".join(
            f"{r['kind']}\t{r['category']}\t{r['name']}\t{str(r['no_category']).lower()}\t{r['dir']}\t{r['desc'][:200]}\n"
            for r in rows), encoding="utf-8")
    # Frozen judge input: one P<k> per candidate, script-generated so that no hand transcription can drift
    # from what the judges were actually asked (the pack's own judge lesson). v2 carries the absolute path so
    # the judge CANNOT judge from the name alone — it must read the full SKILL.md; `bodies` inlines the text
    # for judges that only ever see a string (JEV), so both routes see the same full document.
    bodies = {}
    judge_input = []
    for i, r in enumerate(local, 1):
        md = r["_md"]
        refs = sorted(str(p.relative_to(md.parent)) for p in md.parent.rglob("*")
                      if p.is_file() and p.name != "SKILL.md" and "__pycache__" not in p.parts)
        text = md.read_text(encoding="utf-8", errors="replace")
        bodies[f"P{i}"] = text
        judge_input.append(dict(id=f"P{i}", skill=r["name"], category=r["category"], dir=r["dir"],
                                no_category=r["no_category"], description=r["desc"],
                                path=str(md.parent), skill_md=str(md), refs=refs[:30],
                                body_bytes=len(text.encode("utf-8")),
                                body_lines=len(text.splitlines())))
    (out / "judge-input.json").write_text(json.dumps(judge_input, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    (out / "judge-input-bodies.json").write_text(json.dumps(
        [dict(r, body=bodies[r["id"]]) for r in judge_input], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    index_blocks = []
    for pk in routable:
        idx = out / f"index-{pk['repo']}.txt"
        subprocess.run([sys.executable, "-B", str(parser_path), pk["path"], "--out", str(idx),
                        "--quiet", "--max-desc", "110"], capture_output=True, text=True)
        body = idx.read_text(encoding="utf-8").strip() if idx.is_file() else ""
        pk["index_rows"] = len(body.splitlines()) if body else 0
        if body:
            index_blocks.append(f"## {pk['repo']}  ({pk['identifier'] or 'no-remote'})\n{body}")
    (out / "pack-index.txt").write_text("\n\n".join(index_blocks) + "\n", encoding="utf-8")
    (out / "packs.json").write_text(json.dumps(packs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # The judge's answer space, v2: EVERY AgentSkill-* directory name, split by axis, plus the two naming
    # formulas for a brand-new pack. `routable` (remote + SKILL.md) only says whether a pack can be installed
    # back afterwards — it never restricts which name may be a destination.
    (out / "answer-space.json").write_text(json.dumps(dict(
        dirs=[p["repo"] for p in packs],
        tool_dirs=[p["repo"] for p in packs if p["repo"].startswith(TOOL_PREFIX)],
        topic_dirs=[p["repo"] for p in packs if not p["repo"].startswith(TOOL_PREFIX)],
        routable=[p["repo"] for p in routable],
        new=dict(tool=f"{TOOL_PREFIX}<工具名>", topic=f"{TOPIC_PREFIX}<主题名>")),
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts = {k: sum(1 for r in rows if r["kind"] == k) for k in ("local", "hub", "bundled")}
    idx_chars = (out / "pack-index.txt").stat().st_size
    print(f"[sweep-plan] profile={root} skills={len(rows)} local={counts['local']} "
          f"hub={counts['hub']} bundled={counts['bundled']}")
    print(f"[sweep-plan] packs={len(packs)} routable={len(routable)} placeholder={len(packs) - len(routable)} "
          f"pack_skills={sum(len(p['skills']) for p in routable)} pack_index_est_tokens~{idx_chars // 2}")
    print(f"[sweep-plan] dest_space={len(packs)} 个目录名（tool {len([p for p in packs if p['repo'].startswith(TOOL_PREFIX)])}"
          f" + topic {len([p for p in packs if not p['repo'].startswith(TOOL_PREFIX)])}）→ answer-space.json")
    n_nocat = sum(1 for r in local if r["no_category"])
    print(f"[sweep-plan] no_category={n_nocat}（local skill 直接躺在 skills/ 下，没有类目层——本批必须一并补齐）")
    print(f"[sweep-plan] candidates={len(local)} judge_input={out / 'judge-input.json'} "
          f"({(out / 'judge-input.json').stat().st_size} B) bodies={(out / 'judge-input-bodies.json').stat().st_size} B "
          f"parser={parser_path}")
    print(f"[sweep-plan] 判官必须读每条 P<k> 的 skill_md 全文（judge-input.json 给了绝对路径；只吃文本的判官用 "
          f"judge-input-bodies.json）")
    print(f"[sweep-plan] next: judge every P<k> (JEV, else classifier children) -> {out}/verdicts*.jsonl, then "
          f"`merge --dir {out} --profile {args.profile}`")
    return 0


def _resolve(r: dict, v: dict, packs: dict, by_norm: dict, bad: list):
    """Validate one verdict's `dest` and turn it into a resolution, or record why it was rejected.

    The script never names or classifies anything itself: it only (a) rejects the shapes the user's v2 rules
    forbid, (b) applies the two naming formulas, and (c) lets a new topic colliding with an existing
    directory name reuse that directory instead of creating a twin.
    """
    rid = r["id"]
    dest = v.get("dest")

    def reject(msg: str):
        bad.append(f"{rid}: {msg}")
        return None

    if isinstance(dest, str):                       # a bare string is only ever the v1 / stay-local shape
        if dest.strip() in (STAY_LOCAL, "stay_local", "stay"):
            return reject(f"判官给了 {dest!r} —— 本版已废除 stay local：每条候选都必须落进一个包"
                          "（用户 2026-10-10 改口径）。改判成工具轴或主题轴的落点再交")
        dest = {"kind": "existing", "repo": dest}
    if not isinstance(dest, dict):
        return reject("缺 dest 对象（v2 形状：dest.kind = \"existing\" 或 \"new\"）")

    kind = str(dest.get("kind") or "").strip()
    if kind == "existing":
        repo = str(dest.get("repo") or "").strip()
        if repo in (STAY_LOCAL, "stay_local", "stay"):
            return reject(f"dest.repo={repo!r} 就是 stay local —— 本版已废除（用户 2026-10-10 改口径）")
        if repo not in packs:
            return reject(f"dest.repo {repo!r} 不在 {len(packs)} 个 AgentSkill-* 目录名里"
                          "（落点空间是全部目录名，不是只有能 install 的那些；名字写错就重判）")
        action = str(dest.get("action") or v.get("action") or "move").strip()
        if action not in ACTIONS:
            return reject(f"dest.action {action!r} 不是 {ACTIONS} 之一")
        dskill = str(dest.get("dest_skill") or v.get("dest_skill") or "__new__").strip() or "__new__"
        if not dskill.startswith("__") and dskill not in packs[repo]["skills"]:
            avail = ", ".join(packs[repo]["skills"][:8]) or "（该目录还没有任何技能）"
            return reject(f"dest_skill {dskill!r} 不在 {repo} 的技能清单里 —— 可用：{avail}")
        return dict(repo=repo, kind="existing", dest_skill=dskill, action=action, collided=False,
                    axis="", topic="", personal=False, boundary="")

    if kind == "new":
        axis = str(dest.get("axis") or "").strip()
        if axis not in ("tool", "topic"):
            return reject(f"dest.axis {axis!r} 必须是 \"tool\"（主语是某个软件/工具）或 \"topic\""
                          "（主语是一类任务/学科/项目）—— 二选一先判，别跳过")
        topic = str(dest.get("topic") or "").strip()
        if not topic:
            return reject("dest.topic 为空：新包必须先说出工具名或主题名")
        boundary = str(dest.get("boundary") or "").strip()
        if not boundary:
            return reject("dest.boundary 为空：新包必须写明这个包**不吃**什么（边界是判据的一部分）")
        name = pack_name_for(axis, topic)
        hit = by_norm.get(norm(name))
        if not hit:                                 # 同一 topic 的多条在这一行合成一个包（先到者定名）
            by_norm[norm(name)] = name
        return dict(repo=hit or name, kind="new", dest_skill="__new__", action="move",
                    collided=bool(hit), axis=axis, topic=topic,
                    personal=bool(dest.get("personal")), boundary=boundary)

    return reject(f"dest.kind {kind!r} 不认识（只能是 \"existing\" 或 \"new\"）")


def cmd_merge(args) -> int:
    out = pathlib.Path(args.dir).expanduser()
    judge_input = json.loads((out / "judge-input.json").read_text(encoding="utf-8"))
    packs = {p["repo"]: p for p in json.loads((out / "packs.json").read_text(encoding="utf-8"))}
    routable = {k: v for k, v in packs.items() if not v.get("empty")}
    by_norm: dict = {}
    for name in packs:                              # uniquification: same topic -> the directory already here
        by_norm.setdefault(norm(name), name)

    verdicts, bad = {}, []
    paths = [pathlib.Path(p).expanduser() for p in args.verdicts] if args.verdicts else sorted(out.glob("verdicts*.jsonl"))
    for f in paths:
        for ln in f.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                v = json.loads(ln)
            except json.JSONDecodeError:
                bad.append(f"{f.name}: not JSON: {ln[:60]}")
                continue
            vid = str(v.get("id", "")).strip()
            if not vid:
                bad.append(f"{f.name}: verdict without id: {ln[:60]}")
            elif vid in verdicts:
                bad.append(f"{f.name}: duplicate verdict for {vid}")
            else:
                verdicts[vid] = v
    known = {r["id"] for r in judge_input}
    bad += [f"{vid}: id is not in judge-input.json (ids are a scan artifact — re-run scan, keep the pair)"
            for vid in verdicts if vid not in known]

    resolved, groups = [], {}
    for r in judge_input:
        v = verdicts.get(r["id"], {})
        if not v:
            groups.setdefault(UNJUDGED, []).append((r, {}, "unjudged", {}))
            continue
        res = _resolve(r, v, packs, by_norm, bad)
        if res is None:                             # rejected: recorded in `bad`, never silently dropped
            continue
        resolved.append(dict(r, **{k: res[k] for k in ("repo", "kind", "dest_skill", "action",
                                                       "collided", "axis", "topic", "personal", "boundary")},
                             why=str(v.get("why") or ""), evidence=str(v.get("evidence") or ""),
                             confidence=v.get("confidence", None), source=str(v.get("source") or "agent")))
        groups.setdefault(res["repo"], []).append((r, v, res["action"], res))
    missing = [r["id"] for r in judge_input if r["id"] not in verdicts]

    info: dict = {}
    for repo, items in groups.items():
        if repo == UNJUDGED:
            continue
        new_items = [t for t in items if t[3].get("kind") == "new"]
        info[repo] = dict(
            on_disk=repo in packs, is_new_pack=repo not in packs, from_new_verdicts=bool(new_items),
            collided=sum(1 for t in items if t[3].get("collided")),
            axis=new_items[0][3]["axis"] if new_items else "",
            topic=new_items[0][3]["topic"] if new_items else "",
            boundary=" / ".join(sorted({t[3]["boundary"] for t in new_items if t[3].get("boundary")})),
            personal=bool(new_items) and len(items) == 1 and all(t[3].get("personal") for t in new_items),
            routable=repo in routable)

    lines = ["# Sweep plan", "",
             f"profile `{args.profile}` · candidates {len(judge_input)} · judged {len(verdicts)}"
             f" · unjudged {len(missing)} · resolved {len(resolved)}", ""]
    new_packs = sorted(r for r, i in info.items() if i["is_new_pack"])
    if new_packs:
        lines += ["## 拟新建的包（`gh repo create <owner>/<name> --private`，只在有人在的会话里做）", ""]
        for repo in new_packs:
            i = info[repo]
            lines.append(f"- `{repo}` · 轴 {i['axis']} · {len(groups[repo])} 条 · boundary：{i['boundary']}"
                         + (" · **私人仓库**（personal 且只 1 条）" if i["personal"] else ""))
        lines.append("")
    reused = sorted(r for r, i in info.items() if i["from_new_verdicts"] and i["on_disk"])
    if reused:
        lines += ["## 判官判了新包、但归一化后撞上已有目录 → 复用该仓库", ""]
        lines += [f"- `{r}`：{info[r]['collided']} 条落在它上面" for r in reused] + [""]

    for dest in sorted(groups, key=lambda d: (d == UNJUDGED, info.get(d, {}).get("is_new_pack", False), d)):
        if dest == UNJUDGED:
            head, meta = "未判定（= 拒收，不生成 plan 交付）", []
        elif info[dest]["is_new_pack"]:
            head, meta = f"新包 {dest}", [f"轴上 {info[dest]['axis']} · topic `{info[dest]['topic']}`"
                                          f" · boundary {info[dest]['boundary']}"]
        else:
            pk = packs[dest]
            head = dest
            meta = [f"clone `{pk['path']}` · id `{pk['identifier'] or '无远端'}` · branch `{pk['branch']}`"
                    f" · 已装类目 `{', '.join(pk['categories']) or '无证据'}`"
                    f"{'' if not pk['empty'] else ' · ⚠️ 空壳（无 SKILL.md）'}"
                    f"{'' if dest in routable else ' · ⚠️ 没有远端，装不回来'}"]
        lines += [f"## {head}", ""] + meta + ["",
                  "| id | skill | 落点技能 | 动作 | 依据 | 判据原句 | 置信 |", "|---|---|---|---|---|---|---|"]
        for r, v, action, res in sorted(groups[dest], key=lambda t: int(t[0]["id"][1:])):
            lines.append(f"| {r['id']} | `{r['skill']}` | {res.get('dest_skill') or '—'} | {action} | "
                         f"{str(v.get('why') or '').replace('|', '/')[:80]} | "
                         f"{str(v.get('evidence') or '').replace('|', '/')[:70]} | {v.get('confidence', '—')} |")
        lines.append("")
    (out / "resolved.json").write_text(json.dumps(resolved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Phase 7 helper: the reinstall commands, from lock evidence, printed for approval — never executed here.
    installs, updates, touched = [], [], []
    for dest, items in groups.items():
        if dest == UNJUDGED:
            continue
        if info[dest]["is_new_pack"]:
            installs.append(f"# {dest}: 新包，先 gh repo create + 写技能 + push，再 "
                            f"hermes --profile {args.profile} skills install \"<owner>/{dest}/skills/<名>\" -y")
            continue
        pk = packs[dest]                           # not a new pack => the directory is on disk
        if pk["empty"]:
            installs.append(f"# {dest}: 空壳落点（无 SKILL.md），写入后 MANUAL 安装（远端标识符："
                            f"{pk['identifier'] or '无'}）")
            continue
        cat = (pk["categories"] or ["<category>"])[0]
        touched.append(dest)
        for r, v, action, res in sorted(items, key=lambda t: int(t[0]["id"][1:])):
            target = res.get("dest_skill") or ""
            if action == "merge" and target and not target.startswith("__"):
                updates.append(f"hermes --profile {args.profile} skills update {target}   # 承接 {r['skill']} 的内容")
                continue
            name = r["skill"]
            if name in pk["installed"]:
                updates.append(f"hermes --profile {args.profile} skills update {name}   # 已在装，改动经 update 到达")
            elif pk["identifier"]:
                installs.append(f'hermes --profile {args.profile} skills install '
                                f'"{pk["identifier"]}/skills/{name}" --category {cat} -y')
            else:
                installs.append(f"# {r['skill']}: clone `{dest}` 无远端，落进包后 MANUAL 安装（无远端没有三段式标识符）")
        for name in sorted(pk["installed"]):
            updates.append(f"hermes --profile {args.profile} skills update {name}   # 本包既有成员（整包重装）")
    cmds = ["#!/bin/sh", f"# reinstall the affected packs into {args.profile!r}",
            "# 顺序：先 install 新成员，再 update 改动过的（update 对未装的名字无效，install 对新名字才是唯一入口）",
            ""] + sorted(set(installs)) + [""] + sorted(set(updates)) + [""]
    (out / "install-cmds.sh").write_text("\n".join(cmds) + "\n", encoding="utf-8")

    if bad:                                        # reject BEFORE emitting a plan nobody should consume
        die(4, f"{len(bad)} malformed verdict(s):\n  " + "\n  ".join(bad[:10]))
    if missing:
        die(4, f"coverage {len(verdicts)}/{len(judge_input)} — unjudged: "
               f"{', '.join(missing[:10])}{' …' if len(missing) > 10 else ''}")

    (out / "plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[sweep-plan] plan={out / 'plan.md'} install_cmds={out / 'install-cmds.sh'}"
          f" resolved={out / 'resolved.json'} packs_touched={len(touched)} "
          f"({', '.join(sorted(touched)) or 'none'})")
    print(f"[sweep-plan] 新包 {len(new_packs)} 个（复用已有目录 {len(reused)} 个）："
          f"{', '.join(new_packs) or 'none'}")
    for dest in sorted(groups, key=lambda d: -len(groups[d])):
        tag = (" → 新包" if info.get(dest, {}).get("is_new_pack")
               else (" → 复用" if info.get(dest, {}).get("from_new_verdicts") else ""))
        print(f"[sweep-plan]   {dest}: {len(groups[dest])} 条{tag}")
    return 0


def self_test() -> int:
    """Throwaway tree: the three kinds must classify, .archive skipped, merge must refuse a gap."""
    import tempfile
    global HERMES_HOME
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="sweep-selftest-"))
    sk = tmp / "skills"
    for cat, name in (("cat", "hubskill"), ("cat", "bundledskill"), ("cat", "localskill"),
                      ("cat/sub", "localskill2"), (".archive", "oldskill"), ("", "rootskill")):
        d = sk / cat / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: d-{name}\n---\n# body of {name}\n",
                                    encoding="utf-8")
    (sk / ".hub").mkdir()
    (sk / ".hub" / "lock.json").write_text(json.dumps({"installed": {"hubskill": {
        "identifier": "skills-sh/flmaximwang/AgentSkill-UsingFake/skills/hubskill",
        "install_path": "cat/hubskill"}}}), encoding="utf-8")
    (sk / ".bundled_manifest").write_text("bundledskill:abc\n", encoding="utf-8")
    packs = tmp / "packs"
    (packs / "AgentSkill-UsingFake" / "skills" / "hubskill").mkdir(parents=True)
    (packs / "AgentSkill-UsingFake" / "skills" / "hubskill" / "SKILL.md").write_text(
        "---\nname: hubskill\ndescription: fake\n---\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(packs / "AgentSkill-UsingFake")], check=True)
    subprocess.run(["git", "-C", str(packs / "AgentSkill-UsingFake"), "remote", "add", "origin",
                    "git@github.com:flmaximwang/AgentSkill-UsingFake.git"], check=True)
    (packs / "AgentSkill-Empty").mkdir()          # a placeholder dir IS a legal destination in v2
    subprocess.run(["git", "init", "-q", str(packs / "AgentSkill-Empty")], check=True)
    # a linked worktree of another clone: its name looks like a pack but `.git` is a file, not a directory
    (packs / "AgentSkill-UsingHermes.wt").mkdir()
    (packs / "AgentSkill-UsingHermes.wt" / ".git").write_text("gitdir: /tmp/nope/.git/worktrees/wt\n")
    (packs / "AgentSkill-UsingHermes.wt" / "skills" / "x").mkdir(parents=True)
    (packs / "AgentSkill-UsingHermes.wt" / "skills" / "x" / "SKILL.md").write_text(
        "---\nname: x\ndescription: wt\n---\n", encoding="utf-8")

    real = HERMES_HOME
    HERMES_HOME = tmp
    try:
        assert profile_root("default") == tmp
        assert cmd_scan(argparse.Namespace(profile="default", packs_root=str(packs), out=str(tmp / "out"),
                                          parser_script="", repo_stem="")) == 0
        rows = [ln.split("\t") for ln in (tmp / "out" / "inventory.tsv").read_text().splitlines()[1:]]
        kinds = {r[2]: r[0] for r in rows}
        assert kinds == {"hubskill": "hub", "bundledskill": "bundled", "localskill": "local",
                         "localskill2": "local", "rootskill": "local"}, kinds
        # 没有类目层的 local skill 必须被标出来（用户要求这种形状不许存在）
        assert {r[2]: r[3] for r in rows} == {"hubskill": "false", "bundledskill": "false",
                                             "localskill": "false", "localskill2": "false",
                                             "rootskill": "true"}
        ji = json.loads((tmp / "out" / "judge-input.json").read_text())
        assert [r["id"] for r in ji] == ["P1", "P2", "P3"], ji
        assert next(r for r in ji if r["skill"] == "rootskill")["no_category"] is True
        assert {r["skill"] for r in ji} == {"rootskill", "localskill", "localskill2"}
        # v2: 判官拿到的是路径与正文，不是只给 name+desc（否则就是用户驳回的偷懒判法）
        assert all(r["skill_md"].endswith("/SKILL.md") and pathlib.Path(r["skill_md"]).is_file() for r in ji), ji
        assert all(r["body_bytes"] > 0 and r["body_lines"] >= 4 for r in ji), ji
        bodies = json.loads((tmp / "out" / "judge-input-bodies.json").read_text())
        assert [b["id"] for b in bodies] == ["P1", "P2", "P3"]
        assert all(f"body of {b['skill']}" in b["body"] for b in bodies), bodies
        asp = json.loads((tmp / "out" / "answer-space.json").read_text())
        assert sorted(asp["dirs"]) == ["AgentSkill-Empty", "AgentSkill-UsingFake"], asp
        assert asp["tool_dirs"] == ["AgentSkill-UsingFake"] and asp["topic_dirs"] == ["AgentSkill-Empty"], asp
        assert asp["routable"] == ["AgentSkill-UsingFake"], asp
        # 别的 clone 的 worktree（`.git` 是文件）名字再像包也不算落点
        assert "AgentSkill-UsingHermes.wt" not in asp["dirs"], asp["dirs"]
        assert not any("wt" in d for d in asp["dirs"]), asp["dirs"]
        pk = [p for p in json.loads((tmp / "out" / "packs.json").read_text())
              if p["repo"] == "AgentSkill-UsingFake"][0]
        assert pk["installed"] == {"hubskill": "cat/hubskill"} and pk["categories"] == ["cat"], pk
        assert [p["empty"] for p in json.loads((tmp / "out" / "packs.json").read_text())
                if p["repo"] == "AgentSkill-Empty"] == [True]      # a no-SKILL.md repo is not routable
        assert pk["identifier"] == "flmaximwang/AgentSkill-UsingFake", pk["identifier"]

        def merge(*verdicts, code=0):
            """One JSONL per verdict; return (plan, cmds) — both must be absent when the run was rejected."""
            for p in (tmp / "out").glob("verdicts*.jsonl"):
                p.unlink()
            for f in ("plan.md", "install-cmds.sh"):
                (tmp / "out" / f).unlink(missing_ok=True)
            for i, v in enumerate(verdicts):
                (tmp / "out" / f"verdicts-task-{i+1}.jsonl").write_text(json.dumps(v) + "\n", encoding="utf-8")
            try:
                rc = cmd_merge(argparse.Namespace(dir=str(tmp / "out"), profile="default", verdicts=[]))
            except SystemExit as e:
                rc = e.code
            assert rc == code, (rc, code, verdicts)
            if code != 0:               # 拒收时连 plan 都不该落盘（别人会照着 plan 动手）
                assert not (tmp / "out" / "plan.md").exists(), "rejected verdicts must not emit a plan"
            return ((tmp / "out" / "plan.md").read_text() if (tmp / "out" / "plan.md").is_file() else "",
                    (tmp / "out" / "install-cmds.sh").read_text()
                    if (tmp / "out" / "install-cmds.sh").is_file() else "")

        ok1 = {"id": "P1", "dest": {"kind": "existing", "repo": "AgentSkill-UsingFake", "action": "move"},
               "why": "w", "evidence": "e"}
        ok2 = {"id": "P2", "dest": {"kind": "existing", "repo": "AgentSkill-Empty", "action": "move"},
               "why": "w", "evidence": "e"}
        ok3 = {"id": "P3", "dest": {"kind": "existing", "repo": "AgentSkill-UsingFake", "dest_skill": "hubskill",
                                    "action": "merge"}, "why": "w", "evidence": "e"}

        merge(ok1, code=4)                                          # coverage gap must fail, not go quiet
        merge(dict(ok1, id="P9"), code=4)                           # id that is not in the frozen input
        merge(dict(ok1, dest="__stay_local__"), ok2, ok3, code=4)   # v2 废除 stay local（字符串形态）
        merge(dict(ok1, dest={"kind": "existing", "repo": STAY_LOCAL}), ok2, ok3, code=4)
        merge(dict(ok1, dest={"kind": "existing", "repo": "AgentSkill-Nope"}), ok2, ok3, code=4)
        merge(dict(ok1, dest={"kind": "existing", "repo": "AgentSkill-UsingFake",
                              "dest_skill": "ghost-skill", "action": "merge"}), ok2, ok3, code=4)
        merge(dict(ok1, dest={"kind": "new", "axis": "tool", "topic": "Fake"}), ok2, ok3, code=4)  # no boundary
        merge(dict(ok1, dest={"kind": "new", "axis": "subject", "topic": "Fake",
                              "boundary": "b"}), ok2, ok3, code=4)  # axis 只能 tool|topic
        merge(ok1, ok2, ok3, code=0)                                # the happy path must actually produce a plan
        plan, cmds = merge(
            {"id": "P1", "dest": {"kind": "new", "axis": "tool", "topic": "Fake",
                                  "boundary": "不吃 git 历史"}, "why": "w", "evidence": "e"},
            {"id": "P2", "dest": {"kind": "new", "axis": "topic", "topic": "RunningLocalBatches",
                                  "boundary": "不吃长驻服务"}, "why": "w", "evidence": "e"},
            {"id": "P3", "dest": {"kind": "new", "axis": "topic", "topic": "running local batches",
                                  "boundary": "不吃长驻服务"}, "why": "w", "evidence": "e"}, code=0)
        # new.topic 归一化后撞上已有目录名 → 复用那个仓库，不建孪生目录
        assert "复用该仓库" in plan and "`AgentSkill-UsingFake`" in plan, plan
        # 同一 topic 的多条（"RunningLocalBatches" vs "running local batches"）必须合成一个包
        assert plan.count("## 新包 ") == 1, plan
        assert "## 新包 AgentSkill-RunningLocalBatches" in plan, plan
        assert "- `AgentSkill-RunningLocalBatches` · 轴 topic · 2 条" in plan, plan
        assert 'skills install "flmaximwang/AgentSkill-UsingFake/skills/rootskill" --category cat -y' in cmds, cmds
        assert "# AgentSkill-RunningLocalBatches: 新包" in cmds, cmds
        assert "AgentSkill-Empty" not in cmds, cmds     # 空壳落点不许生成 install 命令
        # 顺序类不变量：install 段必须整体排在 update 段之前（update 对未装的名字无效）
        assert cmds.index("skills install") < cmds.index("skills update") if "skills update" in cmds else True
        resolved = json.loads((tmp / "out" / "resolved.json").read_text())
        assert [r["repo"] for r in resolved] == ["AgentSkill-UsingFake", "AgentSkill-RunningLocalBatches",
                                                "AgentSkill-RunningLocalBatches"], resolved
        assert [r["collided"] for r in resolved] == [True, False, True], resolved

        # dedupe: local 不在任何包里是**硬错误**（v2 判据 local=0），不是一句可以忽略的脚注
        def dedupe(**over):
            a = dict(profile="default", packs_root=str(packs), backup="", dry_run=True,
                     fix_no_category=False, allow_not_in_pack=False)
            a.update(over)
            try:
                return cmd_dedupe(argparse.Namespace(**a))
            except SystemExit as e:
                return e.code

        assert dedupe() == 5, "local skills outside every pack must fail the run, not be a footnote"
        assert dedupe(allow_not_in_pack=True) == 0, "the explicit opt-out must still work"
    finally:
        HERMES_HOME = real
    print("[sweep-plan] self-test OK")
    return 0


def _suggest_category(name: str, local_categories: set) -> str:
    """Suggest an EXISTING local category for a no-category skill, by name keywords.

    Only ever returns a category that already exists in this profile's own skills tree —
    the rule is "move it into an existing category; if none fits, report that a new one is
    needed", never invent a category and never dump it wherever.
    """
    name_lower = name.lower()
    rules = [
        (["hermes", "skill", "profile", "cron", "gateway", "memory", "plugin", "routing", "blind"], "hermes"),
        (["git", "github", "dolt", "annex"], "git"),
        (["saxs", "atsas", "raw", "bioxtas"], "saxs"),
        (["obsidian", "note", "vault", "moc", "clc", "relayer", "restructure", "classification"], "obsidian"),
        (["zotero", "paper", "literature", "reference", "evidence", "research", "prove", "verify", "claim"], "research"),
        (["dolt", "sql", "database", "ledger"], "dolt"),
        (["macos", "brew", "gui", "app", "network-diagnosis", "install-macos"], "macos"),
        (["python", "pytest", "test", "debug", "numeric", "validate"], "software-development"),
        (["image", "comfyui", "figma", "draw", "sketch", "ascii"], "creative"),
        (["pdf", "docx", "xlsx", "office", "ocr"], "office"),
        (["nas", "synology", "rsync", "backup"], "infrastructure"),
        (["protein", "plasmid", "lab", "experiment"], "lab"),
        (["invest", "quant", "trading", "finance", "stock"], "investment"),
        (["travel", "hotel", "flight", "trip"], "travel"),
        (["mcp", "server", "integration"], "mcp-server-integration"),
        (["cli", "tool", "service", "terminal", "log"], "terminal"),
        (["dedupe", "duplicate", "folder"], "file-management"),
        (["explain", "mechanism"], "agent-tooling"),
        (["macos", "gui", "app", "install"], "code"),
        (["macos", "network", "diagnosis"], "code"),
        (["docker", "container", "devops", "ci"], "devops"),
        (["ml", "model", "llm", "huggingface", "vllm"], "mlops"),
        (["web", "scrape", "crawl"], "web"),
        (["media", "video", "audio", "music"], "media"),
        (["apple", "calendar", "reminder", "shortcut"], "apple"),
        (["social", "reddit", "twitter", "discord"], "social-media"),
    ]
    for keywords, cat in rules:
        if any(kw in name_lower for kw in keywords) and cat in local_categories:
            return cat
    # word-overlap fallback, still restricted to existing local categories
    for cat in sorted(local_categories):
        if cat.replace("-", " ") in name_lower:
            return cat
    return ""


def cmd_dedupe(args) -> int:
    """S9: remove profile-local skills that already exist in packs.

    For each profile, find local skills whose name matches a skill in any AgentSkill pack.
    - SKILL.md identical  → delete local (pack is source of truth)
    - SKILL.md different  → check if local has path fixes (old profile names) that pack lacks;
                           if so, restore local SKILL.md to pack first, then delete local
    - SKILL.md different, no path fixes → delete local (pack is newer)

    Reports: total local, identical deleted, path-fixed restored+deleted, not-in-pack stayed.
    """
    import filecmp
    import shutil

    packs_root = pathlib.Path(args.packs_root).expanduser()
    profiles_dir = HERMES_HOME / "profiles"

    # Build pack skill index: name -> [(pack_name, abs_path_to_skill_dir)]
    pack_index: dict = {}
    for pack_dir in sorted(packs_root.glob("AgentSkill-*")):
        skills_dir = pack_dir / "skills"
        if not skills_dir.is_dir():
            continue
        for md in skills_dir.rglob("SKILL.md"):
            pack_index.setdefault(md.parent.name, []).append((pack_dir.name, md.parent))

    if not pack_index:
        die(2, f"no AgentSkill-* packs found under {packs_root}")

    # Old profile names that indicate a path fix
    OLD_NAMES = {"artist","game-research","job-hunter","obsidian-maintenance","personal-accountant",
                 "plan-weave","plasmid-engineer","profile-development","protein-design","quant-investor",
                 "rdm-assistance","secretary","software-development","travel-guider","value-investor"}

    def has_old_refs(text: str) -> bool:
        return any(f"profiles/{n}" in text for n in OLD_NAMES)

    stats = dict(total=0, identical=0, path_fixed=0, newer_pack=0, not_in_pack=0, hub_installed=0,
                 no_category=0, no_category_moved=0)
    deleted_dirs = []
    moved_dirs = []
    stray: list = []          # local skills that no pack contains — v2 treats these as an ERROR, not a footnote

    # Candidate categories for no-category placement = each profile's OWN existing categories.
    # (The rule is "move it into an existing local category; if none fits, report that a new
    # one is needed" — never invent a category and never borrow the pack's layout.)

    if args.profile == "all":
        profiles = [HERMES_HOME] + sorted(profiles_dir.glob("*/"))
    elif args.profile == "default":
        profiles = [HERMES_HOME]
    else:
        profiles = [HERMES_HOME / "profiles" / args.profile]

    for prof_root in profiles:
        skills_dir = prof_root / "skills"
        if not skills_dir.is_dir():
            continue
        prof_name = prof_root.name if prof_root != HERMES_HOME else "default"
        lock = read_lock(prof_root)
        bundled = read_bundled(prof_root)

        # This profile's own existing categories — the only legal destinations for a no-category skill
        local_categories = {md.relative_to(skills_dir).parts[0]
                            for md in walk_skill_dirs(skills_dir)
                            if len(md.relative_to(skills_dir).parts) > 2}

        for md in walk_skill_dirs(skills_dir):
            name = md.parent.name
            stats["total"] += 1
            # hub-installed or bundled skills have a lifecycle (lock entry / manifest) — never dedupe them
            if name in lock or name in bundled:
                stats["hub_installed"] += 1
                continue

            rel = md.relative_to(skills_dir)
            no_cat = len(rel.parts) == 2

            # Fix no-category skills: move skills/<name>/ into skills/<existing-category>/
            if no_cat and args.fix_no_category:
                stats["no_category"] += 1
                suggested = _suggest_category(name, local_categories)
                if suggested:
                    src_dir = md.parent
                    dst_dir = skills_dir / suggested / name
                    if not dst_dir.exists():
                        dst_dir.parent.mkdir(parents=True, exist_ok=True)
                        if args.backup:
                            bak = pathlib.Path(args.backup) / prof_name / "no-category" / name
                            if not bak.exists():
                                bak.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copytree(str(src_dir), str(bak))
                        if not args.dry_run:
                            shutil.move(str(src_dir), str(dst_dir))
                        moved_dirs.append((prof_name, name, suggested))
                        stats["no_category_moved"] += 1
                    else:
                        print(f"  ⚠ {prof_name}/{name}: target {suggested}/{name} already exists, skip")
                else:
                    print(f"  ⚠ {prof_name}/{name}: 没有匹配的现有类目，需要新类目（不硬塞）")
                continue

            if name not in pack_index:
                stats["not_in_pack"] += 1
                stray.append(f"{prof_name}/{(md.relative_to(skills_dir).parent)}")
                continue

            # Find the pack that has this skill
            pack_name, pack_skill_dir = pack_index[name][0]
            pack_md = pack_skill_dir / "SKILL.md"
            if not pack_md.is_file():
                stats["not_in_pack"] += 1
                continue

            local_text = md.read_text(encoding="utf-8", errors="replace")
            pack_text = pack_md.read_text(encoding="utf-8", errors="replace")

            if filecmp.cmp(str(md), str(pack_md), shallow=False):
                stats["identical"] += 1
                # Backup then delete
                bak = pathlib.Path(args.backup) / prof_name / md.parent.parent.name / name
                if args.backup and not bak.exists():
                    bak.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(str(md.parent), str(bak))
                if not args.dry_run:
                    shutil.rmtree(str(md.parent))
                deleted_dirs.append((prof_name, name, "identical"))
            elif has_old_refs(local_text) and not has_old_refs(pack_text):
                # Local has path fixes the pack lacks → restore to pack, then delete
                stats["path_fixed"] += 1
                if not args.dry_run:
                    # Backup pack's old version
                    if args.backup:
                        bak = pathlib.Path(args.backup) / "pack-backup" / f"{pack_name}-{name}-SKILL.md"
                        bak.parent.mkdir(parents=True, exist_ok=True)
                        if not bak.exists():
                            shutil.copy2(str(pack_md), str(bak))
                    # Restore local to pack
                    shutil.copy2(str(md), str(pack_md))
                    # Delete local
                    shutil.rmtree(str(md.parent))
                deleted_dirs.append((prof_name, name, f"path-fixed → {pack_name}"))
            else:
                # Pack is newer → delete local
                stats["newer_pack"] += 1
                if args.backup:
                    bak = pathlib.Path(args.backup) / prof_name / md.parent.parent.name / name
                    if not bak.exists():
                        bak.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(str(md.parent), str(bak))
                if not args.dry_run:
                    shutil.rmtree(str(md.parent))
                deleted_dirs.append((prof_name, name, "pack-newer"))

    print(f"[dedupe] total={stats['total']} identical={stats['identical']} "
          f"path_fixed={stats['path_fixed']} newer_pack={stats['newer_pack']} "
          f"not_in_pack={stats['not_in_pack']} hub_installed={stats['hub_installed']} "
          f"no_category={stats['no_category']} no_category_moved={stats['no_category_moved']}")
    if deleted_dirs:
        print(f"[dedupe] deleted {len(deleted_dirs)} local copies")
        for prof, name, reason in deleted_dirs[:10]:
            print(f"  {prof:24s} {name:30s} {reason}")
        if len(deleted_dirs) > 10:
            print(f"  ... 还有 {len(deleted_dirs)-10} 个")
    if moved_dirs:
        print(f"[dedupe] moved {len(moved_dirs)} no-category skills into categories")
        for prof, name, cat in moved_dirs[:10]:
            print(f"  {prof:24s} {name:30s} → {cat}/")
        if len(moved_dirs) > 10:
            print(f"  ... 还有 {len(moved_dirs)-10} 个")
    if stray:
        print(f"[dedupe] ⚠️ {len(stray)} 个 local skill 不在任何包里（v2 判据：local 必须为 0）")
        for s in stray[:20]:
            print(f"  {s}")
        if len(stray) > 20:
            print(f"  ... 还有 {len(stray)-20} 个")
        if not args.allow_not_in_pack:
            die(5, f"{len(stray)} 个 local skill 没有仓库归属 —— 判据是 local 必须为 0（用户 2026-10-10）。"
                   "先 `scan` + 判官 + `merge` 给它们找落点；确实要带着这批尾巴收尾时加 --allow-not-in-pack")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="enumerate candidates + packs, freeze the judge input")
    s.add_argument("--profile", default="default", help="default = $HERMES_HOME, else profiles/<name>")
    s.add_argument("--packs-root", default="~/Documents/AgentSkill", help="where the AgentSkill-* checkouts live")
    s.add_argument("--out", required=True, help="scratch dir: inventory.tsv / judge-input.json / packs.json")
    s.add_argument("--parser-script", default="", help="override the sibling skill-index.py path")
    s.add_argument("--repo-stem", default="", help=argparse.SUPPRESS)   # accepted, unused: kept for CLI stability
    s.set_defaults(func=cmd_scan)
    m = sub.add_parser("merge", help="judge verdicts (JSONL) -> plan.md + install-cmds.sh")
    m.add_argument("--dir", required=True, help="the --out dir from scan")
    m.add_argument("--profile", default="default")
    m.add_argument("--verdicts", action="append", default=[],
                   help="verdict JSONL file (repeatable); default = <dir>/verdicts*.jsonl")
    m.set_defaults(func=cmd_merge)
    d = sub.add_parser("dedupe", help="S9: remove profile-local skills that already exist in packs")
    d.add_argument("--profile", default="all", help="default = all profiles; 'default' = only default")
    d.add_argument("--packs-root", default="~/Documents/AgentSkill")
    d.add_argument("--backup", default="~/.hermes/backups/dream-dedupe", help="backup dir before deletion")
    d.add_argument("--dry-run", action="store_true", help="report only, no deletion")
    d.add_argument("--fix-no-category", action="store_true",
                   help="move skills/<name>/ into skills/<category>/ for no-category local skills")
    d.add_argument("--allow-not-in-pack", action="store_true",
                   help="accept local skills that no pack contains (v2 default: that is exit 5)")
    d.set_defaults(func=cmd_dedupe)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
