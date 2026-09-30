# Registry routes, maintenance behaviour, and on-disk state

Depth for `install-hermes-skills`. Everything here was exercised against a throwaway
`HERMES_HOME`; numbers are what the commands actually printed.

## The ways a skill gets installed

| Route | Command shape | What you get | Editable by hub commands |
|---|---|---|---|
| A raw URL | `hermes skills install "https://raw.githubusercontent.com/<o>/<r>/<ref>/<path>/SKILL.md" -y` | `SKILL.md` + files the body references under `references/ templates/ scripts/ assets/` | yes (`source: url`) |
| B identifier | `hermes skills install <owner>/<repo>/<path/to/skill-dir> [--category <c>] [--force] -y` | the whole skill directory, pinned to a commit | yes |
| C tap + B | `hermes skills tap add <owner>/<repo>` then B | same as B; the tap only makes the repo appear in `search`/`browse` | yes |
| D manual copy | `cp -R <clone>/<skill-dir> <HERMES_HOME>/skills/[<cat>/]<name>` | the directory as-is | **no** — hub commands do not see it |
| E registry | `hermes skills install "@<publisher>/<slug>" -y` | the registry's packaged copy plus a `_meta.json` next to `SKILL.md` | yes (`source: clawhub`) |
| F npm `skills` CLI | `npx -y skills@<ver> add <owner>/<repo> -a hermes-agent -g -y` | the whole skill directory (copy or symlink) into `<HERMES_HOME>/skills/<name>`, recorded in the installer's own lock `~/.agents/.skill-lock.json` | **no** — no hub entry is written; refreshed by `npx skills update -g` |

B and C share one command; the difference is only whether the repo was registered as a tap.
A URL install lands flat (`skills/<name>/`); `--category <c>` nests it (`skills/<c>/<name>/`).

Route F is a separate ecosystem: its own store (`~/.agents/skills/<name>`), its own lock
(`~/.agents/.skill-lock.json`, per-skill `source` / `sourceType` / `skillPath` / `skillFolderHash` =
commit SHA) and its own updater. Hermes is a first-class target there, but its target **home** comes
from `HERMES_HOME`, so sandboxing with `HOME` alone writes into the real profile — commands, lock
schema and the trap: `install-hermes-skills-from-npx.md`.

### URL route — exactly what gets fetched

`UrlSource.fetch()` reads the **`SKILL.md` body only**, extracts candidate paths, fetches each one
once, and returns. Nothing it fetches is re-parsed, so the route is **one level deep** — there is no
transitive follow. Measured with a controlled fixture (fake host + patched `_fetch_text`/`_fetch_bytes`,
request log):

```
SKILL.md names        → requests: SKILL.md, EXTRA.md, references/a.md, scripts/x.py   (level 1 only)
references/a.md and EXTRA.md each name
references/b.md, scripts/y.py, extractors/c.md  → never requested, though all three exist upstream
bundle.files = [EXTRA.md, SKILL.md, references/a.md]   (scripts/x.py 404ed → skipped, install continued)
```

Rules that follow from that one loop:

- **Top-level allowlist** — `_ALLOWED_SUPPORT_DIRS = {references, templates, scripts, assets,
  examples}`; a reference whose first segment is anything else (`methodology/…`, `extractors/…`) is
  dropped with no warning. (`examples` is fetch-side only — the runtime list does not carry it.)
- **Depth is unlimited** — `references/a/b/c.md` and `assets/img/a.png` are extracted and fetched;
  only the number of hops is capped at one.
- **Extraction syntax** (`_LOCAL_LINK_RE`) — a path counts when preceded by `](`, a backtick, or
  whitespace/quote/line start. Same-directory siblings count only as markdown links
  (`](./FILE.ext)` / `](FILE.ext)`); a bare `EXTRA.md` in prose is not extracted.
- **CJK separators silently kill the pair** — `references/a.md、scripts/x.py` is captured as one
  candidate, and when the final segment no longer ends in an ASCII alphanumeric the candidate is
  discarded: measured, **zero** files fetched from such a body. Author skills for Chinese readers
  with backticks, links, or newlines between paths.
