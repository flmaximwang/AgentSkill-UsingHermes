#!/usr/bin/env bash
# Which scheme does the local proxy actually speak?
#
# Usage: scripts/proxy_scheme_probe.sh [proxy-host:port] [target-url]
#        defaults: 127.0.0.1:7890   https://api.github.com/
#
# Read-only: three GETs, no config and no repo is touched.
set -u

PROXY="${1:-127.0.0.1:7890}"
URL="${2:-https://api.github.com/}"
T=10

probe() {  # $1 = scheme to test for the proxy itself
  local scheme="$1" out
  out=$(curl -sS -m "$T" -x "${scheme}://${PROXY}" -o /dev/null \
        -w '%{http_code} %{time_total}s' "$URL" 2>&1 | tail -1)
  printf '  %-8s proxy %-16s -> %s\n' "$scheme" "$PROXY" "$out"
}

echo "proxy: $PROXY    target: $URL"
probe http
probe https
probe socks5h
echo
echo 'Verdict:'
echo '  http OK, https failing in <0.1s with SSL_ERROR_SYSCALL => the proxy speaks PLAINTEXT HTTP.'
echo '    The https:// scheme means TLS TO the proxy. Callers must use http://<host>:<port>.'
echo '  http failing but socks5h OK  => use socks5h://<host>:<port> (resolves names proxy-side).'
echo '  all three failing             => the proxy is down or the target is blocked; triage Steps 1-4.'
echo '  all three OK but a POST-based transfer stalls => HTTP-proxy-specific; try socks5h for that client.'
