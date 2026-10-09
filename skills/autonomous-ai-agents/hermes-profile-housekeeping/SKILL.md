---
name: hermes-profile-housekeeping
description: Use when removing, disabling, or auditing skills/config.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [hermes, skills, config, cleanup, destructive-ops]
    related_skills: [hermes-agent, session-librarian]
---

# Hermes profile housekeeping

Bulk skill / config surgery inside one profile: enable/disable/delete many skills at once (or one),
reconcile `skills.disabled` against what is on disk (§1/§6 — a disabled name with no directory may be
a deliberate suppression, not a dead entry), edit `config.yaml` safely. Every rule below exists
because the naive version silently does the wrong thing or destroys something unrecoverable.

## When to Use

- The user says to delete or remove **one** skill, disable, purge, or clean up many in a profile.
- `skills.disabled` in `config.yaml` and the on-disk skill dirs disagree in either direction, or a
  disabled name looks stale (§6 — check whether it is a suppression entry before pruning it).
- A settings change must be written to `~/.hermes/config.yaml` (the file tools refuse it).
- The user asks to clean up `~/.hermes/skills/.archive/`, or wants the curator to stop
  retiring bundled skills.
- The user asks why a skill "can't be turned off", or why a skills pane lists far more
  skills than exist on disk (§9).
- The user asks whether an installed hub / ClawHub skill updates itself, or which profile an
  install actually landed in (§10).
- The user asks **whether a skill for some capability exists** ("is there a skill that does X?")
  — the installed list is not the universe (§14).
- Any bulk destructive file operation inside `~/.hermes/` needs a plan, a backup, and proof.

Inspection inside a session: use the native tools — `skills_list`, `skill_view`, and
`search_files (target='files')` — before reaching for shell `find`/`ls`. The probe snippets
in §2 and `references/skills-tree-layout.md` deliberately use shell `find` + `os.walk`
because they must run bulk operations inside one `execute_code` call, and two traversals are
needed to cross-check each other (§5).

## 1. Know the two sources of truth

- `~/.hermes/config.yaml` → `skills.disabled` is the list of names the agent hides. It is
  authoritative for *intent*, not for *existence*.
- `~/.hermes/skills/` is what is on disk.

They drift in both directions: config entries with no directory (dead entries), and
skill directories with no config entry (live). Enumerate both and reconcile before any
delete — never delete on the strength of the config list alone, and never conclude
"nothing left" from one traversal (see §5).

Read targeted values with `hermes config get skills.disabled`; a whole-file parse is the
only reliable "what is actually configured" answer.

## 2. Map names → paths, filtering hard

A skill dir is any dir containing `SKILL.md`. Two traps when matching by directory name:

- **Nested skills**: a skill can package sub-skills at `<category>/<skill>/skills/<sub>/SKILL.md`
  (e.g. a research umbrella skill with dozens of `*-skill` children). `-name <skill>` finds
  siblings, not the parent you meant.
- **Name collisions inside embedded venvs**: skill dirs may ship a `.env/` virtualenv, so
  `find -name <name>` also matches `site-packages/**` directories. Filter every match to
  dirs that actually contain `SKILL.md`.

After mapping, drop dirs nested under another to-be-deleted dir (removing the parent covers
them) and report both counts: matched dirs vs top-level removals.

## 3. Gate the delete on a safety check

Before removing anything: for every to-delete dir, assert that no *enabled* skill (a
`SKILL.md`-bearing dir whose name is **not** in `skills.disabled`) lives underneath it.
Block on any hit and show it. A bulk delete of a category directory that quietly holds one
live skill is the failure mode this prevents.

Present the plan and get explicit user confirmation **before** deleting. Bulk deletes are a
consent-gated operation: a delete script may come back `BLOCKED … the code did NOT run`.
When that happens, do not rephrase it, do not route the same outcome through another tool,
and do not assume partial execution — ask in chat and re-run once the user answers.

## 4. Back up, then delete, then verify

1. Back up the exact targets (not the whole tree):
   `tar -czf ~/.hermes/backups/disabled-skills-$(date +%Y%m%d-%H%M%S).tar.gz -T <list-file>`
   then prove it with `tar -tzf <tarball> | wc -l` against the expected entry count.
2. Delete.
3. Sweep category dirs left holding only `DESCRIPTION.md`, and delete those scaffolds too —
   they render as empty categories. **Never** touch the dotted infra dirs: `.curator_backups`,
   `.hub`, `.locks`, `.codegraph`; `.archive` is off-limits too unless the user explicitly asked
   for archive cleanup (then §8).
