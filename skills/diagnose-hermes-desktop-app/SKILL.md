---
name: diagnose-hermes-desktop-app
description: "Use when the Hermes desktop app or plugin misbehaves. An Electron pane or tab that errors, spins or renders empty, a desktop plugin whose UI appears but whose data call 404s, or a feature that works on one profile and not another. Gateway/platform bot trouble is `debug-hermes-gateway`; bulk profile and config surgery is `maintain-hermes-profile`."
---

# Hermes desktop app diagnostics

Diagnosing the Hermes **desktop app** (Electron) and the things it loads: panes/tabs that error,
desktop plugins whose UI appears but whose data call fails, a feature that works in one profile and
not another. The messaging/gateway surface is a different skill (`debug-hermes-gateway`);
profile/config surgery is `maintain-hermes-profile`.

## When to Use

- A pane or tab in the app errors, spins forever, or renders empty.
- A plugin's navigation item/tab exists but its requests fail (`desktop.log` `hermes:api … Error`).
- The same feature works on one profile and fails on another; an install "didn't work" although the
  files are on disk; the app cannot reach its backend.
- The user points at a path under `$HERMES_HOME/desktop-plugins/` and says it misbehaves.

## 1. Read the app's own state before touching anything

Four reads decide most reports. The app's userData dir is
`~/Library/Application Support/Hermes` on macOS (`%APPDATA%/Hermes` on Windows, `~/.config/Hermes` on
Linux).

```bash
APPSUP="$HOME/Library/Application Support/Hermes"
cat "$APPSUP/active-profile.json"            # {"profile": "..."} — the profile the app is on NOW
cat "$APPSUP/backend-ownership.json"         # per backend: pid, profile, full command line
cat "$APPSUP/connections.json"               # local | remote | cloud (§5)
grep -iE "renderer console|hermes:api" ~/.hermes/logs/desktop.log | tail -40
```

- `backend-ownership.json` `command` is the truth about **which profile the backend serves**: a
  desktop backend is a `serve` process spawned per (connection, profile)
  (`… hermes --profile <name> serve --host 127.0.0.1 --port 0`). `--port 0` is OS-assigned — resolve
  the real port from the listener, never from argv:
  `lsof -nP -p <pid> -a -iTCP -sTCP:LISTEN`.
- `desktop.log` carries renderer console output and every failed `hermes:api` call **with its URL and
  status**. Grep the route or plugin name first; that line plus the profile in §1 is usually the whole
  diagnosis. `~/Library/Application Support/Hermes` also holds `Preferences`, `Local Storage/leveldb`
  (per-profile last route) — needed only when you must prove which profile a pane was showing.
- App logs and backend logs are different files: the backend writes the profile's `logs/agent.log`.
- Never infer the profile from a path you were handed. The user's `~/.hermes/desktop-plugins/...` is
  the **app's** home, not necessarily the profile the app is driving.

## 2. App-level vs profile-level — the default explanation

Two scopes coexist and disagree in exactly one direction, which produces most "this plugin is broken"
reports:

| Thing | Scope | Lives at |
|---|---|---|
| Desktop code the renderer loads (desktop plugins, window/connection state) | **app-level**, one copy for the whole app, loaded on every profile | `<app hermes home>/desktop-plugins/<id>/plugin.js` |
| Agent-side code: plugin Python backends, tools, hooks, memory, config, skills, sessions | **profile-level**, one `serve` backend per profile | `<profile home>/plugins/<id>/`, `<profile home>/config.yaml` |

So a UI element can appear in **every** profile while its API exists in **one**. Consequence to look
for before anything else: HTTP `404 {"detail":"Plugin not found"}` on
`/api/plugins/<id>/…` while the tab renders fine.

