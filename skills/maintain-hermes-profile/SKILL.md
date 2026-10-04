---
name: maintain-hermes-profile
description: "Use when bulk-editing a profile's skills or config. Bulk enable/disable/delete of many skills, dead `skills.disabled` entries, edits to `config.yaml`, the `.archive/` lifecycle and the built-in restore path, adopting an external skill pack, which layer a rule comes from (SOUL.md vs built-in), and reading the session store to see what the agent actually did. Creating or switching profiles is `maintain-hermes-profiles`; one skill's install/update/remove are the `install-`/`update-`/`remove-hermes-skills` siblings."
---

# Hermes profile housekeeping

Bulk skill / config surgery inside one profile: enable/disable/delete many skills at once,
prune dead `skills.disabled` entries, edit `config.yaml` safely. Every rule below exists
because the naive version silently does the wrong thing or destroys something unrecoverable.

## When to Use

- The user says to delete, disable, purge, or clean up many skills in a profile.
- `skills.disabled` in `config.yaml` has grown dead entries, or on-disk skill dirs and the
  config list disagree.
- A settings change must be written to `~/.hermes/config.yaml` (the file tools refuse it).
- The user asks to clean up `~/.hermes/skills/.archive/`, or wants the curator to stop
  retiring bundled skills.
- The user asks why a skill "can't be turned off", or why a skills pane lists far more
  skills than exist on disk (§9).
- The user asks whether an installed hub / ClawHub skill updates itself, or which profile an
  install actually landed in (§10).
- The user asks **how to switch off automatic skill updating / seeding**, or why skills appeared,
  changed or went missing on their own — four independent levers with different defaults (§10).
- The user wants Hermes to **stop turning the conversation into skills / memory**, or wants that
  summarising tuned, gated, or approval-only (§17).
- Which code tree is actually running matters (a probe of the bundled tree contradicts what the app
  does) (§16).
- The user asks **whether a skill for some capability exists** ("is there a skill that does X?")
  — the installed list is not the universe (§14).
- The user deleted many skills (or the curator pruned them) and now wants the built-ins back (§16,
  restore half) — the naive `hermes update` / `hermes skills opt-in --sync` answer does not restore
  them, and its output does not say so.
- The user asks what `.bundled_manifest` / `.curator_suppressed` actually record, or whether a skill
  "was ever installed here" (§16).
- The **desktop app itself** is what misbehaves — a pane errors, a plugin's UI loads but its data
  404s, a feature works on one profile and not another — use `maintain-hermes-desktop-app` for
  the Electron/app-level side (active profile, backend argv, per-profile plugin routes); this skill
  owns the files inside a profile.
- Any bulk destructive file operation inside `~/.hermes/` needs a plan, a backup, and proof.
- The user asks whether a rule the agent follows is **Hermes built-in** or comes from their own `SOUL.md`
  / a skill, or wants a built-in prompt block turned off, narrowed to some models, or overridden (§18).
- The user asks whether a skill was **ever actually loaded / used**, or when a behaviour stopped (§18 —
  the load record lives in the session store, not in the prompt).

Inspection inside a session: use the native tools — `skills_list`, `skill_view`, and
`search_files (target='files')` — before reaching for shell `find`/`ls`. The probe snippets
in §2 and `references/maintain-hermes-profile-skills-tree-layout.md` deliberately use shell `find` + `os.walk`
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
- Prune `skills.disabled` entries whose directories no longer exist; otherwise they are dead
  entries that make the next audit lie to you.
- **A null-word value is written as a YAML null, not as the string you typed** — `_SCALAR_WORDS`
  (`hermes_cli/config.py`) maps `none` / `null` / `~` → `None`, so `hermes config set X none` stores
  a null, and every reader that treats null as "unset" silently keeps its default while the CLI
  prints "saved anyway". Live case: `agent.reasoning_effort none` lands as `reasoning_effort:`
  (null) → `resolve_reasoning_config` (`hermes_constants.py`) returns `None` → **default medium,
  i.e. thinking stays ON** in a profile whose whole point was to have it off. `parse_reasoning_effort`
  does accept the *string* `none`, but `config set` cannot produce it; pass `false` instead (stored as
  the YAML bool → `str(False).lower() == "false"` → `{"enabled": False}`). Prove the effective value by
  calling `resolve_reasoning_config(yaml.safe_load(config.yaml))` with the install's venv python
  (`hermes-agent/venv/bin/python`), never by reading the file back — the file looks the same for both.

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
was asked for, then the explanation.