4. Re-count `SKILL.md` across the tree; `before − after` must equal the number of skill dirs
   removed. Exclude `.archive` / `.curator_backups` from that count or the arithmetic will not close.

Keep every tarball and the pre-edit config copy; list their paths in the final report so
rollback is one command.

**Removing one hub-installed skill** is `uninstall`, never a hand `rm`:
`hermes skills uninstall <name> --yes` drops the directory *and* the lock entry, while a hand delete
leaves the entry behind as the orphan of §9. Back up `config.yaml` + `skills/.hub/lock.json`, then
verify the removal — not the command's own `Uninstalled '…'` line:

```bash
TS=$(date +%Y%m%d-%H%M%S); mkdir -p <home>/backups/<name>-removal-$TS
cp <home>/config.yaml <home>/skills/.hub/lock.json <home>/backups/<name>-removal-$TS/
HERMES_HOME=<home> hermes skills uninstall <name> --yes
ls <home>/skills/<category>/                      # install dir gone
find <home>/skills -iname '*<name>*'              # no leftovers (.locks/, .hub/ included)
HERMES_HOME=<home> hermes skills list | tail -2   # "… N enabled, M disabled"
```

The definitive check is the payload the page reads — no identifier may stay keyed to that `name`:

```bash
cd <hermes source tree> && HERMES_HOME=<home> "$(dirname "$(which hermes)")/python" -c "
from tools.skills_tool import _find_all_skills
from hermes_cli.web_server_profiles import _installed_hub_identifiers
n={s['name'] for s in _find_all_skills(skip_disabled=True)}
print({k:v['name'] for k,v in _installed_hub_identifiers(None).items() if v['name'] not in n})"  # expect {}
```

- **Correct the premise before acting on it.** A card's ✓ and a switch that looks wrong mean
  *installed*; enabled/disabled is a separate axis (`skills.disabled`). When the user says "you have
  X enabled" about a skill the artifacts call disabled, say which of the three states it is
  (installed / enabled / linked to a real local row) instead of confirming a state the data
  contradicts — and lead the report with that correction.
- **Scope the delete to the home the user is looking at.** Each profile keeps its own copy; list the
  others (`ls ~/.hermes/profiles/*/skills/*/<name>`) and delete there only on request (§10).
- A same-named row owned by another publisher is index data, not a file — it cannot be deleted and
  just renders unchecked afterwards (§9). Reinstall path is the lock entry's `identifier`:
  `hermes skills install <identifier> --force --yes` (`--force` when the scan verdict is not clean).

## 5. Verify with two independent methods

A single traversal tool can disagree with the filesystem: `find` / `os.walk` have been
observed skipping a directory that `ls`, `os.listdir`, and `stat` all see. So verify each
removed name by direct path probe (`os.path.exists` / `stat` on the exact path) **and** by a
tree-wide scan, and reconcile the totals. "Zero left" from one method is not evidence.

## 6. Editing config.yaml goes through the CLI

`patch` / `write_file` refuse `~/.hermes/config.yaml` ("security-sensitive configuration").
Use the supported path instead:

```bash
hermes config get skills.disabled       # read a resolved value
hermes config set skills.disabled '[]'  # write a value (YAML literal)
```

- The CLI may warn `'…' is not a recognized config key — it was saved anyway`. That comes from
  an incomplete known-key table, not from a rejected write — confirm by parsing the YAML back.
- Copy the file first, then prove the edit with a **whole-config** key-by-key diff of
  `yaml.safe_load` output (flatten nested dicts, compare every leaf). Proving only the target
  key changed is the point — a serializer can reformat or drop unrelated keys.
- **A `skills.disabled` name with no directory is not automatically a dead entry.** The list does
  double duty: hiding a skill that *is* installed, and suppressing a name the user never wants
  seeded (bundled / official skills this profile never installed — an `airtable`, `polymarket`,
  `macos-computer-use` style entry, §9). Pruning those silently re-enables a preference the user set
  on purpose, so remove an entry only when the user asks, or when this session's own work is what
  disabled the name; otherwise leave the line and say in the report that it is now inert.

## 7. Report shape

Real numbers in a table (counts before → after, dirs removed, backup sizes + paths verified),
the rollback commands, and — critically — any pointer that the deletion invalidated. Memory
entries, vault notes, and other skills that reference a now-deleted skill name must be flagged
explicitly, with the choice offered: restore from the tarball, or rewrite the pointer. Do not
silently edit memory to match a delete you just performed.

