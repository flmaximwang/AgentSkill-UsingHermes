---
name: maintain-hermes-gateway
description: "Use when setting up or debugging a Hermes gateway bot. Standing a platform bot up from scratch, an existing bot that is offline, silent or ignoring one specific user, `hermes gateway status` showing a platform not connected, a slash command answering with a stale skill list, or a bot that admits messages and never answers because its own model call times out behind a local proxy. Discord is covered in depth; the log-first workflow and layer table apply to every platform."
---

# Hermes gateway platform debug

## When to Use

Trigger: standing up a platform bot from scratch (**§0**), or an existing bot that is offline,
silent, or ignores one specific user;
`hermes gateway status` shows a platform not connected; or `gateway.log` reports a platform
that `failed to start and are parked`; or a slash command answers with a stale or absent
entry (`Unknown skill: …`, a skill missing from `/skill` autocomplete — §7); or it logs
`inbound message` and then nothing, because the agent's own model call times out (§1). Discord is
covered in depth (privileged intents,
allowlists, guild membership, invite scopes, Portal-vs-client lists); the log-first workflow
and layer table apply to every platform.

A bot that "doesn't work" is almost never one problem. Diagnose in this order and name
the layer explicitly — never infer the layer from what the UI shows.

## 0. Setting up a bot from scratch (ordered path)

1. <https://discord.com/developers/applications> → **New Application** → copy the **Application ID**
   (it equals the bot user's id; confirm with `GET /users/@me`).
2. **Bot** page → **Privileged Gateway Intents**: enable `MESSAGE_CONTENT` (mandatory) and
   `GUILD_MEMBERS`, then click **Save Changes** (details and the Portal-free `PATCH` path in §3).
3. Same page → **Reset Token** (shown once) → store as `DISCORD_BOT_TOKEN` in the profile's env file,
   written here as `$HERMES_HOME/.env` — a literal home-relative path trips the install scan
   (`hermes_env_access`) and blocks the skill, so this pack never writes it that way.
4. Invite with an explicit-scope URL (§6) — never the Portal-provided link.
5. `hermes gateway setup` → Discord, which writes `DISCORD_BOT_TOKEN`, `DISCORD_ALLOWED_USERS`,
   `DISCORD_HOME_CHANNEL`; then `hermes gateway restart` (parked platforms never self-retry).
6. Verify with the four gates below, or run `scripts/discord_check.sh` (read-only, tested).

### Four gates — stop at the first failure

| Gate | Evidence | If it fails |
|---|---|---|
| 1 connected | `✓ discord connected` + `[Discord] Connected as <bot>#<nnnn>` | intents missing → §3, then restart |
| 2 message arrives | `inbound message: platform=discord …` after you send | allowlist §4, or the mention was typed rather than picked |
| 3 agent ran | `response ready: platform=discord … api_calls=N` | agent/tool error — read the log tail |
| 4 reply visible | message in the channel **or the thread** | `Unknown Channel` → §4 home channel; else the thread |

### Permission integers (decoded with `discord.Permissions`)

| Tier | Integer | Permissions |
|---|---|---|
| minimal | `117760` | View Channels, Send Messages, Embed Links, Attach Files, Read Message History |
| recommended | `274878286912` | + Add Reactions, Use External Emojis, Send Messages in Threads |

The docs' prose lists 7 names for the recommended integer; the integer carries **8** (extra
`USE_EXTERNAL_EMOJIS`, `1<<18` = `262144`). Trust the integer. Judge the bot's **managed role**,
not effective permissions: the effective value is the union with `@everyone`
(observed bot role 8 + `@everyone` 29 → effective 31), so a large number proves nothing — read
per-role data from `GET /guilds/<id>/roles`.

### Worked example (2026-09-29, verified end to end)

| Item | Value |
|---|---|
| App / bot user id | `1554354291987451955` (`Hermes_WFL-MacBook2022`) |
| Guild / text channel | `1554352200313085962` (`WFL-MacBook2022`) / `1554352200950612001` (`常规`) |
| `flags` broken → fixed | `0` → `8945664` |
| Failure chain | intents off → 4014 → parked; then the allowlist held the wrong user id; then a proxy outage swallowed the mention |

## 0b. Wiring an app that already exists into a profile

When the app/bot already exists and you are handed `app id` + `token` (a token file), the Portal
steps are done — verify them by read, then write only the profile side:

