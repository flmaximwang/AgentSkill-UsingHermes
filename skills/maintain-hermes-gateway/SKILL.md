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

## 0. 上线一个 Discord bot（拿到 app id + token 就照这个走）

**这一节只有 5 步，没有研究。** 不查 `flags`、不解析权限整数、不 diff 角色、不探频道、不跑自测、
不去别的 profile 里抄值 —— 这些都不属于上线流程。第 5 步失败时才进 §1–§7。

- app 还没建：<https://discord.com/developers/applications> → **New Application**（复制 Application ID）→
  **Bot** 页开 `MESSAGE_CONTENT` + `GUILD_MEMBERS`、点 **Save Changes** → **Reset Token** →
  用 §6 的显式 scope 链接邀请。做完进第 1 步。
- app 已建好：凭证文件两行 —— 第一行 app id、第二行 bot token。

1. **`clarify` 一次问完这四项**，由用户给，不许自己推、不许抄别的 profile：
   - `DISCORD_ALLOWED_USERS` —— 谁能 @ 这个 bot（user id，逗号分隔）
   - `DISCORD_HOME_CHANNEL` —— 主动推送（cron 投递、关机通知）落哪个频道
   - `DISCORD_HOME_CHANNEL_NAME` —— 上面那个频道的显示名
   - `DISCORD_ALLOW_BOTS` —— 建议 `mentions`
2. 追加写 `$HERMES_HOME/profiles/<name>/.env`：`DISCORD_BOT_TOKEN`、`DISCORD_APPLICATION_ID`，
   加上第 1 步那四项。
3. 写 `profiles/<name>/config.yaml` 的 `discord:` 段：`require_mention: true`、
   `thread_require_mention: true`、`auto_thread: true`、`allow_bots: <第 1 步的值>`。
   **不要**加 `platforms.discord.enabled` —— 有 token 就自动启用（§4c）。
4. 等 multiplex watcher 自己接上（约 60 s），**不要 `gateway restart`**（那会把所有 bot 一起闪掉一分钟）。
   接上的唯一证据是一行 `✓ discord connected (profile: <name>)`。
5. 请用户在那个频道 @ 一次 bot。日志出现 `inbound message` + `response ready` 即完成，报告到此为止。

> 第 5 步没反应，最常见的原因是**频道对该 bot 不可见**：频道级 `@everyone` deny 掉 VIEW_CHANNEL 会盖过
> bot 自己的角色，症状是**一条 `inbound message` 都没有**（与 allowlist 丢弃不可分）。手法、权限解码与
> 用户侧点击路径见 `references/discord-channel-access.md`；其余按 §1 的日志优先顺序排查。

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

### `ack_stale` loop: REST healthy, WebSocket not

A distinct failure mode from the above: the proxy passes REST traffic fine (curl → 200) but
interferes with WebSocket heartbeat/ACK frames. Log signature:
`Discord Gateway WebSocket unhealthy (ack_stale, 1/2)` → `(ack_stale, 2/2)` →
`forcing reconnect` → `Disconnected`, with **no reconnect attempts afterward** (unlike the
`Cannot connect to host` case which retries at 30/60/120/240/300 s). The bot may connect once
(`Connected as <bot>#<nnnn>`) then drop 60–90 s later with `ack_stale`. This is a proxy-level
issue even though REST API calls succeed — the proxy is dropping or delaying WebSocket frames.

Diagnosis: `curl -x http://127.0.0.1:<port> https://discord.com/api/v10/gateway` → 200 proves
REST is fine but says nothing about WS. Grep the per-profile log for `ack_stale` — if present,
the proxy is the cause even though the REST probe succeeds. Fix: restart the proxy core, then
`hermes -p <profile> gateway restart` to force a clean WS handshake.

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

### A bot offline while the gateway process is up: read the per-platform state, not the pid

