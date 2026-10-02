#!/usr/bin/env bash
# Read-only status report for the Hermes Discord channel.
# Gates, in order: API reachability -> privileged intents -> bot guild membership -> allowlist/home channel/log.
# Never prints the bot token. Performs no mutating calls.
#
# Usage: bash scripts/discord_check.sh
# Env:   HERMES_ENV            (default $HERMES_HOME/.env)
#        HERMES_GATEWAY_LOG    (default ~/.hermes/logs/gateway.log)
#        DISCORD_PROXY         e.g. http://127.0.0.1:7890 (auto-detected from macOS scutil otherwise)

set -u

ENV_FILE="${HERMES_ENV:-${HERMES_HOME:-$HOME/.hermes}/.env}"
LOG_FILE="${HERMES_GATEWAY_LOG:-$HOME/.hermes/logs/gateway.log}"
API=https://discord.com/api/v10

env_get() { grep -m1 "^$1=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d "\"' " | tr -d '\r'; }

TOKEN="$(env_get DISCORD_BOT_TOKEN)"
ALLOWED="$(env_get DISCORD_ALLOWED_USERS)"
HOME_CH="$(env_get DISCORD_HOME_CHANNEL)"
if [ -z "$TOKEN" ]; then echo "FAIL  no DISCORD_BOT_TOKEN in $ENV_FILE"; exit 2; fi

# --- proxy: explicit DISCORD_PROXY, else the macOS system proxy -------------------------------
PROXY="${DISCORD_PROXY:-}"
if [ -z "$PROXY" ] && command -v scutil >/dev/null 2>&1; then
  ph=$(scutil --proxy 2>/dev/null | awk '/HTTPProxy/{print $3}')
  pp=$(scutil --proxy 2>/dev/null | awk '/HTTPPort/{print $3}')
  if [ -n "$ph" ] && [ -n "$pp" ]; then PROXY="http://$ph:$pp"; fi
fi
CURL=(curl -s -m 12)
if [ -n "$PROXY" ]; then CURL+=(-x "$PROXY"); fi

fail() { echo; echo "VERDICT: $1"; exit 1; }

# --- gate 0: API reachable -------------------------------------------------------------------
code=$("${CURL[@]}" -o /dev/null -w '%{http_code}' -H "Authorization: Bot $TOKEN" "$API/applications/@me")
if [ "$code" != "200" ]; then
  echo "GATE 0  API unreachable (HTTP $code, proxy=${PROXY:-none})"
  if [ "$code" = "000" ]; then
    echo "        hint: direct access may resolve discord.com into a Clash fake-ip (198.18.0.0/15)."
    echo "        hint: retry with DISCORD_PROXY=http://127.0.0.1:7890"
  fi
  fail "gate 0 failed - fix network/proxy first."
fi
echo "GATE 0  API OK (HTTP 200)${PROXY:+  via $PROXY}"

# --- gate 1: privileged intents --------------------------------------------------------------
app_json=$("${CURL[@]}" -H "Authorization: Bot $TOKEN" "$API/applications/@me")
read -r flags content members presence <<< "$(printf '%s' "$app_json" | python3 -c 'import sys, json
f = (json.load(sys.stdin).get("flags") or 0)
print(f, int(bool(f & (1 << 19))), int(bool(f & (1 << 15))), int(bool(f & (1 << 13))))')"
echo "GATE 1  flags=$flags  MESSAGE_CONTENT=$content  GUILD_MEMBERS=$members  PRESENCE=$presence"
if [ "$content" != "1" ]; then
  fail "gate 1 failed - Message Content Intent is off. Portal > Bot > Privileged Gateway Intents (+ Save Changes), or PATCH /applications/@me flags, then: hermes gateway restart"
fi
if [ "$members" != "1" ]; then echo "        warn: GUILD_MEMBERS off - username-based allowlists cannot resolve."; fi

# --- gate 2: bot guild membership ------------------------------------------------------------
guilds=$("${CURL[@]}" -H "Authorization: Bot $TOKEN" "$API/users/@me/guilds")
printf '%s' "$guilds" | python3 -c 'import sys, json
g = json.load(sys.stdin)
if isinstance(g, list):
    print("GATE 2  bot guild membership: {} guild(s)".format(len(g)))
    for x in g:
        print("          {}  {}".format(x.get("id"), x.get("name")))
    sys.exit(0 if g else 1)
print("GATE 2  unexpected response (HTTP error?)")
sys.exit(2)' || fail "gate 2 failed - the bot user is in no guild. Re-invite with scope=bot+applications.commands (the Portal-provided link installs commands only)."

# --- gate 3: allowlist + home channel + gateway log ------------------------------------------
echo "GATE 3  DISCORD_ALLOWED_USERS=$ALLOWED"
if [ -n "$HOME_CH" ]; then
  hc=$("${CURL[@]}" -o /dev/null -w '%{http_code}' -H "Authorization: Bot $TOKEN" "$API/channels/$HOME_CH")
  echo "        DISCORD_HOME_CHANNEL=$HOME_CH -> HTTP $hc"
  if [ "$hc" != "200" ]; then echo "        warn: not a reachable text channel (404 => a guild id was pasted)."; fi
fi
if [ -f "$LOG_FILE" ]; then
  connected=$(grep -c 'Connected as' "$LOG_FILE")
  inbound=$(grep -c 'inbound message: platform=discord' "$LOG_FILE")
  parked=$(grep -c 'parked' "$LOG_FILE")
  echo "        log: 'Connected as' x${connected}, discord inbound x${inbound}, parked x${parked}"
  if [ "$inbound" = "0" ]; then
    echo "        note: no Discord message has EVER been admitted - send a real @mention (pick it from"
    echo "              autocomplete), then re-run this script."
  fi
else
  echo "        no log at $LOG_FILE"
fi

echo
echo "VERDICT: gates 0-2 passed. If the bot is online but silent, send a real @mention and look for"
echo "         'inbound message: platform=discord' in $LOG_FILE."
