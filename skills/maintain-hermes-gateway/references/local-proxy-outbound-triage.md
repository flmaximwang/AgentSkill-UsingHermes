# Attributing a platform outage to the local proxy's outbound

Use when a gateway platform keeps failing to connect while the proxy port is up and the raw
network works. Everything here is read-only except the two mutations, which you hand over.

## 1. Read the proxy core itself (Clash Verge / mihomo — the common case)

Clash Verge runs mihomo as a **privileged service**, so its runtime dir
(`/Library/Application Support/clash-verge-service/users/<uid>/runtime/`) is root-owned and not
readable. Its control API is on a root-owned unix socket that *is* readable:

```bash
S=/var/run/clash-verge-service/users/<uid>/verge-mihomo.sock
curl -s --unix-socket $S http://localhost/version      # e.g. {"meta":true,"version":"v1.19.32"}
curl -s --unix-socket $S http://localhost/configs      # mixed-port, mode, tun state
curl -s --unix-socket $S http://localhost/proxies      # groups + nodes + delay history
curl -s --unix-socket $S http://localhost/connections  # live chains per host
```

`/connections` is what proves the path a platform's traffic takes — read `chains` and `rule`,
not the group names you remember:

```
discord.com           rule=DomainSuffix   韩国|KR|01 > ✈️ 手动切换 > 🚀 节点选择
gateway.discord.gg    rule=DomainSuffix   韩国|KR|01 > ✈️ 手动切换 > 🚀 节点选择
```

Group and node names carry emoji and spaces → percent-encode every name in a URL path
(`urllib.parse.quote(name, safe="")`); a live liveness probe is
`GET /proxies/<encoded name>/delay?url=<encoded probe url>&timeout=5000` (`{"delay":74}` or
`{"message":"Timeout"}` / `"An error occurred in the delay test"`). Probe with an HTTP 204 URL
(`https://www.gstatic.com/generate_204`) — a URL whose response the node cannot reach reports an
error indistinguishable from a dead node.

## 2. Get the core's own reason from its log stream

```bash
curl -sN --max-time 30 --unix-socket $S "http://localhost/logs?level=debug" > /tmp/core.log
# generate one probe request while it streams, then grep the log
```

The warning lines name the failure exactly:

```
warning [TCP] dial 🚀 节点选择 (match DomainSuffix/gstatic.com) 127.0.0.1:54354(Python)
  --> www.gstatic.com:443 error: failed to create session: dial tcp <ip>:<port>: i/o timeout
```

`timeout(1)` does **not** exist on macOS (`gtimeout` does) — bound the stream with
`curl --max-time`, or run the stream and the probe from one python script, or the stream returns
nothing and you read an empty file instead of the answer.

## 3. The discriminating experiment (this is the one that names the layer)

Same minute, same machine:

| Who dials | Target | Reading |
|---|---|---|
| a normal user process (`socket.create_connection` / `openssl s_client -servername`) | the node's `host:port` | 20/20 TCP + TLS handshake OK |
| the proxy core (root) | the same `host:port` | `failed to create session: dial tcp … i/o timeout` |
| requests through the mixed port | the platform host | ~30–50 % succeed, the rest 5 s timeouts |

Raw connects fine + core dials timing out ⇒ the fault is the **core's dialer state**, not the
network and not the node: restart the core (Clash Verge → 重启内核 / Restart Core; the config is
preserved) and re-measure. Raw connects failing too ⇒ the path to the provider is the problem;
testing from another network/device is the next read.

Measure a **rate**, never a single sample: in a flap window a lone 200 (or a lone `Timeout`) says
nothing. Loop the probe 6–20× and report the ratio.

## 4. Facts that decide the fix

- A subscription's nodes often all resolve to **one host with per-port entries** (read them from
the profile yaml, see below). One host under attack/throttled flaps every "node" together, so
  switching node does not help — the flapping set is not the fault.
- Group topology is what turns a flap into a total outage: `rule → 🚀 节点选择 (Selector) →
  ✈️ 手动切换 (Selector, one pinned node) → <node>`. A pinned node means the platform dies the
  moment that node dies. Put the top-level Selector on the URLTest auto group instead
  (`PUT /proxies/<encoded group>` with `{"name":"<auto group>"}`, 204) or click it in Clash Verge
  → 代理 → the group → the node chip. Either way it is a mutation: ask first.
- The URLTest `alive` flag and cached delay history are **not** traffic truth: a node can read
  `alive: true` (stale history) while forwarded requests stall, and vice versa. Trust the probe
  rate and the core log over the flag.
- Node roster without leaking secrets: the profile yaml
  (`~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/profiles/*.yaml`) holds
  nodes as inline `- {"name":"…","type":"anytls","server":"…","port":…}` lines. Extract with
  `"server":"([^"]+)"` / `"port":(\d+)` / `"name":"([^"]+)"` and print only those three — never
  echo the line, it carries password/uuid/psk.
- `hermes`' own proxy choice is not visible in the core: the adapter logs
  `[Discord] Using proxy for Discord: http://127.0.0.1:<port>`, so the gateway is already using the
  proxy and a proxy-path failure is sufficient to explain it.

## 5. Tooling traps hit on macOS

- `lsof -p <pid> -iTCP -sTCP:LISTEN` **ORs** its selections on macOS: it prints every listener on
  the machine, looking like that pid owns them. Add `-a` (`lsof -nP -a -p <pid> -iTCP -sTCP:LISTEN`).
- `nc -vz <host> <port>` is the cheapest TCP probe; `python3 -c` with
  `socket.create_connection` + `ssl` gives the TLS handshake result and the exception name.
- A root-owned core's FDs/sockets are not inspectable without sudo — read the core API rather than
  trying to inspect the process.

## 6. After the proxy is healthy again (Hermes side)

- `~/.hermes/gateway_state.json` (`platforms.<name>` / `<profile>:<platform>`) carries `state`,
  `error_message`, `updated_at`: `retrying` (backoff up to 300 s) or `fatal`. `fatal` is not
  terminal — the multiplex watcher re-serves per-profile adapters, which is why they flip
  `connected` ↔ `fatal` while the proxy flaps. A `gateway_state.json` read is the cheapest status
  of all bots at once; per-profile `gateway_state.json` files only track non-multiplex platforms.
- Restart the gateway once (not per bot) after the proxy is confirmed, then re-read the state file
  and quote the fresh `✓ discord connected (profile: …)` / `Connected as <bot>` lines.
- Expect the events sent during the gap to be lost: Discord does not replay them, so an "it was
  offline for 20 minutes" window costs those messages permanently — say so instead of promising
  they will arrive late.
