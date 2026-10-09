# Skill inventory, provenance, and availability

Everything that answers "what skills does this profile have, and why is one of them not
turning off". Paths are relative to one home (`~/.hermes`, or `~/.hermes/profiles/<name>/`).

## The stores disagree on purpose

| Store | Means | Read it with |
|---|---|---|
| `<home>/skills/**/SKILL.md` | exists on disk (hidden dirs excluded from the tree view) | `_find_all_skills(skip_disabled=True)` |
| `<home>/config.yaml` → `skills.disabled` | hidden from the prompt, still on disk | `get_disabled_skills(load_config())` |
| `<home>/skills/.archive/` | curator retired it out of the tree (flat dirs, name == skill) | `hermes curator list-archived` |
| `<home>/skills/.hub/lock.json` → `installed` | hub-installed names + identifiers | json parse |
| `<home>/skills/.bundled_manifest` | `name:md5` of bundled skills (user-modified tracking) | line parse |
| `<home>/skills/.hub/index-cache/hermes-index.json` | the **catalog**: `{version, generated_at, skill_count, skills[]}` | json parse |
| `<home>/skills/.curator_ledger.jsonl` | every create/patch/write_file/archive with `actor` | json lines |

`hermes-index.json` entries carry `name, description, source, identifier, repo, trust_level`;
`source` values seen in the wild: `clawhub`, `skills.sh`, `github`, `lobehub`, `browse-sh`,
`official`. The index is large (six figures of entries) and **names collide across publishers**,
so name == skill only for the installed tree, never for a catalog row.

Because each profile has its own `skills/` tree, a count from one home says nothing about
another. Enumerate per home before quoting any total.

## Provenance decides what a surface offers

`tools/skill_usage.py` classifies each installed skill: `hub` (in the hub lock) > `bundled`
(in `.bundled_manifest`) > `agent` (agent-authored *and* locally hand-made). The desktop
detail pane treats only `agent` as editable/deletable; bundled skills are governed by
`hermes skills opt-out` (stop seeding) rather than deletion.

Availability rules that make a switch look broken:

- Local installed row → on/off switch (writes `skills.disabled`), reachable only when
  `skill-catalog.tsx` finds the row in `catalog.skillsById` (local rows have ids `installed:<name>`).
- Catalog row (not installed) → install one-way. There is no "off".
- Name-collision row and lock-orphan row → the default `CatalogInstallSwitch` in its installed
  state: `checked={installed}` with `disabled` including `installed` = **grey, on, inert**. Their
  `isInstalled` hit comes from `skillsByName.has(name)` (collision) or
  `installedIdentifiers.has(identifier)` (orphan), never from a local row.
- `ESSENTIAL_SKILLS = frozenset({"hermes-agent"})` (`agent/skill_utils.py`) —
  `get_disabled_skills` subtracts it and `save_disabled_skills` drops it silently, so it cannot
  be disabled from any surface.

## Reproduce a toggle without the UI

The dashboard's `/api/skills/toggle` needs the backend's per-process session token, so curl is
not an option. Run the same functions it calls, with the **install's** python and the target
home. `cd` into the hermes source tree (so `import tools.…` resolves) and use the venv python
that sits beside the `hermes` entry point
(`<install>/environments/<id>/venv/bin/python`):

```python
from hermes_cli.config import load_config
from hermes_cli.skills_config import get_disabled_skills, save_disabled_skills
from tools.skills_tool import _find_all_skills
from tools.skill_usage import _read_bundled_names, _read_hub_installed_names, provenance
from agent.skill_utils import get_disabled_skill_names

cfg = load_config()
d = get_disabled_skills(cfg)
d.add("<skill>")
save_disabled_skills(cfg, d)
print(get_disabled_skill_names())                       # read it back
print(len(_find_all_skills(skip_disabled=True)))        # rows the pane would list
```

Count and provenance per home by exporting `HERMES_HOME` for the one-liner. Verify the on-disk
result by parsing `config.yaml` — never assume the write landed.

## Attributing a session, a log line, or a count to a profile

- `~/.hermes/logs/agent.log` is the **launch** profile's log file; under a multiplex gateway it
  also contains every additional served profile's sessions. Membership in that file proves
  nothing about which profile a session belongs to.
