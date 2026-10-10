# Heartbeat ownership and outbound-request audit — ready queries

Read-only, no source tracing. Default profile store `~/.hermes/state.db`; another profile's lives in
`~/.hermes/profiles/<name>/state.db`.

## 1. Every recurring heartbeat, and the conversation it belongs to

```bash
sqlite3 -header -column ~/.hermes/state.db "SELECT key, value FROM state_meta WHERE key LIKE 'heartbeat:%';"
```

Value JSON: `prompt`, `interval_seconds`, `status` (`active` | `paused` | `cleared`), `created_at`,
`last_fired_at` (epoch floats), `fire_count`. **Only `active` fires.**

One Python pass resolves each row to its owner conversation and survives unparseable values:

```python
import os, json, datetime, sqlite3
DB = os.path.expanduser('~/.hermes/state.db')
c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
for key, val in c.execute("SELECT key, value FROM state_meta WHERE key LIKE 'heartbeat:%'"):
    sid = key.split(':', 1)[1]
    try:
        d = json.loads(val)
    except Exception:
        d = {}
    row = c.execute('SELECT title, display_name, chat_id, thread_id, message_count, input_tokens '
                    'FROM sessions WHERE id=?', (sid,)).fetchone()
    print(key, d.get('status'), d.get('interval_seconds'), d.get('fire_count'), row)
```

Report:
- the **single active** row's `sessions.title` / `display_name` / `chat_id` — that is "which conversation";
- that the heartbeat is keyed by **session**, so it survived restarts into a new session id with the same
  `created_at` and a continuous `fire_count` (dates the instruction, not the session);
- the action as a command the user sends **in that conversation**: `/heartbeat pause` | `resume` |
  `clear` | `every 10m <prompt>`. The meta row stays untouched.

## 2. Model calls in a time window

Line shape (`~/.hermes/logs/agent.log` and every `profiles/*/logs/agent.log`):

```
YYYY-MM-DD HH:MM:SS,mmm INFO [<session>] agent.conversation_loop: API call #N: model=… provider=… in=… out=… total=… latency=…s cache=X/Y (n%) id=…
```

```python
import os, re, glob, datetime, collections
H = os.path.expanduser('~/.hermes')
now = datetime.datetime.now(); start = now - datetime.timedelta(hours=1)
ts = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})')
call = re.compile(r'API call #\d+: model=(\S+) provider=(\S+) in=(\d+) out=(\d+) total=(\d+) latency=([\d.]+)s cache=(\S+)')
calls = collections.Counter(); tok = collections.Counter()
for p in [f'{H}/logs/agent.log'] + glob.glob(f'{H}/profiles/*/logs/agent.log'):
    size = os.path.getsize(p)
    with open(p, 'rb') as f:
        f.seek(max(0, size - 8_000_000)); lines = f.read().decode('utf8', 'replace').splitlines()[1:]
    for ln in lines:
        m = ts.match(ln)
        if not m:
            continue
        t = datetime.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
        if not (start <= t <= now):
            continue
        mm = call.search(ln)
        if mm:
            tag = os.path.relpath(p, H)
            calls[(tag, mm.group(1), mm.group(2))] += 1
            tok[tag] += int(mm.group(3)) + int(mm.group(4))
print(dict(calls), dict(tok))
```

Other lines from the same window, same timestamp filter:

| Line | Meaning |
|---|---|
| `agent.turn_context: conversation turn: session=… model=… history=N msg='…'` | a turn was handled, with the history depth behind the next call's `in=` |
| `agent.tool_executor: tool <name> completed (12.3s, 4567 chars)` | which tools the turn actually used |
| `API call failed after 3 retries … provider=… model=… msgs=… tokens=~…` | the call that never landed, and the context it carried |
| `429 … Sustained usage limit (…) N weighted / M (1h); … (6h). Cooldown until …` | provider-side quota: quote both windows and the cooldown |
| `gateway.run: inbound message: … chat=… msg='…'` / `response ready … api_calls=N` | inbound/outbound per chat and what a reply cost |

Exact request bodies are dumped when retries are exhausted:
`~/.hermes/sessions/request_dump_<session>_<YYYYmmdd_HHMMSS>.json` with `"reason": "max_retries_exhausted"` —
use it when "what exactly did it send" matters more than the counts.

## 3. The cheapest reading of "it is burning quota"

`in=` is the whole re-sent context, so spend is **turns per hour × context size**, not message length: a
heartbeat on a 90-turn thread fires twice every 10 minutes at >100k input tokens each. Check `cache=X/Y`
before blaming an uncached prefix, and name the responsible session/chat rather than a total.
