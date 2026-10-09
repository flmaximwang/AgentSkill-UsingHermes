# Feishu / Lark — Hermes Gateway Setup Reference

Full official docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/chinese-platforms/feishu/

## Connection Modes

| Mode | When to Use | Requirements |
|------|-------------|--------------|
| **WebSocket** (recommended) | Laptop, workstation, private server — no public URL needed | `pip install websockets`; SDK handles reconnect |
| **Webhook** | You have a reachable HTTP endpoint | `pip install aiohttp`; configure webhook in Feishu Console |

## All Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FEISHU_APP_ID` | ✅ | — | Feishu/Lark App ID |
| `FEISHU_APP_SECRET` | ✅ | — | Feishu/Lark App Secret |
| `FEISHU_DOMAIN` | — | `feishu` | `feishu` (China) or `lark` (international) |
| `FEISHU_CONNECTION_MODE` | — | `websocket` | `websocket` or `webhook` |
| `FEISHU_ALLOWED_USERS` | — | empty | Comma-separated open_id allowlist |
| `FEISHU_ALLOW_BOTS` | — | `none` | Bot-to-bot: `none` | `mentions` | `all` |
| `FEISHU_REQUIRE_MENTION` | — | `true` | Must @mention in groups |
| `FEISHU_HOME_CHANNEL` | — | — | Chat ID for cron/notification output |
| `FEISHU_ENCRYPT_KEY` | — | empty | Webhook signature verification |
| `FEISHU_VERIFICATION_TOKEN` | — | empty | Webhook payload token auth |
| `FEISHU_GROUP_POLICY` | — | `allowlist` | `open` | `allowlist` | `disabled` |
| `FEISHU_BOT_OPEN_ID` | — | empty | Bot's open_id (auto-detected normally) |
| `FEISHU_BOT_USER_ID` | — | empty | Bot's user_id (for tenant-scoped ID apps) |
| `FEISHU_BOT_NAME` | — | empty | Bot display name (auto-detected normally) |
| `FEISHU_WEBHOOK_HOST` | — | `127.0.0.1` | Webhook bind address |
| `FEISHU_WEBHOOK_PORT` | — | `8765` | Webhook port |
| `FEISHU_WEBHOOK_PATH` | — | `/feishu/webhook` | Webhook endpoint path |
| `HERMES_FEISHU_DEDUP_CACHE_SIZE` | — | 2048 | Max deduplicated message IDs |
| `HERMES_FEISHU_TEXT_BATCH_DELAY_SECONDS` | — | 0.6 | Text burst debounce (seconds) |
| `HERMES_FEISHU_TEXT_BATCH_MAX_MESSAGES` | — | 8 | Max messages per text batch |
| `HERMES_FEISHU_TEXT_BATCH_MAX_CHARS` | — | 4000 | Max chars per text batch |
| `HERMES_FEISHU_MEDIA_BATCH_DELAY_SECONDS` | — | 0.8 | Media burst debounce (seconds) |

## Per-Group Access Control

Configure in `config.yaml` under `platforms.feishu.extra`:

```yaml
platforms:
  feishu:
    extra:
      default_group_policy: "open"
      admins:
        - "ou_admin_open_id"
      group_rules:
        "oc_group_chat_id_1":
          policy: "allowlist"
          allowlist:
            - "ou_user_open_id_1"
        "oc_group_chat_id_2":
          policy: "admin_only"
        "oc_group_chat_id_3":
          policy: "blacklist"
          blacklist:
            - "ou_blocked_user"
        "oc_free_chat":
          policy: "open"
          require_mention: false
```

| Policy | Description |
|--------|-------------|
| `open` | Anyone in group can use the bot |
| `allowlist` | Only users in group's allowlist |
| `blacklist` | Everyone except blacklist |
| `admin_only` | Only global admins |
| `disabled` | Bot ignores group |

## Interactive Card Setup

For approval buttons and interactive cards to work:

1. **Subscribe to event:** `card.action.trigger` in Event Subscriptions
2. **Enable capability:** App Features → Bot → Interactive Card toggle
3. **Webhook mode only:** Set Card Request URL to same as event webhook

All three are required. Missing any causes error 200340 when users click buttons.

## Document Comment Intelligent Reply

Hermes can answer @mentions on Feishu documents. Requires these **additional** permissions:
- Subscribe to `drive.notice.comment_add_v1`
- Grant `docs:doc:readonly` and `drive:drive:readonly`
- Access rules in `~/.hermes/feishu_comment_rules.json` (3-tier: exact doc > wildcard > top-level)

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `lark-oapi` not installed | `pip install lark-oapi` |
| `websockets` not installed | `pip install websockets` |
| `aiohttp` not installed | `pip install aiohttp` (webhook mode) |
| Bot doesn't respond in groups | Ensure @mentioned, check `FEISHU_GROUP_POLICY`, verify sender in `FEISHU_ALLOWED_USERS` |
| Webhook rejected: invalid signature | Set `FEISHU_ENCRYPT_KEY` matching Feishu Console |
| Error 200340 on button click | Missing interactive card setup (see above) |
| Another gateway using same app_id | Only one instance per app_id at a time |
| Bot identity not auto-detected | Set `FEISHU_BOT_OPEN_ID` and `FEISHU_BOT_NAME` manually |
| Post messages show as plain text | Normal fallback — Feishu API rejected the rich payload |
