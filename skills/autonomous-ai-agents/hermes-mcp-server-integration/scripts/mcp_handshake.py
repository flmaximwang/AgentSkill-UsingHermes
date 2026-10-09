#!/usr/bin/env python3
"""Probe a stdio MCP server: handshake, tool list, optional single tool call.

Read-only. Sends `initialize`, `notifications/initialized`, `tools/list`, and
(with --call) one `tools/call`; prints what the server actually advertises, so a
doc's tool table never has to be trusted.

Exit codes: 0 = handshake + tools/list ok, 1 = no/failed handshake or bad input,
2 = the requested tool call returned an error.

Server arguments that look like options are passed through (unknown options are
re-collected), so this script's own flags can go anywhere:
  mcp_handshake.py codegraph serve --mcp --cwd /tmp/proj
  mcp_handshake.py codegraph serve --mcp --call codegraph_explore --arguments '{"query":"who calls save"}'
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

PROTOCOL = "2024-11-05"


def probe(a) -> tuple[int, list[str]]:
    lines: list[str] = []
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": a.protocol, "capabilities": {},
                    "clientInfo": {"name": "mcp-handshake", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    if a.call:
        reqs.append({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                     "params": {"name": a.call, "arguments": json.loads(a.arguments)}})
    payload = "".join(json.dumps(r) + "\n" for r in reqs)

    proc = subprocess.Popen([a.command, *a.argv], cwd=a.cwd, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    err = ""
    try:
        out, err = proc.communicate(payload, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()  # retrying after kill does not lose output
        lines.append(f"note: no clean exit within {a.timeout:g}s (killed; "
                     "a server that keeps waiting for input is normal)")

    replies: dict[int, dict] = {}
    for line in (out or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict) and "id" in msg:
            replies[msg["id"]] = msg

    rc = 0
    init = replies.get(1)
    if not init or "result" not in init:
        lines.append(f"initialize: FAILED ({init.get('error') if init else 'no response'})")
        rc = 1
    else:
        res = init["result"]
        lines.append(f"initialize: OK server={res.get('serverInfo')} "
                     f"protocol={res.get('protocolVersion')}")

    listed = replies.get(2)
    if listed and "result" in listed:
        tools = listed["result"].get("tools", [])
        lines.append(f"tools/list: {len(tools)} tool(s)")
        for tool in tools:
            desc = " ".join((tool.get("description") or "").split())[:90]
            lines.append(f"  - {tool.get('name')}: {desc}")
    elif rc == 0:
        lines.append("tools/list: no response")
        rc = 1

    if a.call:
        call = replies.get(3)
        if call is None:
            lines.append(f"tools/call {a.call}: no response")
            rc = rc or 2
        else:
            res = call.get("result") or {}
            text = "".join(b.get("text", "") for b in res.get("content", [])
                           if b.get("type") == "text")
            lines.append(f"tools/call {a.call}: isError={res.get('isError')} "
                         f"error={call.get('error')}")
            if text:
                lines.append("---")
                lines.append(text[:a.max_chars] +
                             ("\n...[truncated]" if len(text) > a.max_chars else ""))
            if call.get("error") or res.get("isError"):
                rc = 2

    if err and err.strip():
        lines.append(f"stderr: {' '.join(err.split())[:300]}")
    return rc, lines


def main() -> int:
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Probe a stdio MCP server: handshake, tool list, optional call.")
    p.add_argument("command", help="server executable (must resolve on PATH)")
    p.add_argument("argv", nargs="*", help="server arguments (e.g. serve --mcp)")
    p.add_argument("--cwd", default=".", help="working directory the server starts in")
    p.add_argument("--timeout", type=float, default=45.0, metavar="SEC",
                   help="wall-clock budget for the whole probe, seconds")
    p.add_argument("--protocol", default=PROTOCOL, help="MCP protocolVersion to request")
    p.add_argument("--call", default="", metavar="TOOL",
                   help="tool to invoke after tools/list; empty = list only")
    p.add_argument("--arguments", default="{}", metavar="JSON",
                   help="JSON object passed to --call")
    p.add_argument("--max-chars", type=int, default=2000,
                   help="max characters of tool output to print")
    a, extra = p.parse_known_args()
    a.argv = [*a.argv, *extra]  # unknown options belong to the wrapped server
    try:
        json.loads(a.arguments)
    except json.JSONDecodeError as exc:
        print(f"--arguments is not valid JSON: {exc}")
        return 1
    rc, lines = probe(a)
    print("\n".join(lines))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
