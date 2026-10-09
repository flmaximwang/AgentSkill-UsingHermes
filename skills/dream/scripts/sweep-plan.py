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

Exit codes: 0 ok | 2 no candidates, no packs, or missing sibling | 3 profile not found | 4 verdict coverage < 100%
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
                         no_category=no_cat, dir=str(rel.parent),
                         desc=" ".join(str(fm.get("description") or "").split()), bytes=md.stat().st_size))
    rows.sort(key=lambda r: (r["kind"] != "local", r["category"], r["name"]))
    local = [r for r in rows if r["kind"] == "local"]
    if not local:
        die(2, f"no profile-local skills in {root} — nothing to recruit")

    packs = []
    for pack in sorted(pathlib.Path(args.packs_root).expanduser().glob("AgentSkill-*")):
        pk_skills_dir = pack / "skills"
        if not (pack / ".git").exists() and not pk_skills_dir.is_dir():
            continue
        remote = git(pack, "remote", "get-url", "origin")
        installed = {n: str(v.get("install_path", "")) for n, v in lock.items()
                     if pack.name in str(v.get("identifier", "")) or pack.name in str(v.get("metadata", {}).get("repo_url", ""))}
        skills = sorted(md.parent.name for md in pk_skills_dir.glob("*/SKILL.md")) if pk_skills_dir.is_dir() else []
        packs.append(dict(repo=pack.name, path=str(pack), identifier=identifier(remote), remote=remote,
                          branch=git(pack, "branch", "--show-current"), skills=skills,
                          # An `AgentSkill-*` directory with no SKILL.md anywhere is a placeholder: it can
                          # never be a routing destination (measured 2026-10-09: 262 of 285 on this machine).
                          empty=not skills and not (pack / "SKILL.md").is_file(),
                          installed=installed,
                          categories=sorted({p.split("/")[0] for p in installed.values() if p})))
    if not packs:
        die(2, f"no AgentSkill-* checkout under {args.packs_root}")
    routable = [p for p in packs if not p["empty"]]
    if not routable:
        die(2, f"every AgentSkill-* under {args.packs_root} is a placeholder (no SKILL.md) — "
               "there is no destination to route into")

    out = pathlib.Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    (out / "inventory.tsv").write_text(
        "kind\tcategory\tname\tno_category\tdir\tdesc\n" + "".join(
            f"{r['kind']}\t{r['category']}\t{r['name']}\t{str(r['no_category']).lower()}\t{r['dir']}\t{r['desc'][:200]}\n"
            for r in rows), encoding="utf-8")
    # Frozen judge input: one P<k> per candidate, name + description only, script-generated so that no
    # hand transcription can drift from what the judges were actually asked (the pack's own judge lesson).
    judge_input = [dict(id=f"P{i}", skill=r["name"], category=r["category"], dir=r["dir"],
                        no_category=r["no_category"], description=r["desc"])
                   for i, r in enumerate(local, 1)]
    (out / "judge-input.json").write_text(json.dumps(judge_input, ensure_ascii=False, indent=2) + "\n",
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

    counts = {k: sum(1 for r in rows if r["kind"] == k) for k in ("local", "hub", "bundled")}
    idx_chars = (out / "pack-index.txt").stat().st_size
    print(f"[sweep-plan] profile={root} skills={len(rows)} local={counts['local']} "
          f"hub={counts['hub']} bundled={counts['bundled']}")
    print(f"[sweep-plan] packs={len(packs)} routable={len(routable)} placeholder={len(packs) - len(routable)} "
          f"pack_skills={sum(len(p['skills']) for p in routable)} pack_index_est_tokens~{idx_chars // 2}")
    n_nocat = sum(1 for r in local if r["no_category"])
    print(f"[sweep-plan] no_category={n_nocat}（local skill 直接躺在 skills/ 下，没有类目层——本批必须一并补齐）")
    print(f"[sweep-plan] candidates={len(local)} judge_input={out / 'judge-input.json'} "
          f"({(out / 'judge-input.json').stat().st_size} B) parser={parser_path}")
    print(f"[sweep-plan] next: judge every P<k> (JEV, else classifier children) -> {out}/verdicts*.jsonl, then "
          f"`merge --dir {out} --profile {args.profile}`")
    return 0


def cmd_merge(args) -> int:
    out = pathlib.Path(args.dir).expanduser()
    judge_input = json.loads((out / "judge-input.json").read_text(encoding="utf-8"))
    packs = {p["repo"]: p for p in json.loads((out / "packs.json").read_text(encoding="utf-8"))}
    routable = {k: v for k, v in packs.items() if not v.get("empty")}
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

    groups: dict = {}
    for r in judge_input:
        v = verdicts.get(r["id"], {})
        dest = str(v.get("dest_pack") or UNJUDGED)
        action = str(v.get("action") or ("unjudged" if dest == UNJUDGED else "?"))
        if dest not in (STAY_LOCAL, UNJUDGED) and dest not in routable:
            bad.append(f"{r['id']}: dest_pack {dest!r} is not a routable local pack "
                       f"({'placeholder, no SKILL.md' if dest in packs else 'not on disk'})")
        groups.setdefault(dest, []).append((r, v, action))
    missing = [r["id"] for r in judge_input if r["id"] not in verdicts]

    lines = ["# Sweep plan", "",
             f"profile `{args.profile}` · candidates {len(judge_input)} · judged {len(verdicts)}"
             f" · unjudged {len(missing)}", ""]
    for dest in sorted(groups, key=lambda d: (d in (STAY_LOCAL, UNJUDGED), d)):
        head = {"__stay_local__": "留本地（不入包）", "__unjudged__": "未判定"}.get(
            dest, dest if dest in routable else f"⚠️ 落点 {dest} 不是可用包")
        lines += [f"## {head}", ""]
        if dest in routable:
            pk = routable[dest]
            lines += [f"clone `{pk['path']}` · id `{pk['identifier'] or '无远端'}` · branch `{pk['branch']}`"
                      f" · 已装类目 `{', '.join(pk['categories']) or '无证据'}`", ""]
        lines += ["| id | skill | 落点技能 | 动作 | 依据 | 置信 |", "|---|---|---|---|---|---|"]
        for r, v, action in sorted(groups[dest], key=lambda t: int(t[0]["id"][1:])):
            dest_skill = str(v.get("dest_skill") or "")
            lines.append(f"| {r['id']} | `{r['skill']}` | {dest_skill or '—'} | {action} | "
                         f"{str(v.get('why') or '').replace('|', '/')[:90]} | {v.get('confidence', '—')} |")
        lines.append("")
    (out / "plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Phase 7 helper: the reinstall commands, from lock evidence, printed for approval — never executed here.
    installs, updates, touched = [], [], []
    for dest, rows in groups.items():
        if dest not in routable:       # stay-local / unjudged / a dest that is not a routable pack
            continue
        pk = routable[dest]
        cat = (pk["categories"] or ["<category>"])[0]
        touched.append(dest)
        for r, v, action in sorted(rows, key=lambda t: int(t[0]["id"][1:])):
            target = str(v.get("dest_skill") or "")
            if action == "merge" and target and not target.startswith("__"):
                updates.append(f"hermes --profile {args.profile} skills update {target}   # 承接 {r['skill']} 的内容")
                continue
            name = target if (action == "rename" and target) else r["skill"]
            if name in pk["installed"]:
                updates.append(f"hermes --profile {args.profile} skills update {name}   # 已在装，改动经 update 到达")
            elif pk["identifier"]:
                installs.append(f'hermes --profile {args.profile} skills install '
                                f'"{pk["identifier"]}/skills/{name}" --category {cat} -y')
            else:
                installs.append(f"# {r['skill']}: clone `{pk['repo']}` 无远端，落进包后 MANUAL 安装（无远端没有三段式标识符）")
        for name in sorted(pk["installed"]):
            updates.append(f"hermes --profile {args.profile} skills update {name}   # 本包既有成员（整包重装）")
    cmds = ["#!/bin/sh", f"# reinstall the affected packs into {args.profile!r}",
            "# 顺序：先 install 新成员，再 update 改动过的（update 对未装的名字无效，install 对新名字才是唯一入口）",
            ""] + sorted(set(installs)) + [""] + sorted(set(updates)) + [""]
    (out / "install-cmds.sh").write_text("\n".join(cmds) + "\n", encoding="utf-8")

    print(f"[sweep-plan] plan={out / 'plan.md'} install_cmds={out / 'install-cmds.sh'}"
          f" packs_touched={len(touched)} ({', '.join(sorted(touched)) or 'none'})")
    for dest in sorted(groups, key=lambda d: -len(groups[d])):
        print(f"[sweep-plan]   {dest}: {len(groups[dest])} 条")
    if bad:
        die(4, f"{len(bad)} malformed verdict(s):\n  " + "\n  ".join(bad[:10]))
    if missing:
        die(4, f"coverage {len(verdicts)}/{len(judge_input)} — unjudged: "
               f"{', '.join(missing[:10])}{' …' if len(missing) > 10 else ''}")
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
        (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: d-{name}\n---\n# body\n", encoding="utf-8")
    (sk / ".hub").mkdir()
    (sk / ".hub" / "lock.json").write_text(json.dumps({"installed": {"hubskill": {
        "identifier": "skills-sh/flmaximwang/AgentSkill-Fake/skills/hubskill",
        "install_path": "cat/hubskill"}}}), encoding="utf-8")
    (sk / ".bundled_manifest").write_text("bundledskill:abc\n", encoding="utf-8")
    packs = tmp / "packs"
    (packs / "AgentSkill-Fake" / "skills" / "hubskill").mkdir(parents=True)
    (packs / "AgentSkill-Fake" / "skills" / "hubskill" / "SKILL.md").write_text(
        "---\nname: hubskill\ndescription: fake\n---\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(packs / "AgentSkill-Fake")], check=True)
    subprocess.run(["git", "-C", str(packs / "AgentSkill-Fake"), "remote", "add", "origin",
                    "git@github.com:flmaximwang/AgentSkill-Fake.git"], check=True)
    (packs / "AgentSkill-Empty").mkdir()          # a placeholder repo must never be a destination
    subprocess.run(["git", "init", "-q", str(packs / "AgentSkill-Empty")], check=True)

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
        pk = [p for p in json.loads((tmp / "out" / "packs.json").read_text()) if p["repo"] == "AgentSkill-Fake"][0]
        assert pk["installed"] == {"hubskill": "cat/hubskill"} and pk["categories"] == ["cat"], pk
        assert [p["empty"] for p in json.loads((tmp / "out" / "packs.json").read_text())
                if p["repo"] == "AgentSkill-Empty"] == [True]      # a no-SKILL.md repo is not routable
        assert pk["identifier"] == "flmaximwang/AgentSkill-Fake", pk["identifier"]

        (tmp / "out" / "verdicts-task-1.jsonl").write_text(json.dumps(
            {"id": "P1", "dest_pack": "AgentSkill-Fake", "dest_skill": "__new__", "action": "move"}) + "\n")
        try:                                     # gap in coverage must be a failure, not a quiet plan
            cmd_merge(argparse.Namespace(dir=str(tmp / "out"), profile="default", verdicts=[]))
            raise AssertionError("merge must refuse incomplete coverage")
        except SystemExit as e:
            assert e.code == 4, e.code
        (tmp / "out" / "verdicts-task-2.jsonl").write_text(json.dumps(
            {"id": "P2", "dest_pack": "AgentSkill-Nope", "action": "move"}) + "\n")
        try:                                     # a verdict naming a non-local pack is malformed
            cmd_merge(argparse.Namespace(dir=str(tmp / "out"), profile="default",
                                         verdicts=[str(tmp / "out" / "verdicts-task-1.jsonl"),
                                                   str(tmp / "out" / "verdicts-task-2.jsonl")]))
            raise AssertionError("non-local dest_pack must be refused")
        except SystemExit as e:
            assert e.code == 4, e.code
        (tmp / "out" / "verdicts-task-3.jsonl").write_text(json.dumps(
            {"id": "P2", "dest_pack": "AgentSkill-Empty", "action": "move"}) + "\n")
        try:                                     # a placeholder pack must not be a destination
            cmd_merge(argparse.Namespace(dir=str(tmp / "out"), profile="default",
                                         verdicts=[str(tmp / "out" / "verdicts-task-1.jsonl"),
                                                   str(tmp / "out" / "verdicts-task-3.jsonl")]))
            raise AssertionError("placeholder dest_pack must be refused")
        except SystemExit as e:
            assert e.code == 4, e.code
        (tmp / "out" / "verdicts-task-9.jsonl").write_text(json.dumps(
            {"id": "P9", "dest_pack": STAY_LOCAL, "action": "stay"}) + "\n")
        try:                                     # an id that is not in the frozen input is malformed
            cmd_merge(argparse.Namespace(dir=str(tmp / "out"), profile="default",
                                         verdicts=[str(tmp / "out" / "verdicts-task-1.jsonl"),
                                                   str(tmp / "out" / "verdicts-task-9.jsonl")]))
            raise AssertionError("unknown id must be refused")
        except SystemExit as e:
            assert e.code == 4, e.code
        (tmp / "out" / "verdicts-task-4.jsonl").write_text(json.dumps(
            {"id": "P2", "dest_pack": STAY_LOCAL, "action": "stay"}) + "\n")
        (tmp / "out" / "verdicts-task-5.jsonl").write_text(json.dumps(
            {"id": "P3", "dest_pack": STAY_LOCAL, "action": "stay"}) + "\n")
        assert cmd_merge(argparse.Namespace(dir=str(tmp / "out"), profile="default",
                                            verdicts=[str(tmp / "out" / "verdicts-task-1.jsonl"),
                                                      str(tmp / "out" / "verdicts-task-4.jsonl"),
                                                      str(tmp / "out" / "verdicts-task-5.jsonl")])) == 0
        assert "留本地" in (tmp / "out" / "plan.md").read_text()
        cmds = (tmp / "out" / "install-cmds.sh").read_text()
        assert "skills install \"flmaximwang/AgentSkill-Fake/skills/rootskill\" --category cat -y" in cmds, cmds
    finally:
        HERMES_HOME = real
    print("[sweep-plan] self-test OK")
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
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
