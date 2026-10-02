#!/usr/bin/env python3
"""Who owns a Hermes chat's routing key, and where did its delegated work go?

READ-ONLY: opens the store with mode=ro and never writes. Usage:

    python3 routing_owner.py 1554813966440603762
    python3 routing_owner.py --db ~/.hermes/profiles/travel-guider/state.db 1554813966440603762
    python3 routing_owner.py "agent:main:discord:thread:1554813966440603762:1554813966440603762"

Prints: the routing entry and its owner session, every row holding that key (more than one live row
is the delegate-child takeover shape), the owner row and its parent chain, and the delegation records
that touch the key with each task's status.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3

DEFAULT_DB = os.path.expanduser("~/.hermes/state.db")

SESSION_COLS = (
    "substr(id,1,26) AS id, source, created_source, substr(parent_session_id,1,26) AS parent,"
    " end_reason, chat_id, chat_type, thread_id, message_count, archived,"
    " datetime(started_at,'unixepoch','localtime') AS started,"
    " datetime(ended_at,'unixepoch','localtime') AS ended,"
    " json_extract(model_config,'$._delegate_from') AS delegate_from,"
    " json_extract(model_config,'$._branched_from') AS branched_from, title"
)


def q(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list:
    try:
        cur = conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    except sqlite3.Error as exc:
        print(f"  ! query failed: {exc}")
        return []


def show(rows: list) -> None:
    if not rows:
        print("  (none)")
    for row in rows:
        print("  " + " | ".join(f"{k}={v}" for k, v in row.items() if v not in (None, "")))


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    ap.add_argument("chat", help="chat/thread id, or a full routing key")
    ap.add_argument("--db", default=DEFAULT_DB, help="state.db to read (one per profile)")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        raise SystemExit(f"no such state.db: {args.db}")
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    needle = f"%{args.chat}%"
    print(f"# state.db = {args.db}\n# needle   = {args.chat}\n")

    print("== ROUTING KEY -> OWNER (gateway_routing) ==")
    entries = q(
        conn,
        "SELECT session_key, json_extract(entry_json,'$.session_id') AS owner_session,"
        " json_extract(entry_json,'$.display_name') AS display_name,"
        " datetime(updated_at,'unixepoch','localtime') AS entry_updated"
        " FROM gateway_routing WHERE session_key LIKE ?",
        (needle,),
    )
    show(entries)

    print("\n== SESSION ROWS HOLDING THIS KEY (one live row only; 2+ = takeover) ==")
    keys = [e["session_key"] for e in entries]
    for key in keys:
        show(
            q(
                conn,
                f"SELECT {SESSION_COLS} FROM sessions WHERE session_key = ? ORDER BY started_at",
                (key,),
            )
        )
    if not keys:
        show(
            q(
                conn,
                f"SELECT {SESSION_COLS} FROM sessions WHERE chat_id = ? OR thread_id = ? ORDER BY started_at",
                (args.chat, args.chat),
            )
        )

    print("\n== OWNER SESSION(S) + PARENT CHAIN ==")
    frontier = [e["owner_session"] for e in entries if e.get("owner_session")]
    seen = set()
    while frontier:
        sid = frontier.pop(0)
        if not sid or sid in seen:
            continue
        seen.add(sid)
        for row in q(conn, f"SELECT {SESSION_COLS} FROM sessions WHERE id = ?", (sid,)):
            show([row])
            parent = row.get("parent")
            if parent and parent not in seen:
                frontier.append(parent)

    print("\n== DELEGATIONS TOUCHING THIS KEY ==")
    delegations = q(
        conn,
        "SELECT delegation_id, origin_session, origin_session_id, parent_session_id, state,"
        " delivery_state, datetime(dispatched_at,'unixepoch','localtime') AS dispatched,"
        " datetime(completed_at,'unixepoch','localtime') AS completed, result_json"
        " FROM async_delegations WHERE origin_session LIKE ? OR parent_session_id IN"
        " (SELECT id FROM sessions WHERE session_key LIKE ?) ORDER BY dispatched_at",
        (needle, needle),
    )
    if not delegations:
        print("  (none)")
    for row in delegations:
        raw = row.pop("result_json", None)
        show([row])
        if not raw:
            continue
        try:
            for task in json.loads(raw).get("results", []):
                summary = (task.get("summary") or "").replace("\n", " ")[:110]
                print(f"    task {task.get('task_index')}: {task.get('status')} — {summary}")
        except (ValueError, AttributeError) as exc:
            print(f"    ! result_json unreadable: {exc}")

    print(
        "\nReminder: read-only. 'dropped' = the parent never got this result;"
        " 'interrupted' = the task was killed and must be re-dispatched."
        " A key pointing at a created_source=subagent row needs /new from the user."
    )


if __name__ == "__main__":
    main()
