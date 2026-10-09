# Hindsight in `local_embedded`: wiring, first boot, verification

Scope: the user has picked Hindsight as the external provider and wants it running on this machine.
Covers the config surface, how the extraction key gets in without ever being typed into chat, the
daemon's one-time runtime provisioning (the part that fails on a slow link), and how to prove the
write path works. Choosing a provider at all: `choose-a-memory-provider.md`. Plugin dependencies
and generation venvs: `install-a-hermes-plugin`.

## Shape

- Provider config: `$HERMES_HOME/hindsight/config.json` (profile-scoped, wins) → `~/.hindsight/config.json`
  (legacy) → env vars.
- Keys that matter: `mode` (`cloud` | `local_embedded` | `local_external`), `bank_id`,
  `bank_id_template`, `llm_provider` (`openai_compatible` / `ollama` / …), `llm_model`, `llm_base_url`,
  `memory_mode` (`hybrid` | `context` | `tools`), `recall_budget`, `port_health_grace_timeout`.
- The daemon-side env is materialized by the plugin, not typed by you: `~/.hindsight/profiles/<profile>.env`
  (0600) holding `HINDSIGHT_API_LLM_{PROVIDER,API_KEY,MODEL,BASE_URL}`. Read it to confirm wiring;
  never print its values.
- Logs: daemon start `$HERMES_HOME/logs/hindsight-embed.log`; daemon runtime `~/.hindsight/profiles/<profile>.log`.
- Daemon owner CLI: `<generation venv>/bin/hindsight-embed -p <profile> daemon start|stop|status|logs`.

## 1. `local_embedded` still needs an LLM endpoint

Storage and retrieval are local; **extraction and synthesis are LLM calls**. "本地能跑" ≠ no egress —
say that in one line when the user picks this mode, and let them choose cloud-LLM-now vs.
local-endpoint-later. `llm_provider: openai_compatible` + `llm_base_url` accepts any OpenAI-compatible
endpoint (Ollama, vLLM, LM Studio, a hosted API).

Wire the key by copying one the profile already has, so no secret ever enters the conversation:

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path.home()/'.hermes/.env'; t = p.read_text()
if 'HINDSIGHT_LLM_API_KEY=' not in t:
    src = [l for l in t.splitlines() if l.startswith('DEEPSEEK_API_KEY=')][0]
    with p.open('a') as f:
        f.write('HINDSIGHT_LLM_API_KEY=' + src.split('=', 1)[1] + '\n')
        f.write('HINDSIGHT_API_LLM_BASE_URL=https://api.deepseek.com/v1\n')
