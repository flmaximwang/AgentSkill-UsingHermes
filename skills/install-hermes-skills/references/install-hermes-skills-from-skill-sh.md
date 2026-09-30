# Install Hermes Skills from skills.sh

Use this file when the thing you were handed is an `owner/repo/path` identifier, or a
`https://skills.sh/<owner>/<repo>/<skill>` link, or a GitHub link you converted per
`install-hermes-skills-from-github.md` type 3. This is the **common case**: most published skill
packs are multi-file repos (with `scripts/`, sub-skills, assets), and this route brings down the whole
skill directory pinned to a commit — unlike the raw-URL route, which takes only the main file plus
explicitly referenced files.

## What this route actually is

The identifier shape routes it: `_split_repo_id` requires at least three segments, so `owner/repo/path`
is handed to the source router, which resolves in this order
(`tools/skills_hub_search.py:99-114`):

```
official → hermes-index → skills.sh → well-known → url → github(tap) → clawhub → lobehub → browse-sh
```

`owner/repo/path` **usually lands on `skills.sh`** — which is a *proxy*: it discovers and pins
(GitHub API), fetches the files from the underlying repo, then relabels the bundle
(`bundle.source, bundle.identifier = "skills.sh", "skills-sh/<canonical>"`). Consequences worth
knowing before you trust the label:

- `Source: skills.sh` does **not** mean the skill is listed on skills.sh. Measured on a self-built
  repo: all three skills.sh URLs **404** (`https://skills.sh/<owner>/<repo>/skills/<name>`,
  `/api/skills/...`, `/<owner>/<repo>`); the `Detail Page:` line in `inspect` output is just a
  **string it builds** (`_detail_to_metadata`).
- Trust is borrowed from the GitHub source (`trust_level_for` → `skills_hub_skillssh.py:64-65`), so
  **any non-whitelisted repo is `community`** — and "community + caution is refused by default" is the
  norm on this route, not the exception.
- Private repos cannot pass: the files always come from GitHub.
- **The truth about where content came from is `metadata.source_url`** (a GitHub tree URL pinned to a
  commit), never `source`.

## Step 1 — Get the identifier right

Three ways to find it; use whichever you can.

1. **`hermes skills search <keyword>`** (first choice): columns are
   `Name / Description / Source / Trust / Identifier`, but the Identifier column gets **folded by
   column width** — add `--json` for the full string (measured: `skills-sh/anthropics/skills/pdf`).
   The returned string **carries a `skills-sh/` prefix and can be passed to `install` as-is** (the
   prefix is stripped). `search` is **fuzzy**: a search for `paper2agent` mixes `pdf`,
   `webapp-testing`, `handoff` into the first 25 rows — pick by the **Name** column.
   `--source` only decides *who else* to query and `official` always tags along (measured: a
   `search paper --source skills-sh` returned 6 rows, 1 of them from `official`). Accepted values:
   `all, official, skills-sh, well-known, github, clawhub, lobehub, browse-sh`, plus vendor aliases
   `nvidia, openai, anthropic, huggingface, voltagent, gstack, minimax`.
