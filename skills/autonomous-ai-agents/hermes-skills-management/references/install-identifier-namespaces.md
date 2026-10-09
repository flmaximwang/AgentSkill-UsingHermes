# One skill, four identifiers

A skill has no single identifier. Four layers name it, and they do not agree.
Comparing strings across layers is the whole of this failure class, so always
say which layer a string came from.

| Layer | Form | Verified example |
|---|---|---|
| Public catalog feed (`https://nousresearch.github.io/hermes-agent/docs/api/skills.json`, Skills → Catalog) | bare slug, source in a sibling field | `identifier: sipoon-codegraph-index`, `source: ClawHub` |
| Hub search (`GET /api/skills/hub/search`, `hermes skills search`) | bare slug | `sipoon-codegraph-index` |
| What the desktop sends to install | source-prefixed | `clawhub/sipoon-codegraph-index` |
| `.hub/lock.json` after install | the adapter's canonical form | `@sipoon/sipoon-codegraph-index` |

Mechanism (all four are current source, not inference):

- `apps/shared/src/catalog-install.ts::skillCatalogInstallIdentifier` prefixes
  `clawhub/` onto any catalog row whose `source` is ClawHub and whose
  `identifier` lacks it — that string is what the install button posts.
- The route (`hermes_cli/web_routers/skills.py::install_skill_hub`) spawns
  `hermes [-p <profile>] skills install <that identifier> --yes`.
- `tools/skills_hub_clawhub.py::ClawHubSource.fetch` mints a `SkillBundle` with
  `identifier="@<owner>/<slug>"` when the payload carries an owner (bare slug
  otherwise); `do_install` writes `bundle.identifier` into the lock.
- `hermes_cli/web_server_profiles.py::_installed_hub_identifiers` keys the UI's
  installed map by that lock identifier, while the UI looks up its own row key
  (`skill-catalog.tsx` `installedIdentifiers` / `matchInstalled`). A miss also
  falls back to matching by NAME — which fails too, because the row's name is
  the display name (`CodeGraph Index`) and the installed skill's name is the
  install directory (`sipoon-codegraph-index`).

Net effect: the install works, the row never lights up, and the Install control
stays. The row's state is derived from the lock map only; the optimistic flip
the store writes (`$hubInstalledOverride`) is read by no production component,
so the UI cannot self-correct after a successful install.

## Recipes

### 1. What identifier did the caller use? (from an action-log filename)

`hermes_cli/web_server_profiles.py::_hub_action_name` builds the action name —
and the log filename — as `skills-<verb>-<slug>-<sha1(identifier)[:8]>`, with
`slug = re.sub(r"[^a-z0-9]+", "-", identifier.lower()).strip("-")[:48]`.
Enumerate the forms an identifier could take and match against the filename:

```bash
python3 -c 'import hashlib,re,sys; k=sys.argv[1]; print("skills-install-%s-%s" % (re.sub(r"[^a-z0-9]+","-",k.lower()).strip("-")[:48], hashlib.sha1(k.encode()).hexdigest()[:8]))' 'clawhub/sipoon-codegraph-index'
# -> skills-install-clawhub-sipoon-codegraph-index-73c711f8
```

### 2. What did the CLI resolve it to?

`hermes skills inspect <identifier>` prints the resolved `Identifier:` — the
canonical bundle identifier, i.e. what the lock will store. Run it on the
caller's string; a different string back is the mismatch.

### 3. What does the lock actually hold?

The CLI list does not print `identifier`, so read the lock with the tree's own
interpreter (`tools` must be importable, hence `cwd`; strip `PYTHONPATH` or the
session's tree shadows the target one):

```bash
cd ~/.hermes/hermes-agent
env -u PYTHONPATH HERMES_HOME="$HERMES_HOME" venv/bin/python3 - <<'PY'
from tools.skills_hub import HubLockFile
for e in HubLockFile().list_installed():
    print(f"{e['source']:9} {e['name']:32} {e['identifier']:42} {e['install_path']}")
PY
```

`HubLockFile(<path>)` takes an explicit path, so another profile's lock reads
without switching `HERMES_HOME`:
`HubLockFile(Path.home()/'.hermes'/'profiles'/<p>/'skills'/'.hub'/'lock.json')`.

### 4. Decide, then act

- Lock has it → it IS installed. Prove with `hermes skills list` (status
  `enabled`) and `hermes skills check` (`up_to_date`), point the user at the
  Skills tab rather than the catalog row, and name the stale marker as a UI
  defect instead of reinstalling.
- A reinstall is genuinely wanted → `hermes skills install <identifier> --force`.
  The desktop cannot do it: its route passes only `--yes`, by design, because
  `--force` is also the security-scan override and is deliberately unwired from
  a UI checkbox.

## Shape of the upstream fix

Alias the adapter's canonical identifier back to the caller-visible one where
the UI's installed map is built — i.e. in
`web_server_profiles.py::_installed_hub_identifiers`, additionally register
`clawhub/<name>` (and the bare `name`) for entries whose `source` is `clawhub`.
One server-side change fixes every ClawHub skill; nothing on the client needs to
move. Editing the mtime/source tree is a `hermes-source-hotfix` job, and the
shared Hermes install is running — get the user's go-ahead first.
