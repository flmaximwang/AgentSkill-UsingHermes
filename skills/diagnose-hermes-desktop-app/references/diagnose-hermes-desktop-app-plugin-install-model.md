# Desktop plugins: where each half lives and why a route 404s

Deep notes behind §2–§4 of SKILL.md. Verified against the running app and the source tree; the
code paths are named so they can be re-read when the app moves.

## The two doors, and the one-time migrations that emptied the old ones

`apps/desktop/electron/desktop-plugins-root.ts` is the owner. Two profile-shaped sources are lifted
into ONE app-level root (`<app hermes home>/desktop-plugins`):

1. `profiles/<name>/desktop-plugins/<id>` — an earlier build scoped the standalone root per profile.
   Nothing reads that path now; a folder left there just sits.
2. `plugins/<id>/desktop/plugin.js` — the desktop half of a unified agent+desktop package, in the
   default home AND in every profile. The **agent half stays where it is** (it runs in that profile's
gateway/backend); only the desktop half is copied out.

The reason it is app-level: a desktop plugin extends the APP (panes, palette, themes), and a
profile-scoped root read to users as "my plugin vanished" on every profile switch. The renderer never
scans `plugins/` itself.

## `.hermes-package.json` — the marker, field by field

Written when the half is materialised; the file sits beside the copied `plugin.js`.

| Field | Meaning / drives |
|---|---|
| `package` | the agent package folder name (`plugins/<name>` key) the half came from |
| `source` | absolute path of that `desktop/` dir; a newer `sourceMtimeMs` re-copies it |
| `sourceMtimeMs` | mtime of the source `plugin.js` at copy time |
| `repo` / `sha` | package provenance from the catalog sidecar (`.hermes-catalog.json`) else the git remote |
| `catalogName` | catalog entry name used to install the agent half elsewhere |

`repo`+`sha` are what the Plugins page's **Install here** consumes: the row shows that button in the
Agent half cell only when the agent package is missing in the profile being viewed
(`pkg.agentMissingInProfile && desktop`) *and* `packageOrigin.repo` exists; the button is disabled
without a resolvable origin. `desktop/plugin.js` inside a package is authoritative — the same folder
name under `desktop-plugins/<git-name>/` is NOT created separately for a unified package.

## Per-profile mounting (the 404 gate)

- `hermes_cli/web_server.py` calls `_mount_plugin_api_routes()` at **import time** → routes exist only
  for the plugins enabled in the home that process was launched for.
- `hermes_cli/web_server_dashboard.py::_mount_plugin_api_routes()` skips a plugin unless it is
  discovered by `_get_dashboard_plugins()` for that home, is in `plugins.enabled`, and is not in
  `plugins.disabled`; it also refuses `source == "project"` (CWD-controlled) and any `api` file that
  resolves outside the plugin's `dashboard/` dir.
- `hermes_cli/web_server.py::_plugin_api_runtime_gate()` re-checks every `/api/plugins/<name>/…`
  request: `blocked = name in disabled_set or (source == "user" and name not in enabled_set)` →
  `404 {"detail": "Plugin not found"}`. It deliberately runs only for requests that already look
  authenticated, so an unauthenticated caller still gets 401 (no plugin-name oracle).
- Practical read: **that exact 404 body means "not enabled in THIS home"**, not "file missing" and not
  "import error". A plugin whose Python failed to import logs a warning from the mount loop and the
  route is simply absent (FastAPI's own 404, different body).

## Install / enable / restart pairing

| Step | Command | Notes |
|---|---|---|
| pick the profile | `hermes -p <profile> …` or `HERMES_HOME=<home>` | a bare command writes to whatever home the shell carries |
| install | `hermes plugins install <catalog-name> \| owner/repo \| URL --enable` | `--ref <40-char sha>` pins, `--force` reinstalls, `--no-deps` leaves it disabled; portable Agent Plugins v1 packages install disabled by default |
| enable later | `hermes plugins enable <name>` | same effect as `--enable` |
| make routes live | restart the app (⌘Q + relaunch) | `serve` dies with the app; no reload verb exists |
| desktop half only | edit `desktop-plugins/<id>/plugin.js` | hot-reloaded by the app, no restart |

Installing through the desktop app's own dialog writes the agent half into the dialog's target profile
(the Plugins page passes the profile being viewed) and then reconciles the desktop half via
`reconcileDesktopPlugins()` — so an in-app install into profile A leaves profile B unchanged, which is
how "it worked yesterday, 404 today" reads after a profile switch.

## Verification ladder

1. `test -f <home>/plugins/<id>/dashboard/manifest.json && echo ok` — agent half present in that home.
2. `hermes -p <profile> plugins list | grep -i <id>` — expect a version and a catalog/git source;
   absent row = not installed in that home (the list only reads that home's plugins dir).
3. Probe the concrete route with an isolated serve (§3 of SKILL.md) — 200 vs 404 settles scope.
4. After the app restart: `grep -c '/api/plugins/<id>/' ~/.hermes/logs/desktop.log` stops growing, and
   the pane renders data.

## Reading the plugin's own backend when the tab still looks wrong

A mounted plugin with an empty pane is a data question, not a routing one. The plugin's
`dashboard/plugin_api.py` resolves its home with `get_hermes_home()` (falling back to
`HERMES_HOME`), so the payload always describes **the backend's profile** — e.g. built-in memory is
read from `<home>/memories/MEMORY.md` and `<home>/memories/USER.md`, and provider sections report
`provider_configured: false` unless the matching `memory.provider` is set in that home's
`config.yaml`. Compare the payload's own `hermes_home` field against the profile you meant to inspect
before calling the data wrong.