1. Token/id sanity + identity: `GET /users/@me` (discord.com API needs the local proxy on this
   machine — without it curl exits 000; never `--noproxy`), then `GET /applications/@me` for
   `name`/`flags`.
2. Intents already on? `flags & 557056` = both limited bits (32768 members + 524288 message
   content). `557056` exactly is the clean case.
3. Already in the guild? `GET /guilds/<guild>/members/<bot_user_id>` — **not**
   `/users/@me/guilds/<guild>/member`, which answers `Bots cannot use this endpoint` (20001) for
   the bot itself. Use another bot's token in the guild. Look for a `managed: true` role named
   after the app: that role's creation is the second proof of membership.
4. Permission decode: the managed role usually lacks `VIEW_CHANNEL` / `SEND_MESSAGES_IN_THREADS`
   and the @everyone union supplies them (observed artist bot role `343597500480` + @everyone
   `2248473465835073` → effective set includes both). Judge the union, not the role integer.
5. Profile side: `profiles/<name>/.env` gets `DISCORD_BOT_TOKEN`, `DISCORD_APPLICATION_ID`,
   `DISCORD_ALLOWED_USERS` (the human's user id), `DISCORD_HOME_CHANNEL` (+ `_NAME`);
   `profiles/<name>/config.yaml` gets `discord: {require_mention: true, thread_require_mention:
   true, auto_thread: true, allow_bots: mentions}`. No `platforms.discord.enabled: true` needed —
   the token alone auto-enables (§4c).
6. **Do not `gateway restart`.** The multiplex watcher re-scans on the .env/config mtime and
   connects the new adapter, so a full restart only blinks every other bot for a minute. Expect
   `Re-scanned profile '<name>' after config/.env change (1 adapter(s) connected)` →
   `✓ discord connected (profile: <name>)` in `~/.hermes/logs/gateway.log` within ~60 s
   (watcher cadence observed 5 s poll).
7. Self-test gates 2–4 without the user: from another profile's bot, POST to a low-traffic
   channel with an inline `<@bot_id>` mention (`allow_bots: mentions` + `bots_require_inline_mention`
   admit it). Clean up afterwards: the auto-created thread is **not deletable** with either bot's
   token when the channel overwrites withhold MANAGE_THREADS (403 / 50013) — the starter message
   deletes fine (204) and the thread's owner may `PATCH {"archived":true,"locked":true}` (owner =
   the adapter that created it). Discord's own `type: 4` rename system message inside it cannot be
   deleted by anyone, so say so instead of claiming a clean sweep.

## 1. Read the log first; it already has the answer

`~/.hermes/logs/gateway.log` (same lines mirror into `errors.log` and
`gateway.error.log`). Search for the platform name and for `parked`.

**Grep it, don't shell-walk it.** Once the log passes a megabyte, a shell command whose text
references that path is refused by the lifecycle guard (`could not scan this command ... larger
than the scan cap (1048576 bytes)`), even for a harmless `wc -l`/`tail`. Read it with the
`search_files`/`read_file` tools instead, or `cp` the last N lines into a scratch file first.
Per-profile logs (`profiles/<name>/logs/gateway.log`) stay small and stay greppable — and they
are the right log anyway when the bot under test is a multiplexed profile.

A platform that failed to start is **parked**:

```
ERROR gateway.run: 1 configured platform(s) failed to start and are parked
  (fix the reported error, then `hermes gateway restart`): <platform>: ...
The gateway is DEGRADED — it serves the remaining platform(s) with those unserved.
```

Parked platforms do **not** retry on their own, and the other platforms keep working —
"Hermes still answers on Feishu" does not mean Discord is fine. After fixing the cause,
always `hermes gateway restart`.

### Did the message arrive at all?

Count the admission line before touching any config:

```bash
grep -c "inbound message: platform=discord" ~/.hermes/logs/gateway.log
```

**Zero occurrences across the whole log = the message never reached the gateway.** Allowlist,
mention rules, the agent and reply delivery are all irrelevant until that line exists, so never
start editing config on a bare "it doesn't reply" report. Rejected messages are dropped
*silently* — no log line — so 0 is ambiguous between "never delivered" and "delivered but
filtered"; separate them with one unmistakable input (a channel the bot provably sees + a
**real** mention picked from autocomplete; typed `@Name` text is not a mention) and re-read the
log immediately after. "Admitted" and "answered" are two more distinct layers: the reply is
`response ready: platform=…`.