Ordering: finish and verify the requested action **first**, then raise side findings as a
compact list, one line each, each with its one-line fix command if it has one. A side
investigation opened while the main task is unfinished reads as stalling — report it, do not
dig it, and do not apply a fix to someone else's concurrent change unasked.

Explain the change in the user's terms before the mechanism. When the action is surgery on a
state file (a hub lock, a disabled list, a config leaf), lead with the plain frame — which
artifact, that it is one text file rather than a database, how many fields you touch, and the
one-line rollback — and unfold the code-level chain only if it is asked for. "So you are changing
Hermes's database?" is a question about blast radius, not about payloads; answering it with the
identifier-fold model reads as evasion, however accurate. Same for numbers: give the count that
was asked for, then the explanation. And when the user says they do not want to run commands
themselves ("just do it"), perform the mutation, then hand back the rollback command instead of a
procedure.

## 8. `.archive/` is a different mechanism than `skills.disabled`

Two independent lists that routinely share **zero** names — never treat one as evidence about
the other:

| | `skills.disabled` (config) | `.archive/` (curator) |
|---|---|---|
| written by | user / agent, by name | the curator, by usage age |
| effect | hidden from the prompt | moved out of the tree, hidden from the prompt |
| reverse with | remove the config entry | `hermes curator restore <name>` — only while the file is still in `.archive/` |

Lifecycle: active → stale (`curator.stale_after_days`, default 14 d unused) → archived
(`curator.archive_after_days`, default 30 d). `hermes curator status` prints both thresholds
plus active/stale/archived counts; `.curator_state` holds last run and run count;
`.curator_ledger.jsonl` records every archive with an `actor` field (`curator` = automatic,
`agent` = hand-archived) and the pre-move file hashes.

- **`curator.prune_builtins: true` disables the bundled-skill protection** — that is why
  shipped skills (pdf, pptx, google-workspace, notion, arxiv) turn up in `.archive/`. Turn it
  off when bundled skills must never be retired: `hermes config set curator.prune_builtins false`.
- Archived ≠ deleted: the documented maximum destructive action of the curator is the move into
  `.archive/`, and its own snapshots include `.archive/`. Emptying the archive is a
  user-requested operation, never a housekeeping side effect.
- **`restore` needs the file, not just the record.** `.usage.json` keeps an entry (with
  `state: archived`) for a skill whose files are long gone, so it is not evidence of existence —
  and with an empty `.archive/` there is nothing for `hermes curator restore` to move back. Check
  `ls <home>/skills/.archive/` before offering restore. When the record is `archived`, the archive
  is empty, **and** the name is still a line in `<home>/skills/.bundled_manifest`, the skill was
  bundled and the package tree still has it: the plain `cp -R <hermes install>/skills/<category>/<name>`
  (§9) restores it, and the surviving manifest hash is what keeps it rendering as unmodified
  built-in rather than a hand-made local copy. A name absent from the manifest is a different
  answer — never existed here.
- Offer `hermes curator pin <name>` for a skill the user still needs rather than restoring the
  same name every cycle.
- `hermes curator purge --days 0` is **disabled, not 'everything'** — the TTL is truthiness
  checked, so pass ≥ 1. Purge takes its own full-tree snapshot first, so it can exceed a 180 s
  foreground timeout: run it in the background (`--dry-run` first) or finish the remainder
  after taking your own tarball. Verify with `hermes curator list-archived` (expect
  `no archived skills`) **and** `hermes curator status` (expect `archived 0`).

Dry-run recipe, command map, and the restore fallback: `references/curator-archive-lifecycle.md`.

## 9. "I can't turn this skill off" / "why does it list N skills?"

A count or a dead-looking switch is a **scoping** question before it is a bug report, so
answer it with numbers from the same source the surface reads:

- Count what is on disk *for that home* (`_find_all_skills(skip_disabled=True)`, with
  `HERMES_HOME` pointed at the profile) — that is the only number meaning "my skills". A
  Capabilities → Skills page count is `/api/skills` rows **merged with the public catalog
  snapshot** (10^5 entries), so it is legitimately much larger.
