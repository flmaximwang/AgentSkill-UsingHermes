#!/usr/bin/env python3
"""Change a Discord bot's own thread membership, or inspect a thread's members.

Subcommands
    status  THREAD_ID                 thread metadata + member list + whether *you* are a member
    leave   THREAD_ID                 DELETE /channels/<id>/thread-members/@me   (no permission needed)
    join    THREAD_ID                 PUT    /channels/<id>/thread-members/@me   (needs send-messages-in-threads)
    remove  THREAD_ID --user-id ID    DELETE /channels/<id>/thread-members/<id>  (needs Manage Threads)

The bot speaks with its own token, read from the profile's env file, so nothing here needs
operator credentials for the `leave` / `join` / `status` paths. The token is never printed.

Exit codes
    0 ok · 1 usage/api error · 2 token not found · 3 permission denied (403)
    4 thread archived/locked (or otherwise not actionable) · 5 thread not found (404)

Stdlib only. Proxy resolution order: --proxy, else this process's HTTPS_PROXY / HTTP_PROXY / ALL_PROXY,
else DISCORD_PROXY / HTTPS_PROXY / HTTP_PROXY from the profile env file (that last source is how a
Hermes gateway itself gets its proxy — a hand-run shell inherits none of it); --no-proxy forces a
direct dial.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://discord.com/api/v10"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NO_TOKEN = 2
EXIT_FORBIDDEN = 3
EXIT_NOT_ACTIONABLE = 4
EXIT_NOT_FOUND = 5


def hermes_home(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".hermes"


def env_file_for(home: Path, profile: str, explicit: str | None) -> Path:
    """default profile -> <home>/.env ; named profile -> <home>/profiles/<name>/.env"""
    if explicit:
        return Path(explicit).expanduser()
    if profile and profile != "default":
        return home / "profiles" / profile / ".env"
    return home / ".env"


def read_env_entry(env_file: Path, *keys: str) -> tuple[str, str]:
    """Return the first (key, value) among *keys* present in the env file, else ("", "")."""
    try:
        text = env_file.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return "", ""
    wanted = set(keys)
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in wanted:
            value = value.strip().strip('"').strip("'")
            if value:
                return key, value
    return "", ""


def read_token(env_file: Path, override: str | None) -> str:
    if override:
        return override.strip()
    _, value = read_env_entry(env_file, "DISCORD_BOT_TOKEN")
    if not value:
        print(f"error: no DISCORD_BOT_TOKEN in {env_file}", file=sys.stderr)
    return value


def resolve_proxy(explicit: str | None, env_file: Path, no_proxy: bool) -> tuple[str | None, str]:
    """--proxy wins, then this process's env, then the profile's own env file.

    Hermes' *gateway* takes its proxy from the profile env file (`DISCORD_PROXY`, or
    HTTPS_PROXY/HTTP_PROXY); a shell that runs this script by hand inherits none of that, and on a host
    that cannot dial out directly (measured on the DS220+ NAS: direct -> blocked, proxy -> 200) the
    call fails with a bare connection error. So the env file is consulted here too.
    Returns (proxy_url_or_None, where_it_came_from).
    """
    if no_proxy:
        return None, "--no-proxy"
    if explicit:
        return explicit, "--proxy"
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        value = os.environ.get(key)
        if value:
            return value, f"env:{key}"
    key, value = read_env_entry(env_file, "DISCORD_PROXY", "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY")
    if value:
        return value, f"{env_file}:{key}"
    return None, "none"


def build_opener(proxy: str | None, no_proxy: bool) -> urllib.request.OpenerDirector:
    if proxy:
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        return urllib.request.build_opener(handler)
    if no_proxy:
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()


def call(opener, token: str, method: str, path: str) -> tuple[int, object]:
    """Return (http_status, parsed_body_or_empty_string). Never echoes the token."""
    req = urllib.request.Request(
        API + path,
        method=method,
        headers={"Authorization": f"Bot {token}", "User-Agent": "Hermes/1.0",
                 "Content-Type": "application/json"},
    )
    try:
        with opener.open(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        status = exc.code
    except Exception as exc:  # network / DNS / proxy failure
        print(f"error: request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("hint: a host that cannot dial out directly needs a proxy. This script picks up "
              "DISCORD_PROXY / HTTPS_PROXY from the profile env file on its own; if the env file has "
              "none, pass --proxy http://127.0.0.1:<port>, or --no-proxy to force a direct dial.",
              file=sys.stderr)
        raise SystemExit(EXIT_ERROR)
    try:
        return status, (json.loads(body) if body.strip() else "")
    except json.JSONDecodeError:
        return status, body


def discord_error(body: object) -> tuple[str, str]:
    if isinstance(body, dict):
        return str(body.get("message", "")), str(body.get("code", ""))
    return "", ""


def describe_thread(opener, token: str, thread_id: str) -> dict:
    status, body = call(opener, token, "GET", f"/channels/{thread_id}")
    if status == 404:
        print(f"error: thread {thread_id} not found (or this bot cannot see it)")
        raise SystemExit(EXIT_NOT_FOUND)
    if status != 200 or not isinstance(body, dict):
        msg, code = discord_error(body)
        print(f"error: GET /channels/{thread_id} -> HTTP {status} {msg} ({code})")
        raise SystemExit(EXIT_ERROR)
    return body


def members(opener, token: str, thread_id: str) -> list[dict]:
    status, body = call(opener, token, "GET", f"/channels/{thread_id}/thread-members")
    if status != 200 or not isinstance(body, list):
        msg, code = discord_error(body)
        print(f"error: GET thread-members -> HTTP {status} {msg} ({code})")
        raise SystemExit(EXIT_ERROR)
    return body


def self_id(opener, token: str) -> str:
    status, body = call(opener, token, "GET", "/users/@me")
    if status != 200 or not isinstance(body, dict):
        print(f"error: token rejected (HTTP {status}); check DISCORD_BOT_TOKEN")
        raise SystemExit(EXIT_NO_TOKEN)
    return str(body["id"])


def cmd_status(opener, token: str, thread_id: str, as_json: bool) -> int:
    thread = describe_thread(opener, token, thread_id)
    rows = members(opener, token, thread_id)
    me = self_id(opener, token)
    meta = thread.get("thread_metadata") or {}
    payload = {
        "thread_id": thread_id,
        "name": thread.get("name"),
        "type": thread.get("type"),
        "parent_id": thread.get("parent_id"),
        "owner_id": thread.get("owner_id"),
        "member_count": thread.get("member_count"),
        "archived": meta.get("archived"),
        "locked": meta.get("locked"),
        "members": [r.get("user_id") for r in rows],
        "self_id": me,
        "self_is_member": any(r.get("user_id") == me for r in rows),
    }
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK
    print(f"thread {payload['name']!r}  id={thread_id} type={payload['type']} "
          f"parent={payload['parent_id']}")
    print(f"  archived={payload['archived']} locked={payload['locked']} "
          f"owner={payload['owner_id']} member_count={payload['member_count']}")
    for row in rows:
        mark = " <- this bot" if row.get("user_id") == me else ""
        print(f"  member {row.get('user_id')}{mark}")
    print(f"self {me} is a member: {payload['self_is_member']}")
    return EXIT_OK


def cmd_leave(opener, token: str, thread_id: str, as_json: bool) -> int:
    me = self_id(opener, token)
    status, body = call(opener, token, "DELETE", f"/channels/{thread_id}/thread-members/@me")
    if status in (200, 204):
        print(f"left thread {thread_id}" + (f" (member id {me})" if not as_json else ""))
        return EXIT_OK
    msg, code = discord_error(body)
    if status == 403:
        thread = describe_thread(opener, token, thread_id)
        meta = thread.get("thread_metadata") or {}
        print(f"error: cannot leave -> HTTP 403 {msg} ({code})")
        if meta.get("archived") or meta.get("locked"):
            print(f"hint: thread is archived={meta.get('archived')} locked={meta.get('locked')}; "
                  "an archived/locked thread accepts no membership change — unarchive it first "
                  "(PATCH /channels/<id> {\"archived\": false}), then retry")
            return EXIT_NOT_ACTIONABLE
        print("hint: leaving needs only visibility of the parent channel; a 403 here is unusual — "
              "read the thread object with `status`")
        return EXIT_FORBIDDEN
    print(f"error: leave -> HTTP {status} {msg} ({code})")
    return EXIT_ERROR


def cmd_join(opener, token: str, thread_id: str, as_json: bool) -> int:
    me = self_id(opener, token)
    status, body = call(opener, token, "PUT", f"/channels/{thread_id}/thread-members/@me")
    if status in (200, 204):
        print(f"joined thread {thread_id}" + (f" (member id {me})" if not as_json else ""))
        return EXIT_OK
    msg, code = discord_error(body)
    if status == 403:
        thread = describe_thread(opener, token, thread_id)
        meta = thread.get("thread_metadata") or {}
        if meta.get("archived") or meta.get("locked"):
            print(f"error: cannot join -> HTTP 403 {msg} ({code}); thread is archived="
                  f"{meta.get('archived')} locked={meta.get('locked')}")
            return EXIT_NOT_ACTIONABLE
        print(f"error: cannot join -> HTTP 403 {msg} ({code}); needs Send Messages in Threads "
              "on this thread")
        return EXIT_FORBIDDEN
    print(f"error: join -> HTTP {status} {msg} ({code})")
    return EXIT_ERROR


def cmd_remove(opener, token: str, thread_id: str, user_id: str, as_json: bool) -> int:
    status, body = call(opener, token, "DELETE",
                        f"/channels/{thread_id}/thread-members/{user_id}")
    if status in (200, 204):
        print(f"removed {user_id} from thread {thread_id}")
        return EXIT_OK
    msg, code = discord_error(body)
    if status == 403:
        print(f"error: cannot remove {user_id} -> HTTP 403 {msg} ({code})")
        print("hint: removing *another* member needs Manage Threads (or being the creator of a "
              "private thread). A bot without that permission gets exactly this 403/50001 — "
              "the target can still remove itself with `leave`.")
        return EXIT_FORBIDDEN
    if status == 404:
        print(f"error: {user_id} is not a member of thread {thread_id} (HTTP 404 {msg} {code})")
        return EXIT_NOT_FOUND
    print(f"error: remove -> HTTP {status} {msg} ({code})")
    return EXIT_ERROR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or change a Discord bot's own thread membership.")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("thread_id", help="thread (channel) id")
        p.add_argument("--profile", default=os.environ.get("HERMES_PROFILE", "default"),
                       help="Hermes profile whose .env holds DISCORD_BOT_TOKEN (default: "
                            "$HERMES_PROFILE or 'default')")
        p.add_argument("--hermes-home", default=None,
                       help="Hermes home (default: $HERMES_HOME or $HOME/.hermes)")
        p.add_argument("--env-file", default=None, help="read DISCORD_BOT_TOKEN from this file")
        p.add_argument("--token", default=None, help="token override (prefer the env file)")
        p.add_argument("--proxy", default=None,
                       help="proxy URL; default: this process's env, then DISCORD_PROXY / "
                            "HTTPS_PROXY from the profile env file")
        p.add_argument("--no-proxy", action="store_true",
                       help="ignore every proxy source and dial directly")
        p.add_argument("--json", action="store_true", help="machine-readable output (status)")

    for name in ("status", "leave", "join"):
        common(sub.add_parser(name))
    p_remove = sub.add_parser("remove")
    common(p_remove)
    p_remove.add_argument("--user-id", required=True, help="member to remove (needs Manage Threads)")

    args = parser.parse_args(argv)

    home = hermes_home(args.hermes_home)
    env_file = env_file_for(home, args.profile, args.env_file)
    token = read_token(env_file, args.token)
    if not token:
        print(f"error: no DISCORD_BOT_TOKEN found (looked at {env_file})", file=sys.stderr)
        print("hint: pass --profile <name> / --env-file <path>, or --token", file=sys.stderr)
        return EXIT_NO_TOKEN

    proxy, proxy_src = resolve_proxy(args.proxy, env_file, args.no_proxy)
    opener = build_opener(proxy, args.no_proxy)
    if args.command == "status" and not args.json:
        print(f"auth: {env_file}\nproxy: {'on' if proxy else 'off'} ({proxy_src})")
    if args.command == "status":
        return cmd_status(opener, token, args.thread_id, args.json)
    if args.command == "leave":
        return cmd_leave(opener, token, args.thread_id, args.json)
    if args.command == "join":
        return cmd_join(opener, token, args.thread_id, args.json)
    return cmd_remove(opener, token, args.thread_id, args.user_id, args.json)


if __name__ == "__main__":
    sys.exit(main())