- Resolve it by id from the profile's own store:
  `sqlite3 -header "file:<home>/state.db?mode=ro" "select id,source,started_at from sessions where id='<id>';"`
  (the column is `id`; `session_id` does not exist).
- A session id absent from the other profiles' stores is the answer, not an error.
- Other profiles' `.env` / config are separate islands — never infer one profile's state from the
  launched one.
- A hub install is recorded in the lock of the home that ran it *and* materialised in that home's
  `skills/` tree, so a double install of one skill leaves **two lock entries and one directory**.
  Locate the directory first (`find ~/.hermes -maxdepth 6 -iname '*<name>*'`), then read each home's
  lock; the home missing the directory has an orphan entry (grey, on, inert switch) even though the
  skill is real in the other home. Name the home in every answer about "my skill X" — the install
  log records the source and verdict, never the destination home.

## Hub updates: what detection and apply actually do

- Adapters are matched by the lock's recorded `source` (`_source_matches`), never by name alone —
  letting a same-named skill in another registry satisfy the fetch would silently reassign
  provenance. No matching adapter → `unavailable`.
- Fast path: when `entry.metadata.source_revision` equals the adapter's current revision the bundle
  bytes cannot differ, so it reports `up_to_date` without downloading. Otherwise the bundle is
  fetched and `bundle_content_hash` compared against the lock's `content_hash` (normalized before
  hashing, otherwise every installed skill reports `update_available` forever).
- Statuses: `up_to_date`, `update_available`, `unavailable`, `orphaned` (recorded `install_path` is
  not a directory), `invalid_install` (path unresolvable). `orphaned` short-circuits before any
  network cost, so `hermes skills check` is cheap right after a bulk directory delete.
- Applying is `hermes skills update [name] [--force]`; locally-edited skills are skipped without
  `--force`. Nothing schedules it — `plugins.auto_update_check_hours` is the only cadence in the
  config schema and it is plugins-only, so an installed skill never updates by itself.
- Per-home verification: `hermes --profile <name> skills check <skill>` (global `-p/--profile` flag)
  prints `Name | Source | Status` plus `N update(s) available across M checked skill(s)`; at the API
  level, `HERMES_HOME=<profile dir>` + `check_for_skill_updates(name=…)` returns the same row with
  `current_hash` / `latest_hash` (drop the `bundle` key before printing).

## The desktop catalog snapshot (what the Skills page merges in)

- The page fetches `<kind>.json` from `https://nousresearch.github.io/hermes-agent/docs/api`
  (`CATALOG_BASE` in `apps/desktop/src/app/capabilities/catalog/catalog-data.ts`) — **not** the
  local `.hub/index-cache/hermes-index.json`. Both run to ~10^5 rows; the public file is ~60 MB.
- Snapshot row shape: `name, description, category, source, installIdentifier, docsPath, tags,
  author, version, commands, envVars`. `source` values seen: `built-in` (58), `optional` (152),
  `ClawHub`, `skills.sh`, `GitHub`, `LobeHub`, `browse.sh`, `NVIDIA`, `gstack`, `OpenAI`,
  `HuggingFace`, `Anthropic`. The local index instead uses `identifier` + lowercase sources.
- Reproduce a count **exactly** — port the real code path line by line and feed it the four real
  payloads. A range, or a total that ends in an unexplained remainder, is a non-answer:
  1. installed rows: `_find_all_skills(skip_disabled=True)` + `provenance()` per name.
  2. `list_skills_hub_sources(None)` (`hermes_cli/web_routers/skills.py`): the payload's
     `installed` map is keyed by **official identifiers** (`official/research/polymarket`), not by
     skill name — each record carries `name`. Treating it as `{name: …}` skips the identifier
     fold, so every official skill is counted a second time.
  3. the official payload: `OptionalSkillSource().list_local()` schema-mapped via
     `_skill_meta_to_payload`, with `installed` computed by `_installed_hub_identifiers(profile)`.
     Rows flagged `installed` put their identifier into `installedIdentifiers`.
  4. the public snapshot (URL above), rows normalized by `skillCatalogInstallIdentifier()`
     (`apps/shared/src/catalog-install.ts`): ClawHub identifiers get a `clawhub/` prefix,
     built-in rows keep their snapshot `installIdentifier`, and a missing identifier falls back to
     `official/<name>` for `optional` and to the bare name otherwise.
  Then the merge (`catalog-browser.tsx`): a feed row whose `matchInstalled` hits an installed entry
  is folded into that entry, and **only the first such row survives** (the rest are dropped by the
  `seen` set); `matchInstalled` folds built-in rows by name only when the local row's provenance is
  `bundled`. So
  `total = installed + (rows that match nothing but whose name is in the installed set) + (rows
  whose installIdentifier is in the lock/official installed-identifier set)`. Cross-check against
  the screen: the duplicate names and their per-publisher counts must match what the user reports.
