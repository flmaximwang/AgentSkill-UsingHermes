# Moonshot/Kimi brotli streaming hotfix

## Symptom

Long streaming replies from provider `kimi-coding-cn` (or `kimi-coding`) die
mid-generation with:

```
DecodingError — brotli: decoder process called with data when
'can_accept_more_data()' is False   (endpoint https://api.moonshot.cn/v1)
```

Fails only on LONG generations (60s+); short replies survive.

## Root cause chain

1. venv has `brotlicffi 1.2.0.1` (pinned for Discord attachment decoding —
   see `tools/lazy_deps.py` "platform.discord" entry; do NOT uninstall it).
2. With brotlicffi importable, httpx (used by the OpenAI SDK) advertises
   `br` in Accept-Encoding; api.moonshot.cn then brotli-compresses the SSE
   stream.
3. brotlicffi 1.2.0.1 has a streaming-decode bug; long streams corrupt the
   decoder state mid-response.
4. Upstream hit the identical error in `tools/skills_hub.py` (~line 3804)
   and worked around it with `headers={"Accept-Encoding": "gzip"}` — this
   patch applies the same workaround to the LLM client path.

## Patch (agent/agent_init.py, inside the default_headers elif-chain)

Inserted after the `api.kimi.com` branch (~line 1122), before
`portal.qwen.ai`:

```python
            elif base_url_host_matches(effective_base, "moonshot.cn") or base_url_host_matches(effective_base, "moonshot.ai"):
                # brotlicffi 1.2.0.1 (pinned for Discord attachment decoding)
                # has a streaming-decode bug that kills long SSE streams from
                # Moonshot with DecodingError("brotli: decoder process called
                # with data when 'can_accept_more_data()' is False"). Forcing
                # Accept-Encoding: gzip makes the server fall back to gzip —
                # same workaround as tools/skills_hub.py.
                client_kwargs["default_headers"] = {"Accept-Encoding": "gzip"}
```

Pyright may flag the dict assignment — false positive; identical pattern is
used by every other branch in the chain.

## Verify

```bash
cd ~/.hermes/hermes-agent
venv/bin/python -m py_compile agent/agent_init.py
venv/bin/python -c "from utils import base_url_host_matches as m; print(m('https://api.moonshot.cn/v1','moonshot.cn'))"
```

Then restart the hermes CLI (old process keeps old code); resume via
`hermes -c`. First applied 2026-07-23; upstream (origin/main +11 commits at
that date) had NO fix — recheck after each `hermes update`.
