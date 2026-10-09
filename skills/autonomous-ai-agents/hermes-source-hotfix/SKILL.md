---
name: hermes-source-hotfix
description: "Diagnose and hotfix problems in the running Hermes Agent itself — provider streaming errors, client-construction quirks, wrong context window / model-metadata detection — with patches or config-level fixes that survive hermes update."
version: 1.0.0
author: Hermes Agent
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hermes, troubleshooting, hotfix, provider, streaming]
---

# Hermes Source Hotfix

For bugs in the Hermes Agent codebase itself (not user config): provider API
calls failing inside hermes, client-construction quirks, known-bug workarounds
that upstream applies in one code path but not another.

## Diagnosis path

Batch the investigation into ONE script instead of one grep per tool call.
Source archaeology on hermes is read-only and cheap to script: write a single
`execute_code` block that runs every grep/sed/python probe you already know you
need, `print()` each result under a labelled header, and read it all at once.
Serial single-pattern greps burn the tool-call budget and lose earlier findings
to context compression. When a command's output must be reasoned about, capture
it and print it from that block rather than relying on the raw terminal result
to come back legible — long or empty terminal stdout is a display problem, not
evidence that the command failed.

1. Match the exact error string against the hermes source FIRST — upstream
   often documents known bugs in code comments:
   `cd ~/.hermes/hermes-agent && grep -rn "<error snippet>" --include="*.py" . | grep -v venv`
   Example: the brotli DecodingError was documented in `tools/skills_hub.py`
   together with the official workaround.
2. Identify the HTTP stack: `~/.hermes/hermes-agent/venv/bin/pip list | grep -iE 'brotli|httpx|aiohttp|openai'`.
3. Find where the LLM client is built before patching:
   - `agent/agent_init.py` — main client_kwargs + per-host `default_headers`
     elif-chain (uses `base_url_host_matches()` from `utils.py`, matches host
     or subdomain).
   - `providers/base.py` — `default_headers` field on provider profiles
     (fallback branch in agent_init.py uses it when no host branch fired).
   - Config-level alternative: `providers:` entries in config.yaml support
     `extra_headers` (see `hermes_cli/config.py` ~line 5193) — survives
     updates, prefer when it can express the fix.

## Patch workflow

1. Check tree is clean: `git -C ~/.hermes/hermes-agent status --short`.
2. Check if upstream already fixed it: `git fetch origin main` (macOS has NO
   `timeout` command — don't prefix; on a shallow checkout this pulls the whole
   history, see "`hermes update` stops at Fetching updates" below) then
   `git log --oneline HEAD..origin/main --grep=<keyword> -i`.
3. Patch minimally, following existing code patterns in the same block.
4. Verify: `venv/bin/python -m py_compile <file>`.
5. Tell the user to RESTART the hermes CLI (running process holds old code);
   resume with `hermes -c`. Restart gateways for other profiles too.

## Surviving `hermes update`

- Update auto-stashes local changes (`_stash_local_changes_if_needed` in
  hermes_cli/main.py) and tries to restore after; conflicts can silently drop
  the patch.
- An update that aborts BEFORE the pull (failed fetch, refused preflight) exits
  without unstashing, so an applied patch can sit in `git stash list` as
  `hermes-update-autostash-*` indefinitely while the working tree looks clean.
  When a hotfix has vanished, run `git stash list` and inspect EVERY entry with
  `git stash show -p` before re-patching, and never bulk-drop those entries on
  the updater's "leftover autostash" warning — one of them is often the only
  copy of a real hotfix, and the newest is not necessarily the one that matters.
- After any update, if the original symptom returns, check
  `git -C ~/.hermes/hermes-agent diff` — reapply if gone.
- Keep the exact patch snippet in this skill's references/ so reapplying is
  mechanical.

## `hermes update` stops at "Fetching updates"

`_git_run(..., network=True)` wraps the update fetch in a **hard-coded 300 s cap**
(`NETWORK_GIT_TIMEOUT_SECONDS` in `hermes_cli/update_cmd.py` — grep it before assuming a config or env
knob exists) and runs a plain `git fetch origin <branch>` with no `--depth`. On a **shallow** checkout
that is an implicit unshallow, so the fetch pulls the entire history — hundreds of thousands of objects —
and on a slow link it is killed at the cap. The message it prints,
`timed out after 300s with no response from the remote`, comes from the timeout branch unconditionally,
so it reads as a dead connection even while the pack is downloading at full speed. Read the state before
theorizing:

```bash
cd ~/.hermes/hermes-agent
git rev-parse --is-shallow-repository; wc -l < .git/shallow    # shallow + many grafts ⇒ unshallow
git ls-remote origin main                                      # remote tip in ~1 s; compare `git rev-parse HEAD`
ls -la .git/objects/pack/tmp_pack_*                            # debris left by each killed attempt
```

Every killed attempt leaves a `tmp_pack_*` whose size is (link throughput × 300 s), and
`clear_stale_tmp_packs` deletes that debris when the next run starts — `git fetch` cannot resume, so each
attempt restarts from zero and the run never converges. The cap is the only thing between that command
and success, so finish the fetch once **outside** the updater (no cap); the checkout then stops being
shallow and every later update transfers only a delta:

```bash
cd ~/.hermes/hermes-agent && git fetch --progress origin main
```