- **The page's "installed only" facet does not make it apples-to-apples.** Its predicate is
  name-based — `isInstalled` in `skill-catalog.tsx` is `skillsById.has(id) ||
  skillsByName.has(entry.name) || …` — and the same predicate is reused as the filter
  (`catalog-query.ts`: `(!installedOnly || isInstalled(entry))`). So every catalog entry that
  shares a *name* with an installed skill is reported as installed: expect an inflated count
  and per-publisher duplicate rows. Those rows cannot be installed — `install()`
  returns early on `isInstalled`, and the name gate is real, not cosmetic: the loader keeps one
  skill per name (`tools/skills_tool.py` drops a name already in `seen_names`) and an install that
  lands on an existing skill directory overwrites it (`tools/skills_hub_install.py`). What they do
  keep is **not** a live switch — it only looks like one, and it is inert. The tab's own
  `renderInstalledAction` (`skills-tab.tsx`, a real name-addressed on/off writing `skills.disabled`)
  is reached only for rows whose id *is* a local row: `skill-catalog.tsx` guards it with
  `catalog.skillsById.get(entry.id)` and returns `null` for everything else, so a duplicate or
  orphan row falls through to the default `CatalogInstallSwitch` — `checked={installed}` with
  `disabled` including `installed` → **grey, on, unclickable**. The list column has no control at
  all, just a ✓ (`catalog-list-row.tsx`). Decide local vs phantom by the row's id, never by "it has
  a switch". Never present the facet as the trustworthy view; hand
  the user the disk count (or `hermes skills list`).
- **Answer the count with the count — it has three terms, not two.**
  `N = installed rows + same-name catalog rows + rows whose identifier is in the lock/official
  installed-identifier set`, with the collision rows broken down per publisher. Reproducible to the
  row by porting `mergeInstalled` + `isInstalled` against the four real payloads (recipe:
  `references/skill-inventory-and-availability.md`). The third term is the quiet one: a skill whose
  directory is gone but whose `.hub/lock.json` entry survives counts through
  `installedIdentifiers.has(identifier)` with **no name collision against your tree at all**, so a
  two-term model lands short and its residue looks unexplained.
  Do not hand back a range, an unattributed residual ("…±1"), or a snapshot-drift story: the user
  asked how the number is built, and an unexplained remainder is almost always a wrong assumption
  about a payload's shape — `/api/skills/hub/sources` keys its `installed` map by *official
  identifier* (`official/research/polymarket`), not by skill name, and reading it as names makes
  every official row look uncounted. If a re-fetch is byte-identical to your earlier fetch, drift is
  not the explanation; your model of the input is.
- **"The switch spins and stays off" is an install, not a toggle.** Read the newest
  `~/.hermes/logs/action-skills-install-*.log` before theorising: it holds the fetched source,
  the quarantine path, every finding with `file:line`, and the decision. Community source +
  `DANGEROUS` verdict is a hard block that `--force` does not override, and the scan matches the
  file's **text**, not just executable lines — a skill's own troubleshooting table that quotes
  `curl … | bash` / `sudo rm -rf` while explaining what gets blocked trips
  `curl_pipe_shell`/`sudo_usage` on that doc line (findings pointing at a markdown table row are
  the tell). That is a scanner false positive, not a broken profile: say so, and fix the install
  route rather than the skill.
- A bundled skill must never be hub-installed (the hub copy gets fetched and scanned). Restore
  it from the package instead: `hermes skills opt-in --sync` re-seeds the whole bundled set for
  the profile with no network and no scan, or `cp -R <hermes install>/skills/<category>/<name>`
  into `<home>/skills/<category>/` for just one. Re-seeding also resurrects bundled names the
  user deleted on purpose, so intersect the delete list with the package tree before recommending
  a mass re-seed. The copied dir renders as `Built In` with one folded card and a real switch only
  because its name is still listed in `<home>/skills/.bundled_manifest` (`<name>:<hash>` per line,
  plus the curator suppression list) — that is exactly what `skill_usage.is_bundled()` reads and
  what `provenance()` keys on, so check the name is there before promising the built-in label.