- **A missing support file is a warning, not an error** — `referenced support file … could not be
  fetched … skipping it`, install completes; hence the standing rule to verify the file list.
- **Cross-host and traversal are fatal** — a reference resolving to a different netloc returns `None`
  for the whole bundle, as does a `../` path (fail-closed in `_referenced_support_paths`).

So: this route suits a single-entry skill whose support files are all named in `SKILL.md`. For a
layered skill, either list every level in the body (a flat manifest that the model never reads as a
manifest — it still discloses one level at a time) or install the whole directory.

### Category placement — the only grouping lever

An install's category comes from exactly three places: `--category` (every route), the identifier's
middle segments for `official`, and an interactive prompt for the URL route on a TTY. Nothing else
moves the directory.

- **A tap carries no category.** `TapsManager.add()` writes only `{"repo","path"}` (there is no
  `--bucket`/`--category` flag) and `tap list` prints only `Repo | Path`. A hand-edited
  `"bucket": "<cat>"` in `taps.json` ends up as `meta.extra["category"]` on the listed skill and stops
  there — no consumer exists anywhere in `tools/`, `hermes_cli/`, `agent/`, `gateway/`, `tui_gateway/`.
  Measured: with `"bucket": "obsidian-notes"` and no `--category`, `skill-creator` still installed to
  `skills/skill-creator/`; the identical command plus `--category obsidian-notes` produced
  `skills/obsidian-notes/skill-creator/`.
- **`--category` nests**: `--category a/b` → `skills/a/b/<name>/`.
- The agent's skill list groups by that directory component, so `--category <cat>` is the only way to
  make several skills share one heading. When a user picks a tap for that reason, correct the premise
  and install per skill with `--category`.

## Identifier discovery

- `hermes skills search <keyword>` — table columns `Name / Description / Source / Trust / Identifier`.
  The identifier column **wraps and truncates**; add `--json` for the full string. The prefix
  (`skills-sh/`) is accepted on input and stripped. Search is fuzzy: read the Name column, not
  the ranking. `--source X` narrows only the *extra* sources queried — `official` always rides along.
- `https://skills.sh/<owner>/<repo>/<skill>` — the site path is the identifier; its homepage
  lists a featured subset, the full catalogue is in its sitemap.
- Repo tree (works for private/new repos, needs no registry):
  `gh api "repos/<o>/<r>/git/trees/HEAD?recursive=1" --jq '.tree[].path | select(endswith("SKILL.md"))'`.
  Strip the trailing `/SKILL.md` from each hit to get the third segment.
- `inspect` takes **only** the identifier — no `--json`, `--source` or `--limit`.

## Search visibility — why a tap does not make a repo findable

`tap add` registers a repo for `search`/`browse` only; it changes nothing about `install`. And for a
self-authored repo that visibility does not materialize:

- **Without `--source`, GitHub is never queried.** `_select_active_sources` drops every id in
  `_API_SOURCE_IDS = {github, skills-sh, clawhub, lobehub, well-known}` as soon as the central index
  is available (the index stands in for them), and the index-miss fallback set is those ids **minus
  `github`** — a miss is far likelier to be a typo than a real skill, and an unauthenticated GitHub
  miss burns the hourly budget. A private/personal repo is not in the index, so no unfiltered
  `search` will ever list it.
- **With `--source github` the enumeration must fit the deadline.** The source walks every tap
  sequentially, one contents call per repo (~25 with one user tap, the user's appended last),
  against the search's `overall_timeout = 30 s`. Measured: that same walk standalone ran past 420 s.
  A tap appended at the end of the list is the first casualty.
- **An empty result list hides the diagnosis.** `do_search` prints `No skills found matching your
  query.` and returns *before* the `⚡ Slow sources skipped: <ids>` line is reached, so a budget cut
  is indistinguishable from "that skill does not exist". Do not read an empty search as evidence.
- **`--source <id>` vs `--source <provider>`**: `openai` / `anthropic` / `nvidia` / `huggingface` /
  `voltagent` / `gstack` / `minimax` (the values of `GITHUB_TAP_PROVIDERS`) filter by provider and
  switch the index off; `github` is not among them, so it stays a genuine source filter.

Working route for anything self-authored: the three-part identifier. `inspect <owner>/<repo>/<path>`
resolves even when no registry lists the repo, because the `skills.sh` adapter's `_discover_identifier`
falls back to enumerating the repo through the GitHub source and re-labels the bundle `skills-sh/…`.

## ClawHub (third-party registry)

- Identifier `@<publisher>/<slug>`; install from that string, never from a search hit.
- **Every ClawHub skill is `community` by construction** — the adapter hard-codes it, on the stated
  grounds that the marketplace's own vetting is insufficient (its docstring cites a mass
  malicious-skill incident). Treat a ClawHub install as untrusted until scanned.