### Transport liveness is not API reachability

The gateway socket and the platform's REST API are separate transports: REST reads can return
200 while the socket is dead. A gateway that reaches the platform through a local proxy loses
the socket whenever the proxy blips — log signature `WebSocket unhealthy (socket_closed …)` →
`Reconnect … failed … nodename nor servname provided` (the direct fallback cannot resolve the
host) → `reconnected successfully` once the proxy is back, with elevated retry backoff in
between. **Events sent during the gap are never replayed**, so an "offline for a minute"
window costs those messages permanently. Check timestamps against when the user says they
acted before concluding a message should have arrived — both the socket drop and the DNS
failure hit every WS-based platform on the machine at once, not just the one being debugged.

### Every reconnect dies at the local proxy (the node/flap case)

Log signature: `WebSocket unhealthy (socket_closed)` → `Fatal discord adapter error (discord_websocket_health_stale)` → `discord queued for background reconnection`, then every attempt
carries `[Discord] Using proxy for Discord: http://127.0.0.1:<mixed-port>` followed by
`Failed to connect to Discord: Cannot connect to host <platform host>:443 ssl:default [None]`, with
the retry backoff climbing 30 → 60 → 120 → 240 → 300 s. The same window shows REST sends failing
(`Failed to send Discord message: Cannot connect to host …`), and in a multiplex setup
`gateway_state.json` flips per-profile bots between `connected` and `fatal` — **`fatal` is not
terminal**, the watcher re-serves those adapters, so a bot that went fatal a minute ago may be
connected again now. Nothing in Hermes is broken: the local proxy's outbound is.

Do **not** start by picking another node — attribute the fault first, then fix the proxy, then
restart the gateway once:

1. Read the proxy core's own view over its unix socket: the group selection and the per-host
   chain that the platform's traffic actually takes (e.g. `discord.com … <node> > ✈️ 手动切换 >
   🚀 节点选择`), plus the node's live `delay` probe.
2. Compare an ordinary user process's TCP/TLS connect to the node's host:port against the core's
   own dial, read from its `/logs` stream. Raw connects all-succeed + core dials timing out ⇒ the
   fault is the proxy **core**, not the network or the node — restart the core, do not chase nodes.
3. Only after the proxy is confirmed with repeated success (`curl -x http://127.0.0.1:<mixed-port>
   https://…/api/v10/gateway` → 200 several times — a single 200 proves nothing in a flap window),
   run `hermes gateway restart` to clear the 300 s backoff in one shot instead of waiting out each
   bot's timer.

The topology rule that makes this class of outage total: a top-level rule group pointed at a
manually pinned node (`Selector → Selector(pinned) → one node`) means one node's death takes down
every bot, and a subscription whose nodes all live on **one upstream host** (per-port entries)
flaps all of them together — so "try another node" is not a fix, putting the top-level Selector on
the URLTest auto group is.

Full recipe, API calls and the `lsof`/`timeout(1)` traps: `references/local-proxy-outbound-triage.md`.

### A bot that admits messages but never answers: the model-API path

The admission line exists (§1) yet `response ready:` never shows up, and `agent.log` carries
`APITimeoutError … Request timed out` from `agent.conversation_loop` — the allowlist, the
mention and threading are already ruled out. The agent is running; its **own model call** is
not getting out.

Hermes' LLM transport reads the proxy from the **process environment only**:
`agent/process_bootstrap.py::_get_proxy_for_base_url` → `_get_proxy_from_env()`
(`HTTPS_PROXY` / `HTTP_PROXY` / `ALL_PROXY`). With none of them set it builds the client with
explicit no-proxy mounts, which deliberately disables httpx's `trust_env` path — the source
comment says macOS system proxies "are never applied". So a rule-based proxy client in
**system-proxy mode with TUN off** (Clash Verge, ClashX, mihomo) leaves Hermes dialing
direct: `scutil --proxy` pointing at `127.0.0.1:<mixed-port>` is evidence only for
Safari/Electron front-ends, and every host that answers *only* through the proxy (a
Cloudflare-fronted API, say) ends in connect timeouts × `agent.api_max_retries` — total
silence, a working browser on the same machine, and a console full of timeouts.