- Never attribute a residual to snapshot refresh without measuring it: re-download and compare
  `sha256`/`last-modified` (`curl -sSI`). Identical hashes across the user's view and your fetch
  mean the bytes did not move — the fault is in your model of a payload. The local
  `.hub/index-cache/hermes-index.json` and the public snapshot are *separate builds* (different
  `generated_at`, different row counts, different `source` casing), so a collision count taken from
  the local index is not the number the page shows — always take the count from the snapshot the
  page actually fetches.
- Duplicate rows are therefore expected, not a bug: one `hermes-agent` per publisher plus the
  built-in row (`installed` rows carry `source: built-in | hub | local`, catalog rows carry the
  publisher source).
- Worked example to check a port against: one profile with 49 installed skills produced
  `146 = 49 + 97`. The 97 rows beyond the installed ones split `skills.sh 50 · ClawHub 27 ·
  optional 10 · GitHub 6 · Anthropic 3 · OpenAI 1`; the 9 `built-in` and 7 `official` same-name
  rows folded into the installed rows instead of counting (`pdf` alone contributed 22 duplicate
  rows, `docx` and `xlsx` 16 each). The 10 `optional` rows are the term a two-part model drops: 6
  are lock orphans (directory deleted by hand, lock entry alive) and 4 are same-name official rows
  — none of them reachable by name collision. A port that misses a fold lands ~10 rows off, and the
  residual names the payload you modelled wrong — usually the identifier shape, not the data.
- Deleting a hub-installed skill's directory by hand (a bulk `rmtree` of disabled skills does
  exactly this) leaves the lock entry behind, and the lock is what makes `/api/skills/hub/official`
  report `installed: true`. Diagnose with `hermes skills check` (`status=orphaned`), clear with
  `hermes skills uninstall <name>`, then re-open the page after the catalog's 30-minute
  `staleTime`.

## When one ClawHub skill renders twice, labelled `hub`

Two normalizations disagree and the fold compares strings:

| Side | Identifier for one ClawHub skill |
|---|---|
| catalog row (compared against) | `clawhub/@owner/slug` — `skillCatalogInstallIdentifier()` prefixes ClawHub rows |
| lock entry (the key in the payload) | `@owner/slug` — the adapter strips the prefix (`tools/skills_hub_clawhub.py`, `removeprefix("clawhub/")`) before the entry is written |

So `matchInstalled` misses, `mergeInstalled` keeps both rows (the local one plus the catalog one), and the
local row's label is provenance-hardcoded — `skill-catalog.tsx` maps `bundled → built-in`, `hub → hub`, else
`local`, never the registry — which is why a ClawHub install reads `hub`. A folded row instead takes the
*feed* row's fields (`{...entry, id: installed.id}`), so aligning the identifiers also restores the `clawhub`
label and the real toggle.

Data-level repair, when the source tree is off-limits. The obvious first guess — set the entry's
`identifier` to the catalog form — is **not sufficient**; stopping there is why the duplicate row
survives a page refresh. Three strings must agree:

| # | String | Where it lives | Why it must match |
|---|---|---|---|
| 1 | `identifier` | lock entry | `/api/skills/hub/sources` keys `installed` by exactly this field (`_installed_hub_identifiers`), and the fold compares it against the catalog row's `skillCatalogInstallIdentifier()` output |
| 2 | the entry's **KEY** (it becomes the payload's `record.name`) | lock map | the fold resolves the local row with `installedByName.get(record.name)` *before* comparing identifiers; `installedByName` is keyed by the skill's own name, so a key that is the registry slug (rather than the `SKILL.md` `name:`) leaves `installedByIdentifier` empty and string 1 is never consulted |
| 3 | last segment of `install_path` | lock entry | `_normalize_lock_install_path` / `_resolve_lock_install_path` require it to equal the key; a mismatch makes `hermes skills check` report `invalid_install` and hub updates stop **silently** — no error reaches the user |

Strings 2 and 3 are the same string, so the repair is a directory rename plus two lock edits:

```bash
cp <home>/skills/.hub/lock.json ~/.hermes/backups/lock.<home>.json.bak-$(date +%Y%m%d-%H%M%S)
mv <home>/skills/<slug-dir> <home>/skills/<skill-name>      # dir name == the SKILL.md `name:`
# lock: rename the installed key "<slug-dir>" -> "<skill-name>"
#       set its install_path to "<skill-name>"    (== key, or check reports invalid_install)
#       set its identifier to the catalog form     ("clawhub/@owner/slug" per skillCatalogInstallIdentifier())
HERMES_HOME=<home> hermes skills check <skill-name>   # expect up_to_date / update_available, NEVER invalid_install
```

- Audit the invariants instead of re-deriving them by hand each time:
  `scripts/check-lock-alignment.py` prints per entry the key, the payload's `record.name`, its
  provenance, `install_path`, whether `_resolve_lock_install_path` accepts the pair, whether the
  directory exists, and the exact fix lines when they disagree. Read-only.
- The adapter accepts `@owner/slug`, `clawhub/@owner/slug`, and the bare `slug`, all yielding the same
  `bundle_content_hash`, so correcting string 1 keeps `hermes skills check` working.
- Reinstalling is **not** the fix: the installer names by the registry slug and rewrites both the entry
  and the directory, so a hand edit is undone — and `hermes skills update` does the same. Re-apply after
  either, and re-run the audit to prove the strings still agree.
- Two publishers can each hold the name (a `skills.sh` `owner/name` row next to a ClawHub slug row), so
  after folding, a search legitimately returns two rows: the one whose identifier is in the lock is the
  installed copy, the other cannot be folded away without a source change. Say that, rather than
  promising a single row — and never describe the remaining row as a duplicate of the installed skill.
- Same shape for any registry whose adapter normalizes its identifiers: compare the lock value against
  `skillCatalogInstallIdentifier()`'s output for that source before concluding the row is uninstallable.

### An orphan entry blocks the install that would clear it

A lock entry whose directory is gone still reads as installed, so every install surface stops early — the
user's "there is an install record so my install fails". Clear, then install:

```bash
HERMES_HOME=<home> hermes skills uninstall <name> -y      # clears the stale entry
HERMES_HOME=<home> hermes skills install 'clawhub/@owner/slug' -y
```

### Never trust the shell's inherited HERMES_HOME

Check `env | grep HERMES_HOME` before mutating anything: a gateway/agent session can carry a *different*
profile's home, so a bare `hermes skills uninstall/install` writes that other home's lock and `audit.log`
while the conversation is about another one — and `Installed: …` in the output is no evidence about the home
you meant. Pass `HERMES_HOME=<home>` (or `--profile`) explicitly, then confirm from the target home's
`skills/.hub/audit.log` tail (`UNINSTALL`/`INSTALL` lines with timestamps) plus the lock entry's
`installed_at`, and re-check hand-edited fields afterwards.

## Why a catalog install fails, and why a bundled skill went missing

- Every hub install scans and writes the full verdict to
  `~/.hermes/logs/action-skills-install-<source>-<path>-<hash>.log`: `Fetching: …` →
  `Quarantined to .hub/quarantine/<name>` → `Scan: …` (findings with `file:line`) →
  `Verdict:` → `Decision:`. Read that file before proposing any fix.
- Block rule: **community source + `DANGEROUS` verdict = hard block**, and `--force` does not
  override a dangerous verdict. `env_exfil_curl` / `echo_pipe_exec` fire on a skill whose own
  documentation does `curl -H "Authorization: Bearer …"` and pipes JSON into `python -c`.
