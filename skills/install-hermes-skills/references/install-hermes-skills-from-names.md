# Install Hermes Skills by name / from the official catalogs

Use this file when the user did **not** hand you a link or an `owner/repo/path` identifier, but a
**name** or a description of what they want ("装个处理 pdf 的 skill", "the official skill-creator"),
or when they want to know what is already available. Here discovery is the hard part: `search` has
several documented ways to return an empty or misleading list, so read the failure modes before
concluding "it does not exist". Two decisions matter, in this order: **which source** the name should
come from (popularity × recency — see *Pick the source BEFORE installing*), and whether that source is
installable at all.

## The nine sources, and which one a bare name hits

Resolution order (`tools/skills_hub_search.py:99-114`):

```
official → hermes-index → skills.sh → well-known → url → github(tap) → clawhub → lobehub → browse-sh
```

A bare name first meets `official` and `hermes-index`:

- **`official`** (`OptionalSkillSource`, `tools/skills_hub_official.py`, `SOURCE_ID = "official"`,
  `TRUST_LEVEL = "builtin"`) — the skills shipped in the repo's `optional-skills/` directory:
  "official (Nous-maintained) but not activated by default — absent from the system prompt and not
  copied to `~/.hermes/skills/` at setup". Its identifier is the relative path `category/skill`
  (used verbatim) **or a bare skill name** (located via the repo tree), and it fetches from the live
  default branch — so a local install can lag behind `main`. `hermes skills repair-official`
  backfills/restores these.
- **`hermes-index`** — the centralized Hermes index (`skills_hub_official.py:288`).

Because `official` carries `builtin` trust, it is **allowed at every verdict** (see the trust table in
`SKILL.md`) — nothing official needs `--force`.

## Bundled (seeded) skills are a different mechanism entirely

Bundled skills do **not** come from the network: `tools/skills_sync.py::sync_skills()` copies them
from the current code root's `skills/` into the profile's `<HERMES_HOME>/skills/`, gated by a
`name:md5` manifest (`.bundled_manifest`). Facts that matter when a user asks "where is skill X":

- **A copy you edited is never overwritten** — the sync prints `user-modified, skipping`, and
  `hermes update` likewise keeps it. `hermes skills list-modified` lists those, `diff` shows how they
  differ, `reset` clears the modified tracking.
- **If the code root has no `skills/` directory, seeding silently copies 0 files** —
  `sync_skills()` early-returns on `if not bundled_dir.exists()`, so it looks like "already up to
  date" when in fact there was no source. (Measured on this machine: two `installs/…/workspace/`
  code roots have no `skills/`; the app/gateway launcher chain pointing at `~/.hermes/hermes-agent`
  has 58 bundled skills.)
- **`HERMES_BUNDLED_SKILLS` is a relocation hook for packagers, not a switch.** To stop seeding use
  `hermes skills opt-out` (writes `<HERMES_HOME>/.no-bundled-skills`; `--remove` additionally deletes
  your unmodified bundled copies) and `hermes skills opt-in [--sync]` to re-enable.
- Three different words mean three different things: **bundled** (seeded from the code tree, managed
  by `diff`/`reset`/`list-modified`), **local** (manually copied, managed by nothing — see
  `install-hermes-skills-from-github.md` rung 2), **hub-installed** (in the lock, managed by
  `check`/`update`/`audit`/`uninstall`).

## `search` — how it lies, and how to make it work

```bash
hermes skills search "<keyword>"                 # fuzzy
hermes skills search "<keyword>" --json          # full identifier strings (the table folds them)
hermes skills search "<keyword>" --source github # only meaningful if you registered a tap
```

- **Fuzzy, so read the `Name` column.** Measured: a search for `paper2agent` mixes `pdf`,
  `webapp-testing`, `handoff` into the first 25 rows. The `Identifier` column is folded by column
  width — use `--json` to get a full string, e.g. `skills-sh/anthropics/skills/pdf`, which can be
  passed to `install` as-is.
