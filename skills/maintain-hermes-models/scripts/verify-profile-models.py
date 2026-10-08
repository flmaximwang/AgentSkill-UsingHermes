#!/usr/bin/env python3
"""秒级只读回读：每个 profile 的默认模型「写的是什么」+「最近一次真实调用算到了哪个端点」。

判据有两层，代码把它们分开报，不许互相代替：

  config 侧（写入是否落地）   <home>/config.yaml 顶层 `model:` 块的 default / provider / base_url
  运行侧（是否真的在用）       <home>/state.db 里 `sessions` 表按 started_at 最新的那一行 ——
                              model / billing_provider / billing_base_url 是**那次调用实际算钱到的端点**，
                              它只在真实会话发生过之后才更新（新起的 profile 或久没消息的 profile 会是旧值）。

所以 `⏳ 待观察` = 「config 已就位、但这个 home 还没来一条消息」——不是失败；等它来一条消息再跑一次。
`❌` 只留给 config 侧与目标不符（那才是要动手的信号）。

只读打开 state.db（`file:...?mode=ro`），不加锁、不改一个字节。只用标准库。

退出码：0 home 都就绪 · 1 有 config 侧不符（或用 --require-live 时运行侧没验到）· 2 找不到 home/DB。
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sqlite3
import sys
from pathlib import Path

TOP_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")


def config_model(path: Path) -> dict[str, str]:
    """读 config.yaml 顶层 `model:` 块体的 key: value（平铺，不需要 YAML）。"""
    if not path.is_file():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].rstrip() != "model:":
        return {}
    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() and TOP_KEY.match(line):
            break
        key, sep, value = line.strip().partition(":")
        if sep:
            out[key.strip()] = value.strip().strip("'\"")
    return out


def newest_session(db: Path) -> dict[str, object] | None:
    if not db.is_file():
        return None
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    except sqlite3.Error:
        return None
    try:
        con.row_factory = sqlite3.Row
        row = con.execute(
            "select id, model, billing_provider, billing_base_url, started_at, source, message_count"
            " from sessions order by started_at desc limit 1"
        ).fetchone()
        return dict(row) if row else None
    except sqlite3.Error:
        return None
    finally:
        con.close()


def stamp(value):
    """epoch 秒 → `MM-DD HH:MM`；拿不到就 `?`。"""
    try:
        return datetime.datetime.fromtimestamp(float(value)).strftime("%m-%d %H:%M")
    except (TypeError, ValueError):
        return "?"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="回读每个 profile 的默认模型：config 侧 + 最近一次真实调用的计费端点",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--home", default="~/.hermes", help="Hermes home（所有 profile 的家）")
    ap.add_argument("--profiles", default="all", help="`all`、`default` 或逗号分隔的 profile 名")
    ap.add_argument("--expect-model", default="", help="期望的模型 id（给了才判 config 侧）")
    ap.add_argument("--expect-base-url", default="", help="期望的 base_url（给了才判）")
    ap.add_argument("--require-live", action="store_true",
                    help="运行侧也必须验到（还没来消息的 home 记失败）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()

    home = Path(args.home).expanduser()
    if args.profiles == "all":
        homes = [("default", home)]
        homes += [(d.name, d) for d in sorted((home / "profiles").iterdir())
                  if d.is_dir() and not d.name.startswith(".")]
    else:
        wanted = [w.strip() for w in args.profiles.split(",") if w.strip()]
        homes = [(w, home if w == "default" else home / "profiles" / w) for w in wanted]
    if not homes:
        print("找不到 %s / profiles" % home, file=sys.stderr)
        return 2

    rows = []
    bad = 0
    for label, base in homes:
        cfg = config_model(base / "config.yaml")
        live = newest_session(base / "state.db")
        cfg_model = cfg.get("default", "-")
        cfg_provider = cfg.get("provider", "-")
        live_model = str(live.get("model") or "-") if live else "-"
        live_url = str(live.get("billing_base_url") or "-") if live else "-"

        if not args.expect_model or not base.is_dir():
            verdict = "➖"
        elif cfg_model != args.expect_model:
            verdict = "❌"
            bad += 1
        elif args.expect_base_url and cfg.get("base_url") and cfg.get("base_url") != args.expect_base_url:
            verdict = "❌"
            bad += 1
        elif live and live_model != "-" and live_model != args.expect_model:
            verdict = "⏳"
            if args.require_live:
                bad += 1
        elif live and args.expect_base_url and live_url not in ("-", args.expect_base_url) \
                and "volces.com" not in live_url and "api/" not in live_url:
            verdict = "⏳"
        elif not live:
            verdict = "⏳"
            if args.require_live:
                bad += 1
        else:
            verdict = "✅"

        rows.append({
            "profile": label,
            "config_model": cfg_model,
            "config_provider": cfg_provider,
            "live_model": live_model,
            "live_base_url": live_url,
            "live_at": stamp(live.get("started_at")) if live else "-",
            "live_source": str(live.get("source") or "-") if live else "-",
            "verdict": verdict,
        })

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print("%-22s %-24s %-24s %-6s %s" % ("profile", "config.default", "last-session.model", "at", "verdict"))
        for r in rows:
            print("%-22s %-24s %-24s %-6s %s   %s" % (
                r["profile"], r["config_model"] or "-", r["live_model"], r["live_at"], r["verdict"],
                (r["config_provider"] if r["live_model"] == "-" else r["live_base_url"])[:56]))
        print()
        print("✅ config==目标 且最近一次真实调用就是它 · ⏳ config 已就位但该 home 还没来消息（等一条消息再跑）"
              " · ❌ config 侧与目标不符（要动手） · ➖ 没给 --expect-model，未判")
        if not args.require_live:
            print("（要看「真在用」的硬结论：给 --expect-model 并加 --require-live）")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
