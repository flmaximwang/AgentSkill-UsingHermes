# Hub-skill diagnosis: error text → cause → fix

Depth for `install-hermes-skills`. Every entry was measured against a throwaway `HERMES_HOME` unless a
line says otherwise, and the error strings are verbatim CLI output. The install procedure it was
written next to is `SKILL.md`'s "The commands"; the maintenance loop (check / update / audit /
uninstall) is `update-hermes-skills/SKILL.md`.

Merged 2026-09-30 from the standalone `hermes-skills-hub-operations` skill, which was retired into
its four siblings.

## Verifying an install you just ran

   wants several skills under one heading — that flag is the only grouping lever (see the category
   pitfall).
4. **Verify in the target home, payload included.** `hermes skills list` plus a real file listing —
   confirm the expected support files exist, not just `SKILL.md`. Then check completeness properly:
   pull every path the installed `SKILL.md` references and confirm each exists on disk. A registry
   package can ship a body whose referenced files were never published (measured: 6 of 18 referenced
   paths missing, all `templates/*.template`, while `methodology/` and `extractors/` were complete).
   Report that gap as the install's state — an incomplete fork is not a clean install, and it is the
   missing files the user will hit first.

## Procedure — reconstruct how a skill got installed

"我是怎么装这个 skill 的" / "when and from where was this installed" / "why did it need `--force`?" —
read the record; never infer it from the display columns. All of it is read-only:

1. ``scripts/lock-provenance.py` <name>` (interpreter note in its docstring) prints the lock entry
   (`source`, `identifier`, `trust_level`, `scan_verdict`, `installed_at`, pinned
   `metadata.source_revision`), the recorded vs on-disk `content_hash`, and whether `update` would
   skip it as locally edited.
2. `skills/.hub/audit.log` is the timeline: one line per hub action,
   `<ISO-8601>Z <VERB> <name> <source>:<trust> <verdict> sha256:<hash>`, verbs `INSTALL` /
   `UNINSTALL` / `BLOCKED` (a `BLOCKED` line carries the reason where the hash would be). The lock
   holds current state, the log holds the sequence — quote both when the user asks about one install.
3. Separate **fact** from **reconstruction** in the answer. Neither file records the argv, so the
   command must be rebuilt from the identifier's shape against the route table — a three-part
   `owner/repo/path` is claimed by the skills.sh adapter, so it was the
   `install <owner>/<repo>/<path> [--category <c>] [--force] -y` route. Say the shape is what fixes
   the command; do not present the rebuilt command as something that was logged.
4. `hermes skills list --source all` adds the display columns (parent = `skills.sh`/`community`,
   nested children = `local`/`local`). Those are *labels*, not provenance — `local` means "no lock
   entry of its own", which a nested child of an upstream bundle also is.

## Diagnosis table (error → cause → fix)

