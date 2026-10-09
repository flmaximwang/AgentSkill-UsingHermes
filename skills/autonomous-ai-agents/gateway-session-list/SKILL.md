---
name: gateway-operations
description: "Hermes Gateway lifecycle management — per-profile start/stop/status, platform setup (Feishu/Lark, Telegram, etc.), and multi-gateway inspection."
version: 2.0.0
author: Agent
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [hermes, gateway, ops, profiles, feishu, setup]
---

# Gateway Operations

Hermes Gateway lifecycle management: inspecting running gateways, starting/stopping per profile, and configuring messaging platforms.

This skill consolidates:
- Per-profile gateway lifecycle (`start`/`stop`/`status`)
- Interactive platform setup (`gateway setup`) in PTY mode
- Feishu/Lark setup reference
- Multi-gateway process inspection

---

## Per-Profile Gateway Lifecycle

Hermes supports multiple profiles, each with its own gateway process and config. Manage them independently.

### Check Profile Gateway Status

```bash
hermes profile list
```

Output shows a `Gateway` column per profile: `running` or `stop`.

### Inspect Running Gateway Processes

```bash
# Count gateway instances
ps aux | grep "gateway run" | grep -v grep

# See all Hermes processes (gateway, dashboard, desktop helpers)
ps aux | grep -i hermes | grep -v grep
```

Each gateway process shows its profile flag:
- Default profile: `python -m hermes_cli.main gateway run --replace`
- Named profile: `python -m hermes_cli.main --profile lab-assistant gateway run --replace`

### Start a Gateway

```bash
# As background launchd service (recommended — macOS):
hermes --profile <name> gateway start
# Auto-generates launchd plist if missing, then starts

# Foreground:
hermes --profile <name> gateway run
```

### Stop a Gateway

```bash
hermes --profile <name> gateway stop
```

### Restart a Gateway

```bash
hermes --profile <name> gateway restart
```

---

## Interactive Platform Setup

Configure messaging platforms (Telegram, Feishu, Discord, WeCom, etc.) for any profile.

### Run Interactively

```bash
hermes --profile <name> gateway setup
```

This opens a TUI that:
1. Optionally starts the gateway if stopped
2. Shows a numbered menu of all available platforms (with configured/not-configured status)
3. Supports QR-code scan-to-create for some platforms (Feishu, Telegram)
4. Falls back to manual credential input when scan is unavailable

### Important: PTY Mode Required

The `gateway setup` tool is a curses-style interactive TUI. **It requires a pseudo-terminal (PTY).** Never run it in plain foreground mode — use one of:

```python
# Background mode with pty=true, user interacts via Hermes Desktop terminal pane
terminal(command="hermes --profile <name> gateway setup", pty=True, background=True)

# Or foreground with pty=true for a one-shot interaction
terminal(command="hermes --profile <name> gateway setup", pty=True, timeout=300)
```

When running in background PTY mode, send responses with `process(action="submit")` for simple yes/no prompts (e.g. "Start it now? [Y/n]:" → send `Y`).

---

## Feishu / Lark Setup

Full official docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/chinese-platforms/feishu/

### Quick Reference

**Credentials needed:**
- `FEISHU_APP_ID` — from Feishu Developer Console → Credentials & Basic Info
- `FEISHU_APP_SECRET` — from same page
- `FEISHU_DOMAIN` — `feishu` (China) or `lark` (international)

**Minimal `.env` config:**
```
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=***
FEISHU_CONNECTION_MODE=websocket   # recommended; no public URL needed
```

**Required permissions** (Feishu Console → Permission Management):
| Scope | Purpose |
|-------|---------|
| `im:message` | Receive and read messages |
| `im:message:send_as_bot` | Send messages as bot |
| `im:resource` | Access images/files/audio |
| `im:chat` | Access chat/group metadata |
| `im:chat:readonly` | Read chat list and membership |

**Required event subscription:** `im.message.receive_v1`

**After configuration:** publish app → `/set-home` in target chat for cron output channel.

**Security (production):**
```
FEISHU_ALLOWED_USERS=ou_xxx,ou_yyy   # user allowlist
FEISHU_GROUP_POLICY=allowlist          # open | allowlist | disabled
```

**Pitfalls:**
- Bot only responds to @mentions in group chats by default
- Both `im:message` and `im:message:send_as_bot` scopes must be granted
- After adding permissions, publish a new app version for them to take effect
- The `websockets` Python package must be installed (`pip install websockets`)
- Only one Hermes instance can use the same `app_id` at a time

### Setup via wizard (recommended)

```bash
hermes --profile <name> gateway setup
# → Select "10. Feishu / Lark"
# → Scan QR code with Feishu mobile app, or enter credentials manually
```

---

## Session List

```bash
# Basic session listing
~/.hermes/hermes-agent/venv/bin/hermes sessions list

# Interactive picker (requires TTY)
~/.hermes/hermes-agent/venv/bin/hermes sessions browse
```

**Note:** `hermes` CLI is typically not in `$PATH`. Use the venv path or an alias.

---

## Feishu Setup Reference

See `references/feishu-setup.md` for the full env-var table, connection-mode details (WebSocket vs Webhook), per-group access control rules, interactive card configuration, document-comment intelligent reply setup, and troubleshooting steps.