- **`--source` decides who *else* gets queried, and `official` always tags along.** Measured:
  `search paper --source skills-sh` returned 6 rows, 1 of them from `official`. Accepted source
  values: `all, official, skills-sh, well-known, github, clawhub, lobehub, browse-sh`; plus vendor
  aliases `nvidia, openai, anthropic, huggingface, voltagent, gstack, minimax`.
- **Without `--source`, GitHub is skipped entirely** — `_select_active_sources`
  (`tools/skills_hub_search.py:132-152`) drops `_API_SOURCE_IDS = {github, skills-sh, clawhub,
  lobehub, well-known}` whenever the central index is available and the filter is `all`, and the
  fallback set after an index miss is `_API_SOURCE_IDS - {"github"}` (`:95`), with the source comment
  *"GitHub stays out — one miss (a typo) would burn an unauthenticated user's whole hourly GitHub
  budget."* → **a private repo you tapped is never listed by a plain `search <word>`.**
- **Even `--source github` usually loses to the budget.** `GitHubSource.search` walks **all 25 taps
  sequentially** (24 built-in + yours appended, measured at **position 24**), at least one contents
  API call each, under an `overall_timeout = 30` s budget (`tools/skills_hub_search.py:225`).
  Measured by driving the same enumeration directly: **>420 s** to time out → a self-registered tap
  at the end almost never gets reached.
- **Zero results swallows the "slow source skipped" hint.** `do_search` prints
  `No skills found matching your query.` and returns immediately (`hermes_cli/skills_hub.py:335-336`),
  while `⚡ Slow sources skipped: …` is at line **411** — so you cannot tell "timed out" from
  "genuinely absent".
- **ClawHub search has a 12 s catalog-walk budget** (`CATALOG_WALK_BUDGET_SECONDS = 12`, 50k+ skills,
  sequential requests): measured `hermes skills search cangjie --source clawhub` →
  `No skills found matching your query.`, while `inspect` with the full `@publisher/slug` works. On
  that source, **only a known identifier is reliable**.
- **The same-name trap.** Measured: `hermes skills search nuwa` → 12 rows, **all from `clawhub`**
  (`nuwa-dual-mode`, `nuwa-video-gen`, …), none of them the GitHub repo the user meant. Search is not
  evidence that a GitHub skill does not exist; a three-segment identifier or a raw URL is.

## tap — register a GitHub repo so `search`/`browse` can list it

```bash
hermes skills tap add anthropics/skills     # → Added tap: anthropics/skills   (writes skills/.hub/taps.json, default path "skills/")
hermes skills tap list
hermes skills search "<keyword>" --source github
hermes skills browse --source github --size 30
hermes skills tap remove anthropics/skills  # only affects future search/browse — never touches installed skills
```

- Measured `taps.json` shape: `{ "taps": [ { "repo": "anthropics/skills", "path": "skills/" } ] }`.
  It lives under `<HERMES_HOME>/skills/.hub/`, so **each profile has its own**.
- **A tap is discovery-only.** `install` resolves by identifier shape and does not need the tap; the
  real benefit is being searchable. On this machine (2026-09-30) `hermes skills tap list` prints
  `No custom taps configured. Using default sources only.`
- **`bucket` in `taps.json` is a dead field.** `tap add` writes only `{repo, path}` (`TapsManager.add`,
  `tools/skills_hub.py:365-372`) and `tap list` shows only two columns; hand-writing a `bucket` key
  changes nothing on disk because **no code in the tree reads it** — its only effect would be
  `meta.extra["category"]` on search results. Grouping is done with `--category <cat>` at install
  time (see `install-hermes-skills-from-skill-sh.md`).
- **You can skip the tap entirely**: the three-segment identifier route reaches the same repo through
  `skills.sh` (its `_discover_identifier` falls back to GitHub enumeration,
  `tools/skills_hub_skillssh.py:241,254`). Measured: `hermes skills inspect
  flmaximwang/AgentSkill-ObsidianManagement/skills/organize-obsidian-notes` → `Source: skills.sh`,
  `Trust: community`, no tap involved.

## Pick the source BEFORE installing: popularity × recency, then verify it is installable