- **`search --source clawhub` is normally empty**: the catalogue walk is bounded to 12 s over a very
  large catalogue. Take the identifier from wherever the user saw it, and `inspect` first.
- An ambiguous slug (same slug, several publishers) is answered with `409 AMBIGUOUS_SKILL_SLUG`; the
  adapter disambiguates with `?owner=`. The `@publisher` part is load-bearing, not decoration.
- Download cap: 25 MB zip.
- The installed directory carries `_meta.json` (`ownerId`, `slug`, `version`, `publishedAt`) and the
  lock entry records `source: clawhub`. That publisher is frequently **not** the upstream author: the
  same slug can carry a rewritten fork (different `name:`/version lineage and file inventory). Compare
  the frontmatter before calling two packages the same skill.

### Popularity and recency signals, per source

Read these **before** choosing which bloodline to install — the ranking and the installability are
independent facts, and the popular one can be the un-installable one.

| source | popularity | recency |
|---|---|---|
| skills.sh detail page | `Installs <n>` (scraped by `_WEEKLY_INSTALLS_RE`), `GitHub Stars <n>` | `First Seen <date>`; the bundle's frontmatter `version:` |
| the GitHub repo behind it | `gh api repos/<o>/<r> --jq .stargazers_count` | `--jq .pushed_at` (with `.archived`, `.created_at`) |
| ClawHub | `GET https://clawhub.ai/api/v1/skills/<slug>` → `.skill.stats.installs` / `.downloads` / `.stars` | `.skill.stats.versions`, `.skill.updatedAt` (epoch ms, same value as `_meta.json.publishedAt`), `.latestVersion.version` |
| any package's own `SKILL.md` | — | `version:` + `author:` — the bloodline check, not a popularity signal |

The same endpoint also exposes `.owner.handle` (the `@publisher` part of the identifier),
`.moderation.verdict` / `.isSuspicious` / `.isMalwareBlocked`, and `.skill.createdAt`. Two live
packages of one name measured ~10.8K stars with a push days old and a 2.5.0 body against 15 installs,
1.0.0, untouched for months — and the second one is the one that installed while the first could not
be installed by any Hermes route. Report both columns; do not let installability silently decide
which bloodline the user gets.

## Resolution order (why the same shape hits different sources)

```
official → hermes-index → skills.sh → well-known → url → github(taps) → clawhub → lobehub → browse-sh
```

Consequences: an arbitrary GitHub repo normally resolves through `skills.sh` (which supplies
discovery + metadata and fetches the bytes from the underlying GitHub repo, pinned to a commit
tree URL), which in turn makes it `community` — so `community + caution = blocked` is the norm
on that route, not an exception. A repo that is in `TRUSTED_REPOS` resolves through `github` as
`trusted` and its caution verdict passes. `_split_repo_id` requires **≥3 segments**; two segments
report `Could not find … in any source.`

## Provenance — what `Source:` and `metadata` actually record

- The skills.sh adapter is a **front end for GitHub**, not an independent registry: its `fetch()`
  calls the GitHub adapter and then rewrites the bundle (`source = "skills.sh"`,
  `identifier = "skills-sh/<canonical>"`) and merges `detail_url`/`repo_url` **on top of** the GitHub
  bundle's own `source_url`/`source_revision` (update adds, it never replaces). Its own detail page
  is optional: measured on a repo skills.sh does not list, the detail page, the API path and the
  repo page all returned **404** while the install still reported `Source: skills.sh`.
