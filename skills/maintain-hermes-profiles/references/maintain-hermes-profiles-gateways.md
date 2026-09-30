# Per-profile gateway services

Each profile's gateway is an **independent system service**. Starting several of them is how multiple
agents stay online at once, each on its own messaging channel.

## Start them

```bash
hermes -p alice gateway start
hermes -p bob   gateway start
hermes -p coder gateway start
```

## Where the service definition lands

**macOS (LaunchAgent)** — one plist per profile, with login autostart and crash auto-restart:

> 每个 Profile 获得独立的 `~/Library/LaunchAgents/ai.hermes.gateway-<name>.plist`，支持开机自启和崩溃自动重启。

**Linux (systemd --user)** — one unit per profile:

```bash
hermes -p alice gateway start
hermes -p bob   gateway start
```

> 每个 Profile 获得独立的 `~/.config/systemd/user/hermes-gateway-<name>.service`。

## Batch management

The official docs provide a batch script, meant to live at `~/.local/bin/hermes-gateways`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-status}"

for profile in ~/.hermes/profiles/*/; do
  name="$(basename "$profile")"
  echo "[$name] hermes -p $name gateway $ACTION"
  hermes -p "$name" gateway "$ACTION"
done
```

Usage:

```bash
hermes-gateways status      # 查看所有 Profile 的 Gateway 状态
hermes-gateways start       # 启动所有
hermes-gateways stop        # 停止所有
hermes-gateways restart     # 重启所有
```

It loops over `~/.hermes/profiles/*/`, so it acts on **every profile directory** — including ones
whose gateway you did not mean to touch. The `default` profile is the exception the script cannot
handle for you:

> 注意：`default` Profile 使用 `hermes gateway <action>`（不带 `-p`），而非 `hermes -p default gateway <action>`。

## Ports

Each profile should listen on its own gateway port, or they conflict. Per profile, in its
`config.yaml`:

```yaml
gateway:
  port: 8643    # 不同的 Profile 用不同的端口
```

Distinct ports are also what lets the Desktop app reach a specific profile indirectly by Remote URL,
since the GUI itself cannot select one (see `maintain-hermes-profiles-limitations.md`).

## The dashboard `/chat` exception

`hermes dashboard`'s embedded `/chat` tab does **not** go through the gateway. Per WebSocket
connection it spawns a `hermes --tui` PTY process (`hermes_cli/web_server.py:3404-3450`), so it
follows the CLI's `--profile` argument and is **not** subject to the gateway's profile-blind
behaviour — the one place a profile switch shows up without a gateway restart.

## Measured on this machine (2026-09-30)

Commands re-verified while writing this skill, and they describe a **newer, single-host-gateway
topology** than the per-profile plists above:

```
$ hermes gateway list
Gateways:
  ✓ default (current)       
  ✓ game-research            — served by the default multiplexer
  ✓ investment-advisor       — served by the default multiplexer
  …

$ hermes gateway status
Launchd plist: /Users/maxim/Library/LaunchAgents/ai.hermes.gateway.plist
✓ Gateway is supervised by launchd (PID 58244)
  Auto-start at login and auto-restart on crash are available.
```

Two consequences worth stating when advising on this machine:

- Only **one** plist exists (`ai.hermes.gateway.plist`, label `ai.hermes.gateway`) — no
  `ai.hermes.gateway-<name>.plist` per profile — and `hermes gateway list` reports every other profile
  as "served by the default multiplexer".
- `hermes gateway --help` (measured) therefore exposes a `migrate` subcommand, worded as
  "Converge every per-profile gateway onto the ONE host gateway", next to the documented
  `start`/`stop`/`restart`/`status`/`install`/`uninstall`/`list` group.

Do not run `hermes gateway migrate` or any `start`/`stop`/`restart` to "check" this: those are
state-changing on a live machine whose bots are serving users. `list`, `status` and `--help` are the
read-only way to see the topology, which is all a support answer needs.
