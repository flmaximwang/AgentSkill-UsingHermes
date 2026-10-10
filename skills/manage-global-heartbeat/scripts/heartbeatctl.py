#!/usr/bin/env python3
"""从**会话外**读/改某个 session 的 heartbeat —— 走官方 `HeartbeatManager`，不手写 `state_meta`。

```bash
python3 heartbeatctl.py --session <session_id> status     # 看（只读）
python3 heartbeatctl.py --session <session_id> clear      # 等价于在那条会话里发 /heartbeat clear
python3 heartbeatctl.py --session <session_id> pause      # 保留、不再触发
python3 heartbeatctl.py --session <session_id> resume
python3 heartbeatctl.py --session <session_id> set 10m "检查当前进度"
python3 heartbeatctl.py --self-test                       # 临时 HERMES_HOME 里跑一遍全流程
```

为什么不能直接改库：`state_meta` 里那行 JSON 是 `HeartbeatState.to_json()` 的产物，手改一个字段就可能写成
**解析不了的行**，而 `store_has_active_heartbeat()` 对解析不了的行**按「active」处理**（未知即保守）——
于是你以为停了、别的调用方照样按「有活跃心跳」对待。走 API 则永远是合法状态。

每个子命令都先打 `before`、改完再从库里 `load` 一次打 `after` —— 看见 after 才算改到。

**一个例外要说清**：交互式 CLI 里开着的会话，它的 watchdog 把 `HeartbeatManager` 缓存在内存里，下次轮询会用
内存态 `save_heartbeat()` 把 `active` 写回去（`due_prompt()` 自己就会 save）——那种情况必须在**那条会话里**发
`/heartbeat clear`。Discord / gateway 侧每次轮询都新建 manager、从库里 load，所以从会话外清是有效的。

`--hermes-home`（默认取 `HERMES_HOME`，否则 `~/.hermes`）决定动哪个 profile 的库，实现方式是把官方的
context-local override 指过去（`set_hermes_home_override`），不改本进程的环境变量；`--hermes-agent` 指 checkout
（默认 `~/.hermes/hermes-agent`）。只动 heartbeat 那一行，不碰消息与其它 meta。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_AGENT = "~/.hermes/hermes-agent"
DEFAULT_SESSION = "20260101_000000_deadbe"
STATES = ("status", "pause", "resume", "clear", "set")


def _load_api(agent_home: Path):
    if str(agent_home) not in sys.path:
        sys.path.insert(0, str(agent_home))
    from hermes_cli.heartbeat import MIN_INTERVAL_SECONDS, HeartbeatManager, load_heartbeat, parse_interval
    return HeartbeatManager, load_heartbeat, parse_interval, MIN_INTERVAL_SECONDS


def _show(load_heartbeat, session: str, label: str) -> None:
    state = load_heartbeat(session)
    if state is None:
        print(f"{label}: (no heartbeat — 库里是空的或 status=cleared)")
        return
    print(f"{label}: status={state.status} every={state.interval_seconds // 60}m "
          f"fired={state.fire_count} prompt={state.prompt!r}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="从会话外读/改某个 session 的 heartbeat（官方 API）")
    ap.add_argument("action", nargs="?", choices=STATES, help="status|pause|resume|clear|set")
    ap.add_argument("value", nargs="*", help="set 用：<间隔> <prompt>")
    ap.add_argument("--session", default="", help="目标 session id（先用 manage-global-heartbeat 的 scan-heartbeats.py 查出来）")
    ap.add_argument("--hermes-home", default=os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes"))
    ap.add_argument("--hermes-agent", default=DEFAULT_AGENT)
    ap.add_argument("--self-test", action="store_true", help="用临时 HERMES_HOME 跑一遍 set→pause→resume→clear")
    args = ap.parse_args(argv)

    home = Path(args.hermes_home).expanduser()
    agent = Path(args.hermes_agent).expanduser()
    if str(agent) not in sys.path:
        sys.path.insert(0, str(agent))
    # 目标 profile 走官方的 context-local override（get_hermes_home(): override → HERMES_HOME → 默认），
    # 不改进程环境变量；SessionDB 按 home 字符串缓存，所以必须在第一次取库之前设。
    from hermes_constants import set_hermes_home_override

    set_hermes_home_override(str(home))

    if args.self_test:
        return _self_test(agent, Path.home() / ".hermes")

    if not args.action:
        print("要一个动作：status|pause|resume|clear|set（或 --self-test）", file=sys.stderr)
        return 2
    if not args.session:
        print("--session 必填（先用 manage-global-heartbeat 的扫描器查出 session id）", file=sys.stderr)
        return 2
    if not (agent / "hermes_cli" / "heartbeat.py").is_file():
        print(f"找不到 hermes checkout: {agent}", file=sys.stderr)
        return 2

    HeartbeatManager, load_heartbeat, parse_interval, min_interval = _load_api(agent)
    _show(load_heartbeat, args.session, "before")
    mgr = HeartbeatManager(session_id=args.session)

    if args.action == "status":
        print(mgr.status_line())
        return 0
    if args.action == "clear":
        print("cleared:", mgr.clear())
    elif args.action == "pause":
        print("paused:", mgr.pause() is not None)
    elif args.action == "resume":
        print("resumed:", mgr.resume() is not None)
    else:  # set
        if len(args.value) < 2:
            print('set 用法: set <间隔> <prompt>（例：set 10m "检查当前进度"）', file=sys.stderr)
            return 2
        interval = parse_interval(args.value[0])
        if not interval or interval < 0:
            print(f"间隔要写成 10m / 2h / 90 minutes 这类形式（下限 {min_interval}s）", file=sys.stderr)
            return 2
        state = mgr.set(" ".join(args.value[1:]), interval)
        print(f"set: every {state.interval_seconds // 60}m prompt={state.prompt!r}")
    _show(load_heartbeat, args.session, "after")
    return 0


def _self_test(agent: Path, live_home: Path) -> int:
    """临时 HERMES_HOME 里跑一遍真 API：set → status → pause → resume → clear，逐条断言落库结果。"""
    if not (agent / "hermes_cli" / "heartbeat.py").is_file():
        print(f"找不到 hermes checkout: {agent}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        base = [sys.executable, os.path.abspath(__file__), "--session", DEFAULT_SESSION,
                "--hermes-agent", str(agent), "--hermes-home", tmp]
        def run(*extra: str) -> str:
            r = subprocess.run(base + list(extra), capture_output=True, text=True)
            assert r.returncode == 0, (extra, r.returncode, r.stdout, r.stderr)
            return r.stdout
        assert "no heartbeat" in run("status")
        out = run("set", "10m", "检查当前进度")
        assert "status=active" in out and "after" in out, out
        assert "status=active" in run("status")
        assert "status=paused" in run("pause")
        assert "status=active" in run("resume")
        assert "cleared: True" in run("clear")
        assert "no heartbeat" in run("status"), run("status")
    assert live_home.is_dir()
    print("self-test ok (临时库；没碰 " + str(live_home) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