- Field ownership in `lock.json`:

| Field | Written by | Meaning |
|---|---|---|
| `metadata.source_url` | GitHub adapter | commit-pinned tree URL of what was downloaded — the real provenance |
| `metadata.source_revision` | GitHub adapter | the commit the bundle is pinned to |
| `metadata.detail_url` | skills.sh adapter (string-built, no request) | `https://skills.sh/<canonical>` — says nothing about whether the skill is listed |
| `metadata.repo_url` | skills.sh adapter | `https://github.com/<owner>/<repo>` |
| `metadata.url` / `source_url` (url route) | url adapter | the URL that was passed, and nothing more |
| `metadata.awaiting_name` | url adapter | frontmatter carried no usable `name:` |

- The claim is decided by the **shape of the argument**, not by a flag: `owner/repo/path` is taken by
  skills.sh (third in the router, ahead of the tap-backed github source), a bare
  `http(s)://…/SKILL.md` only satisfies the url adapter's `_matches`. The same skill installed the
  two ways lands with a different `source`, different `metadata` and a different file set.
- `hermes skills install` exposes only `--category`, `--name`, `--force`, `--yes` — there is **no**
  `--source`, so provenance cannot be pinned from the CLI (`do_install(source_id=…)` exists but only
  `do_update` passes it). If the label matters, the lever is the identifier's form.

## Diagnosing which route an identifier will take

Probe the router in-process instead of guessing — read-only, no install, and the same code path
`install`/`inspect` use:

```python
from tools.skills_hub_search import create_source_router
from tools.skills_hub_github import GitHubAuth
for src in create_source_router(auth=GitHubAuth()):
    b = src.fetch("<identifier>")
    if b:
        print(src.source_id(), "CLAIMED", b.source, b.identifier, list(b.files), b.metadata)
        break
    print(src.source_id(), "-> None")
```

Import `GitHubAuth` from `tools.skills_hub_github` (the old `tools.skills_hub` path emits a
plugin-compat warning). A three-part identifier is claimed by position 3; a bare URL reaches
position 5 at the latest, so the walk stays cheap.

## Fake-IP proxies (TUN / Clash / Mihomo style) and the URL source

- Symptom: install/`check`/`update` for a **url**-sourced skill fails with
  `Blocked request to private/internal address: <host> -> <ip>` plus
  `Blocked unsafe Skills Hub URL: <url>`, while `curl` to that same URL returns 200 (curl just dials
  the address the local proxy owns).
- Cause: the proxy answers DNS inside `198.18.0.0/15` (the benchmark range Mihomo/Clash fake-ip and
  Surge enhanced mode hand out) and `tools/url_safety.py` classifies that as private/benchmark.
- Supported fix — declare the block; the guard's own module docstring names this exact case. A
  fake-IP proxy answers **both** families, and the guard inspects every answer, so **declare each
  range the host is answered with** — commonly an IPv4 *and* an IPv6 one:

```yaml
security:
  fake_ip_ranges:
    - 198.18.0.0/15
    - 2001:2::/48
```

  Measured on one host: with only `198.18.0.0/15` declared the fetch still failed, blocked at
  `2001:2::13` (the AAAA sentinel); adding `2001:2::/48` turned `is_safe_url` to `True` and the
  fetch succeeded. Enumerate both families before editing config:
  `dig +short <host>` **and** `dig +short AAAA <host>` — or read the blocked address in the error,
  which names whichever family is still undeclared.

  Entries overlapping RFC 1918 / loopback / link-local / CGNAT are dropped with a warning, so a
  declaration cannot be used to reach real internal hosts. `security.allow_private_urls: true` (or
  `HERMES_ALLOW_PRIVATE_URLS=1`) is the blunter global opt-out, and a proxy env var
  (`HTTPS_PROXY=…`) is a third lever — the guard then delegates hostname DNS to the proxy.
- Prove a declaration works **in a throwaway home** before editing the real config (pattern the
  config the same way the guard reads it):