**A "what does it read / when does it change" question is a naming question first.** Open with one
sentence that names the artifact and the frame — "它读的是一张记账文件，不是文件夹" — then walk ONE concrete
instance end to end with the real values (the entry as it sits in the file, the path that is missing,
the two counts), and unfold the layer/source map only if it is asked for. Opening with the source
decomposition earns "你说得有些复杂，我还是没弄懂看的是什么" and the question comes back a second time, which
costs more than the precision bought. The same applies to the investigation itself: once the mechanism
is confirmed, answer and close. Call it a complex problem and the user notices ("看起来你把它定义为一个
复杂问题") — so an observation you cannot reproduce (a count matching no surface you can query) is one
open line plus "which surface produced it?", never a second probe campaign inside the same reply. And when the user says they do not want to run commands
themselves ("just do it"), perform the mutation, then hand back the rollback command instead of a
procedure.

**When the ask is a command, the reply opens with the command.** A "how do I remove X" / "give me
exact commands" round is not the round to report in: lead with one copy-pasteable block, then at
most two or three one-line caveats (the scope flag, the verification line, the one thing that
behaves differently on this machine). Summary headings, evidence narrative and before/after counts
up front read as stalling and earn a "just give me the command"; the long form belongs in the round
where the work was done *for* the user, not in the round where they run it themselves.

**Name a path in full the first time.** Do not introduce a shorthand the user has never seen ("the
runtime code root `…/workspace/`") — it cannot be acted on, and it costs a round trip ("是哪里？").
Give the absolute path, or the `ls` output that shows it, then abbreviate freely afterwards. Same for
counts: attribute each number to the file and the home it came from, or the next round is spent
re-deriving which home the number described.

**A one-sentence request gets one sentence** — no headings, no table, no bullet list, even when the
mechanism has three gates. Fold the gates into subordinate clauses and end on the actionable clause
(what to run, or that recovery is still possible). When the question's premise is itself wrong ("why
can't they be restored"), the single sentence carries both halves: why the normal path fails **and**
that the data is still there, with the command that takes it back.

**A condense request binds the round summary too.** "太长了" arrives with the answer already written,
so it is an instruction about shape, not a request to re-order the same content: cut to one line per
mechanism, drop source paths and code line numbers, and shrink the trailing summary block to a single
line per heading — headings only when the round did the work *for* the user; a quick how-to needs no
summary scaffolding at all. The same round may also end a topic mid-thread ("先别管这个"): drop it
without re-litigating it, and do not reopen it unasked later in the session.

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

Dry-run recipe, command map, and the restore fallback: `maintain-hermes-memory` → `references/maintain-hermes-curator-archive-lifecycle.md`.

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
  `maintain-hermes-skills` → `references/maintain-hermes-skills-inventory-and-availability.md`). The third term is the quiet one: a skill whose
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
  file's **text**, not just executable lines — a skill's own troubleshooting table that quotes the
  download-piped-into-a-shell shape, or a recursive delete behind a privilege-escalation prefix, while
  explaining what gets blocked, trips `curl_pipe_shell` / `sudo_usage` on that doc line (findings pointing
  at a markdown table row are the tell). That is a scanner false positive, not a broken profile: say so, and
  fix the install route rather than the skill.
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
- **An orphan entry is permanent until it is removed or satisfied, because nothing ever prunes the
  lock.** Exactly three code paths write `lock.json`: `HubLockFile.record_install`
  (`tools/skills_hub.py`, called only from `tools/skills_hub_install.py`) on install,
  `HubLockFile.record_uninstall` on uninstall, and `_backfill_optional_provenance`
  (`tools/skills_sync_optional.py`, which `atomic_write_text`s the file itself) on every
  bundled-skill sync — `hermes update`, `hermes setup`, and the `hermes skills` sync/repair paths.
  No reconcile step compares the lock against the tree and `hermes doctor` only counts entries, so
  entries routinely outlive their directories. When asked "when does this file change", that list is
  the answer; read-only surfaces (`hermes skills list`, the page's filters, `doctor`) are not on it.
- **Read the entry to date the disappearance.** The backfill writes an entry only while the directory
  exists *and* hashes byte-identical to its `<hermes install>/optional-skills/` source, so for a
  `"scan_verdict": "backfilled"` entry (plus `"metadata": {"backfilled_from": "optional-skills"}`)
  `installed_at` is a moment the skill was still really on disk: entries sharing one timestamp are a
  single bulk run, and the newest timestamp brackets when the directory vanished. A normal record
  (`scan_verdict` from the install scan) instead dates the registry install. One backfill run scans
  the **whole** optional tree, so the `name` argument never narrowed what it wrote.
- **Orphan repair has two opposite directions — pick by intent.** `hermes skills uninstall <name> -y`
  drops the record (the directory is already gone, so nothing is lost), or
  `hermes skills repair-official <name> --restore --yes` rebuilds the files from the package's
  `optional-skills/` tree and keeps the entry. The second exists only for *official optional* skills
  (anything else: re-install), it moves any mutated or relocated active copy into
  `<home>/skills/.restore-backups/official-optional-<timestamp>/` before copying, and **without
  `--restore` it is a no-op for a missing directory** — the restore loop is literally
  `for … in targets if restore else []`, so the default form only backfills provenance. Spell it with
  the hyphen (`repair-official`); `hermes skills repair official` is an unknown subcommand.
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
  `maintain-hermes-skill-cards` → `scripts/check-lock-alignment.py`, `maintain-hermes-skills` → `references/maintain-hermes-skills-inventory-and-availability.md`.
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
  install's venv python and confirm with `agent.skill_utils.get_disabled_skill_names()`.
- **The backend's HTTP API *is* readable — take the token from the process, not from config.** It
guards every route with a per-process session token, and that token is an environment variable of
the running backend:
  ```bash
  T=$(ps -Eww -p <backend pid> | tr ' ' '\n' | sed -n 's/^HERMES_DASHBOARD_SESSION_TOKEN=//p')
  lsof -nP -iTCP -sTCP:LISTEN | grep -i python     # the REAL port, not the one in the argv
  curl -s -H "X-Hermes-Session-Token: $T" 'http://127.0.0.1:<port>/api/skills?profile=<home>'
  ```
  Without the header every route answers `{"detail":"Unauthorized"}` (401), which is why this reads
  as "cannot be curl-ed". Prefer it over porting the code path: `/api/skills`,
  `/api/skills/hub/sources`, `/api/skills/hub/official`, `/api/profiles`, `/api/toolsets` return
  byte-for-byte what the page renders, `?profile=` is what scopes a home other than the backend's
  launch home, and the served port can differ from the configured one (a `--port 9120` process has
  been found listening elsewhere) — always resolve it from the listener.
- **Attribute a session or a write to a profile by id, never by log path**: `~/.hermes/logs/agent.log`
  is the *launch* profile's log, and a multiplex gateway writes every served profile's sessions
  into it. Look the id up in that home's own `state.db` (`sessions.id`, not `session_id`) before
  claiming which profile something belongs to.

Layers, provenance classification, the probe recipe, and the index/catalog layout:
`maintain-hermes-skills` → `references/maintain-hermes-skills-inventory-and-availability.md`.

## 10. Hub skills never update themselves, and one name can live in two homes

- **There is no automatic skill update — for hub skills.** Both halves are manual: `hermes skills check [name]`
  (read-only — refetch per the lock's recorded `source`, compare `bundle_content_hash` against the
  lock's `content_hash`) and `hermes skills update [name] [--force]` (apply). The `skills` config
  section carries no cadence key. **Do not widen that into "nothing changes my skills by itself".**
  Three other paths mutate the tree with no user action, with different defaults: bundled seeding
  (**on**; `hermes skills opt-out`), Skill Sync (off — `sync.enabled: false`, and inert anyway until a Nous login carrying an
  admin role **and** a resolvable `sync.base_url`; the gateway's per-profile pull tick calls
  `maybe_pull_skills()`, read it with `hermes sync status`, exclude a single skill with
  `hermes sync disable <name>`), and the curator (**on**; `curator.enabled` / `hermes curator pin`). Name
  the lever, its default and its one command; mis-attributing new or changed skills to
  `plugins.auto_update_check_hours` (+ `plugins.auto_apply`, git-class plugins only) sends the user to
  a switch that moves nothing in their skills tree. Say so plainly instead of implying self-updating,
  and offer a cron if the user wants one — the command has to name the profile.
- `update` **skips a skill you edited locally** unless `--force` is given. A skill that stays put is
  usually this rule, not a failed update — confirm with `check` afterwards.
- Scope both commands to a home: `hermes --profile <name> skills check <skill>` (`-p/--profile` is a
  global flag handled in `hermes_cli/main.py`, not a `skills` subcommand flag); at the API level set
  `HERMES_HOME=<home dir>`. **Never trust the shell's inherited `HERMES_HOME`** (print it first:
  `echo "${HERMES_HOME:-<unset>}"`): a gateway/agent session can carry another profile's home, so a bare `hermes skills
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
- **The core `hermes update` never touches hub skills.** It re-seeds *bundled* skills only
  (`update_cmd_maint.py::_print_bundled_skills_sync_report` → `tools/skills_sync.sync_skills`), so a
  Hermes upgrade is not an update path for a registry- or GitHub-installed skill either.
- **Following upstream automatically is a risk decision, not a setting.** A skill is instructions the
  agent loads on its own; the scan runs at install/update time only, and `hermes skills audit [--deep]`
  is the re-scan of what is already on disk. For a repo the user wants to track, either schedule
  `check` + `update` (cron; the command has to name the profile) or clone it and register the checkout
  via `skills.external_dirs` with a scheduled `git pull` — the second is the documented route for
  "upstream moves, my copy moves", at the cost of leaving the hub's lock/audit trail. State the
  trade-off explicitly instead of implying a self-updating install exists.

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
- **Which profile a pane was scoped to is recorded, not guessable.** The app's active profile and its
  last route per profile live in `<userData>/Local Storage/leveldb` under keys
  `hermes-desktop-active-profile-v1` and `hermes.desktop.lastRoute.profile.<name>`; dump them with
  `strings -a '<userData>/Local Storage/leveldb/'* | grep -i 'active-profile\|lastRoute'`
  (`userData` = `~/Library/Application Support/Hermes` on macOS, values interleave as UTF-16 —
  `strings` still surfaces them). That settles "was the report about the home I am diagnosing?" before
  any modelling, which is the usual reason a pane's numbers cannot be reproduced.

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
- **Probe in a throwaway `HERMES_HOME`, never the live profile** (`references/maintain-hermes-profile-skills-tree-layout.md`).
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
`install-hermes-skills` → `references/install-hermes-skills-external-pack-adoption.md`.

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
| GitHub repo / tap | `hermes skills search <term> --source <publisher>` (§15) | trusted for known publishers, else community |

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
`maintain-hermes-skills` → `references/maintain-hermes-skills-inventory-and-availability.md`.

## 15. GitHub sources: direct paths and taps

A skill can be installed straight out of a GitHub repo, with or without subscribing to the repo. Full
command set, identifier grammar, tap config, and the auto-update options:
`install-hermes-skills` → `references/install-hermes-skills-github-sources.md`. Rules that change the answer:

- **Resolve the identifier from search, never from a doc example.** The identifier embeds the repo's
  own layout (`anthropics/skills/skills/pptx`, `openai/skills/skills/.curated/hatch-pet`), and a doc's
  example path goes stale the moment upstream reorganizes — a bare `openai/skills/k8s` answers
  `Could not find … in any source`, which is a moved path, not a broken hub. Filter by publisher:
  `hermes skills search <term> --source openai|anthropic|huggingface|nvidia|gstack|voltagent|minimax`.
- **`--source github` does not surface tap content** — it comes back with rows from other sources.
  Filter by the publisher name.
- **A tap is a repo subscription, not a skill**: `hermes skills tap add owner/repo` (config
  `<home>/skills/.hub/taps.json`, `path` defaults to `skills/`). Known publishers (openai, anthropics,
  huggingface, NVIDIA, gstack, K-Dense-AI) are default taps and need no setup; any other repo is
  `community` trust and pays the install-time scan.
- **Read the tap's cached index when a path looks wrong**:
  `<home>/skills/.hub/index-cache/<owner>_<repo>_<path>.json` holds exactly what that repo+path
  exposes (an empty `<owner>_<repo>_skills__.json` next to a populated `…_skills_.curated__.json` is
  the tell).
- **An installed GitHub skill is an ordinary hub entry** — same lock, same `check`/`update`, same home
  scoping as §10, plus the status `unavailable` when the recorded source can no longer produce the
  bundle (e.g. the tap was removed).
- **One install can be several skills, and the fetch is the whole directory tree.** Installing a parent
  skill dir brought its nested sub-skills and MB of assets along (71 files / 6.3 MB), and each nested
  `SKILL.md` registered as its own skill. Count the rows before reporting "installed", and treat bundle
  size as an install cost — it feeds the scan verdict.
- **A `BLOCKED` install is a `--force` decision; the update path is not blocked again.** A community
  repo whose `caution` verdict clears the thresholds installs nothing until `--force`, while `update`
  internally calls `do_install(force=True)`, so a scheduled update runs unattended. Say which step needs
  the human.
- **The clone route is verified and mutually exclusive with the hub route.** `skills.external_dirs`
  pointing at a checkout's skills directory registered every skill in the repo as `local` with no scan;
  never keep both routes for one repo, because external dirs lose the name collision and one copy goes
  unreachable.

## 16. Removing or restoring skills (three kinds, three mechanisms)

The `Source` column of `hermes skills list` (`builtin` / hub sources / `local`) decides the path.
Only one of the three kinds has a CLI verb, so "remove it completely" has three different answers:

| Source shown | What it is | Removal |
|---|---|---|
| `official` / `clawhub` / `skills.sh` / `github` | hub-installed: an entry in `<home>/skills/.hub/lock.json` | `hermes skills uninstall <name> --yes` |
| `builtin` | seeded from the package tree, tracked in `<home>/skills/.bundled_manifest` | `rm -rf <home>/skills/<category>/<name>` |
| `local` | hand-written or agent-created | `rm -rf …`, or `skill_manage(action='delete', name=…)` |

- **`uninstall` refuses anything without a lock entry** — `'<name>' is not a hub-installed skill
  (may be a builtin)`. That message means "switch to the directory path", never "the skill cannot
  be removed"; report the command that does work, not the refusal. It is a real `rmtree` + lock-entry
  drop, and it clears the skills cache itself (`_finish_change(invalidate_cache=True)`), so it needs
  no `--now` — unlike install or config changes.
- **A hand-deleted bundled skill is permanent because the manifest line is what records the
  deletion.** `tools/skills_sync.sync_skills` (the engine behind `hermes update`) classifies per name:
  *in manifest + not on disk* → "user deleted it", counted into `skipped`; *not in manifest* →
  `_install_new_skill` → re-copied. So delete the directory and **leave its `.bundled_manifest` line
  alone**; clearing that line is precisely what makes the next sync resurrect the skill. Scripted
  deletes use the sync module's own remover, `_rmtree_writable` (read-only dirs + scope guard) —
  API-level mechanics for all three paths: `references/maintain-hermes-profile-skills-tree-layout.md`.
- **Bulk alternative, all-or-nothing**: `hermes skills opt-out --remove` deletes every *pristine*
  bundled skill and writes the `.no-bundled-skills` marker so nothing is seeded again
  (user-modified, hub and local skills are never touched). Without `--remove` it only writes the
  marker — the way to keep the tree as-is but stop future seeding. There is no per-skill CLI
  removal for bundled skills, so say that rather than hunting for a flag.
- **Local/agent-created**: foreground `skill_manage(action='delete')` is a hard `shutil.rmtree`;
  only the *background* curator review archives instead, into `<home>/skills/.archive/`
  (recoverable with `hermes curator restore <name>`). `hermes curator archive <name>` is the
  deliberately recoverable variant — offer it when the user may want the skill back.
- **Removal is per home.** Each profile owns its own `skills/`; a name removed in the default
  profile still exists at `~/.hermes/profiles/<name>/skills/`. Name the home covered.
- Cleanup after any of the three: the name lingers in `skills.disabled` (dead entry — §6) and in
  `.usage.json` (harmless sidecar; never evidence of existence — §8). In-session, `/reload-skills`
  re-scans for added/removed skills; a **gateway** session needs a new one, because the skill index
  is baked into the system prompt at session start. Two leftovers are worth naming because they are
  *not* inert: `<home>/cache/banner_snapshot.json` keeps listing the removed skill in the CLI banner
  (its fingerprint covers only `config.yaml`/`.env` mtime+size and the version — the skills tree is
  not an input), and another skill's `SKILL.md` may reference the deleted name by hand. The rest
  (`.curator_ledger.jsonl` audit lines with absolute paths + sha256, `.usage.json`, session
  transcripts) is cosmetic. Full audit list: `references/maintain-hermes-profile-skills-tree-layout.md`.
- **Restoring a bundled skill needs BOTH records cleared, and a valid bundled tree.** Un-suppress
  the name in `<home>/skills/.curator_suppressed` *and* drop its `.bundled_manifest` line, then sync
  — the same manifest line that makes a deletion stick is the one that blocks the re-seed, so the
  two rules are one mechanism read in both directions. Suppression is the one people miss: it is
  written whenever the curator prunes a built-in under `curator.prune_builtins: true`, so a profile
  can be both "in manifest" and "suppressed" and stay empty through any number of updates.
  Un-suppress only the names being restored; leave other prunes alone. The four states and what one
  sync does with each:

  | `.bundled_manifest` line | dir on disk | sync action |
  |---|---|---|
  | present | present | participates in the update (hash match → overwrite, differ → keep as user-modified) |
  | present | missing | `skipped` — read as "user deleted it" |
  | absent | missing | `_install_new_skill` → re-copied |
  | any | any | name in `.curator_suppressed` → `skipped` regardless |

- **What `.bundled_manifest` records, in both directions.** Each line is `<name>:<origin hash>`: the
  name means "this bundled skill was seeded into this home at some point" (install, or a later sync
  that added it), the hash is the baseline of the shipped version at that moment — used to decide
  overwrite-vs-keep and to list user-modified copies (`hermes skills list-modified`). It is **not** a
  record of hub or local installs, not a version string, and not the only built-in source of truth:
  `.curator_suppressed` names count as built-in too (`skill_usage.is_bundled()` reads both). A name
  absent from both means "never seeded in this home" — a different answer from "deleted".
- **`hermes curator restore <name>` beats a re-seed when `.archive/` still holds the copy**, because a
  sync overwrites with the shipped version while restore returns your own archived copy. Verified
  behaviour: it is allowed for a *bundled* name only while `curator.prune_builtins: true`; it ignores
  `.bundled_manifest` entirely; it moves the directory to `<home>/skills/<name>/` **flat** (the
  category dir is not rebuilt); and it drops exactly that name from `.curator_suppressed`. So a
  profile whose `.archive/` is intact has a per-skill command for its pruned built-ins — check
  `hermes curator list-archived` before offering a script.
- **No row means no skill.** `hermes skills list` enumerates on-disk `SKILL.md` only and its status
  column is just "name not in `skills.disabled`" — curator state (archived / suppressed / deleted)
  has no term in it. So a list taken *before* a delete cannot be re-read afterwards as evidence those
  skills were still installed, and "it showed as enabled" is never a claim about curator state. To
  answer "did I ever have this here", read `.archive/` and `.bundled_manifest`, not the list.
- **Check what the sync resolves as its bundled source before trusting its counts.** `sync_skills`
  returns `total_bundled=0, copied=[]` when the bundled dir does not exist, and the CLI prints that
  as a normal one-liner — indistinguishable from "nothing to do". `_get_bundled_dir()` is
  `HERMES_BUNDLED_SKILLS` → `<dir of tools/skills_sync.py>/../skills` → `<home>/skills`, and a
  managed/lease install runs the code from `~/.hermes/installs/<id>/environments/<id>/workspace/`,
  which ships **no** `skills/` tree — so on such an install the default source is a missing path and
  no update will ever re-seed a built-in. The fix is the documented packaging hook, not a source
  edit: `HERMES_BUNDLED_SKILLS=<checkout>/skills` around the command. Re-seed script (dry-run +
  `--apply`): `update-hermes-skills` → `scripts/restore_builtin_skills.py`.
- **Probe that resolution from a neutral cwd, and probe the launcher you actually mean.** Two launch
  paths coexist on one machine: the `hermes` on `PATH` (a pip console script whose editable finder maps
  the package to `…/installs/<id>/environments/<id>/workspace/`, bundled tree = the missing
  `…/workspace/skills`) and the shim a desktop app / gateway runs
  (`~/.hermes/hermes-agent/.hermes/bin/hermes`, which does `sys.path.insert(0, '<checkout>')` and so
  resolves `skills/` inside the git checkout, where the tree does exist). "The bundled tree is empty" is
  therefore a claim about *one* launcher: read the live process command lines (`ps -eo command`) to see
  which shim a running gateway came from before generalising it to "Hermes has no bundled skills".
  Probe as `cd /tmp && env -u PYTHONPATH <venv>/bin/python3 -c "import tools.skills_sync as m;
  print(m.__file__, m._get_bundled_dir(), m._get_bundled_dir().exists())"` — from a cwd *inside* the
  checkout, `python -c` puts that cwd on `sys.path[0]` and the import silently resolves to the checkout
  instead of the install, which inverts the answer.
- Prove the permanence instead of asserting it — the probe deletes from a throwaway `HERMES_HOME`
  and re-runs the sync, never from the live tree: `references/maintain-hermes-profile-skills-tree-layout.md`.

## 17. Turning off / tuning "Hermes summarises the conversation into skills"

The post-turn **background review fork** (`agent/background_review.py`, spawned from
`agent/turn_finalizer.py` once the reply is delivered) replays the round and may write memory or patch
skills — it is what produces an unasked-for "saved that as a skill". Three tiers:

| Goal | Command |
|---|---|
| no automatic fork at all (`/refine` still runs one on demand) | `hermes config set auxiliary.background_review.enabled false` |
| keep memory review, stop skill creation | `hermes config set skills.creation_nudge_interval 0` |
| keep writing, but every write needs approval | `hermes config set skills.write_approval true` |

- **`skills.creation_nudge_interval` is a top-level `skills:` key — never `agent.skills.*`.** The reader
  (`agent/agent_init.py::_apply_agent_section`) pulls the `agent` section for its other keys but reads
  this one as `_agent_cfg.get("skills", {})` off the **whole merged config**. Default 10, and the
  skill-review trigger is `interval > 0 AND tool-iterations-since-last-skill-write >= interval`
  (`agent/turn_finalizer.py`). Writing it under `agent:` creates a key nothing ever reads.
- **Tune before disabling.** A user who only wants fewer summaries wants the interval raised (15 → 40),
  not zeroed; `memory.nudge_interval` (default 10 user turns) is the memory-side twin.
- **Killing the fork does not stop foreground writes.** The agent can still call `skill_manage` from its
  own judgement mid-turn; only `skills.write_approval` / `memory.write_approval` gate that path, and a
  staged write is cleared with `/skills pending`, `/skills diff <id>`, `/skills approve|reject <id>`
  (`/memory` likewise). Say both halves rather than implying one switch covers the class.
- A key absent from `DEFAULT_CONFIG` (this one is) makes `hermes config set` print "not a recognized
  config key — it was saved anyway" — the incomplete known-key table of §6, not a rejected write; parse
  the YAML back to prove the value.
- **They are read at agent init, so they apply in a NEW session** (`/reset`, or `/restart` for a
  gateway), never mid-conversation — prompt caching is preserved by design.
- `display.background_review_notices` (`off|on|verbose`) only changes the chat notice; it neither starts
  nor stops the fork. `auxiliary.background_review` also takes `provider`/`model`/`max_input_tokens` to
  route the fork off the main-model replay instead of switching it off.

Key table with defaults and read sites, plus the "did the new value take effect" check:
`maintain-hermes-memory` → `references/maintain-hermes-self-improvement-controls.md`.

## 18. Is that rule built-in, or is it mine?

A "why does the agent do X / which priority wins / can I switch that off" question is a **layer** question
before it is a code question: `SOUL.md` (identity slot #1, user-owned), the memory files, the skill index,
and the model-gated built-in guidance blocks are separate layers with separate owners and separate
switches. Name the layer and its file first — a behaviour question answered at the wrong layer produces a
fix that moves nothing.

- `SOUL.md` is **user-owned**: the lever is the user's edit, and the agent's job is to say the file's path
  and that it is theirs, not to rewrite it unasked.
- A built-in block (the `# Execution discipline` group, tool-use enforcement, the Google operational block)
  is gated **per model**, not per profile: `agent.execution_guidance` and `agent.tool_use_enforcement` take
  `auto` / `true` / `false` / a **list of model-name substrings**, so "is this block even in this session's
  prompt" is answerable with `_model_gate(...)` rather than argued from the prompt text (§18 reference).
- Nothing in the code assigns a precedence between the layers — the model resolves a conflict. So when a
  user-authored rule loses to a built-in block, the fix is an explicit line in `SOUL.md` or turning that
  block's gate off; do not claim file order decides it.
- **A rule moved out of `SOUL.md` into a skill stops applying until something loads that skill — silently.**
  The skill index that rides in every prompt carries `name` + `description` only; the body arrives only
  through an explicit `skill_view`. So "split the persona into skills" is a **behaviour change, not a
  relocation**: no error is raised, the rule's output shape simply stops appearing, and the skill that was
  supposed to replace it sits unloaded (a hub skill can sit at zero loads for its whole life — install state
  in `lock.json` records nothing about use). Prove it from the load record, never from the prompt text you
  believe is loaded: `/Users/maxim/.hermes/state.db`, `SELECT content FROM messages WHERE
  tool_name='skill_view'`, JSON-parse each row for `name` (recipe + the prompt-hash join that dates which
  `SOUL.md` text was active per session: `maintain-hermes-memory` → `references/maintain-hermes-session-store-forensics.md`).
- Answer shape: **layer + file + gate key with its current value**, then the consequence. Read the files and
  run the gate probe; never reconstruct a prompt-layer answer from memory of the prompt. When the question
  is "did this rule/skill actually run", the evidence is the **load record** in the session store (plus a
  count of the turns whose output shape matches the rule) — a diff of the skill body against the old prompt
  text tells you which layer the behaviour was really coming from.

Layer map, gate semantics, and the re-runnable probe: `references/maintain-hermes-profile-prompt-assembly-and-guidance-gates.md`.

## Support files

Two references ship with this skill. The skills-subsystem depth that §8–§18 lean on was moved into the
sibling skills on 2026-09-30, because that is where it belongs — every pointer above names the sibling
it went to, and this table is the map:

| Topic this skill uses | Now lives in |
|---|---|
| installing from a GitHub repo — direct identifier vs tap vs bare URL, identifier grammar, tap config, the two honest answers to "can it auto-update?" (§15) | `install-hermes-skills` → `references/install-hermes-skills-github-sources.md` |
| adopting a third-party skill/plugin pack — manifest shim, loader probe, scan verdicts, index-size measurement, subsetting (§13) | `install-hermes-skills` → `references/install-hermes-skills-external-pack-adoption.md` |
| the curator's `.archive/` — command map, what an archive record holds, the purge recipe (§8) | `maintain-hermes-memory` → `references/maintain-hermes-curator-archive-lifecycle.md` |
| every mechanism that mutates a profile with no user command, with each lever's default and off switch (§10, §17) | `maintain-hermes-memory` → `references/maintain-hermes-self-improvement-controls.md` |
| read-only SQL over a home's `state.db` — which skills loaded, which prompt text was active, dating an install (§18) | `maintain-hermes-memory` → `references/maintain-hermes-session-store-forensics.md` |
| every store that answers "what skills does this profile have" **plus** the uninstalled stores that answer "is there a skill for X", the provenance rules, the venv-python probe that reproduces a UI toggle (§9, §14) | `maintain-hermes-skills` → `references/maintain-hermes-skills-inventory-and-availability.md` |
| the read-only audit of a home's hub lock for the three-string agreement (lock key == `install_path` last segment == the skill's own name) | `maintain-hermes-skill-cards` → `scripts/check-lock-alignment.py` |
| re-seeding bundled skills that were pruned or deleted from a home | `update-hermes-skills` → `scripts/restore_builtin_skills.py` |

What stays here:

- `references/maintain-hermes-profile-prompt-assembly-and-guidance-gates.md` — how the system prompt is assembled layer by layer
  (SOUL.md identity slot, memory, skill index, context files, model-gated guidance blocks), the
  `_model_gate` semantics for `agent.execution_guidance` / `agent.tool_use_enforcement`, and the probe that
  prints whether a given model's session receives the `# Execution discipline` block.
- `references/maintain-hermes-profile-skills-tree-layout.md` — concrete on-disk layout of the skills tree and the
  probe snippets (name→path mapping, two-method delete verification, config-leaf diff,
  throwaway `HERMES_HOME` write probe, removal-persistence probe).

## Skill Structure

<!-- Generated by Scripts -->

```
maintain-hermes-profile/
├── SKILL.md  (816 lines)
└── references/
    ├── maintain-hermes-profile-prompt-assembly-and-guidance-gates.md  (81 lines)
    └── maintain-hermes-profile-skills-tree-layout.md  (296 lines)
```

<!-- Generated by Scripts -->