Mechanism (read it, don't guess):

- `hermes_cli/web_server_dashboard.py::_mount_plugin_api_routes()` runs **at process start** and mounts
  `/api/plugins/<id>/` only for plugins that are **installed in that home AND listed in
  `plugins.enabled`**. It is called at import time (`hermes_cli/web_server.py`), i.e. there is no
  reload path.
- A runtime gate (`hermes_cli/web_server.py::_plugin_api_runtime_gate`) answers
  `404 {"detail":"Plugin not found"}` for any `source == "user"` name not in `plugins.enabled`
  (or in `plugins.disabled`) — so an installed-but-not-enabled plugin 404s without any log noise on
  the backend side.

Check both homes explicitly, because the shell's inherited `HERMES_HOME` may point at a *different*
profile than the one under discussion:

```bash
ls -d "$HOME/.hermes/plugins/<id>" "$HOME/.hermes/profiles/<name>/plugins/<id>" 2>/dev/null
grep -A6 '^plugins:' "$HOME/.hermes/config.yaml"          # default profile's enabled list
grep -A6 '^plugins:' "$HOME/.hermes/profiles/<name>/config.yaml"
```

## 3. Probe route scope without the GUI (same plugin, two homes)

To prove whether a failing route is a plugin bug or a profile-scope mismatch, run the plugin's own
backend under two homes with the same code and compare. Mint your own token for the probe server —
you do not need to lift the running backend's.

```bash
HERMES_HOME="$HOME/.hermes/profiles/<name>" \
HERMES_DASHBOARD_SESSION_TOKEN=probe-tok HERMES_DESKTOP=1 \
  "$(command -v hermes)" serve --isolated --port 9321 --skip-build      # terminal(background=true)

curl -s -o /tmp/probe.json -w '%{http_code}\n' -H 'X-Hermes-Session-Token: probe-tok' \
  'http://127.0.0.1:9321/api/plugins/<id>/snapshot?limit=5&min_trust=0'
```

- `--isolated` keeps the probe from attaching to (or starting) the machine-level server; `--skip-build`
  skips the web-UI build. Loopback bind + a token you minted is enough auth.
- Same plugin code, home A → 200 with a payload, home B → 404 `Plugin not found` ⇒ **profile scope**,
  not plugin breakage. Both homes 404 ⇒ the plugin/enablement is missing in both; 200 in the home the
  app is *not* on ⇒ install the agent half into the home it *is* on.
- Start probe servers with `terminal(background=true)` and curl in the next call — a foreground
  terminal command is **rejected** for using `&`. Kill by pattern
  (`pkill -f 'serve --isolated --port 9321'`), then prove the port is free
  (`lsof -nP -iTCP:9321 -sTCP:LISTEN`) and leave no orphan backend behind. `hermes serve --status`
  lists running web servers.
- Non-throwing alternative for "is it mounted at all": the SPA/route list is version-dependent and
  `hermes serve` refuses `/api/plugins` (headless), so probe the concrete plugin route, not the index.

## 4. Plugin halves: install, enable, restart

A unified package ships both halves and Hermes keeps them where each scope can see it:

```
<profile home>/plugins/<id>/{plugin.yaml, __init__.py, dashboard/{manifest.json, plugin_api.py, dist/}, desktop/plugin.js}
<app hermes home>/desktop-plugins/<id>/plugin.js + .hermes-package.json   # the desktop half, lifted out
```

- The `.hermes-package.json` marker (`package`, `source`, `repo`, `sha`, `catalogName`) pairs the app-level
  UI row back to the agent package; it is what powers the Plugins page's **Install here** button.
- Fix for §2's 404: install the agent half into **the profile the app is on**, then restart.
  - GUI: Capabilities → Plugins → **Installed** → the plugin's **Agent** half cell → **Install here**.
  - CLI (names the target explicitly; no `-p` means the default profile):
    `hermes -p <profile> plugins install <catalog-name> --enable`
    (`--ref <40-char sha>` to pin; `--force` to reinstall; installs land disabled without `--enable`).
  - **Restart the app** (⌘Q, relaunch). The `serve` backend dies with the app and routes mount at
    process start; enabling alone changes nothing at runtime, and there is no `plugins reload` verb.
    The desktop half *is* hot-reloaded from disk — changing `plugin.js` needs no restart.
- Verify, in this order:
  ```bash
  test -f "$HOME/.hermes/plugins/<id>/dashboard/manifest.json" && echo ok
  hermes -p <profile> plugins list | grep -i <id>        # expect enabled + a catalog/<git> source
  grep -c "/api/plugins/<id>/" ~/.hermes/logs/desktop.log   # count must stop growing after restart
  ```
- The desktop half is app-wide but the backend half is per profile: to browse/use the plugin on several
  profiles, install the agent half in each (`hermes -p <each> plugins install <catalog-name> --enable`).
  "Works on the profile I installed it in, 404 elsewhere" is expected, not a bug.
- Installs are home-scoped. A bare `hermes plugins install` writes to whatever `HERMES_HOME` the shell
  carries, which in an agent/gateway session can be another profile — pass `-p <profile>` (or set
  `HERMES_HOME`) and read the target home back to confirm where it landed.

Deeper install model (marker fields, legacy profile-scoped desktop dirs, install/update/uninstall
pairing, UI states): `references/diagnose-hermes-desktop-app-plugin-install-model.md`.

## 5. Remote / cloud backend

With a non-local connection (`connections.json` mode `remote`) the app cannot read the remote box's
`plugins/` as a filesystem — only packages installed locally contribute a desktop half, and the
Plugins page shows the agent half as unavailable (remote backend) rather than pending. Do not diagnose
a remote backend from local files; say which side the evidence comes from.

## 6. Report shape (this user)

1. **Root cause first, with the line that proves it** — the failing `desktop.log` URL/status, the
   config list that lacks the entry, the `backend-ownership.json` argv. No tour of the architecture
   before the cause.
2. **Then the executable path**: the GUI route with exact on-screen labels *and* the one CLI command,
   including the step people skip (**restart the app**, or the enable is inert).
3. **Then verification** with expected output (file exists, `plugins list` row, 404 count stops
   growing).
4. **Diagnose read-only; hand over mutations.** Log greps, state-file reads and probe servers are
   yours. Installing into a profile and editing `config.yaml` change his setup — give the command and
   ask before running it.
5. Close with the question-format summary (1 What I ask / 2 What you did / 3 Keypoints you offer /
   4 Questions to dig in); each keypoint carries its evidence, and state what was ruled out.

## Support files

- `references/diagnose-hermes-desktop-app-plugin-install-model.md` — the two desktop-plugin doors and their one-time
  migrations, `.hermes-package.json` fields and what each drives, the per-profile mount/404 gate, and
  the install/enable/restart pairing rules.

## Skill Structure

<!-- Generated by Scripts -->

```
diagnose-hermes-desktop-app/
├── SKILL.md  (184 lines)
└── references/
    └── diagnose-hermes-desktop-app-plugin-install-model.md  (87 lines)
```

<!-- Generated by Scripts -->