- **Only local rows carry a *meaningful* switch.** A row that merely shares a name with an
  installed skill renders one too, in its grey/on/disabled state, so "this row has a switch" is not
  evidence the row is local; the id (and the list column's ✓) is. Check
  `~/.hermes/skills/.hub/lock.json` before calling a row local — and note the lock alone is not
  proof either: deleting a skill directory by hand (or in a bulk delete) leaves its lock entry
  behind. The official payload derives its `installed` flag from that lock
  (`_installed_hub_identifiers`), so a deleted skill keeps showing up as installed — a grey, on,
  unclickable row with nothing behind it. Hermes calls these **orphaned**: `hermes skills check`
  lists them with `status=orphaned` ("lock-file entries whose local directory is missing"), and
  `hermes skills uninstall <name>` clears the entry. Run that check after any hand-deletion of
  hub-installed skills and report the orphans with the command; it is the difference between "the
  page is lying" and a stale lock you created.
- **A surviving lock entry also blocks the install that would repair it.** With the entry present,
  an install from any surface reads "already installed" and stops — that is the whole content of "I
  have an install record so my install fails". Order matters: `hermes skills uninstall <name>`
  (clears the stale entry) **then** `hermes skills install '<source>/<identifier>'`.
- **A ClawHub install is labelled `hub` and renders twice, from two disagreeing normalizations.**
  The display layer never carries the registry: local rows map provenance to
  `bundled → built-in`, `hub → hub`, else `local` (`skill-catalog.tsx`). The duplicate comes from the
  fold key — the catalog row's identifier is prefixed (`clawhub/@owner/slug`, via
  `skillCatalogInstallIdentifier()`) while the installer strips that prefix before writing the lock
  (`skills_hub_clawhub.py`), so `matchInstalled` misses and both rows survive. Repair it at the data
  level (no source edit) — but the identifier is only one of **three** strings that must agree, and
  editing it alone is the standard false start: the duplicate survives the refresh. The fold calls
  `installedByName.get(record.name)` *before* comparing identifiers and `record.name` is the lock
  entry's **KEY**, so a key that is the registry slug rather than the skill's own `SKILL.md` `name:`
  leaves `installedByIdentifier` empty and the identifier is never consulted; and `install_path`'s last
  segment must equal that key (`_normalize_lock_install_path`) or `hermes skills check` returns
  `invalid_install` and updates stop **silently**. Fix all three together — `mv` the skill directory
  plus the lock key and `install_path` — then re-check. The adapter accepts the prefixed and bare
  identifier forms alike, so updates keep working; a folded row takes the *feed* row's fields, which is
  what makes the label read `clawhub` again. A reinstall *and* an `update` re-normalize the strings by
  the registry slug, so re-apply after either. Two publishers can each hold the name, so a second row
  owned by *another* registry is legitimate and cannot be folded away. Audit + recipe:
  `scripts/check-lock-alignment.py`, `references/skill-inventory-and-availability.md`.
- A skill NAME can appear once per publisher, so the same name in several rows is not a bug and
  the extras are not on disk. Say which one is the installed copy.
- `ESSENTIAL_SKILLS = frozenset({"hermes-agent"})` (`agent/skill_utils.py`) is silently dropped
  by `save_disabled_skills` — that one row is genuinely un-disableable from every surface.
- **A switch's state is `skills.disabled`, and the page can be 60 s stale.** Before calling a
  toggle broken, read the CLI's own row — `hermes skills list` prints `builtin|hub|local` plus
  `enabled|disabled` per skill — and the leaf (`hermes config get skills.disabled`). A card that
  reads off for a skill the CLI calls `enabled` is a stale query
  (`/api/skills/hub/sources` carries `staleTime: 60_000`), not state: tell the user to switch
  panes and re-check, and only investigate if the toggle still disagrees. When checking a
  *specific* skill, remember the disabled list is names — an absent name means enabled, and a
  similarly-named sibling (`macos-computer-use` next to `computer-use`) being disabled says
  nothing about it.
- Prove the mechanism instead of asserting it: call the same functions the toggle endpoint calls
  (`load_config` → `get_disabled_skills` → `save_disabled_skills` → re-`load_config`) with the
  install's venv python and confirm with `agent.skill_utils.get_disabled_skill_names()`. The
  desktop backend's HTTP API carries a per-process session token, so it cannot be curl-ed.
- **Attribute a session or a write to a profile by id, never by log path**: `~/.hermes/logs/agent.log`
  is the *launch* profile's log, and a multiplex gateway writes every served profile's sessions
  into it. Look the id up in that home's own `state.db` (`sessions.id`, not `session_id`) before
  claiming which profile something belongs to.

Layers, provenance classification, the probe recipe, and the index/catalog layout:
`references/skill-inventory-and-availability.md`.

## 10. Hub skills never update themselves, and one name can live in two homes