```bash
P=~/.hermes/cache/scratch/hh-fakeip; mkdir -p "$P"
printf 'security:\n  fake_ip_ranges:\n    - 198.18.0.0/15\n    - 2001:2::/48\n' > "$P/config.yaml"
HERMES_HOME="$P" venv/bin/python3 -c "
from tools.url_safety import _global_fake_ip_ranges, is_safe_url
from tools.skills_hub_sources import UrlSource
print(_global_fake_ip_ranges()); print(is_safe_url(U))
print(UrlSource().fetch(U))"
```

  `_global_fake_ip_ranges()` echoing the parsed networks proves the declaration was accepted (a
  dropped entry logs `Ignoring security.fake_ip_ranges entry …`); `is_safe_url(url) -> True` and a
  non-`None` `UrlSource.fetch` prove the path cleared. This reuses the guard's own code path, so it
  is the same verdict `install`/`check` will reach — no need to touch the user's config to test.
- One-line diagnosis: `curl -s -o /dev/null -w '%{http_code} %{remote_ip}\n' -L "<url>"` — a 200 whose
  `remote_ip` sits in `198.18.0.0/15` (or any private range) is this situation exactly.
- Measured: only the url route is affected — `github`/`skills.sh` entries fetch through the GitHub
  API path and keep working, so "reinstall that skill by identifier" is both the workaround and the
  durable fix (`fake_ip_ranges` is for when the URL route must stay in use).

## Scan policy (`skills_guard`)

| trust \ verdict | safe | caution | dangerous |
|---|---|---|---|
| builtin | allow | allow | allow |
| trusted | allow | allow | block |
| community | allow | **block** | block |
| agent-created | allow | allow | ask |

`TRUSTED_REPOS = {openai/skills, anthropics/skills, huggingface/skills, NVIDIA/skills}`; everything
else — custom taps included — is `community`. `--force` overrides a caution verdict and an
existing install, never a dangerous verdict.

Findings alone never block: verdict `safe` installs without `--force` however many `medium` entries it
carries (oversized asset, `python_subprocess`, `unicode_escape_chain` are typical, and a self-authored
script full of `subprocess` calls is exactly that shape). Read the verdict, not the finding count —
show the findings to the user and only reach for `--force` when the verdict is `caution` (community)
against the policy table. The verdict depends on what got downloaded, so the
same skill can be `SAFE` via the single-file URL route and `CAUTION` via the whole-directory
route.

### `.skillignore` — the supported lever when the scan judges repo infrastructure

`scan_skill(dir)` reads a gitignore-style `.skillignore` (or `.clawhubignore`, honored for ClawHub
publishes) from the skill directory and skips matching paths in **both** passes — the structural check
and the per-file pattern scan. Syntax: blank lines and `#` comments skipped, a trailing `/` means that
directory and everything under it, `*`/`?` globs are matched against the full path and against each
segment, a leading `/` anchors to the root. The ignore file itself is always excluded and `SKILL.md`
can never be ignored; there is no negation, so nothing inside an ignored directory can be recovered.

Why it matters: CI, tests and promo assets are not skill content, but they are what gets judged when
the "skill directory" is the repo root. Measured on a repo where the only blocker was a `critical
traversal` finding raised by a *test file* probing a system path outside the workspace (367 files / 73 MB):

| Scanned | verdict | findings |
|---|---|---|
| as fetched | `dangerous` | 33 (1 critical, 31 medium, 1 low) |
| + `.skillignore` for `.github/ tests/ books/ benchmarks/ dist/ website/ assets/ docs/ *.png *.jpg` and the README/CHANGELOG files | **`safe`** | 25 (all medium) |
| + the repo's own maintenance-only scripts | `safe` | 23 |

`community` allows `safe` outright, so the identifier route then needs no `--force`, lands in
`lock.json`, and becomes `check`/`update`-able — the one thing a hand copy can never be. Two things to
state plainly when offering it:

- **It changes the verdict, not the payload.** The only consumer of the ignore file is `scan_skill`
  (grep it: nothing under `tools/` reads it for bundling), so ignored files are still downloaded and
  installed and the installed directory keeps the size of the fetched tree. Payload reduction needs a
  narrow in-repo directory instead.