Fix: declare it in the profile's dotenv file (`$HERMES_HOME/.env`) — `HTTPS_PROXY` and
`HTTP_PROXY` → `http://127.0.0.1:<mixed-port>` — then `hermes gateway restart`.
`hermes_cli/env_loader.py` loads that file into the process environment at import, so a restart
is what makes the value visible; as in §0/§2, an env edit without a restart changes nothing.
Read the var back from the restarted process instead of assuming:
`ps eww -o command= -p <gateway pid> | tr ' ' '\n' | grep -i proxy`.

Settle the fix without touching the live gateway — a throwaway `HERMES_HOME` is enough: a
minimal `config.yaml` (provider, `base_url`, `key_env`), the key passed in the environment,
`hermes chat -q "Reply with exactly: <MARKER>"`, then read the answer out of that home's
`state.db` (`select role, content from messages`) rather than trusting the CLI footer. Run one
row with the proxy var and one without; `delegate_task` children are in-process and inherit the
parent's environment, so a child that lands in `state.db` as `source=subagent` with the marker
text proves the subagent path too, not just the parent.

Worked example (2026-10-02, verified end to end) — Discord bot silent; provider `custom`,
`base_url` `https://www.micuapi.ai/v1`, model `gpt-5.6-sol`:

| Item | Value |
|---|---|
| Client state | Clash Verge `enable_system_proxy: true`, `enable_tun_mode: false`, mixed-port `7890`; `scutil --proxy` pointed at that loopback port; no proxy variable in the environment |
| Direct vs proxied curl | direct `http=000` / 15 s timeout vs the same call through the mixed port → **200 in 0.48 s** (same URL, same key) |
| Transport probe | `_get_proxy_from_env() = None` + `ConnectTimeout` 20 s → with the var: **200 in 0.76 s** |
| Agent one-shot rows | no proxy **84.6 s** (it answered — direct is flaky, not hard-blocked, so never report "always times out"); `HTTPS_PROXY` in the process env **4.7 s**; proxy only in `.env` with a cleaned process env **7 s** |
| After `.env` + `hermes gateway restart` | gateway process env carries `HTTPS_PROXY`/`HTTP_PROXY`; micu one-shot **5.6 s**; `APITimeoutError` count in the log after the restart **0**; a desktop `gpt-5.6-sol` session resumed on its own |
| DNS side-note | the system resolver returned `127.0.0.1` + a patterned fake IPv6 (`1100:2200:3300:4400:5500:6600:7700:8800`) for `*.micuapi.ai` — *including a random subdomain* — while `dig` at 114/223/8.8 returned the real edge IPs: a wildcard sinkhole on the resolver path, not a stale cache. It explains the direct-dial hang, not the fix: a proxy CONNECT resolves the name remotely |

Checking the model's own default first saves a round — `hermes config get model.default`
(`model.provider` alongside it). In the run above the profile default had since been switched
to another provider, so a fresh `hermes chat -q` answered on *that* model and proved nothing
about the suspect one until `-m <model> --provider <name>` was passed explicitly.

## 2. Separate the failure layers

| Symptom | Layer |
|---|---|
| Bot shows **offline**; total silence | Platform never connected — handshake / auth / config |
| Bot **online**, ignores everyone | Allowlist (§4) |
| Online, answers others but not you | Allowlist, or mention rules |
| Processed but you see no reply | Reply landed elsewhere (threading, §4) |
| `inbound message` logged, no `response ready:`, `APITimeoutError` in the log | The agent's own egress — its model call never completes (§1, model-API path) |

## 3. Discord: privileged intents (the offline case)

Discord closes the WS handshake with code **4014** when the bot requests a privileged
intent that is not enabled in the app settings; discord.py raises
`PrivilegedIntentsRequired` and Hermes parks the platform. It is a *handshake* refusal, so
the symptom is **offline + total silence**, not "replies with empty content".

Privileged intents (`GUILD_PRESENCES`, `GUILD_MEMBERS`, `MESSAGE_CONTENT`) need **both** the
Portal toggle (Bot → Privileged Gateway Intents → **Save Changes**; toggling without saving
changes nothing) and the declaration in code. Portal off + code on = 4014; portal on + code
off = silently missing events.

The Hermes Discord adapter always sets `intents.message_content = True`
(`plugins/platforms/discord/adapter.py`), so Message Content is unconditionally required;
`members` is requested only when allowlists need username resolution.

