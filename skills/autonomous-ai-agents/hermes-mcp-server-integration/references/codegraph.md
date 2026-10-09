# CodeGraph as a Hermes MCP server

`@colbymchenry/codegraph`: a local-first code knowledge graph (Rust kernel +
tree-sitter, per-project `.codegraph/` index, MCP server over stdio). Every
ClawHub skill named `codegraph*` wraps or documents this; go to the upstream
package instead of a skill — the hub's `codegraph` row is unfetchable (ambiguous
slug) and `codegraph-tool` is hard-blocked by the security scanner.

## Install and wire

```bash
npx -y @colbymchenry/codegraph install --target=hermes --location=global --yes  # config only
npm i -g @colbymchenry/codegraph                                              # binary on PATH
```

The first command writes ONLY `config.yaml` — it does not install the CLI, despite
what the interactive flow implies. `--print-config hermes` prints the same block and
writes nothing; both honour `$HERMES_HOME`, so they name the active profile's
config. `codegraph uninstall` removes the same lines.

Written block (additive; verified diff on a live profile = 9 added lines, 0
removed, `yaml.safe_load` clean, pre-existing `mcp_servers` child intact):

```yaml
mcp_servers:
  codegraph:
    command: codegraph
    args: [serve, --mcp]
    timeout: 120
    connect_timeout: 60
    enabled: true
platform_toolsets:
  cli: [..., mcp-codegraph]
```

## Verified surface (v1.6.0)

- Handshake: `initialize` → `{"name": "codegraph", "version": "1.6.0"}`,
  protocol `2024-11-05`.
- `tools/list` advertises ONE tool: `codegraph_explore`. That is deliberate, not a
  broken install — `src/mcp/tools.ts` has
  `DEFAULT_MCP_TOOLS = new Set(['explore'])`, with the comment that the other
  seven "are no longer LISTED to agents". Re-expose any of them through the
  server's `env:` with `CODEGRAPH_MCP_TOOLS=explore,node,search,callers,…`.
- The CLI keeps the full verb set regardless of the MCP surface:
  `init|index|sync|status|query|explore|context|node|files|callers|callees|impact|affected|install`.
- Without a project index the server still starts and answers, but warns on stderr
  (`No .codegraph/ at or above <cwd>: no default project, live sync disabled`) and
  has nothing to explore — index first, then probe.

## Indexing and querying

`codegraph init` builds the graph in one step (creates `.codegraph/`), then the
watcher syncs edits incrementally; there is no per-query re-index. Measured on a
hand-written three-file Python project: 3 files, 9 nodes, 13 edges in 671 ms.

`codegraph explore "<question>"` returns the same payload the MCP tool does —
relevant symbols' verbatim source grouped by file, plus a blast-radius block
(caller count and test-coverage gap). That makes it the cheap way to validate an
index before a session ever loads the tool.

Telemetry is on by default (anonymous; no code, paths or names): `codegraph
telemetry off`, or `CODEGRAPH_TELEMETRY=0`.