Run it detached with progress rather than in a foreground tool call — expect minutes to tens of minutes.
Confirm it is really transferring before waiting on it: `Receiving objects: N% … MiB | X MiB/s` climbing
is progress (compare the throwaway `tmp_pack_*` size at two sampling points if the output is buffered;
`remote: Compressing objects:` is server-side work with zero client bytes expected). Do not raise the cap
by patching the updater — an update replaces the tree and reintroduces it.

## Wrong context window / compression firing early

Symptom: `hermes logs | grep "context length"` reports a window far below the
model's real one, or compression triggers at an oddly low token count.

Resolution chain for a custom endpoint (`agent/model_metadata.py`,
`agent/agent_init.py::_resolve_context_length`): 0 `model.context_length`
config override -> per-model `context_length` in a route-matching
`providers.<name>.models` entry (`get_custom_provider_context_length`) ->
endpoint `/models` probe -> Ollama `/api/show` -> hardcoded catalog
(`DEFAULT_CONTEXT_LENGTHS`) -> 256K fallback. Read the chain off the log
lines, which name the tier that won.

Pitfalls:
- The catalog is matched by **longest key**, not exact id. A versioned id
  (`...-v4-1-flash`) misses the family key (`deepseek-v4-flash` -> 1M) and
  falls through to the bare catch-all (`deepseek` -> 128K), so the session is
  billed and compacted against 128K while the provider serves 1M. Diff the
  id against the catalog keys before blaming the endpoint.
- An OpenAI-compatible gateway that 404s `GET <base_url>/models` kills the
  probe tier, so detection silently lands on the catalog or the 256K
  fallback. `curl -s -i` the endpoint and read the status code first.
- A `providers.<name>.models[].context_length` edit fixes only NEWLY built
  agents. The Desktop/TUI hot-reload signature
  (`tui_gateway/session_compression.py::_tui_compression_config_signature`)
  carries `compression.*` keys plus `model.context_length` ONLY — the
  provider-entry route is not in it, so a running session keeps its old window
  and its old trigger indefinitely. Sessions started AFTER the write still log
  the old `threshold=`. When the fix must reach the running session, also set
  the top-level `model.context_length` (hot-reload picks it up next turn), or
  tell the user to restart the app.
- `compression.threshold` in config.yaml is NOT the trigger you observe:
  windows under 512K are raised to a 75% floor
  (`_SMALL_CTX_THRESHOLD_PERCENT`) and the trigger is computed from
  `context_length - max_tokens`. Read `main_context_limit` and
  `effective_threshold` from the compression telemetry line in
  `~/.hermes/logs/agent.log` instead of recomputing them.
- `hermes config set <dotted.path> <value>` rewrites the WHOLE file through the
  YAML dumper: trailing comment blocks and commented-out templates (e.g. a
  commented `fallback_model:` example) are silently dropped. Diff the result
  against the backup you took and restore what was lost before reporting
  success.

Fix (config-level, survives `hermes update`): add `context_length:` to the
model's entry under `providers.<name>.models`. Read the WHOLE `models:` list
before editing — partial coverage is the norm, and any entry lacking
`context_length:` silently falls through every tier below it. Never write to
config.yaml to TEST the hypothesis — load it, deep-copy, mutate the copy, and
call the real resolver in the hermes venv, passing the MUTATED provider list
explicitly (a `None` argument makes the resolver re-read the real file from
disk, so the test "confirms" the unfixed value):

```
env -u PYTHONPATH ~/.hermes/hermes-agent/venv/bin/python -c \
  "from hermes_cli.config_providers import get_compatible_custom_providers, \
   get_custom_provider_context_length; ..."
```

(`env -u PYTHONPATH` — an inherited Hermes PYTHONPATH shadows the venv's own
packages.) Then back up config.yaml, apply the edit, and confirm the log line
stops reporting `catalog match on '<key>'`.

There are TWO knobs and they reach different consumers — set the one that
matches what the user needs:

| Knob | New agents | Running Desktop/TUI session |
|---|---|---|
| `providers.<name>.models[].context_length` | yes | no (not in hot-reload signature) |
| `model.context_length` | yes (scoped to the default runtime) | yes, next turn |

Apply with the CLI rather than hand-editing, so the value round-trips through
the real config layer. List entries are addressed by numeric index:
`hermes config set providers.<name>.models.<i>.context_length <n>`. Locate the
index first by dumping the list with `enumerate`, and re-read the file after
writing — `hermes config set` normalizes key order and drops comments.

Take the value from a real source, in this order: a sibling entry in the same
`models:` list, the vendor's own model page, then the local models.dev cache
(`~/.hermes/models_dev_cache.json` -> `limit.context`). When the vendor page and
the local cache disagree (e.g. 1024k vs 1000000), prefer the vendor's documented
figure and say which source you used — a wrong-but-plausible window is worse
than the conservative default.

After ANY write, diff the file against the backup you took. `hermes config set`
rewrites the whole file and can drop commented-out template blocks; restore them
and report any *other* changed key you did not write (a config write can carry
collateral changes from a UI model switch) rather than silently accepting it.

Detail: references/context-length-resolution.md

## Applied hotfixes (reapply after update if lost)

- references/moonshot-brotli-patch.md — Accept-Encoding: gzip for
  moonshot.cn/moonshot.ai clients; fixes DecodingError on long Kimi streams.
