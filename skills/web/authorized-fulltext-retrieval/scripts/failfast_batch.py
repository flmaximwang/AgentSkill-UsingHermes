#!/usr/bin/env python3
"""Fail-fast batch driver — run one command per item, stop at the first item that is not successful.

    python3 failfast_batch.py \
        --items "10.1039/aaa,10.1039/bbb" \
        --cmd 'node fetch.mjs --doi {item} --out out/' \
        --ok-regex '^(downloaded|downloaded_with_si|open_access_downloaded)$' \
        --progress out/progress.jsonl [--resume]

Why one subprocess per item: a batch tool that only reports at the end spends the entire run every time
something breaks. Driving items one at a time means the first bad item stops the run immediately and the
user is asked for the one thing only they can supply (a login, a bot check) while the rest is untouched.

Statuses are appended to the progress JSONL as they happen, so `--resume` turns a stop into a pause
instead of a restart. Exit code is 0 only when every item matched --ok-regex.

Tune --status-regex to however your toolchain prints its per-item verdict; the default reads a JSON
`"status": "..."` field out of the combined stdout+stderr.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True, help="comma-separated item list")
    ap.add_argument("--cmd", required=True, help="command template; `{item}` is substituted")
    ap.add_argument("--ok-regex", required=True, help="regex a status must match to count as success")
    ap.add_argument(
        "--status-regex",
        default=r'"status"\s*:\s*"([^"]+)"',
        help="regex capturing the per-item status from combined stdout+stderr",
    )
    ap.add_argument("--progress", required=True, help="JSONL progress file (created/appended)")
    ap.add_argument("--timeout", type=int, default=900, help="per-item timeout, seconds")
    ap.add_argument("--resume", action="store_true", help="skip items already recorded successful")
    a = ap.parse_args()

    if "{item}" not in a.cmd:
        print("[!] --cmd contains no {item} placeholder; every item would run identically.", file=sys.stderr)
        return 2

    ok_re = re.compile(a.ok_regex)
    st_re = re.compile(a.status_regex)
    items = [s.strip() for s in a.items.split(",") if s.strip()]
    if not items:
        print("[!] no items", file=sys.stderr)
        return 2

    done: dict = {}
    if a.resume and os.path.exists(a.progress):
        for line in open(a.progress, encoding="utf-8"):
            try:
                r = json.loads(line)
                done[r["item"]] = r
            except Exception:
                pass

    succeeded = 0
    for i, item in enumerate(items, 1):
        if ok_re.match(done.get(item, {}).get("status", "")):
            print(f"[{i}/{len(items)}] {item} — skip (already ok)")
            succeeded += 1
            continue

        print(f"[{i}/{len(items)}] {item} … ", end="", flush=True)
        t0 = time.time()
        try:
            p = subprocess.run(
                a.cmd.format(item=item),
                shell=True,
                capture_output=True,
                text=True,
                timeout=a.timeout,
            )
            blob = (p.stdout or "") + "\n" + (p.stderr or "")
            found = st_re.findall(blob)
            status = found[-1] if found else f"exit_{p.returncode}"
            tail = blob[-400:].strip()
        except subprocess.TimeoutExpired:
            status, tail = "timeout", ""
        dt = time.time() - t0

        with open(a.progress, "a", encoding="utf-8") as f:
            f.write(json.dumps({"item": item, "status": status, "secs": round(dt, 1)}) + "\n")

        if not ok_re.match(status):
            print(f"FAIL {status}  ({dt:.0f}s)")
            if tail:
                print("     " + tail.replace("\n", "\n     ")[:400])
            print(
                f"[STOP] fail-fast: item {i}/{len(items)} failed; "
                f"{len(items) - i} item(s) not attempted. "
                f"Resolve it, then re-run the same command with --resume."
            )
            return 1

        succeeded += 1
        print(f"ok {status}  ({dt:.0f}s)")

    print(f"all {succeeded} item(s) ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