- **It has to exist in the fetched tree**, so it is a repo change (or a change to a fork the user
  installs from) — never a local setting. Offer it as a one-file upstream change with the before/after
  verdicts as its justification.

## Update decision (`check_for_skill_updates`)

1. install directory missing → `orphaned` (network skipped entirely; clear with `uninstall`).
2. `metadata.source_revision` equals upstream's current revision → `up_to_date` **without downloading**.
3. otherwise fetch upstream and compare the recorded install-time `content_hash` against the
   fetched bundle hash → `up_to_date` / `update_available`; unfetchable → `unavailable`.
   - Step 3 is reached by **every** `url` entry, always: `_source_matches` restricts the fetch to
     adapters whose `source_id()` equals the recorded source, and `current_revision` is implemented
     by `GitHubSource` alone — so only a github/skills.sh entry whose `source_revision` is still
     current can take the no-download shortcut.
   - The two fetch paths differ in SSRF posture: the url adapter's `GuardedFetchMixin`
     (`_fetch_text`/`_fetch_bytes`) goes through the guarded GET, which resolves the host and refuses
     private/benchmark answers, while `GitHubSource._github_get` uses the plain hub GET with no such
     pre-check. Measured on one machine against a healthy URL:
     `organize-obsidian-notes (skills.sh) → up_to_date`, `respond-to-questions (url) → unavailable`,
     `respond-to-requirements (url) → unavailable`.

So: `check` answers "has upstream moved" and is blind to your local edits; local edits are judged
only inside `update` (`_has_local_edits()` — on-disk hash vs install-time hash), which prints
`Skipping: <name> — you have local edits` and needs `--force` to overwrite. `update` itself calls
`do_install(..., force=True)`, so the scan gate never blocks an update — only a first install.
Scripting: grep the `update_available` status token, never the summary line, which also matches
`0 update(s) available`.

## Runtime surface — what the agent actually sees

Installed ≠ listed. `skill_view(name)` returns the `SKILL.md` body plus `linked_files`, built from
`_LINKED_FILE_SPECS` (tools/skills_tool.py:371):

| support dir | globs | recursive |
|---|---|---|
| `references` | `*.md` | **no** |
| `templates` | `*.md *.py *.yaml *.yml *.json *.tex *.sh` | yes |
| `assets` | `*` (files only) | yes |
| `scripts` | `*.py *.sh *.bash *.js *.ts *.rb` | no |

Measured on a throwaway home with a fixture skill: `linked_files = {"references":
["references/00-overview.md"], "templates": ["templates/deep/x.md"], "assets":
["assets/img/a.png"], "scripts": ["scripts/p.py"]}` — `references/stage1/01.md` existed and was **not**
listed. Reading is not narrowed the same way: `skill_view(name, file_path='references/stage1/01.md')`
returned its content (`_serve_skill_file` rejects only `..`, paths escaping the skill root, and
non-files), and a wrong path returns a **recursive** `available_files` listing that does include the
unlisted nested file. `SKILL_SUPPORT_DIRS` (discovery side, agent/skill_utils.py:30) is
`{references, templates, assets, scripts}` — a directory outside it (`methodology/`, `docs/`,
`extractors/`) is never listed in either direction.

Authoring consequence for progressive disclosure: entry points as top-level `references/*.md`, the
next level named inside those files' own bodies (that is the mechanism — one level enters context at a

time), and bulk data under `templates/` or `assets/` when it should show up in the first listing. A
skill that keeps its depth in non-support directories is invisible to this surface even when it is
installed correctly.

## On-disk state

| Path (under `HERMES_HOME`, one per profile) | Contents |
|---|---|
| `skills/` | the skills themselves |
| `skills/.hub/lock.json` | per-skill: `source`, `identifier`, `trust_level`, `scan_verdict`, `content_hash`, `install_path`, `files`, `metadata` (`source_url`, `source_revision`), `scan_provenance`, timestamps |
| `skills/.hub/taps.json` | registered GitHub taps |
| `skills/.hub/quarantine/` | staging area before the scan; empty after a successful install |
| `skills/.hub/scan-cache/` | scan results keyed by bundle hash |
| `skills/.hub/audit.log` | one line per hub action: `<ISO-8601>Z <VERB> <name> <source>:<trust> <verdict> sha256:<hash>`, verbs `INSTALL` / `UNINSTALL` / `BLOCKED`. A `BLOCKED` line carries the reason where the hash would be (`dangerous 5_findings`, `invalid_path …`). Append-only timeline — the lock holds current state only |