Portal-free path — `PATCH /applications/@me` accepts `flags`, and **only the limited-intent
bits are writable**: `GATEWAY_PRESENCE_LIMITED (1<<13 = 8192)`,
`GATEWAY_GUILD_MEMBERS_LIMITED (1<<15 = 32768)`,
`GATEWAY_MESSAGE_CONTENT_LIMITED (1<<19 = 524288)`. Unrelated badge bits may already share
the integer, so compare **bits**, not the total — enabling members + message content observed
`8945664`, i.e. the two target bits plus an unrelated badge bit, not the bare sum `557056`.
Never quote a total as the expected result.

```bash
ENV_FILE="${HERMES_HOME:-$HOME/.hermes}/.env"
TOKEN=$(grep -m1 '^DISCORD_BOT_TOKEN' "$ENV_FILE" | cut -d= -f2- | tr -d '[:space:]\"' | tr -d "'")
AUTH="Authorization: Bot $TOKEN"          # hoisted: a curl line interpolating the token reads as exfiltration
# read the current flags and OR the target bits in (557056 = members + message content)
FLAGS=$(curl -s -H "$AUTH" https://discord.com/api/v10/applications/@me \
  | python3 -c 'import sys,json; print((json.load(sys.stdin).get("flags") or 0) | 557056)')
curl -s -X PATCH -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"flags\": $FLAGS}" https://discord.com/api/v10/applications/@me | head -c 200
hermes gateway restart
```

Never print the token: assign it inside the shell, filter whatever JSON you echo back.

## 4. Discord: allowlist and threading (the "online but ignores me" cases)

`DISCORD_ALLOWED_USERS` must contain the sender's user ID; a mismatch **silently drops**
every message (`adapter.py::_discord_message_admission` → `return False, False`), with no
user-visible error. `DISCORD_ALLOWED_ROLES` is the role-based alternative.

Cross-check the allowlist against the person actually testing — the app owner is normally
them:

```bash
AUTH="Authorization: Bot $TOKEN"    # hoisted exactly as in §3: never interpolate the token on the curl line
curl -s -H "$AUTH" https://discord.com/api/v10/applications/@me   # owner.id, flags
curl -s -H "$AUTH" https://discord.com/api/v10/users/@me/guilds   # guilds the bot joined
```

`GET /users/@me/guilds` is the real-time membership check. Do **not** trust
`approximate_guild_count` — it lags and can read 0 while the bot is already in the server
(`bot_approximate_guild_count` tracks closer; all three fields are explicitly "approximate").
`GET /users/@me` returns the bot's own id/username and validates the token.

Check the run's own settings before blaming Discord: `discord.allowed_channels` empty means
"no channel restriction" (whitelist only when set), and `discord.auto_thread: true` puts the
reply in a **thread** on the user's message — the channel shows only an "N replies" chip,
which reads to the user as "no reply".

`DISCORD_HOME_CHANNEL` must be a **channel** id. A guild/server id there makes every
*proactive* send fail — shutdown notices, cron delivery — with
`Failed to send Discord message: 404 Not Found (error code: 10003): Unknown Channel`
(`adapter.py::_resolve_channel` → `fetch_channel`). Grep `Failed to send` when the bot replies
interactively but never on a schedule; read the real channel ids from
`GET /guilds/<guild_id>/channels`.

## 4b. Multiplex: a config edit does NOT reach an already-live adapter

