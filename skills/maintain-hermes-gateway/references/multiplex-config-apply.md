# Multiplex: making a per-profile platform config edit actually apply

## A config edit does NOT reach an already-live adapter

The 30s profile watcher (`gateway/run_profile_reconcile.py`; signature = mtime/size of the served
profile's `config.yaml` + `.env`) fires a rescan that **logs**

```
[MULTIPLEX] Re-scanned profile 'X' after config/.env change (N adapter(s) connected)
```

but `_start_one_profile_adapters` skips every platform already live in `self._profile_adapters[X]`
("never a second poller on the same bot"). So a rescan of an **already-connected** platform returns
`0 adapter(s) connected`, and the running adapter keeps the OLD settings in memory: the resolvers
read `adapter.config.extra`, which is the PlatformConfig captured at connect time. `0 connected`
right after your edit is not success evidence — it is evidence the edit did **not** apply.

Apply it surgically, without touching other profiles' bots:

```bash
hermes -p <name> gateway restart      # → unserve-profile + serve-profile-hot control verbs
# success: "Profile 'X' restarted by the host gateway."
```

Confirm in the profile's own log (`~/.hermes/profiles/<name>/logs/gateway.log`):

```
✓ <platform> disconnected (profile: X)
[MULTIPLEX] Profile 'X' unserved — 1 adapter(s) stopped and unrouted
[<scoped>.adapter] Connected as <bot>
```

A host-wide `hermes gateway restart` is only needed when the host itself must re-read defaults — it
disconnects every profile's bots; the per-profile restart does not.

## Host-wide restart from inside a session: SIGUSR1, never the CLI

The host gateway runs the agent turn in-process, so the CLI cannot be used from a tool call inside
that turn: `hermes gateway restart` sends SIGUSR1 then **waits for the gateway PID to exit**, which
cannot happen until the caller's own turn ends — the call burns the whole drain budget and then
force-kills the gateway mid-turn, losing the reply. Send the signal yourself instead:

```bash
kill -USR1 $(hermes gateway list | sed -n 's/.*default (current).*PID \([0-9]*\).*/\1/p')
```

SIGUSR1 is drain-aware and safe from inside a turn: the gateway logs
`Restart requested with N active work unit(s); deferring stop() until they finish (cap=1800s) (#77184)`,
finishes the in-flight turn (reply delivered), exits 75, and launchd relaunches. Cost: **every**
profile's bots blip for the reboot (~40 s), and while draining the gateway refuses new turns — so
prefer the per-profile restart above unless the host genuinely must re-read defaults. Uptime is
irrelevant to the `restart_loop_guard` (3 restarts / 60 s window) unless you restart repeatedly.

## Precedence when the value still will not change

`extra_or_secret()` reads env → YAML `extra` → default. The env rung for a *secondary* profile is
scope-only: a scoped miss returns `None` and never borrows the launcher's `os.environ`, where the
DEFAULT profile's YAML→env bridge has already left `DISCORD_*=false` (first-writer-wins). So the
profile's own `config.yaml` wins — put the value there, and use that profile's `.env` only to
override itself. `_apply_yaml_config` seeds YAML keys (incl. `require_mention`,
`thread_require_mention`) into that profile's `extra`, and `yaml_env_setter` deliberately skips the
process-global env write for a scoped load.

## Multi-bot Discord threads: gate threads like channels

**Symptom:** profile B's bot answers messages in a shared thread that were addressed to profile A's
bot (both bots in one thread; the user ends up hammering `/stop` on B).

**Cause:** `discord.require_mention: true` (default) is bypassed for a thread the bot already
joined — `_handle_message` skips the gate when `_in_bot_thread()`, and that helper returns False
only when `thread_require_mention` is true.

**Fix** in the *joining* profile's `config.yaml`:

```yaml
discord:
  require_mention: true
  thread_require_mention: true   # threads need the literal @ too, own auto-threads included
  allow_bots: mentions
```

Escape hatch when one thread must stay mention-free: list its id in `discord.free_response_channels`.

**Evidence first:** fetch the offending message with the `discord` tool and look for a literal
`<@BOT_ID>` token — the gateway's own `inbound message` log line has mentions stripped, so it
cannot show whether the bot was addressed. DMs are exempt from all of this: `require_mention`
never applies to `discord.DMChannel`, and DMs dispatch for any allowlisted user (no config key
disables DMs except a `pre_gateway_dispatch` hook returning `{"action": "skip"}` on
`event.source.chat_type == "dm"`).