`gateway_state.json` holds one entry per platform under `platforms` (`<profile>:<platform>` in a
multiplexed setup), and *that entry* — not the process, not `gateway status` — says which bot is down.
`"state":"retrying"` with `error_message: Discord startup failed: Cannot connect to host
discord.com:443 ssl:default [None]` means the adapter is alive and inside its own retry loop, whose
backoff climbs 30 → 60 → 120 → 240 → 300 s; the last thing you see before a long wait is that 300 s
timer, and a retry pending at that moment is the whole story.

Measured on the DS220+ (2026-10-09): sockets dropped 16:45:40, attempts 1–5 failed 16:45:51 → 16:53:57,
attempt 6 at 16:58:57 reconnected (`[Discord] Connected as DS220p2022#0029`) and the multiplexed
`light` profile 4 s earlier — **13 m 25 s dark, no operator action, no restart**. The proxy path was
already healthy 2 minutes before the next tick (3× `curl -x http://127.0.0.1:<mixed-port>
https://discord.com/api/v10/gateway` → `http=200`).

- **Do not restart while a retry is pending** — a restart only skips the rest of the backoff. Confirm
  the proxy path, then either wait for the tick or restart once if the bot must be back this minute.
- **Attribute through the proxy's per-domain dial, not through "is the proxy running".** The core's
  own log holds `dial 🚀 节点选择 (match DomainSuffix/discord.com) … error: failed to create session:
  context deadline exceeded` for exactly the failing minutes, while the proxy watchdog's probe on a
  *different* domain answered healthy in the same hour: the group pinned for that domain was dead,
  the proxy was not.
- **A `<profile>:<platform>` entry reading `fatal` is not proof the adapter gave up.** Measured: the
  `light` entry was written `fatal` (`… [Connection reset by peer]`) at 16:53:53, and that profile's
  adapter was connected at 16:59:01 with no operator action. Read the profile's own
  `logs/gateway.log` (`Secondary discord reconnect retry in <n>s (profile: <p>)`) and its retry
  cadence before concluding that only a whole-gateway restart brings it back.
- **No pid-level watchdog can see this state.** The gateway held an ESTABLISHED socket (another
  platform, feishu) for the whole 13 minutes, so a "pid alive + any ESTABLISHED socket" predicate
  reads healthy while Discord is dark. Give the predicate the platform's own signal —
  `platforms.discord.state == "connected"`, or ESTABLISHED sockets to that platform's hosts.

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
| Online, no reply anywhere, **no `inbound message` line at all** | It cannot see the channel — channel overwrites / role-gated visibility (§0 末段, `references/discord-channel-access.md`) |
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

## 4d. `gateway restart` from inside a gateway session: you cannot; hand it over

The terminal tool **refuses it by design** — `Blocked: command or referenced script cannot restart,
stop, or uninstall the gateway from inside the gateway process`, with the reason in the same line:
SIGTERM reaches the child mid-command, so the command never completes, and the turn that ordered it
dies with it. Do not reach for a wrapper to sneak it through (a detached
`sh -c 'sleep N; hermes gateway restart'`, a `launchctl kickstart` of the gateway job): the same guard
fires, and a restart that lands *after* the reply reads to the user as a random outage.

Hand it over instead — **first thing in the reply**, with the cost in the same sentence: run
`hermes gateway restart` in your own terminal → every profile's bot blips ~1 min, and the change (a
new plugin, a provider switch, a config edit) only takes effect after it.

One case is genuinely optional: switching the active **memory provider** needs only a *new session*
(the installer prints "new sessions use it" — the provider is resolved when an agent session is
built), so say which one you are asking for: `/new` in that chat, or the full restart.

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
├── SKILL.md  (507 lines)
└── references/
    ├── discord-channel-access.md  (84 lines)
    ├── local-proxy-outbound-triage.md  (113 lines)
    └── multiplex-config-apply.md  (89 lines)
```

<!-- Generated by Scripts -->
