---
name: remove-a-hermes-plugin
description: "插件删不掉（Cannot remove plugin…/gateway 在跑/UI 的 Remove 按钮）时用：合法绕法（--allow-live-gateway vs 停网关）、跨 profile 清残留、删完要不要重启。装/更新插件与删 skill 是兄弟技能。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, plugins, gateway, profiles, removal]
---

# Remove a Hermes plugin cleanly

## When to Use

- `hermes plugins remove` (or a UI Remove button) refuses with "Cannot remove plugin files while the
  messaging gateway is running".
- A plugin must be gone from *every* profile, not just the active one, and the stale
  `plugins.enabled` / `plugins.disabled` entries cleaned up with it.
- Someone asks whether the gateway really has to be restarted after a plugin change.

## Symptom

```
Could not remove plugin 'X': Cannot remove plugin files while the messaging gateway is running
and its loaded plugin callbacks import from the installed checkouts. Run `hermes gateway stop`,
apply the change, then `hermes gateway start`. To skip this check pass --allow-live-gateway
(callbacks may fail until restart).
```

**Version check first (measured 2026-10-08, v0.21.5+9287).** On a current install that guard is
**gone**: `grep -rn "_refuse_live_gateway" hermes_cli/` finds nothing, `hermes plugins remove --help`
lists only `name`, and `--allow-live-gateway` is rejected as an unknown flag (you get the top-level
`hermes` usage). Removal of a `disabled`, callback-free plugin succeeded live — multiplexed gateway
running, no flag, no restart. So: try the plain command first; only read the paragraph below if the
refusal actually appears (older builds).

The guard (older builds: `hermes_cli/plugins_cmd.py:_refuse_live_gateway_mutation`) is a **blanket** refusal:
it fires whenever a gateway is live for the active `HERMES_HOME`, even for a plugin that is
`disabled` and declares no emits/listens. The dashboard/desktop remove path
(`dashboard_remove_user_plugin`) never passes the flag, so clicking Remove in a UI can *never*
succeed while a gateway runs — the CLI is the only way.

## Procedure

1. **Never stop the gateway from inside a gateway session.** A Discord/Telegram session's agent
   process is a *child* of the gateway process (`ps -o ppid` up from your own PID proves it), and
   the reply itself is delivered by that gateway. `hermes gateway stop` mid-turn kills the session
   and the answer is lost.

2. **Removal is one checkout per profile.** Each profile has its own plugin dir:
   `$HERMES_HOME/plugins/<name>` — the default profile's is `~/.hermes/plugins/`. A plugin can be
   installed in several profiles at once; enumerate before removing:
   ```bash
   ls -d ~/.hermes/plugins/*/ ~/.hermes/profiles/*/plugins/*/
   ```
   Remove each copy:
   ```bash
   hermes plugins remove <name>
   HERMES_HOME=~/.hermes/profiles/<p> hermes plugins remove <name>
   # older builds only, when the live-gateway refusal fires:
   hermes plugins remove <name> --allow-live-gateway
   ```
   Removal also drops the plugin's entries from *that* profile's `config.yaml`
   (`plugins.enabled` / `plugins.disabled`) and from that dir's `.install-metadata.json`.

   **Residue removal deliberately leaves (measured 2026-10-08).** For a plugin that shipped a platform
   adapter, `config.yaml` keeps four things: `platform_toolsets.<platform>:` (a dangling
   `hermes-<platform>` toolset), `known_plugin_toolsets.<platform>: [- <plugin>]` (the off-list), and
   `_left_core_scoped` / `_left_core_installed` (`hermes_cli/left_core_migration.py`).
   * `platform_toolsets.<platform>` is the only one that **hurts**: `hermes config check` then prints
     `⚠ platform '<p>' references unknown toolset 'hermes-<p>'` + `no valid toolsets configured` in
     every home. Delete the key, proving the edit with a diff (nothing else may change):
     ```bash
     cp <home>/config.yaml <scratch>/<p>.config.yaml
     hermes config unset platform_toolsets.<platform>      # HERMES_HOME=… for a profile
     diff -u <scratch>/<p>.config.yaml <home>/config.yaml   # must show only that 2-line block
     ```
   * `_left_core_installed` is the marker that makes **removal stick** (`_pending()` skips a marked
     row, so the migration never re-installs the plugin) — keep it. Keep `_left_core_scoped` and
     `known_plugin_toolsets` too: inert without the plugin, and they preserve the toolset scope if the
     user reinstalls.

