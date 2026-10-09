# Context-length resolution — where to look, what to check

Answers "how big is my context window really?" and "why did it pick that number?"
Source tree: `~/.hermes/hermes-agent`.

## Step 1 — get the live answer, not a recomputed guess

```
grep "context length" ~/.hermes/logs/agent.log | tail -5
grep "API call #" ~/.hermes/logs/agent.log | tail -3
```

The log lines name the tier that produced the number, e.g.
`Could not detect context length ... defaulting to 256,000 tokens (probe-down)`
followed by `Using hardcoded context length 128,000 for model '<id>' (custom
endpoint, catalog match on '<key>')`. The second line is the answer.

For the compaction trigger, read the telemetry JSON on the
`agent.conversation_compression: context compression attempt telemetry` line
rather than computing it: `main_context_limit`, `effective_threshold`,
`current_estimated_tokens`, `protected_tail_tokens`, `middle_window_tokens`.
The same JSON is echoed by `agent/context_compressor.py` (~line 1692,
`"event": "compression_attempt"`), which is the authoritative field list.

A brand-new session has no telemetry line yet — reuse a recent one for the
same model; the window is a property of model + endpoint, not of the session.

## Step 2 — resolution chain (first hit wins)

`get_model_context_length()` in `agent/model_metadata.py`:

0. `model.context_length` in config.yaml — explicit override. Scoped to the
   configured *default* runtime by
   `agent_init.py::_scope_context_length_to_default_runtime`: if `--model`
   launched a different model, or the route differs, the value is dropped
   (logged at DEBUG) so a stale window does not carry over.
0b. Per-model `context_length` in a route-matching provider entry —
   `hermes_cli/config_providers.py::get_custom_provider_context_length`,
   reached from `agent_init.py::_resolve_context_length` (only when the
   `model.context_length` branch produced nothing). Precedence inside it:
   `models.<model>.context_length` -> entry-level `context_length`.
   Reads `providers.<name>.models` through
   `providers_dict_to_custom_providers` + `get_compatible_custom_providers`
   (legacy `custom_providers:` list is the other accepted shape).
1-9. Endpoint `/models` probe, local probe, Ollama `/api/show`, provider-aware
   lookups, hardcoded `DEFAULT_CONTEXT_LENGTHS`, 256K fallback.

The catalog lookup is `_longest_key_match(DEFAULT_CONTEXT_LENGTHS,
model.lower())` — longest matching key wins, so a versioned id can skip its
family entry and land on a short catch-all key.

## Step 3 — verify a config fix WITHOUT touching config.yaml

Load the real file, deep-copy, mutate the copy, call the real resolver with the
hermes venv interpreter:

```
env -u PYTHONPATH ~/.hermes/hermes-agent/venv/bin/python - <<'EOF'
import yaml, copy
from hermes_cli.config_providers import (get_compatible_custom_providers,
                                         get_custom_provider_context_length)
cfg = yaml.safe_load(open('/Users/<user>/.hermes/config.yaml'))
url = "<provider base_url>"
print("BEFORE:", get_custom_provider_context_length("<model-id>", url, get_compatible_custom_providers(cfg), cfg))
cfg2 = copy.deepcopy(cfg)
for m in cfg2["providers"]["<provider>"]["models"]:
    if m["id"] == "<model-id>":
        m["context_length"] = 1000000
print("AFTER :", get_custom_provider_context_length("<model-id>", url, get_compatible_custom_providers(cfg2), cfg2))
EOF
```

`env -u PYTHONPATH` matters: an inherited Hermes `PYTHONPATH` shadows the venv's
installed packages and the import fails or resolves elsewhere. The venv lives at
`~/.hermes/hermes-agent/venv` (fall back to `.venv`).

**Pass the mutated list explicitly — never `None`.** Every entry point
(`get_custom_provider_context_length`, `get_model_context_length`) treats a
`None` `custom_providers` argument as "go load config.yaml yourself", so the
resolver re-reads the *unmutated* file from disk and the AFTER run prints the
same value as BEFORE. It looks like "the fix does not work" when nothing was
tested at all. Convert once and reuse the same object:
`cps = providers_dict_to_custom_providers(cfg2)` — note
`providers_dict_to_custom_providers` is the `providers:` -> custom-providers
adapter, while `get_compatible_custom_providers(cfg)` is the wrapper that
accepts a whole config dict.

To verify the *end-to-end* number rather than just the config-lookup tier, call
`get_model_context_length(model, base_url=..., api_key=..., provider=...,
custom_providers=cps)` with the mutated list. That is the same function the
agent uses, so a BEFORE/AFTER pair from it is the actual claim being made.

Strongest of all: drive the exact function the Desktop/TUI calls at agent
construction — `agent/agent_init.py::_resolve_context_length(agent, cfg, base_url)`
— against a stub agent carrying only `model`, `provider`, `base_url` and the
three no-op LM Studio hooks (`_ensure_lmstudio_runtime_loaded` -> None,
`_lmstudio_load_was_unverified` -> False, `_effective_lmstudio_context_length`
-> first arg). It returns `(_config_context_length, _custom_providers,
_effective_context_length, _model_cfg)`, i.e. the resolved window AND the
provider list that produced it. This catches route-scoping bugs
(`_scope_context_length_to_default_runtime` drops `model.context_length` when
the active model or route differs from the configured default) that a bare
resolver call cannot show. Note `ContextCompressor.__init__` does NOT accept
`context_length=` — construct it the way `agent_init` does instead of guessing
kwargs.

