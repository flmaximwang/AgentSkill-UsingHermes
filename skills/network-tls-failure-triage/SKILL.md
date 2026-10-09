---
name: network-tls-failure-triage
description: "Use when shell HTTPS calls fail or hang — TLS errors, proxy misconfig, stalled transfers."
version: 1.0.0
author: Agent
platforms: [macos, linux]
metadata:
  hermes:
    tags: [network, tls, captive-portal, proxy, troubleshooting, macos]
---

# Network / TLS Failure Triage

Triage order for HTTPS that dies in the shell: **captive portal → system proxy → TLS interception →
the caller's own proxy config → target itself**. Covers the probe, the fingerprints that identify each, and how to clear a portal.

## The rule that saves the most time

**When every host fails TLS from the shell, the fault is the local network layer — not the target
service, its credentials, or the plugin code you were about to debug.** Symptoms that masquerade as an
app bug: a platform-setup wizard that "cannot reach the API", `web_search`/`web_extract` dying with
`SSL: UNEXPECTED_EOF_WHILE_READING`, `pip install` / `git clone` / `curl` failing, and QR or
device-code onboarding silently falling back to a manual path.

Run the probe (~10 s) before opening a single config file: `bash scripts/probe.sh` (in this skill), or
the individual commands below.

## Step 1 — probe

```bash
# (a) plain HTTP — a captive portal answers here even while TLS is broken
curl -sS -i -m 12 http://captive.apple.com/hotspot-detect.html | head -25
# (b) TLS with verification off — separates "cannot connect" from "cert not trusted"
curl -sS -k -m 12 -o /dev/null -w 'http=%{http_code}\n' https://<host>
# (c) who signed the certificate
echo | openssl s_client -connect <ip>:443 -servername <host> -showcerts 2>&1 | openssl x509 -noout -subject -issuer
# (d) local proxy + the process behind it
scutil --proxy; ps aux | grep -iE 'clash|mihomo|surge|sing-box|proxyman|charles' | grep -v grep
```

## Step 2 — read the fingerprint

| Observation | Meaning | Action |
|---|---|---|
| Plain HTTP returns `302` with `Location: http://<portal-host>/…` | Captive portal (hotel / airport / campus WiFi) | Open that URL; the user authenticates |
| Only HTTPS fails (`self signed certificate`, `SSL_ERROR_SYSCALL`, `UNEXPECTED_EOF_WHILE_READING`) while plain HTTP works | Portal/blocking gateway forges a certificate and lets only HTTP through, to steer you to its login page | Same as above |
| `curl -k` against ANY host or path returns `<WISPAccessGatewayParam>…<NextURL>…` | Definitive portal fingerprint — the gateway answers for every request | Open the `NextURL` |
| Certificate subject is a self-signed root (a `…Certification Authority…` CN served as the leaf) | TLS interception: portal gateway or a MITM proxy | Portal probe vs proxy process decides which |
| Only ONE host fails, everything else is fine | Genuine target / DNS / cert problem | Legitimately app- or site-specific — debug the app |
| Everything fails including HTTP, no proxy process | Upstream link or DNS down | `dig +short <host>`, check the router |

## Step 3 — clear a captive portal (macOS)

```bash
# (A) preferred — the gateway reissues a fresh token on its own redirect
open "http://captive.apple.com/hotspot-detect.html"
# (B) fallback — the portal entry captured from the probe's Location header
open "http://<portal-host>/entrance?param=…&uuid=…"   # param/uuid are per-AP-session and often one-shot
# (C) force the system captive window / re-probe
open -a "/System/Library/CoreServices/Captive Network Assistant.app"
networksetup -setairportpower <wifi-device> off; sleep 4; networksetup -setairportpower <wifi-device> on
```

Portal logins are usually JS SPAs; read the page `<title>` and hand that to the user so they know what
they are looking at. **The user completes the login** (phone + SMS code, WeChat, room number). Never
fill a portal's credentials, and never treat `-k` as the fix — it is a diagnostic only.

## Step 4 — verify, then re-run the blocked task

```bash
curl -sS -m 10 http://captive.apple.com/hotspot-detect.html | head -3   # expect <TITLE>Success</TITLE>, not a 302
curl -sS -m 15 -o /dev/null -w '%{http_code}\n' https://<the-host-that-failed>   # expect a real status, never 000
```

Then re-run whatever was blocked — wizard, search, install — and report to the user the portal host,
the page title, and what it asks for.

## Step 5 — the caller's own proxy settings (git, curl, package managers)

