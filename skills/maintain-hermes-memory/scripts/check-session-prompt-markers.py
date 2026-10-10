#!/usr/bin/env python3
"""Which system prompt is a chat actually running?

Usage:
    check-session-prompt-markers.py <chat_id> [--db PATH] [-n 5] [--selftest]

A config key read at agent init (memory switches, `memory.provider`, persona text) reaches only
sessions *created* after the change: a gateway restart restores a live session's stored prompt by
hash, it does not rebuild it. The rebuild shows up as a new session id + a new `system_prompt_hash`
ending the previous row (`ended_at` set).
"""
import argparse
import datetime
import os
import sqlite3
import sys

MARKERS = (
    "# Hindsight Memory",             # hindsight provider block active
    "MEMORY (your personal notes)",   # built-in store on
    "USER PROFILE",                   # built-in user profile on
    "persistent memory via Limbic",   # limbic provider block active
)


def report(con, chat_id, n=5):
    rows = con.execute(
        "SELECT id, started_at, ended_at, system_prompt_hash FROM sessions"
        " WHERE chat_id = ? ORDER BY started_at DESC LIMIT ?", (chat_id, n)).fetchall()
    if not rows:
        return ["no session rows for chat_id=%s" % chat_id]
    out = []
    for sid, started, ended, h in rows:
        when = datetime.datetime.fromtimestamp(started).strftime("%F %T") if started else "?"
        row = (con.execute("SELECT prompt FROM system_prompts WHERE hash LIKE ?",
                           (h + "%",)).fetchone() if h else None)
        marks = dict((m, None) for m in MARKERS) if not row else dict((m, m in row[0]) for m in MARKERS)
        out.append("%s  start=%s  live=%s  hash=%s  %s"
                   % (sid, when, ended is None, (h or "?")[:12], marks))
    return out


def selftest():
    con = sqlite3.connect(":memory:")
    con.executescript(
        "CREATE TABLE sessions(id TEXT, started_at REAL, ended_at REAL,"
        " system_prompt_hash TEXT, chat_id TEXT);"
        "CREATE TABLE system_prompts(hash TEXT, prompt TEXT);")
    con.execute("INSERT INTO system_prompts VALUES ('aa11','x # Hindsight Memory y')")
    con.execute("INSERT INTO system_prompts VALUES ('bb22','MEMORY (your personal notes)')")
    con.execute("INSERT INTO sessions VALUES ('s_new', 1000, NULL, 'aa11', 'c1')")
    con.execute("INSERT INTO sessions VALUES ('s_old', 900, 1000, 'bb22', 'c1')")
    lines = report(con, "c1")
    assert lines[0].startswith("s_new") and "'# Hindsight Memory': True" in lines[0], lines
    assert "'MEMORY (your personal notes)': True" in lines[1], lines
    assert report(con, "nope") == ["no session rows for chat_id=nope"]
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chat_id", nargs="?")
    ap.add_argument("--db", default=os.path.expanduser("~/.hermes/state.db"))
    ap.add_argument("-n", type=int, default=5)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    if not a.chat_id:
        ap.error("chat_id is required (or use --selftest)")
    con = sqlite3.connect("file:%s?mode=ro" % a.db, uri=True)
    for line in report(con, a.chat_id, a.n):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
