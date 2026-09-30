# Adopting an external skill/plugin pack into a Hermes profile

Depth for `install-hermes-skills`; the profile-side view of the same decision is `maintain-hermes-profile/SKILL.md` §13. Scope: deciding whether a third-party pack (Codex `.codex-plugin`, Claude
`.claude-plugin`, any Agent Plugins v1 package) can be installed, and doing it without bloating the
prompt or tripping the install scan.

## Where the pieces live

| Concern | Owner |
|---|---|
| Portable manifest validation (`$schema` check, name regex, author/keywords types, unknown top-level fields → warning) | `hermes_cli/agent_plugins.py::_validate_manifest` |
| Skill discovery inside a pack (root `skills/`, frontmatter `name` must equal the directory, description ≤ 1024 chars) | `hermes_cli/agent_plugins.py::_discover_skills` |
| Loading a portable package (registers skills, wires portable MCP servers) | `hermes_cli/plugins_loader.py::_load_portable_plugin` |
| Foreign-harness manifest dirs that are deliberately never parsed | `hermes_cli/plugins_discovery.py::_FOREIGN_HARNESS_MANIFEST_DIRS` |
| Install/validate-time content scan | `tools/plugin_guard.py` over `tools/skills_guard.py` |
| Package-gate switch (leave alone) | `hermes_cli/plugins_cmd.py::_scan_on_install_enabled` → `plugins.scan_on_install` |

Adapter shape, not a dependency: the pack's own `scripts/*.py` are ordinary files the agent runs
through `terminal`. There is no MCP server and no connector unless the pack's manifest declares one.

## Manifest shim (only for the plugin route)

Start from the pack's own manifest and change three things:

1. Move `plugin.json` from `.codex-plugin/` (or `.claude-plugin/`) to the pack root.
2. Add `"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"` — absent or
   different → `plugin.json declares an unsupported or missing Agent Plugins schema`.
3. Drop `interface` (vendor UI block) and `skills` (discovered by directory; keeping it only yields the
   diagnostic `ignored unknown top-level field: skills`).

`author` stays an object with only string `name`/`email`/`url`; `keywords` stays an array of strings.
Then, in a throwaway home:

```bash
hermes plugins validate <pack-dir>     # expect the manifest checks green
```

## Loader probe (the honest "can it load" answer)

```bash
PYTHONPATH=<hermes tree> <hermes venv python> -c "
from pathlib import Path
from hermes_cli.agent_plugins import load_agent_plugin
pkg = load_agent_plugin(Path('<pack-dir>'), Path('<home>/plugin-data/probe'))
print(pkg.name, pkg.version, len(pkg.skills), [d.message for d in pkg.diagnostics])"
```

As-shipped Codex layout → `AgentPluginError: plugin.json must be a regular file within the plugin
root`. Shimmed → `name=<pack> v<ver> skills=<N>` with the `skills` diagnostic. Run it against both
layouts when the user asks whether an install is possible — the two lines are the answer.

## Scan verdicts actually seen on a research pack

`scan_skill(dir, source='community')` per skill dir; the pack's own usage examples are what trip it:

| Pattern | Severity / class | Trigger in the pack |
|---|---|---|
| `echo_pipe_exec` | CRITICAL / obfuscation | a documented `echo '<json>' \| python scripts/rest_request.py` invocation |
| `unpinned_pip_install` | MEDIUM / supply_chain | "if `requests` is missing, install it once" prose |
| `python_environ_get_secret` | — | API-key env reads inside the pack's own scripts |
| `python_subprocess` | safe | a script shelling out to a CLI |

Verdict policy (`tools/skills_guard.py::should_allow_install`): community/trusted source + `dangerous`
verdict is a hard block and `--force` does not override it; other combinations resolve through
`INSTALL_POLICY[trust][verdict]` to allow / ask / block. So a pack whose *documentation* pipes into an
interpreter cannot be installed via `hermes plugins install` at all, even though the pack is benign —
report it as a scanner false positive and switch route rather than weakening the gate.

## Prompt-cost measurement (run before copying)

```bash
PYTHONPATH=<hermes tree> <hermes venv python> -c "
from pathlib import Path
from agent.prompt_builder import build_skills_system_prompt
for home in ['<empty-home>', '<home-with-pack>']:
    b = build_skills_system_prompt(skills_dir_override=Path(home)/'skills')
    print(home, len(b), 'chars', len(b.splitlines()), 'lines')"
```

An empty home returns an empty block, so the diff is the whole cost. Descriptions are truncated to
roughly 60 chars in the rendered index, so the block is **not** the sum of the frontmatter
descriptions — a 50-skill pack measured ~5.5 k chars / ~60 lines (~1.4 k tokens) per turn while its
frontmatter name+description summed to ~10 k chars. Install the subset tied to the user's domain and
name what was skipped.

## Subsetting recipe

```bash
# monorepo pack: sparse clone, then copy only the chosen skill dirs into a category folder
mkdir -p <home>/skills/<category>
cp -R <pack>/skills/{research-router,uniprot,rcsb-pdb,alphafold,string}-skill <home>/skills/<category>/
hermes skills list | tail -3      # expect: N local — N enabled
```

Directory names keep the pack's own convention (a `-skill` suffix is fine — the name must equal the
directory). Category choice is free and becomes the index grouping line.

## Verification checklist

1. Throwaway `HERMES_HOME` used for every probe; the live profile's `skills/` untouched until the user
   confirms.
2. `hermes plugins validate` (plugin route) or `hermes skills list` tail (skills route) quoted verbatim.
3. Index-size delta given as a number, with the chosen subset listed.
4. Licence of the pack stated from both the manifest field and the repo's own LICENSE, if redistribution
   is on the table.
