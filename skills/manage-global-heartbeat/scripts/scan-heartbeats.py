#!/usr/bin/env python3
"""列出本机所有带 heartbeat 的 session（跨 profile）。

heartbeat 就是会话里 `/heartbeat every 10m <prompt>` 设的那个循环指令：它**跟着 session 走**，
存在每个 profile 的 state.db → `state_meta` 表里，key = `heartbeat:<session_id>`，
value = JSON（`prompt` / `interval_seconds` / `status` / `created_at` / `last_fired_at` / `fire_count`）。

    python3 scan-heartbeats.py              # 所有 profile，active 排最前
    python3 scan-heartbeats.py --active     # 只看在跑的
    python3 scan-heartbeats.py --self-test  # 用临时库自检解析与聚合

只读：每个库都以 `mode=ro` 打开，不写任何文件。退出码 0 = 扫完；2 = 有库读不了。
`--fail-on-active` 时发现 active heartbeat 退 1（给「有没有东西在自动烧 token」当闸门用）。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

COLS = ["PROFILE", "SESSION", "STATUS", "EVERY", "FIRES", "LAST", "MSGS", "IN_TOK", "PROMPT", "TITLE / CHAT"]
PROMPT_WIDTH = 24
FIELDS = ("status", "interval_seconds", "fire_count", "last_fired_at", "created_at", "prompt")


def discover_dbs(home: Path) -> list[tuple[str, Path]]:
    """default profile 的库在 <home>/state.db，其余在 <home>/profiles/<name>/state.db。"""
    out: list[tuple[str, Path]] = []
    root = home / "state.db"
    if root.is_file():
        out.append(("default", root))
    for path in sorted(home.glob("profiles/*/state.db")):
        out.append((path.parent.name, path))
    return out


def _connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def read_db(profile: str, path: Path) -> tuple[list[dict], list[str]]:
    """返回 (该库里的 heartbeat 记录, 告警)。库缺少表/读不了都不抛，交回调用方报。"""
    con = _connect(path)
    try:
        if not con.execute(
            "select count(*) from sqlite_master where type='table' and name='state_meta'"
        ).fetchone()[0]:
            return [], [f"{profile}: no state_meta table at {path} (skipped)"]
        raw = con.execute("select key, value from state_meta where key like 'heartbeat:%'").fetchall()
        if not raw:
            return [], []

        rows: list[dict] = []
        for key, value in raw:
            row = {"profile": profile, "session": key.split(":", 1)[1], "unparsable": False}
            try:
                meta = json.loads(value)
            except (TypeError, ValueError):
                row["unparsable"] = True
                rows.append(row)
                continue
            if not isinstance(meta, dict):
                row["unparsable"] = True
                rows.append(row)
                continue
            for field in FIELDS:
                row[field] = meta.get(field)
            rows.append(row)

        ids = [r["session"] for r in rows]
        info: dict[str, tuple] = {}
        try:
            q = "select id, title, chat_id, message_count, input_tokens from sessions where id in (%s)" % (
                ",".join("?" * len(ids))
            )
            info = {r[0]: r[1:] for r in con.execute(q, ids)}
        except sqlite3.Error:
            pass  # 老库里没有 sessions 表：标题列留空，不影响 heartbeat 本身
        for row in rows:
            title, chat, msgs, in_tok = info.get(row["session"], (None, None, None, None))
            row.update(title=title, chat=chat, msgs=msgs, in_tok=in_tok)
        return rows, []
    finally:
        con.close()


def _fmt_ts(ts) -> str:
    if not isinstance(ts, (int, float)) or ts <= 0:
        return "-"
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _fmt(row: dict, key: str) -> str:
    if key == "status" and row["unparsable"]:
        return "unparsable"
    value = row.get(key)
    if value in (None, ""):
        return "-"
    if key == "last_fired_at":
        return _fmt_ts(value)
    if key == "interval_seconds":
        return f"{int(value) // 60}m" if value else "-"
    return str(value)


def render(rows: list[dict]) -> str:
    table = []
    for row in rows:
        where = " · ".join(str(x) for x in (row.get("title"), row.get("chat")) if x)
        table.append(
            [
                row["profile"],
                row["session"],
                _fmt(row, "status"),
                _fmt(row, "interval_seconds"),
                _fmt(row, "fire_count"),
                _fmt(row, "last_fired_at"),
                _fmt(row, "msgs"),
                _fmt(row, "in_tok"),
                (_fmt(row, "prompt")[:PROMPT_WIDTH]),
                where or "-",
            ]
        )
    widths = [max(len(COLS[i]), *(len(r[i]) for r in table)) if table else len(COLS[i]) for i in range(len(COLS))]
    lines = ["  ".join(c.ljust(widths[i]) for i, c in enumerate(COLS)).rstrip()]
    lines += ["  ".join(c.ljust(widths[i]) for i, c in enumerate(r)).rstrip() for r in table]
    return "\n".join(lines)


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (r.get("status") != "active", -(r.get("last_fired_at") or 0)))


def scan(home: Path, active_only: bool = False) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    notes: list[str] = []
    for profile, path in discover_dbs(home):
        try:
            got, warns = read_db(profile, path)
        except sqlite3.Error as exc:
            notes.append(f"{profile}: cannot read {path}: {exc}")
            continue
        notes += warns
        rows += got
    if active_only:
        rows = [r for r in rows if r.get("status") == "active" and not r["unparsable"]]
    return sort_rows(rows), notes


def _self_test() -> int:
    """临时库：active / cleared / 坏 JSON 各一条，外加一个没有 state_meta 的 profile 库。"""
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        con = sqlite3.connect(home / "state.db")
        con.executescript(
            "create table state_meta (key text primary key, value text);"
            "create table sessions (id text primary key, title text, chat_id text,"
            " message_count integer, input_tokens integer);"
        )
        con.execute("insert into sessions values ('s-active','对话A','111',95,1056307)")
        con.execute(
            "insert into state_meta values ('heartbeat:s-active', ?)",
            (json.dumps({"status": "active", "interval_seconds": 600, "fire_count": 804,
                         "last_fired_at": 1791600000, "prompt": "检查当前进度"}),),
        )
        con.execute("insert into state_meta values ('heartbeat:s-clear', ?)",
                    (json.dumps({"status": "cleared", "interval_seconds": 600, "fire_count": 7}),))
        con.execute("insert into state_meta values ('heartbeat:s-broken', 'not json')")
        con.commit()
        con.close()
        (home / "profiles" / "other").mkdir(parents=True)
        sqlite3.connect(home / "profiles" / "other" / "state.db").execute("create table t (x)").connection.commit()

        rows, notes = scan(home)
        assert [r["session"] for r in rows] == ["s-active", "s-clear", "s-broken"], rows
        assert rows[0]["title"] == "对话A" and rows[0]["msgs"] == 95 and rows[0]["in_tok"] == 1056307
        assert rows[2]["unparsable"] and _fmt(rows[2], "status") == "unparsable"
        assert _fmt(rows[1], "last_fired_at") == "-" and _fmt(rows[0], "interval_seconds") == "10m"
        assert len(notes) == 1 and "other" in notes[0], notes
        active, _ = scan(home, active_only=True)
        assert [r["session"] for r in active] == ["s-active"], active
        assert "s-active" in render(rows) and "对话A · 111" in render(rows)
    print("self-test ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="列出所有带 heartbeat 的 session（跨 profile，只读）")
    ap.add_argument("--hermes-home", default=os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes"),
                    help="Hermes home（默认 $HERMES_HOME 或 ~/.hermes）")
    ap.add_argument("--active", action="store_true", help="只看 status=active 的")
    ap.add_argument("--fail-on-active", action="store_true", help="有 active heartbeat 时退 1")
    ap.add_argument("--self-test", action="store_true", help="用临时库自检解析与聚合")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    home = Path(args.hermes_home).expanduser()
    if not home.is_dir():
        print(f"no such Hermes home: {home}", file=sys.stderr)
        return 2
    rows, notes = scan(home, active_only=args.active)
    if not rows:
        print(f"no heartbeat rows under {home} (profiles scanned: {len(discover_dbs(home))})")
        for note in notes:
            print(f"  ! {note}")
        return 0
    print(render(rows))
    tally: dict[str, int] = {}
    for row in rows:
        key = "unparsable" if row["unparsable"] else str(row.get("status"))
        tally[key] = tally.get(key, 0) + 1
    print("\n%d heartbeat row(s): %s | profiles scanned: %d" % (
        len(rows), ", ".join(f"{k} {v}" for k, v in sorted(tally.items())), len(discover_dbs(home))))
    for note in notes:
        print(f"  ! {note}")
    if args.fail_on_active and any(r.get("status") == "active" and not r["unparsable"] for r in rows):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
