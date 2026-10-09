#!/usr/bin/env bash
# Network / TLS failure triage probe. READ-ONLY: changes no config and no network state.
# Usage: bash probe.sh [url ...]
set -u
HOSTS=("$@")
if [ ${#HOSTS[@]} -eq 0 ]; then
  HOSTS=(https://www.baidu.com https://accounts.feishu.cn https://open.feishu.cn)
fi

hr() { printf '\n== %s ==\n' "$1"; }

hr "1. default route / Wi-Fi device"
route -n get default 2>/dev/null | grep -E 'gateway|interface' || echo "(no default route)"
networksetup -listallhardwareports 2>/dev/null | awk '/Wi-Fi/{getline; print "Wi-Fi device:" $2}'

hr "2. captive-portal probe (plain HTTP) - look for 302 + Location: http://<portal>"
curl -sS -i -m 12 http://captive.apple.com/hotspot-detect.html 2>&1 | head -25

hr "3. TLS, verification OFF (diagnostic only: 200/302 proves reachability, cert is the issue)"
for u in "${HOSTS[@]}"; do
  printf '%-42s ' "$u"
  curl -sS -k -m 12 -o /dev/null -w 'http=%{http_code}\n' "$u" 2>&1 | tail -1
done

hr "4. TLS, verification ON (000 = untrusted / intercepted)"
for u in "${HOSTS[@]}"; do
  printf '%-42s ' "$u"
  curl -sS -m 12 -o /dev/null -w 'http=%{http_code}\n' "$u" 2>&1 | tail -1
done

hr "5. certificate issuer of the first host (self-signed root as leaf = interception)"
first="${HOSTS[0]#https://}"; first="${first%%/*}"
printf '' | openssl s_client -connect "${first}:443" -servername "$first" 2>&1 \
  | openssl x509 -noout -subject -issuer 2>/dev/null || echo "(handshake failed)"

hr "6. captured portal fingerprint (a gateway answers any host with this XML)"
curl -sS -k -m 12 -X POST https://accounts.feishu.cn/oauth/v1/app/registration -d 'action=init' 2>&1 \
  | head -12

hr "7. local proxies and interception processes"
scutil --proxy 2>/dev/null | grep -E 'Enable|Proxy|Port'
ps aux | grep -iE 'clash|mihomo|surge|sing-box|proxyman|charles|mitm' | grep -v grep || echo "(no proxy process)"

echo