- **There is no automatic skill update.** Both halves are manual: `hermes skills check [name]`
  (read-only — refetch per the lock's recorded `source`, compare `bundle_content_hash` against the
  lock's `content_hash`) and `hermes skills update [name] [--force]` (apply). The `skills` config
  section carries no cadence key; the only scheduled checks in Hermes are
  `plugins.auto_update_check_hours` (+ `plugins.auto_apply`, git-class plugins only) and the agent's
  own update cron. Say so plainly instead of implying self-updating, and offer a cron if the user
  wants one — the command has to name the profile. Note `check` reads the **update feed**, never
  install health: a correctly installed `official`-source skill reports `unavailable` (no adapter
  matches that source) and a name with no hub entry prints `No hub-installed skills to check.` —
  judge install health from the lock entry plus `install_path` existing on disk.
- `update` **skips a skill you edited locally** unless `--force` is given. A skill that stays put is
  usually this rule, not a failed update — confirm with `check` afterwards.
- Scope both commands to a home: `hermes --profile <name> skills check <skill>` (`-p/--profile` is a
  global flag handled in `hermes_cli/main.py`, not a `skills` subcommand flag); at the API level set
  `HERMES_HOME=<home dir>`. **Never trust the shell's inherited `HERMES_HOME`** (`env | grep HERMES_HOME`
  first): a gateway/agent session can carry another profile's home, so a bare `hermes skills
  uninstall/install` mutates *that* home — its lock and `.hub/audit.log` take the write — while the
  conversation is about the other one, and a successful-looking `Installed: …` line says nothing about
  the intended target. Pass the home explicitly on every mutating command and read the target home's
  audit tail back to confirm. An install/update also rewrites the lock entry it lands on, so any
  hand-edited lock field (identifier repairs included) must be re-checked afterwards.
- **One name, two homes**: installing the same skill twice records an entry in *each* home's
  `.hub/lock.json` while only one home gets the directory. Before answering anything about "my
  skill X", locate its directory across homes (`find ~/.hermes -maxdepth 6 -iname '*<name>*'`) and
  read every home's lock, then **name the home in the answer**. The home without the directory
  holds an orphan entry, so its page renders a grey, on, inert switch for a skill that is real
  elsewhere — and the install log alone does not say which home it landed in.

## 11. Ground the diagnosis in the surface, and bound every probe

- **Bound every network probe.** Registry/adapter calls have no internal deadline (a live ClawHub
  search has sat for minutes); a stalled probe reads to the user as the agent being stuck, and stock
  macOS has no `timeout(1)` binary. Use `curl --max-time <s>`, wrap adapter calls in a
  subprocess/signal timeout, or run them backgrounded and read the tail — never leave an unbounded
  call in a foreground turn. Prefer the local artifacts (lock, payloads, cached index) over live
  registry calls: a question answerable from `lock.json` needs no network at all.
- **When your model says the observation cannot exist, stop modelling and look at the surface.** A
  row absent from every artifact you can fetch is evidence you are modelling the wrong source, not
  that the user misread the screen — the Skills page reads four sources (local list, official list,
  hub sources, public snapshot) and a live hub search lives outside them. Ask which pane and filter
  the observation came from, and read the screen directly (`screencapture -x <file>`, then inspect it
  with vision): the window may sit on another page or another profile, and the Hermes window is one
  of several running apps.
- **The running desktop app is a build, not the source tree you read.** Its renderer bundle
  (`apps/desktop/dist`, `Resources/app.asar`) can predate or postdate the checkout, so a code path
  that contradicts the screen means "check the build", not "the user is wrong". Cite a source line
  as the cause only once the running artifact agrees with it.

## 12. Writing the skills themselves (`skill_manage`)

When the deliverable is a new or edited skill in this profile's library:

- **`description` must fit 60 characters** — one sentence, trigger first, ending with a period
  (`Use when a hub-installed skill shows 2 cards or Hub.`). The index truncates at 57 chars, so a
  longer description is rejected outright; put the detail in the body instead.
- **One rejected op aborts the whole `operations` array** — nothing is written, including the ops
  listed before the failing one. Re-issue the full batch once the field is fixed, and state which
  op failed in the same reply: a rejected batch otherwise reads to the user as a hang.
- Lint findings (`missing author`, `missing license`, `no '## When to Use'`) are advisory — the
  write landed. Peers carry `author` + `license: MIT` and a `## When to Use` block; match them.
- Keep it class-level: always-on rules in `SKILL.md`, occasional depth in
  `references/<topic>.md`, re-runnable checks in `scripts/`. Extend an existing umbrella before
  creating a sibling skill, and never file a per-incident note.

## 13. Adopting an external skill/plugin pack