Once the network layer is exonerated, the next suspect is **the scheme of the proxy URL the caller was
given**. A proxy field is not "a URL for the proxy host" — the scheme says how to talk to it.
`https://127.0.0.1:7890` means **TLS to the proxy**; a plaintext HTTP proxy (Clash/mihomo and most local
proxies) receives a TLS ClientHello, reads it as a malformed request and never answers, so the client sits
until its own timeout instead of failing fast. Plain `GET`s often still succeed while `POST`-based
transfers stall, which is what makes it masquerade as a target-side problem.

Discriminator (5 s, read-only) — same target, both schemes:

```bash
curl -sS -m 10 -x http://127.0.0.1:7890   -o /dev/null -w 'http-proxy: %{http_code} %{time_total}s\n' https://api.github.com/
curl -sS -m 10 -x https://127.0.0.1:7890  -o /dev/null -w 'tls-proxy:  %{http_code} %{time_total}s\n' https://api.github.com/
```

`SSL_ERROR_SYSCALL` in milliseconds on the `https://` line while the `http://` line returns `200` is the
fingerprint. `scripts/proxy_scheme_probe.sh` runs both plus `socks5h` in one shot.

Rules that follow:

- **Fix the client's proxy value, not the shell env.** git hands `http.proxy` to libcurl as
  `CURLOPT_PROXY`, and libcurl then ignores `https_proxy`/`all_proxy`; `export https_proxy=…` cannot work
  around a bad `~/.gitconfig` entry. Fix the config, then retry.
- **`http.proxy` and `https.proxy` are separate git keys**, and `https.proxy` is the one an `https://`
  remote actually uses — repairing only `http.proxy` changes nothing.
- **Never drop the proxy setting to "test direct" without confirming the host is reachable without it.**
  A blocked host and a workable proxy look identical once the proxy is gone. Plenty of networks reach a
  vendor's API host while `github.com:443` itself is unreachable — probe the exact host the task needs.
- **SOCKS5 is a different transport** and routinely clears stalls specific to an HTTP proxy:
  `socks5h://127.0.0.1:7890` (the `h` resolves the hostname proxy-side).

## Pitfalls

- **HTTP-up / HTTPS-down is the portal signature, not a certificate bug.** Plain HTTP is deliberately
  allowed (302 to the login page) while TLS gets a forged cert. Do not "fix" it by disabling
  verification in a config file.
- **A working GUI browser plus a failing shell is normal on a portal.** Browsers ride the macOS system
  proxy (`scutil --proxy`) and often hold an authenticated session; `curl`/`urllib` pick up a proxy only
  from `HTTP(S)_PROXY` env vars, so the shell can look broken while Safari/Chrome is fine. Exporting
  `HTTPS_PROXY` is not the fix — it only changes which layer sees the interception.
- **Test both paths before blaming a proxy**: `curl -x http://127.0.0.1:7890 …` vs `curl --noproxy '*' …`.
  A running Clash/mihomo with a dead subscription node on hotel WiFi is indistinguishable from a portal
  block until you compare.
- **Interface names lie.** Wi-Fi is not always `en0`; `networksetup -getairportnetwork <dev>` can print
  "not associated" while that device still carries the default route — trust `route -n get default`.
- **The API/onboarding layer hides the cause.** urllib-based flows swallow network errors behind one
  generic line (the reason is only in the log), then "fall back" to a manual path that cannot work
  either. Fix the network first; do not re-run the wizard or edit credentials.
- Linux counterpart: `nmcli -f GENERAL,IP4 device show`; check `http://connectivitycheck.gstatic.com/generate_204`
  (expect `204`) or `http://captive.apple.com/`.
- **A client's timeout message is not evidence of a dead transfer.** Wrappers print one canned string for
  every expiry — "no response from the remote", "connection reset" — whether or not bytes were moving.
  Measure the transfer before believing it: watch the destination/temp file grow, or re-run with progress
  output on (`git fetch --progress`, `curl -#`). In a git fetch, `remote: Compressing objects:` means the
  *server* is working and zero client bytes are expected; `Receiving objects:` is when bytes land. Growth
  ⇒ slow link (let it finish / raise the cap); no growth ⇒ real stall (fix transport). Opposite remedies,
  so never act on the message alone.
- **A transfer that fails and restarts from zero is often a size problem, not a network problem.** A
  client that cannot resume (git fetch) plus a sweeper that deletes aborted temp packs means every retry
  redownloads everything. Read the leftover temp files in the destination directory: their size is your
  throughput times the timeout, and comparing that with what the transfer needs tells you whether it can
  ever fit inside the cap.

## Related

- Feishu/Hermes bot setup that trips this: `lark-cli` → `references/new-profile-feishu-bot.md`
  ("When the scan flow can't reach Feishu").
- `scripts/probe.sh` — the read-only probe from Step 1 as one re-runnable script.
- `scripts/proxy_scheme_probe.sh` — which scheme the local proxy actually speaks (http / https / socks5h).