| Error / symptom | Cause | Fix |
|---|---|---|
| `Fetching: <owner>/<repo>/<a>/<b>` then `Could not download '<arg>'` — *and* `inspect <same arg>` prints `Could not find '<arg>' in any source.` | The shape is legal: `_split_repo_id` keeps everything after the second `/` as the path, so a 4-segment argument clears the segment check and the failure is upstream — the **owner or repo in the argument does not exist**, so every source 404s. The message blames the network instead of the name | Verify the name against GitHub before touching anything else: `curl -s -o /dev/null -w '%{http_code}' https://github.com/<owner>/<repo>` (and `raw.githubusercontent.com/<owner>/<repo>/HEAD/<path>/SKILL.md`). Measured: `anthropic/skills` → 404 vs `anthropics/skills` → 200 — the one-letter owner typo in `anthropic/skills/skills/skill-creator` gave exactly this error, while `anthropics/skills/skills/skill-creator` installed 18 files unattended |
| `Fetching: <arg>` then `Could not download '<arg>'` (generic; advises `hermes doctor`) | Two different causes share this one message: a raw URL short of 4 segments, **or an argument with fewer than 3 segments** (`owner/repo` reaches no adapter at all — every source returns `None`, nothing is requested, and the message never mentions the argument's shape) | Re-check the argument before the network: for `owner/repo`, `inspect` the same string — it prints `Could not find … in any source.` for the same fact, which is what tells the two apart; for a URL, count the segments and confirm with `curl -s -o /dev/null -w '%{http_code}' <url>` |
| `Error: '<id>' is listed in the hermes-index index, but its files no longer exist upstream.` (advice: run `search` for an alternative) | The registry built the third segment from the skill's **name**, not from a path that exists — entries of the shape `<repo>/<skill-name>` appear for repos whose tree has no such directory (one repo carried two entries, an older name and its current one, neither resolvable) | Rebuild the identifier from the repo tree (`gh api … endswith("SKILL.md")`, see ``references/install-hermes-skills-repo-structure-routing.md``) or use the raw URL of the root `SKILL.md`; a local index-cache wipe and the suggested `search` both change nothing |
| `inspect <id>` shows the metadata panel but **no `SKILL.md Preview`**, and the install then prints that stale-index mistake even though the files exist | Same fact one layer earlier: the meta came from an **index** adapter (measured: `hermes-index`) while every *fetching* adapter returned `None`, because the identifier's third segment is the skill's **name**, not an in-repo directory — the root skill of a repo that also ships other top-level content dirs has no working identifier | Rebuild the identifier from the repo tree (``references/install-hermes-skills-repo-structure-routing.md``, type 4); when no such directory exists, the trailing-slash whole-repo form is the only one that resolves — scan its payload first, since it can be a permanently blocked `dangerous` |
| `inspect <owner>/<repo>/<path>` prints `Could not find … in any source.`, yet `install` with the SAME identifier succeeds | `do_inspect` aborts on `meta is None` even when a bundle fetched fine: `_resolve_source_meta_and_bundle` returns `(None, bundle, src)` whenever the winning source implements `fetch` but its `inspect` returns `None`. Measured on a private repo: `GitHubSource.inspect` → `None` while `GitHubSource.fetch` → 5 files; the winning source is `skills.sh`, which only relabels the GitHub bytes. The usual trigger is an **empty (or whitespace-only) `SKILL.md`**: `inspect` does `content = self._fetch_file_content(repo, _skill_file_path(skill_path))` then `if not content: return None` (`tools/skills_hub_github.py:361-368`), while `fetch` never reads the body — measured on `flmaximwang/AgentSkill-UsingHermes/skills/remove-hermes-skills` at revision `5798d4d`, a committed 0-byte placeholder whose 5 files all install as 0 bytes | Do not read `inspect`'s verdict as "does not exist" — run `install`; the bundle, not the meta, is what install consumes. Then confirm the payload is not empty (`ls -l` the installed tree — a matching file list says nothing about sizes). Confirm the bytes independently with `GitHubSource(auth).fetch(ident)` under `~/.hermes/hermes-agent/venv/bin/python` |
| `Installation blocked: Unsafe skill name: .` | The identifier's third segment was `.` to mean "repo root" | Use a trailing slash instead: `owner/repo/` |
| `Could not find '<owner>/<repo>' in any source.` | Fewer than 3 identifier segments — the source router needs a path | Add the in-repo path, or use the raw URL |
| `Could not find '<owner>/<repo>/…/SKILL.md' in any source.` | The third segment carries the file name: `_split_repo_id` keeps everything after the second `/` as the path, and `_skill_file_path` then appends `/SKILL.md`, so it looks for a directory literally named `SKILL.md` | Drop the trailing `/SKILL.md` — the third segment is the containing **directory** |
| `Decision: BLOCKED — Blocked (community source + caution verdict, N findings)` | community + caution policy | Re-run with `--force` **after** reading the findings; a `dangerous` verdict is never overridable |
| `Warning: '<name>' is already installed at <path>` | Re-install attempt **or an orphaned lock entry** — the recorded directory was deleted by hand while `lock.json` kept the entry, so `install` refuses on the stale record | Prefer `hermes skills uninstall <name> -y` then `install` again: it still succeeds with the directory missing and clears the entry (`Uninstalled '<name>' from <path>`), which keeps the lock consistent; `--force` also installs but leaves the two-step history implicit |
| `Error: '<name>' is not a hub-installed skill (may be a builtin)` | The directory was copied in by hand; it has no lock entry | Hub commands cannot manage it — `rm -rf` the directory, or reinstall via a registry |
| `hermes skills check <name>` → `No hub-installed skills to check.` for a skill the user can see in `list` | It has no `lock.json` entry: hand-copied, a nested child of a bundle, or installed by an **external installer** — the npm `skills` CLI keeps its own record in `~/.agents/.skill-lock.json` | The hub will never refresh it. Update it with the installer that made it (`npx skills update -g -y`) or reinstall by identifier for hub tracking; `local`/`local` in `list` is the matching display symptom |
| `No skills found matching your query.` for a repo you just added with `tap add` | Unfiltered `search` never queries GitHub while the central index is up, and `--source github` spends its 30 s deadline walking ~25 taps, so a tap appended last is rarely reached; an empty result list also suppresses the `⚡ Slow sources skipped` hint | Do not search for it — install by `owner/repo/path/to/skill-dir` (see the tap-visibility pitfall) |
| `⚡ Slow sources skipped: <source>` | Only ever printed next to a non-empty result list: the enumerating source finished after the deadline | Run it a second time (cached), or set `GITHUB_TOKEN` / have `gh` logged in |
| `hermes skills list` shows a registry-installed skill as `local` / `local` | Lock key ≠ the skill's frontmatter `name:` — the skill index keys on the `SKILL.md` name, so the hub row never matches | Align the **lock to the SKILL.md name** (lock key == `install_path` last segment == directory name), backing up `lock.json` first; never rename the SKILL.md, an update overwrites it |
| `check` → `unavailable`, or `Blocked request to private/internal address: <host> -> <ip>`, or `Could not find 'https://…/SKILL.md' in any source.` right after an install that worked in a sandbox | One cause behind all three messages: a `Source: url` entry is always re-fetched through the URL adapter's SSRF-guarded GET, which resolves the host and refuses private/benchmark answers, and the CLI collapses that block into whichever message its call path uses — the host's DNS answer is the real problem, never a missing skill. `198.18.0.0/15` (IPv4) and `2001:2::/48` (IPv6) are the TUN/fake-IP blocks, and the guard inspects **every** answer, so a host with an AAAA record stays blocked until the IPv6 block is declared too | Confirm the URL itself answers (`curl -s -o /dev/null -w '%{http_code} %{remote_ip}' <url>`) then declare **every** range the host is answered with — IPv4 *and* IPv6, e.g. `198.18.0.0/15` + `2001:2::/48` — in `security.fake_ip_ranges` (probe it in a throwaway home first), or reinstall that skill by identifier. Never disable the guard wholesale |

## Pitfalls

- **A short name resolves on the skill's `name`, so the identifier a registry package answers to on the
  CLI is not always the one you read off its page.** Measured: the ClawHub package whose slug is
  `cangjie-skill` carries the display name `Cangjie Skill`, so typing `cangjie-skill` never reaches it —
  `_resolve_short_name` name-matches the *skills.sh* row (`name: cangjie-skill`) first and the clawhub
  slug loses, while `install "Cangjie Skill"` resolves to the clawhub bundle (`@<publisher>/cangjie-skill`,
  21 files). Same family, two lineages: read the bundle's own `SKILL.md` frontmatter before believing it is
  the repo's skill, and when slug and frontmatter `name` disagree the directory lands under the slug while
  the index keys on the frontmatter name (`local`/`local` in `list`).
- **A private repo is installable, and the anonymous probes lie.** `curl https://github.com/<o>/<r>` and the unauthenticated contents API answer **404** while `gh api repos/<o>/<r> --jq '{private,pushed_at}'` shows `private: true`. The `github`/`skills.sh` adapters take the token from the profile secrets (`get_secret("GITHUB_TOKEN")` / `GH_TOKEN`, then `gh auth token`) — no env export needed; verify presence with `GitHubAuth().auth_method()` (`pat` = a PAT is stored). A three-part identifier therefore resolves for a private repo just like a public one, tap or no tap.
- **Never hand `install` a `github.com/.../blob/...` page URL.** Any URL whose path ends in `.md`
  is claimed by the URL adapter, so the HTML page is downloaded as if it were the skill, scores
  `dangerous`, and installs nothing — `--force` cannot override a dangerous verdict. Use
  `raw.githubusercontent.com`.
- **A tap does not make a self-authored repo searchable.** Without `--source`, `search` never asks
  GitHub at all: `_select_active_sources` drops the API sources (`github`, `skills-sh`, `clawhub`,
  `lobehub`, `well-known`) whenever the central index is available, and the index-miss fallback set is
  those ids **minus `github`** (a miss is too likely to be a typo to spend the user's hourly GitHub
  budget on). With `--source github` the source walks every tap sequentially, one contents call per
  repo, against the search's 30 s deadline, so a tap appended at the end is the first casualty — and
  because the empty-result path returns before the `⚡ Slow sources skipped` line prints, the whole
  failure surfaces as a bare "No skills found". Install by three-part identifier instead; it resolves
  for a repo no registry lists. Keep a tap only when the user also wants the repo in `browse`.
- **A tap cannot group skills into a category; `--category` is the only lever.** `tap add` stores
  only `{"repo","path"}` and a hand-written `"bucket"` in `taps.json` reaches
  `meta.extra["category"]` on search hits, where no code in the tree reads it — install placement is
  untouched (measured: `"bucket": "obsidian-notes"` set, no `--category` → still flat in
  `skills/<name>/`; same command with `--category obsidian-notes` → `skills/obsidian-notes/<name>/`).
  Pass `--category <cat>` per install, nesting allowed (`--category a/b` → `skills/a/b/<name>/`); the
  skill index derives each skill's category from that first directory component, so it is what puts
  several skills under one heading in the agent's list. Batch it:
  `for s in <skill1> <skill2>; do hermes skills install <owner>/<repo>/skills/$s --category <cat> -y; done`
- **The URL route ships only `SKILL.md` plus the files its body *directly* references under
  `references/ templates/ scripts/ assets/ examples/`, and it never follows a second hop.** Only the
  `SKILL.md` text is parsed — a fetched support file that names further files is not re-read, so a
  layered skill installs as a shell whose links dangle (measured: one support file naming three more
  files caused zero further requests). A support file that 404s is a warning, not a failure, so the
  install still reports success with the file missing — list the installed files before saying it
  worked. Path *depth* is unlimited (a path several directories deep under a support dir is fetched);
  only the number of hops is
  one, so the remedy is a flat manifest (every level's files named in the body) or the whole-directory
  route. A body that links `methodology/`, `docs/`, `extractors/` is out of scope for this route
  entirely. Syntax and the CJK-separator trap: ``references/install-hermes-skills-registry-routes.md`` § URL route. If the
  whole directory is blocked on repo infrastructure, fix the block with the `.skillignore` lever
  (``references/install-hermes-skills-registry-routes.md`` § Scan policy). A hand copy is a last resort for a private repo or
  a deliberate subset, and it forfeits lock tracking.
- **What `skill_view` lists is narrower than what got installed.** `references/` is listed one level
  deep and `*.md` only, `scripts/` likewise, while `templates/` and `assets/` are listed recursively;
  nothing outside `{references, templates, assets, scripts}` is listed at all. A file under
  `references/<sub>/…` is still readable by explicit path (and a wrong path returns the full recursive
  listing), which is how progressive disclosure is meant to work: top-level `references/*.md` as
  entry points, each naming the next level inside its own body. Author or recommend layouts that way,
  and put bulk data under `templates/`/`assets/` when it should appear in the first listing — table
  and read-path rules: ``references/install-hermes-skills-registry-routes.md`` § Runtime surface.
- **The identifier route downloads the FULL skill directory**, and for the repo-root layout
  (`owner/repo/`) "the directory" is the entire repo — a large monorepo becomes a huge skill and
  trips the file-count/size findings. Fix the cause rather than shipping a subset: a `.skillignore`
  in the repo changes the verdict (not the payload) and a narrow in-repo directory layout fixes both,
  either of which keeps the install lock-tracked; a hand copy of the wanted subdirectories loses
  `check`/`update`.
- **A repo whose root holds `SKILL.md` *and* nested `SKILL.md`s (main skill + `examples/`) has no
  identifier for its main skill.** The trailing-slash form is only offered when the whole tree holds
  **exactly one** `SKILL.md` (`_find_repo_root_skill` guards on `skill_mds == ["SKILL.md"]`), and any
  tree link or three-part identifier you can build points at a *child* skill instead. Measured on such
  a repo (212 tree entries, 38.6 MB): raw URL of the root `SKILL.md` → 3 files / 52 KB; trailing slash
  → 93–117 s of fetch+scan, whole repo (156 files / 33.69 MB) and `BLOCKED` on 29 findings — including
  a HIGH `exfiltration` in the repo's own `.github/scripts/`. Two consequences worth stating to the
  user: the scan is judging the repo's **infrastructure** files, not the skill, and `.github/foo.py`
  `is` bundled because the dotfile skip tests the basename, not any path component.
- **A registry/website identifier whose third segment is the skill's NAME is not a path, and the
  root skill of a repo that also ships other top-level content dirs has NO working identifier.**
  Measured on `kangarooking/cangjie-skill` (367 blobs / 6.86 MB; root `SKILL.md` + 35 nested ones
  under `books/ benchmarks/ dist/`): the id every registry hands out, `…/cangjie-skill/cangjie-skill`,
  makes the adapter try `cangjie-skill/`, `skills/cangjie-skill/`, `.agents/skills/cangjie-skill/`,
  `.claude/skills/cangjie-skill/` (all 404 — the segment is the *name*) and `_discover_identifier`
  finds no `…/cangjie-skill/SKILL.md`; `_find_repo_root_skill` refuses because it needs the WHOLE tree
  to hold exactly one `SKILL.md`. So the trailing-slash form is the only one that resolves — and it
  drags the entire repo, whose own dev files then decide the verdict: that bundle scanned **DANGEROUS**
  (18 findings, one CRITICAL `traversal` at `tests/test_compile_resources.py:66`) → BLOCKED, and
  `--force` cannot override it, so the whole-repo route is permanently dead. The raw URL of the root
  `SKILL.md` installs (4 files, `safe`) but ships a **stub**: support files come only from
  `references/ templates/ scripts/ assets/ examples/`, so a body whose pipeline hangs on `methodology/`,
  `extractors/`, `schemas/` loses them **silently**. When the payload is spread over top-level dirs the
  fix belongs upstream — measured: a `.skillignore` (`tests/ benchmarks/ books/ dist/ website/ registry/
  docs/ assets/`) flips that same 366-file bundle DANGEROUS → `safe` (12 medium), and moving the 51
  files / 0.23 MB that are the actual skill into one directory scans `safe` too. Say which of those is
  needed and ask before shipping anything hand-assembled.
- **Predict an install's verdict WITHOUT installing — that is how "where can this succeed?" gets
  answered.** Assemble the exact bundle the route would download (for the identifier/trailing-slash
  route: the GitHub **tree API** filtered by `_skip_bundle_file`, which tests the basename only — so
  `.github/` ships and `.git/` never appears in a tree answer; a `git clone` copy is wrong on both
  counts) and run `tools.skills_guard.scan_skill(bundle_dir, source="skills.sh")` on it: needs no
  Hermes state, and `ScanResult.verdict` + `Finding.severity/.category` match the quarantine scan.
  Use it to decide which route is worth *trying*, never as a substitute for the attempt: when the user
  asks where an install succeeds, run the route in the mirrored sandbox and quote the real output
  (verdict, error text, file list). A modelled verdict is not an answer to "did it actually install?"
- **`inspect` printing a metadata panel with NO `SKILL.md Preview` means no adapter could fetch the
  bundle** — `_resolve_source_meta_and_bundle` falls back to the first meta-only hit, so the panel can
  come from an index adapter while `skills-sh`, `well-known`, `url`, `github` and `clawhub` all return
  `None`. Always read a healthy identifier as the control (`hermes skills inspect
  anthropics/skills/skills/pdf` prints the preview). The install that follows reports the stale-index
  error, i.e. misnames a routing problem as a removed skill.
- **Hub modules import only under `~/.hermes/hermes-agent/venv/bin/python`** (that venv has `httpx`;
  the launcher's runtime python at `~/.hermes/tools/python-3.14*/` does not). `tools/skills_guard`
  imports under either.
- **Do not confirm a repo-only claim from the `search` table.** A query for the repo's name can return
  a page of same-named packages from another registry (community forks on `clawhub`) while the repo
  itself is unreachable by search — installing the top hit then installs somebody else's skill. Match
  the identifier's owner/repo against the repo the user named before trusting a row.
- **The argument's shape decides which adapter claims it — and `Source: skills.sh` is a label over
  GitHub bytes, not evidence the skill is listed on skills.sh.** Routing is
  `official → hermes-index → skills.sh → well-known → url → github(taps) → …` and the first
  `fetch()` that returns a bundle wins: a three-part `owner/repo/path` is claimed by the skills.sh
  adapter, which resolves the bytes through the GitHub adapter and then rewrites
  `source`/`identifier` while merging a string-built `detail_url`/`repo_url` **on top of** GitHub's
  own `source_url`/`source_revision`; a bare `…/SKILL.md` URL only satisfies the url adapter's
  `_matches`. An arbitrary GitHub repo therefore usually lands on `skills.sh` as `community` — which
  is why an `--force` is so often needed, and why a self-authored repo can carry that label while its
  skills.sh pages 404. **For real provenance read `metadata.source_url` + `source_revision` in
  `lock.json`, never `source`.** Never promise a `--force`-free install without an `inspect` first.
- **`check` and local edits are two different judgements.** `check` compares the install-time
  hash against upstream (your edits are invisible to it); `update` alone compares on-disk
  content and skips locally edited skills. Rewriting the lock's `source_revision` does not make
  `check` report an update — the content hash is the criterion.
- **A `url`-sourced skill can report `unavailable` forever while its URL is perfectly healthy.**
  Each lock entry is re-fetched only from adapters matching its recorded `source`, and only
  `GitHubSource` implements `current_revision`, so a `url` entry always takes the full-download path
  — through the SSRF-guarded HTTP route that the github/skills.sh adapters do not use. Behind a
  TUN/fake-IP proxy (local DNS answering inside `198.18.0.0/15`) the guard reads that answer as a
  private address and blocks, while `curl` to the same URL returns 200. Diagnose with
  `curl -s -o /dev/null -w '%{http_code} %{remote_ip}'`; fix by declaring the proxy's block
  (`security.fake_ip_ranges` — declare *every* range the proxy answers with, IPv4 and IPv6 alike;
  declaring one family leaves the other block live and the symptom unchanged, see the reference) or
  by installing that skill by identifier.
- **Reinstalling under a different `--category` leaves the previous directory behind**: `list`
  shows one row, the disk holds two, and the skill scanner dedupes by name so the orphan is
  invisible everywhere. `rm -rf` it by hand.
- **`hermes skills check` cannot detect a lock-key/frontmatter name disagreement**: it resolves the
  directory from `install_path`, which is still consistent, so it reports `up_to_date`. Detect it by
  comparing the lock key against the on-disk `SKILL.md` `name:` (or by the `local` mislabel in
  `hermes skills list`) — asking `check` will tell you it is fine.
- **One install can bring in several skills**: nested directories carrying their own `SKILL.md`
  are indexed separately (parent = 1 hub entry, children = `local` rows). `uninstall <parent>`
  removes the whole tree; updating the parent refreshes all of them.
- **Never author your own skill *inside* an installed bundle.** A self-authored child directory (or
  any edit under the bundle) changes the bundle's content hash, so `_has_local_edits()` turns true
  and **every later `update <parent>` is skipped** as `you have local edits` — and `--force`, being a
  full directory replace, deletes the addition. `check` stays blind to all of it and keeps reporting
  `up_to_date` (it compares the install-time hash against upstream, not against disk). Measured on an
  installed bundle after adding one child skill dir: recorded `sha256:c20a6094…` vs on-disk
  `sha256:a402940d…`, `local_edits True`, `check` → `up_to_date`. Put self-authored skills in their
  own top-level directory (`--category <cat>`) and, if one already sits inside a bundle, offer to move
  it out rather than leaving the bundle un-updatable.