A pack is a directory carrying a manifest plus `skills/<name>/SKILL.md` (usually with `scripts/`).
Codex ships the manifest at `.codex-plugin/plugin.json`, Claude at `.claude-plugin/plugin.json`;
Hermes reads that shape natively as an **Agent Plugins v1 portable package**
(`hermes_cli/agent_plugins.py`, loaded by `plugins_loader.py::_load_portable_plugin`, which registers
the pack's skills and imports no Python). Pick the route by what the pack contains:

- **Skills route — the default for a skill-only pack.** Copy the pack's `skills/*` into
  `<home>/skills/<category>/`. That tree is user-owned, so neither the manifest nor the install-time
  scan applies. Verify with `hermes skills list` (tail reads `N local — N enabled`).
- **Plugin route — only when the pack carries MCP servers or the user wants update tracking.** The
  manifest must sit at the pack **root** as `plugin.json` with
  `"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"`. Foreign-harness manifest
  directories (`.codex-plugin`, `.claude-plugin`, `.cursor-plugin`, …) are skipped by design
  (`plugins_discovery.py::_FOREIGN_HARNESS_MANIFEST_DIRS`), so as-shipped it fails with
  `plugin.json must be a regular file within the plugin root`. Shim it: copy the manifest to the root,
  add `$schema`, drop the UI-only keys (`interface`; `skills` is discovered as a directory, not a
  manifest field), then `hermes plugins validate <dir>`.

Rules that cost a round trip each when ignored:

- **Never flip `plugins.scan_on_install: false` to get a pack past a scan.** That disables the check
  globally; the skills route installs the same content with the guard untouched. The verdict policy
  itself (dangerous + community/trusted = hard block, `--force` no help, doc text counts) is §9.
- **Measure the prompt cost before copying anything.** The skill index rides in every system prompt,
  so a 50-skill pack is per-turn money. `build_skills_system_prompt(skills_dir_override=<home>/skills)`
  returns the exact block — diff it against an empty home. The index truncates descriptions, so
  frontmatter sizes overstate the cost; measure, never estimate. Install the subset the user's domain
  actually needs and say in the reply what you left out.
- **Probe in a throwaway `HERMES_HOME`, never the live profile** (`references/skills-tree-layout.md`).
  For "can this even load", call the loader directly — `load_agent_plugin(root, data_root)` → its
  `.skills` / `.diagnostics` — and quote the error; that is the answer, not a reading of the schema.
- **Sparse-cloning a monorepo pack: re-set the cone with every path you need.** A second
  `git sparse-checkout set --no-cone <path>` *replaces* the previous set and deletes the rest of the
  worktree, so the manifest directory silently vanishes mid-session.
- **If the plugin route fails inside the Hermes install tree for its own reasons**, say which layer
  failed and fall back to the skills route — do not report the pack as uninstallable.
- **Check the licence in both places before recommending redistribution**: a manifest `license` field
  can read `Proprietary` while the repo root carries no LICENSE at all and the GitHub API reports
  `license: null`.
- **Hand back commands, not a sidelined install, when the user runs mutations themselves**: the
  clone/copy command, the expected `hermes skills list` tail, and the one-line verification.

Code map, shim diff, verdict table, measurement and subsetting recipes:
`references/external-skill-pack-adoption.md`.

## 14. Answering "is there a skill for <capability>?"

`hermes skills list` is the **installed** set, never the universe: a capability can ship as a
bundled or official skill that this profile never seeded, or live only in a community registry.
Enumerate all four stores before saying "no such skill", and name the store that holds the hit.

| Store | Enumerate with | Trust |
|---|---|---|
| installed | `hermes skills list` (prints `builtin\|hub\|local` + `enabled\|disabled`) | mixed |
| bundled (ships with Hermes) | `<hermes install>/skills/<category>/<name>/SKILL.md` | builtin |
| official optional | `<hermes install>/optional-skills/<category>/<name>/` | ★ official |
| community hub | `hermes skills search <term>` | community, unvetted |

The two repo trees are one `search_files (target='files')` each and need no network — that is the
whole official catalog, so do not script it through `hermes skills browse --json` (writes nothing
to stdout). The bundled tree is also the recovery source for a pruned skill (§8).

- **`inspect` wants the registry-prefixed identifier.** `hermes skills search` prints the bare
  `Identifier: flaky-test-detective`, but `hermes skills inspect flaky-test-detective` answers
  `No exact match … Did you mean` and never shows a body; pass `clawhub/<name>`, or
  `skills-sh/<owner>/<repo>/<name>`. `install` takes the same form.
- `official/...` resolves only for skills that really are optional — a bundled name is not
  installable from the official source (`official/software-development/test-driven-development`
  → `Could not find`); copy it into the home instead.
- Rank the stores in the answer and label trust: never present a community hit and a bundled skill
  as the same class of option. Preview community hits with `inspect` before recommending one.
- A capability word like "optimize tests" hides several different asks (fewer flakes / more
  coverage / faster suite / delete bad asserts) and each lands on a different skill. Give the store
  answer, then ask which one is meant rather than picking one for the user.

Store-by-store commands, identifier forms, and the bundled-name-miss signature:
`references/skill-inventory-and-availability.md`.

## 15. Editing a profile's own context files (SOUL.md, README.md)

The files a profile loads by itself — `SOUL.md` (injected into every system prompt),
`memories/*.md`, `config.yaml` — are also the ones the user hand-edits between turns. Both
failure modes are silent: the write lands in a home nobody reads, or it erases an edit made two
turns earlier.

- **Resolve the live profile directory from `$HERMES_HOME` before writing anything into a
  profile.** The active-profile path quoted in the system prompt can lag a rename, and the
  superseded directory usually still exists as a shell. A near-miss sibling (e.g.
  `profiles/<name>-assistant` sitting next to the live `profiles/<name>-assistance`) accepts the
  write happily and the deliverable is invisible to the profile that loads it. Confirm the target
  holds `SOUL.md`, `memories/`, `skills/` and `state.db` before writing.
- **Cross-check that your memory writes land in that same home**: after a `memory` call,
  `<live home>/memories/MEMORY.md` mtime is now. An older mtime means two different homes are in
  play and one of them is not the live one.
- **Re-read the target immediately before rewriting it.** Compare size/mtime against what you last
  wrote — a changed file means the user edited it. Read it, keep their text verbatim (they may have
  retitled your section, corrected a fact, or rewritten the intro), and splice your content around
  it instead of overwriting.
- **Back up per edit with a suffix naming the change** (`SOUL.md.bak-<YYYYMMDD>-<what-changed>`),
  keep the pre-change copy of the original persona as its own file, and prove the backup matches the
  untouched source with `md5` — that is what makes "I only appended" checkable afterwards.
- **Splice rather than hand-retype**: keep the first N lines with `head -N`, append the new tail
  from a scratch file, and prove the kept prefix is byte-identical with
  `cmp <(head -N <old>) <(head -N <new>)` before moving it into place. Recipe and verification
  commands: `references/profile-context-file-edits.md`.
  - **Each revision of the tail goes to its own scratch filename.** `write_file` refuses to
    overwrite a file this session has not fully read, and a tail the user has just asked you to
    rewrite is normally one you wrote earlier — so the second rewrite silently bounces. Write
    `<tail>-v2.md`, `-v3.md`, …, and keep the previous revision as the backup instead of
    re-reading scratch output just to overwrite it.
- **Budget the prompt cost, and say the delta.** `SOUL.md` rides in every system prompt, so measure
  `wc -l -c` before and after. Keep the always-on file to rules plus a one-line pointer and push
  frequency tables, evidence and long instances into a `README.md` **in the same home** — a pointer
  to a file that does not exist in the live home is worse than no pointer.
- **Report which file changed, in which home, with before/after byte counts and the backup path.**
  When the file you edited is a user-authored persona, also state that their text survives as a
  byte-identical prefix, so the edit is reviewable rather than alarming.

## Support files

- `references/profile-context-file-edits.md` — recipe for editing a profile's own context files:
  resolving the live `$HERMES_HOME`, spotting a stale sibling home, detecting a user edit made
  between turns, backup/splice/verify commands, and the prompt-budget check.
- `references/external-skill-pack-adoption.md` — installing a third-party skill/plugin pack
  (Codex/Claude/Agent Plugins v1) into a profile: manifest shim, loader probe, scan verdicts seen on
  real packs, index-size measurement, subsetting.
- `references/skills-tree-layout.md` — concrete on-disk layout of the skills tree and the
  probe snippets (name→path mapping, two-method delete verification, config-leaf diff,
  throwaway `HERMES_HOME` write probe).
- `references/curator-archive-lifecycle.md` — the curator's command map, what each archive
  record holds, and the purge recipe with its timeout and verification steps.
- `references/skill-inventory-and-availability.md` — every store that answers "what skills does
  this profile have" (live tree, `.archive`, `skills.disabled`, hub lock, catalog index) **plus the
  uninstalled stores** (bundled package tree, `optional-skills/`, registry search) that answer "does
  a skill for X exist", the provenance/essential-skill rules, and the venv-python probe that
  reproduces a UI toggle.
- `scripts/check-lock-alignment.py` — read-only audit of one home's hub lock for the three-string
  agreement (lock key == `install_path` last segment == the skill's own name) that decides whether a
  ClawHub install folds into a single row, shows up twice, or reports `invalid_install`.
