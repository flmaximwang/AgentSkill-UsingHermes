# Discord channel access: why a connected bot can see nothing

The gate that decides whether a freshly wired bot is usable at all — run it before the mention
self-test in §0b, because an invisible channel cannot deliver a test message and the symptom
(silence, **no `inbound message` line**) is identical to an allowlist drop.

## Symptoms

- The adapter is connected (`✓ discord connected (profile: X)`, `[Discord] Connected as <bot>`,
  `gateway_state.json` state `connected`) and its permission integer looks healthy.
- `GET /guilds/<g>/channels` with the **bot's own** token returns almost nothing (or only category
  stubs) — this endpoint returns only channels that token can see.
- `GET /channels/<id>` with the bot's own token → `403 {"message": "Missing Access", "code": 50001}`.
- Nothing ever reaches the agent: no `inbound message`, no drop log, no error.

## Why the managed role is not enough

Effective channel permission = (@everyone guild perms ∪ the member's role guild perms), then the
channel's `permission_overwrites` are applied: the `@everyone` overwrite first, then overwrites for
roles the member actually carries, then any member overwrite. A **deny in the `@everyone` channel
overwrite** is only re-allowed by an **allow in a role overwrite for a role the member has**. So a
managed bot role whose integer contains `VIEW_CHANNEL` (`1024`) still loses to a channel-level
`@everyone` deny of `1024` — the role's own bit does not survive that overwrite.

The reverse case is just as common (a managed role *without* VIEW_CHANNEL, the `@everyone` union
supplying it). Never conclude from a permission integer; conclude from the effective overwrite set.

## Observed layout of a role-gated guild

- Every channel under a locked-down category carries two overwrites:
  - role `<access role>` → allow `1049600` (VIEW_CHANNEL `1024` | CONNECT `1048576`)
  - `@everyone` (the guild id) → allow `0`, deny `1049600`
- Custom roles with permissions `0` (team-membership labels) grant nothing at all.
- The access role is carried by every bot that works there, so a **newly invited bot is missing it**
  until someone adds it. The default bot and each working profile bot have it; the new one has only
  its own managed role plus a label role.
- A single channel may additionally carry a member overwrite allowing VIEW_CHANNEL for one bot.

## Read-only probe (two tokens: the new bot's, and one that works)

```bash
API=https://discord.com/api/v10
# 1 what the new bot sees — its own token
curl -s -H "Authorization: Bot $NEW" "$API/guilds/$G/channels"   # count + names; zero => gated
curl -s -H "Authorization: Bot $NEW" "$API/channels/$CH"        # 403 Missing Access => invisible
# 2 what the channel actually gates — a working bot's token
curl -s -H "Authorization: Bot $REF" "$API/channels/$CH"        # permission_overwrites[]
# 3 the decisive diff — role lists, not integers
curl -s -H "Authorization: Bot $REF" "$API/guilds/$G/members/$NEW_BOT_ID"   # roles[]
curl -s -H "Authorization: Bot $REF" "$API/guilds/$G/members/$REF_BOT_ID"   # roles[]
curl -s -H "Authorization: Bot $REF" "$API/guilds/$G/roles"                 # id -> name
```

The `roles` set difference between a working bot and the new one **is** the missing grant.
`scripts/discord_check.sh` gate 2b does steps 1 and 3 (`DISCORD_REF_ENV=<working profile>/.env`).

## Fix and handover

Adding the role is a guild mutation needing MANAGE_ROLES, and the gateway bots do not have it
(`274878024768` carries no `1<<28`) — so hand it to the user as a click path: Server → member list →
the bot → right-click → **Roles** → the access role. It applies immediately: no gateway restart, no
adapter rescan, no re-invite.

Only invite scopes and the bot's own role need the Portal; channel visibility is a server-side
role assignment.

## Integer decode used above

| Integer | Meaning |
|---|---|
| `1024` | VIEW_CHANNEL (the bit that decides visibility) |
| `1048576` | CONNECT; `1049600` = VIEW_CHANNEL + CONNECT — what a category-level allow/deny uses |
| `117760` | minimal bot set: VIEW_CHANNEL, SEND_MESSAGES, EMBED_LINKS, ATTACH_FILES, READ_HISTORY |
| `274878024768` | this guild's working-bot role: the minimal set + ADD_REACTIONS + SEND_MESSAGES_IN_THREADS |
| `309240908864` | a freshly created app's managed role: minimal set + CREATE_PUBLIC_THREADS + SEND_MESSAGES_IN_THREADS |
| `2248473465835073` | a permissive `@everyone` — a large number proves nothing on its own |

Compare **bits**, never totals.

## Cleanup after the delivery test

Sending a test mention from another bot leaves a message: `DELETE /channels/<ch>/messages/<id>` →
`204` removes the starter. A thread the mention auto-created cannot be deleted without
MANAGE_THREADS (403 / 50013); the adapter that owns it can `PATCH {"archived": true,
"locked": true}`. Report what could not be cleaned instead of claiming a clean sweep.