PY
```

Use the wizard-shaped name `HINDSIGHT_LLM_API_KEY`; the daemon itself reads
`HINDSIGHT_API_LLM_API_KEY`, and the plugin copies one to the other when it materializes the profile
env. Verify by listing key **names** in `~/.hindsight/profiles/<profile>.env`, never their values.

## 2. First boot provisions its own runtime — budget minutes, raise the wait

`local_embedded` builds a whole Python runtime for the daemon on first start: embedded PostgreSQL
(`pg0-embedded`), `hindsight-api-slim`, torch, `claude-agent-sdk`, `mlx-metal`, litellm, onnxruntime,
transformers — several hundred MB, downloaded into `~/.hindsight/`. On a slow or proxied link it misses
the readiness deadline and the plugin reports:

```
✗ Daemon failed to start (timeout)
RuntimeError: Failed to start the Hindsight daemon for profile '<profile>'
```

- **Raise the grace before judging it broken**: add `"port_health_grace_timeout": 1800` to
  `$HERMES_HOME/hindsight/config.json` (exported as `HINDSIGHT_EMBED_PORT_HEALTH_GRACE_TIMEOUT`).
- **Pre-warm out of band**, so the first user turn does not pay for it:
  `<generation venv>/bin/hindsight-embed -p <profile> daemon start` in the background, then
  `daemon status` / `daemon logs` to watch. Re-running after the runtime exists succeeds — the timeout
  is a slow download, not a broken install.
- Watching the log, `Downloading torch (…)` re-printing is normal, not a download loop.
- The daemon stops after a few minutes idle and restarts on next use; a cold turn therefore pays the
  start again. If a first turn feels slow, check `daemon status` before blaming the provider.
- **A foreground `daemon start` hands the daemon its SIGTERM when that CLI exits.** As a pre-warm it
  prints `✓ Daemon started successfully!` and then the daemon logs `Received signal 15` +
  `Application shutdown complete`; a probe seconds later hits a dead port (`http=000`). So the
  write→read probe must run in the process that owns the daemon: let the provider start it (that is
  what the gateway does), or start the CLI detached — do not "pre-warm" it from a tool call that ends.
- **A proxy in the process environment captures the loopback call too.** With `HTTPS_PROXY` /
  `HTTP_PROXY` set, `recall` against the daemon URL comes back `502 Bad Gateway` from the proxy while
  `retain` a second earlier succeeded — same process, same base URL, so the provider looks
  half-broken. Add `NO_PROXY=127.0.0.1,localhost,::1` (plus the lowercase twin) to the profile's
  dotenv file. Measured: before, `retain` OK / `recall` `(502) Reason: Bad Gateway`; after,
  `retain` 21.2 s (cold daemon) and `recall` returns the stored fact verbatim — assert on the content
  coming back, not on the absence of an error.

## 3. Do not set a per-user `bank_id_template` on a single-human gateway

`bank_id_template` accepts `{profile} {workspace} {project} {platform} {user} {session}` and empty
placeholders collapse. `hermes-{platform}-{user}` looks like the fix for "one person, many platforms",
but CLI/cron sessions carry no platform or user, so they collapse to the bare `bank_id` while gateway
sessions write to the templated bank: **two stores for one person** — the same split-brain that made
the previous provider look broken. Keep one static `bank_id` until a second human actually shares the
bot; add the template (or `mirror_to_own_bank: true`) when that changes.

## 4. Verification: `memory status` is not the test

`hermes memory status` reports `Plugin: installed ✓ / Status: available ✓` from an import probe. It
does not start the daemon and does not prove a write path works. Probe the provider the way the host
does — in-process, and under the plugin's **own generation venv**, never the core venv:

```bash
# 最新 generation 的那套（按 mtime 挑最新的；`hermes pm status` / installs 树里能看到它的 id）
VENV=<hermes root>/installs/<install id>/environments/<generation>/venv
PYTHONPATH=<hermes root>:$VENV/lib/python*/site-packages $VENV/bin/python probe.py
# probe.py: provider.post_setup(hermes_home, config) → initialize(session_id, platform=…, hermes_home=…)
#           → handle_tool_call('hindsight_retain', {...}) → handle_tool_call('hindsight_recall', {...})
```

Then assert on real content and read it back through the daemon:
`<generation venv>/bin/hindsight-embed -p <profile> memory recall <bank> "<query>"`.
Note `_mode` after initialize: a mode of `disabled` means the local runtime was not importable
(`_check_local_runtime`), which is an install/environment problem, not a config typo — and a tool call
that raises `AttributeError` on a `self._*` setting is the same cause (initialize returned early).

## 5. Cross-profile memory: shared by default — so make it a decision

The daemon's **hindsight profile name is the plugin's own `profile` config key, and its default is the
constant `hermes`, not the Hermes profile name** (`profile = cfg.get("profile", "hermes")`). So every
Hermes profile that leaves that key unset talks to *one* daemon, one embedded PostgreSQL
(`~/.pg0/instances/hindsight-embed-hermes`) and one `~/.hindsight/profiles/hermes.env` — and every one
of them defaults to `bank_id: hermes`. Measured: a second Hermes home, with its own
`hindsight/config.json`, recalled a fact written by the first profile in the same bank (asserted on a
random token inside the recalled text).

- **Sharing user preferences across profiles is the default, not a feature to build.** Decide it on
  purpose: keep the shared `bank_id` for "one person, many agents", split with
  `bank_id_template: "{profile}-…"`, or give each Hermes profile a distinct `profile` key to get a
  physically separate daemon + database.
- The flip side: `~/.hindsight/profiles/<profile>.env` (LLM provider / key / model / base URL) is a
  **single shared file** whenever the daemon is shared, so profiles overwrite one another's LLM config.
  Sharing memory means sharing the extraction LLM; a per-profile LLM means a per-profile `profile`
  name, and that ends the sharing.
- `additional_banks` / `recall_additional_banks` / `mirror_to_own_bank` appear in the vendor's Hermes
  doc but **not in the pinned plugin build** (v1.2.1: only `bank_id` and `banks.<name>.bankId` are
  read) — with this version it is whole-bank sharing or nothing.
- The built-in MEMORY.md / USER.md stay per profile regardless; hindsight does not change that.

## 6. Two things not to do as part of the install

- The vendor docs suggest turning the built-in stores off when Hindsight is active
  (`memory.user_profile_enabled false`). That is a separate decision about where the user's durable
  facts live — run both in parallel first and let them decide.
- Do not retire the previous provider's plugin/models the same day. Install, verify with the user's
  real data, then retire: export the old store first (proof-of-content-before-deletion is this user's
  standing rule for anything they cannot easily get back).