- Bundled inventory check: shipped count
  (`find <hermes install>/skills -name SKILL.md | wc -l`) vs `.bundled_manifest` lines vs how
  many of those names exist in the home. `curator.prune_builtins: true` lets the curator retire
  them into `.archive/`, so a profile can silently lose most of its bundled set — and emptying
  `.archive/` makes the loss permanent for those names.
- Recovery, in order of blast radius: `cp -R <hermes install>/skills/<category>/<name> <home>/skills/<category>/`
  (one skill) → `hermes skills reset <name> --restore` (stock copy over the current one) →
  `hermes skills opt-in --sync` (whole bundled set, no network, no scan; also re-enables seeding
  for future updates). Before recommending `--sync`, intersect the user's delete list with the
  package tree — bundled names they deleted on purpose come back enabled.

## Finding a skill for a capability (the uninstalled stores)

"What does this profile have" and "does a skill for this capability exist at all" are different
questions — the store table above answers only the first. Add the stores that hold skills the home
does not:

| Store | Enumerate with |
|---|---|
| bundled, ships with Hermes | `<hermes install>/skills/<category>/<name>/SKILL.md` |
| official optional (152 rows on the live repo) | `<hermes install>/optional-skills/<category>/<name>/` |
| community registry (clawhub, skills.sh, github) | `hermes skills search <term>` |

- `hermes skills browse --source official` prints a paginated table; its `--json` flag writes
  **nothing** to stdout. Enumerate the `optional-skills/` tree instead — one
  `search_files (target='files')`, no network, and it is the same list the browse page paginates.
- Adapters reason in identifiers; the tables print names. `hermes skills inspect <name>` answers
  `No exact match … Did you mean` and shows no body for a registry skill — pass `clawhub/<name>` or
  `skills-sh/<owner>/<repo>/<name>`. `install` takes the same prefixed form.
- Bundled ≠ optional: `official/<category>/<name>` for a bundled skill answers `Could not find`.
  Restore those from the package tree (see SKILL.md §8/§9), never via `install`.
- **Bundled-but-gone signature**: name present in `<hermes install>/skills/<category>/`, name listed
  in `<home>/skills/.bundled_manifest`, `.usage.json` entry with `state: archived`, and **no
  directory in the home's tree while `.archive/` is empty**. That combination is
  pruned-but-recoverable — `cp -R` it back, and the surviving manifest hash keeps it rendering as
  unmodified built-in. `hermes curator restore` cannot help: it moves a file out of `.archive/`,
  and there is no file. `.usage.json` records state for skills that no longer exist, so it is never
  evidence of existence.
- Answer with the store, the identifier, and the trust level per hit; mark community rows as
  unvetted and preview them with `inspect` before recommending. Never present a community hit and a
  bundled skill as the same class of option.
- When the capability word is ambiguous ("optimize tests" = fewer flakes? more coverage? faster?
  drop bad asserts?), hand back the hits per meaning and ask which is meant — each meaning routes to
  a different skill, and picking one for the user answers a question they did not ask.

## Probing hub and catalog state without hanging

- `env | grep HERMES_HOME` first; then pin the home explicitly on every read and every mutation.
- HTTP probes: `curl -sS --max-time 20 -o <file> -w "http=%{http_code} bytes=%{size_download}\n" <url>`.
  The catalog snapshot is ~60 MB and lands in seconds; the docs domain redirects to the Pages host
  and both serve the same bytes, so compare `sha256` rather than believing a second URL is a second
  source.
- Adapter searches (ClawHub, skills.sh) can block indefinitely. Wrap them (`subprocess.run(...,
  timeout=…)`, `signal.alarm`) or background them and read the log tail; a foreground call that can
  hang is what makes a short task look like a stuck agent.
- `timeout` does not exist on stock macOS — use `curl --max-time`, python timeouts, or `gtimeout`.
- Answer "which artifact is missing this row" from the fetches, then stop: if the row is in neither
  the published snapshot nor the local index nor the official payload, the next step is the screen
  (`screencapture -x ~/.hermes/cache/scratch/screen.png` + vision), not a bigger model.
