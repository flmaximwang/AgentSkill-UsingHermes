---
name: hermes-mcp-server-integration
description: Use when wiring an MCP server into a Hermes profile.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, mcp, install, toolsets, verification]
    related_skills: [hermes-skills-management, hermes-agent]
---

# Wiring an external MCP server into a Hermes profile

Giving the agent a tool's real surface: install the server, write the two config
keys it needs, prove the tools reach a session. Prefer this over a hub skill that
merely DESCRIBES the tool — a skill is text the agent may or may not read, an MCP
server is a tool the agent actually gets.

## When to use

- The user wants tool X usable by the agent and X ships an MCP server.
- A vendor installer offers a Hermes / "Hermes Agent" target.
- A hub skill for that tool is blocked, stale, or a wrapper around the same server.
- A configured server's tools never show up in a session.

## Target the profile first

Every write lands in `$HERMES_HOME`. A desktop-app session exports the active
profile's home, so `echo $HERMES_HOME` before touching anything; `hermes profile
list` marks the active profile with `◆`, and `hermes -p <profile> …` retargets one
command. "Global" in a vendor's wording still means *that* profile's `config.yaml`.

## Procedure

### 1. Read what will be written, before writing it

A vendor with a real Hermes integration ships a dry run:

```bash
npx -y <pkg> install --print-config hermes     # writes nothing; prints YAML + the target path
```

Confirm the printed path is the profile you chose. No dry run? `hermes mcp add
<name> --command <cmd> --args …` writes the same keys and is the canonical path.

### 2. Back up, write, then diff

Third-party installers do **line surgery** on `config.yaml` (string splicing, not a
YAML merge), so prove nothing else moved:

```bash
cp "$HERMES_HOME/config.yaml" /tmp/config.yaml.pre-<server>
shasum -a 256 /tmp/config.yaml.pre-<server>
# run the installer, or hermes mcp add
diff /tmp/config.yaml.pre-<server> "$HERMES_HOME/config.yaml"
python3 -c "import yaml,sys; d=yaml.safe_load(open(sys.argv[1])); print('yaml OK', list(d.get('mcp_servers',{})))" "$HERMES_HOME/config.yaml"
```

The diff must be additions only: every pre-existing `mcp_servers` child and every
entry of `platform_toolsets.cli` still present.

### 3. The two keys — both are required

```yaml
mcp_servers:
  <name>:
    command: <binary>        # must resolve on PATH
    args: [serve, --mcp]
    timeout: 120             # seconds, per tool call
    connect_timeout: 60      # seconds, connect + tool discovery
    enabled: true

platform_toolsets:
  cli:
    - ...                    # keep every existing entry
    - mcp-<name>             # append; this is what lets the tools through
```

`mcp-<name>` is derived by Hermes, never invented: `tools/mcp_tool_registration.py`
`registry.register_toolset_alias(server, f"mcp-{server}")`. A profile that sets an
explicit `platform_toolsets.cli` list filters out every toolset not named in it,
so a server can be connected and still invisible in CLI sessions.

### 4. Verify — three checks, in this order

1. **Binary on PATH**: `which <binary>`. An `npx -y <pkg>` run installs nothing;
   a `command:` that does not resolve makes the server silently absent. Install it
   (`npm i -g <pkg>` — Hermes bundles node under `~/.hermes/tools/node-*/bin`,
   already on PATH).
2. **Handshake**: `scripts/mcp_handshake.py <binary> [args…]` sends `initialize` →
   `notifications/initialized` → `tools/list` and prints the server name, protocol
   version and every tool it advertises. Read-only, exit 1 on a failed handshake.
   Use it instead of trusting any doc's tool table.
3. **One real call, in a THROWAWAY directory** — never the user's repos. For an
   indexer: `mkdir /tmp/probe`, write three files with a known call chain, run the
   tool's index command, then one query whose answer you can check by eye.

### 5. Say when it takes effect

MCP servers are materialized per session at startup. A server added mid-session is
NOT available in the session that added it — say "start a new session" instead of
implying the tools are live now.

## Pitfalls

1. **A vendor's bundled skill doc is not the tool's surface.** Community skills
   drift: one advertised a multi-tool MCP table while the installed server listed a
   single tool, deliberately. Probe the server and report the drift; never repeat
   the table into your own instructions.
2. **A pruned tool list can be intentional.** Vendors collapse overlapping tools
   into one good one and re-expose the rest behind an env knob (in the server's
   `env:`). Check the server's own source or `--help` before calling a missing tool
   a bug.
3. **`--print-config` prints the path it WOULD write.** With `$HERMES_HOME` unset
   that is `~/.hermes/config.yaml` — the default profile. Set it before the real
   write.
4. **Telemetry.** Many of these tools collect anonymous usage stats by default and
   print the opt-out once. Surface it and offer to turn it off.
5. **Never index the user's real project trees as part of "install".** Probing
   belongs in a throwaway dir; per-project setup is a separate, user-chosen step
   (ask which repo).

## Support files

- `scripts/mcp_handshake.py` — stdio MCP probe (handshake, tool list, one optional
  call); the check in step 4.2.
- `references/codegraph.md` — the CodeGraph MCP server: its Hermes target, the exact
  config block, the verified handshake, and its deliberate one-tool surface.
