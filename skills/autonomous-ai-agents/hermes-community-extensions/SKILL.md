---
name: hermes-community-extensions
description: "Find, vet, and install ready-made Hermes profiles/skills."
version: 1.0.0
author: Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, profiles, skills, distributions, discovery, install]
    related_skills: [hermes-profile-authoring, gateway-operations, hermes-agent]
---

# Hermes Community Extensions (profiles & skills)

Answering "does a ready-made Hermes agent/skill for X exist?" and everything that follows: discovering
candidates on GitHub and in the Skills Hub, vetting them against the *running* build, and handing the
user a verified install + verification path. Defer Hermes-wide config/CLI facts to the bundled
`hermes-agent` skill; this skill is the discovery-and-acquisition procedure.

## When this applies

- "Hermes 里有可下载的 X Profile 吗？" / "is there a ready-made agent for X?"
- Vetting a candidate profile distribution before installing it
- Finding out where an installed profile came from (`hermes profile list` / `profile info`)
- Choosing between a full profile (**distribution**) and a single hub **skill**

## The supply channels (know the shape before searching)

| Channel | Artifact | How it is obtained |
|---|---|---|
| Official docs | Mechanism only — **no official profile registry or marketplace exists**. Never imply one does. | `hermes profile install` docs, skills catalog |
| Community git repo | Profile **distribution**: `distribution.yaml` + `SOUL.md` + `skills/` + `cron/` + `mcp.json` | `hermes profile install <git URL \| local dir> --alias --yes` |
| Skills Hub | Single skill | `hermes skills search <term>` → `hermes skills inspect <id>` → `hermes -p <profile> skills install <id>` |

A **community "gallery"** repo is an index of links, not a store: its entries may be `seed`/`candidate`
(pre-admission) and can lack `distribution.yaml` in the source repo. Check the source repo, never the
gallery page, for the manifest.

## Procedure

### Step 1 — Translate the ask into the community's vocabulary

Packs name profiles by **English role** (`accountant`, `finance-ops`, `cfo`, `bookkeeping`, `tax`,
`audit`). A Chinese domain word (会计/财务/记账) returns nothing on GitHub; a zero-result search is a
vocabulary failure, not evidence of non-existence. Also split vague domain words into their real
flavours before searching, because they map to different artifacts: 记账/报税/对账 (bookkeeping) vs
财务运营 (FP&A / finance ops) vs 财务分析/估值 (valuation modelling). Search all of them, then ask the
user which flavour they meant if the answer hinges on it.

### Step 2 — Establish the local baseline first

```bash
hermes profile list          # Distribution column: '—' = hand-built, '<name>@<version>' = repo-installed
hermes profile info <name>   # source URL, version, installed-at timestamp
```

Do not assume a profile named after a topic was downloaded — a profile the user created by hand shows
`—` in the Distribution column. Check `~/.zsh_history` for `hermes profile create …` when the origin is
unclear, and check the profile dir for `distribution.yaml` / `.git`.

### Step 3 — Discover (GitHub API + Skills Hub in parallel)

Exact calls, snippets, and the tree-grep pattern: `references/github-discovery-recipes.md`.

- Repo search finds index repos and themed collections; it only searches name/description.
- For each candidate repo, fetch **one** recursive tree and keyword-filter the paths client-side
  (account/financ/bookkeep/tax/audit/ledger/cfo + Chinese equivalents). This is what surfaces a
  profile buried inside a 100+ profile pack that repo search never returned.
- Read decisive files from `raw.githubusercontent.com`, not the GitHub HTML page — raw is exact,
  cheap, and not truncated mid-README.
- Run `COLUMNS=200 hermes skills search <term>`: the default table truncates the Identifier column
  that `skills install` needs.

### Step 4 — Vet before recommending

1. The candidate profile directory must contain `distribution.yaml` (its presence is what makes it a
   distribution rather than a folder of prompts).