A `clawhub` entry looks different: `identifier: @<publisher>/<slug>` and an extra `_meta.json`
inside the installed directory (`ownerId`, `slug`, `version`). The publisher named there is often
**not** the upstream author — check before treating it as the same skill.

## Provenance audit — what to read, and with which interpreter

The claim "installed 2026-09-29 from X as community/caution" is provable from two files, no network:
`skills/.hub/lock.json` (state) and `skills/.hub/audit.log` (timeline, see the table above). The lock
entry carries `installed_at` / `updated_at`, `metadata.source_url` (commit-pinned tree URL) and
`metadata.source_revision` (**the commit it is pinned to** — the thing to quote when the user asks
"which version"), `scan_provenance.verdict` + its `findings` list, and the install-time
`content_hash`.

Two limits to state rather than paper over:

- **The argv is not recorded anywhere.** `source` + `identifier` + the route rules are what let you
  rebuild the command; present that as a reconstruction.
- **`check` cannot see local edits** (it compares the install-time hash against upstream). Whether
  `update` would skip the skill is a separate, in-process question:

```python
from hermes_cli.skills_hub import _has_local_edits
from tools.skills_guard import content_hash
from tools.skills_hub import SKILLS_DIR
# entry = lock.json["installed"][<name>]
print(entry["content_hash"], content_hash(SKILLS_DIR / entry["install_path"]), _has_local_edits(entry))
```

Use `scripts/lock-provenance.py` for this (it also prints the audit timeline); the import-path
version above is the fallback when the script cannot be used.

**Interpreter**: the hub modules need a modern Python plus `rich`/`httpx`, so the system interpreter
is the wrong one — a fresh shell's `python3` may be 3.9 and dies on `str | object` inside
`hermes_constants`, and even the managed 3.14 toolchain has no site-packages for this tree. Use the
runtime venv Hermes itself runs from, and point `PYTHONPATH` at the source tree:

```bash
PY=$(for p in ~/.hermes/installs/*/environments/*/venv/bin/python3; do
       "$p" -c 'import rich,httpx' 2>/dev/null && { echo "$p"; break; }; done)
HERMES_HOME=~/.hermes PYTHONPATH=~/.hermes/hermes-agent "$PY" <script-or-c>
```

`HERMES_HOME` must be set before the import: `SKILLS_DIR` is bound at import time, so a wrong home
prints another profile's paths without erroring. Authored scripts under a repo profile
(`profiles/<name>/`) have their own `skills/.hub/lock.json` and `audit.log` — audit the profile whose
skill list the user is looking at (`hermes -p <name> skills list`).

## Which command governs which skill

- Hub-installed (A/B/C): `list`, `check`, `update`, `audit`, `uninstall`, `inspect`, `search`, `browse`, `config`, `snapshot export/import`, `publish`.
- Bundled only: `diff`, `reset`, `list-modified`, `repair-official`, `opt-out`, `opt-in`. In `reset`,
  only `--restore` reverts to the stock copy (plain `reset` re-baselines *your* edited copy and keeps it,
  and neither form backs your copy up) — the procedure lives in `maintain-hermes-skills`.
- Repo-local skill dirs: `trust` / `untrust`.
- No lock entry of its own: none of the above — `Source: local / Trust: local`, `check` reports
  `No hub-installed skills to check.`, `uninstall` errors. That covers a hand copy, a skill installed
  by an external installer (route F — maintain it with `npx skills update` / `remove`), **and** a
  nested child of a hub-installed bundle (the child has no entry of its own), so `local` is not itself
  evidence of a hand copy. Maintain a hand copy by hand; for a self-authored nested child, move it
  into its own directory instead — see the last pitfall in SKILL.md.