## Step 3b — the running session is a SEPARATE consumer

Resolving the right number is necessary but not sufficient: a long-lived
Desktop/TUI process does not rebuild its agent per turn, so a config edit can be
correct on disk and still have no effect on the session in front of the user.

The hot-reload signature is
`tui_gateway/session_compression.py::_tui_compression_config_signature(cfg)`:

```
keys = GatewayRunner._extract_cache_busting_config(cfg)
picked = {k: v for k, v in keys.items()
          if k.startswith("compression.") or k == "model.context_length"}
```

Only `compression.*` and `model.context_length` are watched. A change to
`providers.<name>.models[].context_length` alone does NOT invalidate the
signature, so `_apply_live_compression_config` never runs for it and the live
compressor keeps its captured window and trigger. Confirm by printing the
signature directly:

```
from tui_gateway.session_compression import _tui_compression_config_signature
print(dict(_tui_compression_config_signature(cfg)).get("model.context_length"))
```

Consequences to state plainly to the user:
- new agents get the new window; the running session does not;
- sessions started AFTER the write can still log the OLD trigger, which is
truthful, not a failed edit — do not "re-verify" by starting more sessions;
- to reach the running session, also set `model.context_length`, or restart.

Because the signature carries `model.context_length`, that key is the one to use
when the user wants the fix to land immediately. It is scoped to the configured
default runtime, so a live `/model` switch to something else drops it — which is
the safe behaviour, and the reason to keep the provider-entry form as the
durable record.

## Partial coverage in the config's own `models:` list is the strongest clue

When a provider entry lists many models and only SOME carry `context_length:`,
the unset ones are the ones falling through the chain — and that asymmetry is
the fastest confirmation the endpoint probe is dead. Dump the list and read it
before touching the catalog:

```
python3 -c "import yaml;c=yaml.safe_load(open('/Users/<user>/.hermes/config.yaml'));\
[print(f\"{m['id']:32s} ctx={m.get('context_length')}\") for m in c['providers']['<provider>']['models']]"
```

Sibling models already carrying `1048576` / `262144` mean whoever wrote the
config did it by hand and missed entries — match the sibling's literal value
rather than inventing one, and flag any other unset entry (especially
`model.default`) to the user in the same reply.

Other probes worth running:

```
curl -s -i -m 25 -H "Authorization: Bearer <key>" <base_url>/models | head -20
```

A `404` (or any non-2xx) here means the endpoint has no model-metadata route and
the probe tiers are dead for this provider — the config override is the only
reliable route.

For third-party model facts, the local models.dev cache at
`~/.hermes/models_dev_cache.json` is keyed `/<provider>/models/<id>` and carries
`limit.context` / `limit.output` — a quick cross-check of what the window
*should* be, without a network call.

## Step 4 — apply

Back up `~/.hermes/config.yaml` first (`cp -p config.yaml config.yaml.bak.$(date +%Y%m%d_%H%M%S)`),
then set the value through the config CLI so it round-trips the real config
layer. List entries are addressed by numeric index:

```
env -u PYTHONPATH ~/.hermes/hermes-agent/venv/bin/hermes \
  config set providers.<name>.models.<i>.context_length <n>
```

Find `<i>` by enumerating the list first; do not count by eye across a long
`models:` block. Prefer the CLI over a hand edit or a generic file-patch tool:
config.yaml is guarded, and a generic editor can corrupt structure it does not
understand.

`hermes config set` parses then re-dumps the whole file, so it will:
- normalize key order (acceptable — the file's convention is alphabetical
  within a mapping);
- DROP trailing comment blocks and commented-out templates, e.g. a commented
  `fallback_model:` example. Diff against the backup and restore them.

Verify with a semantic diff, not a textual one — key reordering makes a textual
diff noisy and hides real changes. Flatten both YAML trees and compare leaf
paths:

```
flat(cfg)  # recursive: dict -> "a.b", list -> "a[i]", else leaf
# print every path where backup != current
```

Expect exactly ONE changed leaf for a one-key edit. If the diff shows more
(e.g. `model.default`, `model.base_url`, `model.api_mode` changed), you did not
cause all of it — a UI model switch or a gateway config-sync can write those.
Report the extra changes to the user and offer to revert them; do not quietly
accept them, and do not claim them as your own work.

Then confirm through the agent-construction path (Step 3), not just the
resolver, and re-check the log line — it must stop reporting the catalog /
fallback tier for NEW agents. For the running session, see Step 3b.

Note: `agent_init.py::_warn_invalid_custom_provider_context_length` exists to
surface a `context_length` that was silently skipped for not being a positive
int. If a value you added appears to be ignored, look for that warning.