2. Read the manifest and cross-check its keys against the keys the **installed** build parses:
   `hermes_cli/profile_distribution.py` → `DistributionManifest.from_dict`. As of the Sep-2026 tree
   those are `name`, `version`, `description`, `hermes_requires`, `author`, `license`, `env_requires`,
   `distribution_owned`. **Unknown keys are silently ignored** — a manifest advertising e.g.
   `preload_skills` installs fine and that feature simply never runs. Never promise a manifest feature
   without verifying it in the source of the running build.
3. Record what decides the recommendation: license (some packs are AGPL-3.0-only), trust level
   (Skills Hub `community` vs `official`), required env vars, and whether it is a full profile
   (SOUL + skills) or only a skill bundle — a skill is not an agent.

### Step 5 — Install (git cannot clone a subdirectory)

```bash
# Repo ROOT is the distribution — install straight from the URL:
hermes profile install github.com/<owner>/<repo> --alias --yes

# A profile nested inside a pack repo — clone the pack, install from the local path:
git clone https://github.com/<owner>/<pack>.git ~/Repositories/<pack>
# prefer the pack's own installer, which previews first:
python3 install.py --profiles <profile-name> --dry-run
python3 install.py --profiles <profile-name> --yes
# or call hermes directly on the nested directory:
hermes profile install ~/Repositories/<pack>/<pack-dir>/profiles/<profile-name> --alias --yes
```

### Step 6 — Verify (state these as the acceptance checks)

```bash
hermes profile list                 # new row, Distribution = '<name>@<version>'  ← the hard evidence
hermes profile info <name>          # source URL, version, installed-at
hermes -p <name> skills list        # the bundled skills actually landed
```

An install that leaves the Distribution column empty did not install a distribution.

### Step 7 — Report

Lead with the yes/no per flavour, then a table of verified candidates with what you actually checked
(contents read, license, trust, env vars), then the commands with expected output and the verification
steps. If nothing matches the exact ask, say so plainly and name the closest substitute — for accounting
the honest answer is "closest is a finance-ops profile; real bookkeeping today exists as hub skills,
not as a packaged profile".

## Pitfalls

- **Silently-ignored manifest keys.** Verify keys against the running build's parser before promising
  behaviour (Step 4) — the failure mode is a no-op, not an error, so nothing warns you.
- **Repo-search blind spot.** `search/repositories` matches name/description only; a profile can live
  deep inside a well-named pack. Enumerate pack trees (Step 3) before concluding "nothing exists".
- **Gallery ≠ distribution.** An index page can list a profile whose source repo has no
  `distribution.yaml`; `hermes profile install` needs the manifest.
- **HTML pages vs raw files.** `web_extract` on `github.com/.../blob/...` truncates long READMEs and
  mangles code blocks; use the `raw.githubusercontent.com` path when you must quote or diff content.
- **Unauthenticated GitHub code search is not available.** Use repo search + recursive tree +
  client-side filtering instead of trying to grep code server-side.
- **Truncated tables hide the IDs you need.** Run CLI table commands with `COLUMNS=200`.
- **Don't restate a pack's own README as verified fact.** Pack docs routinely describe features gated
  on newer Hermes builds; check the local source, and label the rest as the author's claim.

## Standing user preferences (this user)

- **Give the command, the expected output, and the verification step — do not run mutating installs**
  (`hermes profile install`, `skills install`, `git clone` into his dirs) on his behalf.
- **Answer the yes/no first**, then the evidence table; keep the reply proportional, address him by name.
- **Factual software knowledge → Obsidian note, not memory.** For Hermes facts the target folder is
  `🗂️ Classifications/TP317 程序包（应用软件）/database/Hermes Agent/`; offer to write the note and give
  the absolute path (vault root `/Users/maxim/Documents/Obsidian/wangfanlin1`, rules in its README.md).
- **No invented sources, versions, or install results.** State what was checked and what was not.
- Flag a package's license and any credential/shared-bot conflict you notice while inspecting profiles
  (`hermes profile list` warnings), even when it is tangential to the question.

## Support files

- `references/github-discovery-recipes.md` — exact GitHub API calls, the recursive-tree keyword sweep,
  raw-file reads, the manifest-vs-running-build key check, and known source families.