2. **The skills.sh website**: addresses look like `https://skills.sh/<owner>/<repo>/<skill>` — the
   last segments of the URL *are* the identifier, and the page prints a ready-made install command.
   The homepage only lists ~200 featured entries; the full catalog is in the sitemap (~20k+, which is
   what the adapter's `_SITEMAP_INDEX_URL` reads).
3. **Ask the GitHub repo tree directly** (no registry involved — the only option for private or
   brand-new repos):
   ```bash
   gh api "repos/<owner>/<repo>/git/trees/HEAD?recursive=1" --jq '.tree[].path | select(endswith("SKILL.md"))'
   ```
   Each path **minus the trailing `/SKILL.md`** is the third segment. Measured on `jmiao24/Paper2Agent`:
   4 rows, all nested under `skills/paper2agent/`.

Always validate the string with a read-only `inspect` first (no `--force` needed):

```
Source: skills.sh
Trust: community
Identifier: skills-sh/jmiao24/Paper2Agent/skills/paper2agent
Repo: https://github.com/jmiao24/Paper2Agent
```

`inspect` takes **only the identifier** (measured: `--help` has no `--json`/`--source`/`--limit`), so
the only machine-readable string comes from `search --json`.

Two shortcuts the router accepts: the prefixes `skills-sh/`, `skills.sh/`, `skils-sh/`, `skils.sh/`
are stripped (`:54,:366-368`), and the third segment may be omitted — the source tries `skills/`,
`.agents/skills/`, `.claude/skills/` first and then falls back to sitemap discovery (`:56`, `:241-286`).

## Step 2 — Install

```bash
hermes skills install jmiao24/Paper2Agent/skills/paper2agent --yes --force
```

Whether `--force` is required is decided by trust × scan verdict, not by you — see the verdict table
in `SKILL.md`. On this route the answer is usually yes: `community` + `caution` = blocked by default
(`anthropics/skills/...` is the exception because it resolves to the `github` source with
`trusted` trust).

Then verify: `hermes skills list` — the row shows `Source`, `Trust`, `enabled`; the files land in
`<HERMES_HOME>/skills/<name>/` (or `<category>/<name>/` with `--category`).

Measured install of a self-built repo, no tap involved:

```bash
$ hermes skills install "flmaximwang/AgentSkill-ObsidianManagement/skills/organize-obsidian-notes" --category obsidian -y
Decision: ALLOWED — Allowed (community source, safe verdict)
Installed: obsidian/organize-obsidian-notes
Files: SKILL.md, assets/darwin-card-20260930.png, scripts/organize.sh,
       scripts/organize_notes.py, scripts/test_organize_notes.py, test-prompts.json
```

- Landing: `skills/obsidian/organize-obsidian-notes/`; lock records `source: skills.sh`,
  `install_path: obsidian/organize-obsidian-notes`,
  `source_revision: 7884d88dee7938b47c5115a4d1d91e7e71970de9`.
- **`safe` verdict → no `--force` needed**, even with **9 medium findings** reported
  (`oversized_file`: 707 KB PNG > 256 KB limit; `python_subprocess` ×5; `unicode_escape_chain` ×1).
  **medium ≠ blocked**: community + safe is allowed outright; only caution/dangerous goes through
  `--force`.
- Batch recipe (no tap needed):
  ```bash
  for s in <skill1> <skill2>; do hermes skills install <owner>/<repo>/skills/$s --category <cat> -y; done
  ```

## Step 3 — What landed, and what a later `update` will do

- **A directory with several `SKILL.md` installs as several skills, but only one hub identity.**
  Measured with `paper2agent`:
  ```
  paper2agent        |             | skills.sh | community | enabled
  paper2agent-paper  | paper2agent | local     | local     | enabled
  paper2mcp          | paper2agent | local     | local     | enabled
  paper2skill        | paper2agent | local     | local     | enabled
  1 hub-installed, 0 builtin, 3 local
  ```
  So `update paper2agent` updates the whole tree, and `uninstall paper2agent -y` **deletes the whole
  tree** (measured: after uninstall, `list` is empty and nothing is left on disk) — **one entry
  removes all four, no orphans**.
- **Updates are not re-gated**: `do_update` calls `do_install(..., force=True)`
  (`hermes_cli/skills_hub.py:902`), so a weekly update will not hit the first-install `BLOCKED`. But
  **a skill you edited locally is skipped** unless you pass `--force`.
- **`--category` decides the landing folder, and nothing else does.** Default is flat
  `skills/<name>/`; `--category <cat>` → `skills/<cat>/<name>/` (layered values work: measured
  `--category "obsidian/notes"` → `skills/obsidian/notes/pdf/SKILL.md`). The agent's skill listing
  groups by that disk category (`agent/prompt_builder.py:1336`), so `--category` is the way to group
  several skills under one heading.
  Traps: re-installing with a different `--category` leaves the old flat directory on disk
  (invisible in `list`, `skills_list()` reports 1 because it de-duplicates by name — clean it with
  `rm -rf`). And **`bucket` in `taps.json` is a dead field** — it only ever sets
  `meta.extra["category"]` for search results (`tools/skills_hub_github.py:405-407`) and **no code
  in the tree reads it**; the landing path has exactly three sources
  (`hermes_cli/skills_hub.py:695-709`): `--category`, the official identifier's middle segment, or a
  url-source prompt in a TTY.
- **Lock entry shape** (this route):
  ```json
  "paper2agent": {
    "source": "skills.sh",
    "identifier": "skills-sh/jmiao24/Paper2Agent/skills/paper2agent",
    "trust_level": "community",
    "scan_verdict": "caution",
    "content_hash": "sha256:c20a6094082b688a",
    "install_path": "paper2agent",
    "metadata": {
      "source_url": "https://github.com/jmiao24/Paper2Agent/tree/8c2d059165ef8cdcb70dbea76655b9c2b55b38e6/skills/paper2agent",
      "source_revision": "8c2d059165ef8cdcb70dbea76655b9c2b55b38e6",
      "detail_url": "https://skills.sh/jmiao24/Paper2Agent/skills/paper2agent",
      "repo_url": "https://github.com/jmiao24/Paper2Agent"
    }
  }
  ```
  Measured size: `~/.hermes/skills/paper2agent/` is 6.5 MB; the lock records **69 files**, the disk
  holds 77 (`find -type f | wc -l`).

## FAQ

- **Why does `paper2agent` fail without `--force`?** Measured error:
  ```
  Decision: BLOCKED — Blocked (community source + caution verdict, 23 findings).
    rules: dump_all_env, oversized_file, oversized_skill, python_getenv_secret,
           python_os_environ, too_many_files, unpinned_pip_install, uv_run
  Not installed: ... Re-run with --force to install anyway.
  ```
  The verdict is `caution`, not `dangerous`, so `--force` can override it. **The most conspicuous of
  the 23 findings are images, not code**: `oversized_file` ×6 (`paper2agent-paper/assets/figure/figure-3.jpg`
  995 KB vs a 256 KB limit), `too_many_files` (69 > 50), `oversized_skill` (6311 KB > 5120 KB),
  `uv_run` ×9, `python_os_environ` ×1 (`paper2mcp/scripts/verify_mcp_server.py:107`). **For this class
  of skill, being blocked is structural, not evidence of malice** — adding only `--yes` wastes a round
  trip.
- **Why does the same shape resolve to different sources?** Measured two cases:
  `jmiao24/Paper2Agent/skills/paper2agent` → `Source: skills.sh` / `Trust: community` (needs
  `--force`); `anthropics/skills/skills/skill-creator` → `Source: github` / `Trust: trusted` (caution
  passes). Trust is asked of the GitHub source (`tools/skills_hub_skillssh.py:64-65`).
- **What is on the skills.sh page that I should not run?** `npx skills add <repo> --skill <name>` —
  that page command is *scraped* by the adapter's `_INSTALL_CMD_RE`, so its value to you is as
  metadata, not as something to execute. Details: `install-hermes-skills-from-npx.md`.
- **Can I pin the source?** No: `hermes skills install` has **no `--source`** (measured:
  `hermes: error: unrecognized arguments: --source github`; `--help` offers only
  `--category / --name / --force / --yes`). `do_install(source_id=...)` is only used internally by
  `do_update`. The identifier shape is the only lever you have.
- **What does the scan judge, exactly, and can `--force` beat everything?** The same skill gets
  different verdicts depending on download scope: URL route → `SAFE` (3 files scanned), tap route →
  `CAUTION` (it reaches `scripts/*.py`'s `subprocess.Popen` and `eval-viewer/*.html`'s `atob`).
  `--force` overrides a caution verdict and an "already installed" conflict; it **cannot** override
  `dangerous` (`--force does not override a dangerous verdict.`).