A bare name usually exists in several bloodlines at once, and **the one the name resolves to is not
necessarily the one worth installing — nor the one that installs at all.** Score every candidate on two
axes first, then check that the winner actually installs.

Measured on `cangjie-skill` (2026-09-30), one name, two bloodlines:

- **`kangarooking/cangjie-skill`** — popularity: skills.sh page says `Installs 1.4K` / `GitHub Stars
  10.8K`; `gh api repos/kangarooking/cangjie-skill --jq '{stars,pushed_at,archived}'` →
  `10757` / `2026-09-26T09:38:37Z` / `false` (repo created 2026-04-16, MIT). Recency: repo pushed 4 days
  before the install, frontmatter `cangjie.version: 2.5.0`, skills.sh `First Seen Jun 30, 2026`, three
  third-party audits (Agent Trust Hub Pass, Socket Warn, Snyk Pass).→ **wins both axes.**
- **`@terrybenedict0515/cangjie-skill`** (ClawHub, display name "Cangjie Skill") — popularity/recency
  come from `GET https://clawhub.ai/api/v1/skills/<slug>`: `.skill.stats.installs` `15`,
  `.stats.downloads` `2101`, `.stats.stars` `1`, `.stats.versions` `1`, `.skill.updatedAt` = `.createdAt`
  = `1781784343470` (= 2026-06-18, untouched for 3.5 months); `.moderation.verdict` `clean`. → **loses
  both axes** (15 installs vs 1.4K).

Where each axis is readable, per source:

| source | popularity | recency |
|---|---|---|
| skills.sh | `Installs …` on the detail page (scraped by `_WEEKLY_INSTALLS_RE`) | `First Seen` + frontmatter `version:` |
| the GitHub repo behind it | `gh api repos/<owner>/<repo> --jq .stargazers_count` | `--jq .pushed_at` (and `.archived`) |
| clawhub | `.skill.stats.installs` / `.downloads` / `.stars` | `.skill.updatedAt`, `.stats.versions` |

**Then verify the winner is installable — the ranking hides this completely.** In the measured case the
winner could not be installed at all while the loser installed cleanly:

- The identifier every registry hands out (`skills-sh/kangarooking/cangjie-skill/cangjie-skill`) dies at
  fetch: `Error: '…' is listed in the hermes-index index, but its files no longer exist upstream.`
- The only GitHub form that resolves (`kangarooking/cangjie-skill/`, the whole 366-file repo) is
  **permanently** blocked: `Decision: BLOCKED — dangerous verdict, 18 findings … --force does not
  override a dangerous verdict.`
- The raw URL of the root `SKILL.md` installs, but as a 4-file stub (`methodology/`, `extractors/` are
  outside the URL route's support dirs).
- The ClawHub loser installed (`safe`, 21 files) — and is a *different, incomplete* bloodline: its
  `SKILL.md` says `name: book2skill`, `version: 2.0.0`, `author: 花叔 AlchainHust (原版) ·
  mac-openclaw-manager (改造版)`, and 6 files its body references (`templates/*.template`) were never
  published.

So: rank first, then prove the winner installs, and when the popular/maintained bloodline cannot be
installed, **say that** instead of quietly installing the fork under the same name — and never present a
winner you have not tried. `install-hermes-skills-from-clawhub.md` covers the bloodline check on the
package side.

## Verify what a name resolved to

```bash
hermes skills inspect <identifier>     # read-only; shows Source / Trust / Identifier / Repo
hermes skills list                     # Name | Category | Source | Trust | enabled
hermes skills list --source builtin    # seeded bundled skills
hermes skills list --source local      # manually copied skills
hermes skills list --enabled-only      # what a given profile will actually load: add -p <profile>
```

`install` has **no `--source`** (measured: `--help` offers only `--category / --name / --force /
--yes`), so naming cannot pin a source — the identifier shape does. When the name is ambiguous
between an official skill and a same-name ClawHub package, inspect both and compare frontmatter:
`install-hermes-skills-from-clawhub.md` documents how ClawHub packages differ from upstream
(`name` + `version` mismatches = a different bloodline, not an update).