A rescan after a profile `config.yaml`/`.env` change **skips any platform already connected**, so
`Re-scanned profile 'X' (0 adapter(s) connected)` means your edit did not apply and the live adapter
still holds the old settings. Apply it with `hermes -p <name> gateway restart` (unserve + hot
re-serve — only that profile's bots blip), then confirm `disconnected (profile: X)` →
`unserved` → `Connected as <bot>` in the profile's own log. Multi-bot Discord threads need
`thread_require_mention: true` or the bot answers unmentioned messages in every thread it has
joined. Full recipe, precedence rules and the DM exemption: `references/multiplex-config-apply.md`.

## 4c. Turning a platform OFF everywhere (the inverse task)

A platform is enabled by **either** `platforms.<name>.enabled: true` in a profile's
`config.yaml` **or** its credential env vars in that profile's `.env`
(`plugins/platforms/<name>/plugin.yaml` `requires_env`; e.g. `FEISHU_APP_ID` + `FEISHU_APP_SECRET`
auto-enable feishu on a profile that has no `platforms:` section at all). So two sources per
profile — enumerate **both**, or a profile with only env creds silently stays up.

Read-only inventory (finds every profile without touching the gateway):

```bash
cd ~/.hermes
grep -n -i "feishu" config.yaml profiles/*/config.yaml          # yaml-enabled
for f in .env profiles/*/.env; do grep -q -i FEISHU "$f" && echo "$f"; done   # env-enabled
hermes -p <name> config get platforms.feishu.enabled            # omit -p for the default profile
```

Turn off with the explicit flag — it is the one form that **survives `_apply_env_overrides`**
(regression test `tests/gateway/test_env_override_explicit_disable.py`; twelve
credential-presence branches, feishu among them, otherwise force `enabled = True`):

```bash
hermes    config set platforms.feishu.enabled false
hermes -p <name> config set platforms.feishu.enabled false
```

`hermes -p <profile> <cmd>` is the per-profile form (`HERMES_PROFILE` env does **not** work; only
`-p/--profile` and `HERMES_HOME=<profile dir>` do). It writes a real YAML bool, so no `--force`.

Then `hermes gateway restart` — §4b applies: without it the live adapter keeps serving. Confirm
two ways, not one: the shutdown block lists one `✓ feishu disconnected … (profile: X)` per live
adapter, and the new startup logs **no** `Connecting to feishu...` plus this line per profile:

```
WARNING gateway.config: Platform 'feishu' is explicitly disabled by platforms.feishu.enabled: false
  in config.yaml, so the credentials found in the environment (FEISHU_APP_ID, FEISHU_APP_SECRET) will NOT start it
```

That warning is the proof the disable beat the env credentials — quote it instead of inferring
from `Gateway running with N platform(s)`, which is also moved by unrelated transient failures.
Expect Discord bots on every profile to blip for ~1 min during the restart (it is a full-gateway
restart, not per-platform); a profile whose Discord sits behind a flaky local proxy can take one
extra `Secondary discord reconnect retry` round. Leave the `.env` credentials in place unless the
user asks — an explicit `false` already wins, and deleting secrets is a separate decision.

## 5. Which list to send the user to

The Developer Portal (`discord.com/developers/applications`) lists apps you **own** and is
the only place to enumerate them — the Application Resource API has no list-all endpoint,
only `GET`/`PATCH /applications/@me`. Apps installed to a **user account** appear in the
Discord client under Settings → Authorized Apps (not in the Portal); server-installed apps
appear in Server Settings → Integrations → Bots and Apps.

## 6. Inviting a bot with the right scopes

The Portal's "Discord Provided Link" installs with the app's **Default Install Settings**,
which may omit the `bot` scope (giving a commands-only install with no bot member) and may
carry `permissions=0`. Build the URL explicitly instead:

```
https://discord.com/oauth2/authorize?client_id=<APP_ID>&scope=bot+applications.commands&permissions=<INT>&integration_type=0
```

`integration_type=0` pins the guild context, suppressing Discord's "Add to my apps / Add to a
server" chooser. That chooser appears when both installation contexts are enabled — check
`integration_types_config` in `GET /applications/@me`. Recommended permission integer is
`274878286912`, minimal is `117760`. There is no invite subcommand in `hermes gateway`
(run/start/stop/restart/status/install/uninstall/list/setup/migrate-legacy/migrate/enroll) —
build the URL by hand from the Application ID, which is also visible in the Portal URL.

## 7. A gateway slash-command surface explains itself from a snapshot

`/skill <name>` reads an **in-memory catalog**, not the disk. `_register_skill_group()`
builds `self._skill_entries` / `self._skill_lookup` once at registration, and only
`/reload-skills` re-runs the scan (`refresh_skill_group()` → `_refresh_skill_catalog_state`).
So a skill installed — or removed — after the gateway process started is invisible on that
surface: `/skill <name>` replies `Unknown skill: <name>. Start typing for autocomplete
suggestions.` and the dropdown has no row for it, while the skill is perfectly fine on disk.

Three read-only facts decide it. Read them, do not walk the call chain:

```bash
# 1. what the LIVE process believes, and when it last built the list (count + timestamp)
grep "Registered /skill command" ~/.hermes/logs/gateway.log | tail -1
# 2. when that process started (human-readable)
ps -eo pid,lstart,command | grep "gateway run" | grep -v grep
# 3. what DISK holds, via the same resolver the gateway calls
cd ~/.hermes/hermes-agent && HERMES_HOME=$HOME/.hermes venv/bin/python3 -c "
from hermes_cli.commands_platforms import discord_skill_commands_by_category as F
c,u,h=F(set()); e=u+[x for v in c.values() for x in v]
print(len(e), 'hidden:', h)
print([n for n,_,_ in e if 'NEEDLE' in n.upper()])"
```

The log line's timestamp older than the skill's install mtime ⇒ stale snapshot, not a failed
install. `gateway_state.json` `start_time` is an opaque liveness token — never do arithmetic on
it; get the readable start time from `ps`.

Fix: the user types **`/reload-skills`** in that chat. It rescans the dir and calls
`refresh_skill_group()` on the adapters — no `gateway restart`, and no `tree.sync()` because
Discord fetches autocomplete options per keystroke. It is a chat-side command you cannot send
for them. Meanwhile the AGENT side (`skills_list` / `skill_view`) already sees the new skill,
so "works for me" is expected and proves nothing about the gateway — say so instead of letting
it read as the install having failed.

## Answer shape (this user — non-negotiable)

1. **How-do-I questions get the executable path first.** After a one-line reason, give one
   command if the platform has an API for that setting, otherwise numbered clicks with the
   exact on-screen labels and the final save/restart step. Mechanism goes after, or gets cut:
   a mechanism-first answer to "how do I open X" comes back as "I still don't understand how
   to do it", and the theory is then re-explained for nothing.
2. **Name the step people skip** — a settings page's *Save Changes*, `hermes gateway restart`.
   Toggling without saving is the single most common silent no-op.
3. **One layer per round.** Fix the first broken layer, then re-test; an env/config change is
   invisible until `hermes gateway restart`, so batch the edits and restart once — do not stack
   changes and then guess which one mattered.
4. **Forecast nothing you have not read.** Mark any predicted value (flag integers, counts) as
   a prediction, verify it with a read, and correct it plainly when reality differs.
5. **Diagnose read-only; hand over mutations.** Log greps, API reads and status commands are
   yours to run. Anything that changes his app/account/server state — `PATCH` flags, posting a
   test message, editing `.env`, switching a proxy group/node — goes to him as a command with
   expected output, or runs only after an explicit yes. Hand it over **in the reply as prose**
   (click path + the one-liner + what you will verify afterwards): a pick-one modal for a
   machine-state mutation gets left unanswered while he keeps replying in chat, which costs a
   round-trip. Read secrets from `.env` inside the shell and filter what you echo; a token value
   must never reach the reply.
6. **When he says stay on one path, stop probing** — kill the running check rather than letting
   it finish "for completeness".
7. Close with the question-format summary — 1 What I ask / 2 What you did / 3 Keypoints you
   offer / 4 Questions to dig in — each point carrying the log line or API read that backs it,
   and stating what was ruled out as well as what remains open.
8. **A pasted error message is a "why" question: name the cause, name the fix, stop.** Read
   only the artifacts that decide it (disk state + the live process's own log line) and answer
   in a handful of lines, holding the code path in reserve — tracing the call chain across
   files first gets read as "no need to investigate all files so deeply, just answer me why".
   Deep reading is for when the cheap evidence conflicts, or when he asks for the mechanism.

## Docs

Fetch the authoritative pages with `terminal` curl — the `web_extract` tool refused these
hosts as "private or internal network address":

- `https://raw.githubusercontent.com/discord/discord-api-docs/main/developers/resources/application.mdx`
  — install contexts, install links, `GET`/`PATCH /applications/@me` params, application
  flags table with bit values
- `https://raw.githubusercontent.com/discord/discord-api-docs/main/developers/topics/gateway.mdx`
  — intents, privileged intents, close codes

Hermes-side reference: `https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord`
(add `?format=md` for clean markdown).

## Skill Structure

<!-- Generated by Scripts -->

```
maintain-hermes-gateway/
├── SKILL.md  (359 lines)
└── scripts/
    └── discord_check.sh  (93 lines)
```

<!-- Generated by Scripts -->