3. **Clean stale config entries in the other profiles via the CLI.** A profile that never had the
   files can still list the plugin under `plugins.enabled`/`disabled`. `hermes config set` accepts a
   JSON array and edits surgically (comments preserved), so rebuild the list with the plugin
   dropped:
   ```bash
   HERMES_HOME=~/.hermes/profiles/<p> hermes config set plugins.enabled '["a", "b"]'
   ```
   **Pitfall:** do not copy one profile's list into another. Back up first and prove the edit with a
   diff — a wrong list silently *enables new plugins* in that profile:
   ```bash
   cp ~/.hermes/profiles/<p>/config.yaml <scratch>/<p>.config.yaml   # before
   diff -u <scratch>/<p>.config.yaml ~/.hermes/profiles/<p>/config.yaml
   ```
   The diff must show only the removed line.

4. **Decide whether a gateway restart is really needed.** Restarting drops every profile's live
   session (all bots blip), so it is a confirmation-worthy step — and for a `disabled`,
   callback-free plugin it is not required. Evidence to collect instead of guessing:
   ```bash
   hermes plugins show <name>            # Status: disabled  /  Emits: (none)  /  Listens: (none)
   lsof -p <gateway_pid> | grep <name>   # no open files from the removed tree
   ```
   Only enabled plugins with emits/listens (callbacks loaded into the running gateway) need the
   stop → change → start cycle. Otherwise report the removal as complete and offer the restart.

5. **A memory provider is two removals, not one.** `hermes plugins remove <name>` deletes the code,
   but the provider stays **active**, because activation is `memory.provider` in `config.yaml` —
   *not* `plugins.enabled`, and `hermes plugins enable <name>` does **not** activate one either
   (`website/docs/user-guide/features/memory-providers.md`). Retire it in this order:
   ```bash
   hermes memory status                 # which provider is active, and what the store looks like
   hermes memory off                    # clears memory.provider; built-in MEMORY.md/USER.md untouched
   hermes plugins remove <name>
   ```
   Residue a memory provider leaves **beyond** the plugin dir — enumerate it before declaring done:
   * its store (`$HERMES_HOME/*.db`) and whatever tuning/sidecar files it wrote next to it
     (`<name>_params.json` & co.);
   * its identity mapping file if it had one (`$HERMES_HOME/users.yaml`) — nothing else reads it;
   * its model cache, which normally lives **outside** `$HERMES_HOME` (`~/.cache/<name>/`) and is
     therefore *not* removed with the profile — this is the GB-scale part the user is usually
     thinking of when they say "把模型也删掉".

6. **Before deleting a memory store, prove each row lives elsewhere — that is the user's bar, and
   row counts / byte sizes do not meet it.** Export first (the provider's own `export --user … -o …`
   CLI; mind that the bucket name is the *raw* platform/user id unless it resolved an identity, and
   a CLI bucket default such as `general` is not the session's bucket). Then show, per row, where the
   content still exists: for a row that is a transcript/document dump, strip whitespace, keep the
   substantive lines (say ≥25 chars) and count how many appear **verbatim** in a file that still
   exists, then name the home of the remainder (the chat history, the source document). Say plainly
   when a referenced source is already gone (e.g. a chat attachment the cache has since pruned)
   instead of silently counting that row as covered.

## Verification (all four must hold)

```bash
# 0. every home is warning-free (this is what catches a dangling platform_toolsets entry)
for p in default <profiles>; do … hermes config check | grep -c "⚠"; done
# 1. no config anywhere still names the plugin outside the intentional bookkeeping keys
grep -rn "<name>" ~/.hermes/config.yaml ~/.hermes/profiles/*/config.yaml
# 2. no dir left
ls -d ~/.hermes/plugins/*/ ~/.hermes/profiles/*/plugins/*/
# 3. no install-metadata key
for f in ~/.hermes/plugins/.install-metadata.json ~/.hermes/profiles/*/plugins/.install-metadata.json; do
  python3 -c "import json,sys;print(sys.argv[1],list(json.load(open(sys.argv[1])).keys()))" "$f"; done
# 4. the plugin is unknown to the CLI
hermes plugins show <name>        # -> Plugin '<name>' not found.
```

## Restoring

Installed plugins are pinned git checkouts, so removal is reversible: `hermes plugins show <name>`
before the removal prints the source repo, and `.install-metadata.json` records the exact revision.
```bash
hermes plugins install <owner>/<repo>     # re-adds from the catalog pin
```

## Skill Structure

<!-- Generated by Scripts -->

```
remove-a-hermes-plugin/
├── SKILL.md  (171 lines)
├── test-prompts.json  (27 lines)
└── test-results.md  (47 lines)
```

<!-- Generated by Scripts -->
