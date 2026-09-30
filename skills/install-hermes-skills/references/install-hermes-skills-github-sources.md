# GitHub skill sources: direct paths, taps, update lifecycle

Scope: getting a skill that lives in a GitHub repo into one profile, keeping it current, and knowing
what "current" costs. Every mutating command is scoped to one home — pass the home explicitly (`maintain-hermes-profile/SKILL.md` §10).

## Three install routes

| Route | Command | What is copied |
|---|---|---|
| Single skill from a repo path | `hermes skills install <owner>/<repo>/<path-to-skill>` | the whole skill directory tree, nested sub-skill dirs and assets included |
| Whole repo as a source (tap) | `hermes skills tap add <owner>/<repo>` → `hermes skills install <owner>/<repo>/<slug>` | every `SKILL.md`-bearing dir under the tap path becomes installable |
| Any URL | `hermes skills install https://…/SKILL.md [--name <slug>]` | `SKILL.md` + explicitly referenced files only |

`inspect` takes the same identifier as `install` and is read-only — prove a path resolves before
installing anything. Name resolution for the URL route: frontmatter `name` → URL slug → interactive
prompt → `--name`.

## Resolve the identifier, never guess it

The identifier embeds the repo's *own* layout, nested category dirs included:

```
anthropics/skills/skills/pptx                  # owner/repo/<skills dir>/<skill>
openai/skills/skills/.curated/hatch-pet
openai/skills/skills/.system/imagegen
```

Read it off the search table instead of writing it by hand:

```bash
hermes skills search <term> --source <publisher> --limit 5
# prints Name | Description | Source | Trust | Identifier
```

- Publisher filter values are exactly: `nvidia, openai, anthropic, huggingface, voltagent, gstack,
  minimax`, beside the registry ids `official, skills-sh, well-known, github, clawhub, lobehub,
  browse-sh`. An invalid value fails loudly with the full choice list.
- **`--source github` is not the tap filter.** It does not surface tap content: observed runs returned
  rows from other sources or nothing at all. Filter by the publisher name.
- A doc/README example path goes stale the moment upstream reorganizes: `openai/skills/k8s` answers
  `Could not find '…' in any source` because those skills moved under `skills/.curated/`. A moved path
  is not a broken hub — re-resolve, do not debug the install.
- Docs identifiers are sometimes written without the middle directory
  (`openai/skills/skill-creator`). Trust the search output over both the docs and intuition.

## Taps: what a tap publishes

- Config: `<home>/skills/.hub/taps.json` → `{"taps": [{"repo": "owner/repo", "path": "skills/"}]}`.
  `hermes skills tap add` defaults `path` to `skills/` and there is no flag for a different one — it is
  a file edit. `hermes skills tap list` prints the effective path per tap, and says
  `No custom taps configured.` when the file is empty.
- Default taps browsable with no setup: `openai/skills`, `anthropics/skills`, `huggingface/skills`,
  `NVIDIA/skills`, `garrytan/gstack`, `K-Dense-AI/scientific-agent-skills` (+ `synthetic-sciences/openscience`).
- Each repo+path listing is cached at
  `<home>/skills/.hub/index-cache/<owner>_<repo>_<path with / → _>.json`. It is the fastest way to see
  what a tap really exposes, and it explains a bare-path miss: `openai_skills_skills__.json` is `[]`
  (2 bytes) while `openai_skills_skills_.curated__.json` carries the skills. A tap may also ship
  `skills.sh.json` at its root, whose `groupings` become the hub's category labels.
- Trust: the known publishers install as `trusted`; a repo added as a tap is `community` and pays the
  install-time scan and third-party panel. `--force` clears caution/warn findings, never a
  `dangerous` verdict (`maintain-hermes-profile/SKILL.md` §9).

## Updates: what the provenance buys you

`<home>/skills/.hub/lock.json` records per installed skill: `source`, `identifier`, `content_hash`,
`install_path`, `files`, `trust_level`, and a scan-provenance block.

- `hermes skills check [name]` — read-only; refetches through the adapter matching the recorded
  `source` and compares the upstream bundle hash against `content_hash`. Entries whose recorded source
  has no matching adapter are not rebound to a same-named skill elsewhere; they degrade to
  `unavailable`.
- `hermes skills update [name] [--force]` — applies to entries with a real change only; a locally
  edited skill (on-disk hash ≠ recorded hash) is skipped unless `--force`, which rmtree-replaces it.
- Statuses from `check`: `up_to_date`, `unavailable` (source could not produce the bundle — a removed
  tap shows up here), `orphaned` (lock entry, no directory; clear with `hermes skills uninstall`),
  `invalid_install` (recorded path unusable; inspect the lock, do not just retry).
- A GitHub-installed skill is an ordinary hub entry after install: same lock, same skip-if-edited rule,
  same home scoping (`maintain-hermes-profile/SKILL.md` §10). No GitHub-specific update path exists.

## One install can be several skills, and the verdict differs by route

- **A directory install fetches the whole tree.** Installing a parent skill dir (`<repo>/skills/<parent>`)
  brought its nested sub-skill dirs (`<parent>/<sub>/SKILL.md` + their `references/`, `scripts/`, MB of
  assets): 71 files / 6.3 MB for one command. The `references|templates|scripts|assets|examples`
  allowlist in `tools/skills_hub_models.py` gates only the *link-derived* same-dir file list, not the
  fetch — so bundle size is a real install cost and a scan-verdict input (`oversized_skill`,
  `too_many_files`).
- **Nested `SKILL.md` files register as their own skills.** One install of the parent produced four rows
  in `hermes skills list` (`<parent>` plus each sub-skill, category = the parent dir). Count them before
  reporting "installed": a parent that is a router over sub-skills is normal, not a broken bundle.
- **A blocked install is a `--force` decision, not a failed route.** A community repo whose `caution`
  verdict clears the thresholds answers `Decision: BLOCKED — Blocked (community source + caution verdict,
  N findings)` and installs nothing; `--force` clears it (`dangerous` never does — `maintain-hermes-profile/SKILL.md` §9).
- **The update path carries `force` itself, so a scheduled update is not re-blocked.** `do_update` calls
  `do_install(..., force=True)` (`hermes_cli/skills_hub.py`, ~line 902). Name which step needs the human:
  the first install may need a manual `--force`, while the cron job that later runs `hermes skills update`
  does not.
- **Probe an install without touching the live profile**: `HERMES_HOME=<scratch> hermes skills install
  <id> --yes [--force]`, then read `<scratch>/skills/` (file count, tree depth) and
  `<scratch>/skills/.hub/lock.json`. That is how a route's real cost and its verdict are known before
  recommending it to the user.

## Answering "can it auto-update from GitHub?"

There is no builtin switch: the `skills` config section carries no cadence key, `hermes update`
re-seeds bundled skills only, and update is always an explicit `check`/`update` run. Two honest
options, both requiring a schedule the user owns:

1. **Scheduled hub update** — a cron job that runs `hermes skills check` and, only when updates are
   reported, `hermes skills update` (a script-only / no-LLM job keeps the token cost at zero; the
   command must name the profile). Cost: the update replaces the skill's files wholesale, so review what
   changed, and re-scan anything refetched with `hermes skills audit [--deep]`.
2. **Clone + external dir** — clone the repo, register the checkout under `skills.external_dirs`, and
   schedule `git pull`. This is the only route where "upstream moves ⇒ my copy moves", and it gives up
   the hub's lock/scan/audit trail, so `hermes skills check` no longer covers that content.
   Point the entry at the directory that *contains* the skill dirs (`<clone>/skills`, not the repo root).
   Verified: a fresh home whose only entry was that path listed every skill of a multi-skill repo as
   `local/local/enabled`, with no hub install and no scan. `~` and `${VAR}` expand in these paths.
   Do not keep both routes for one repo — the two copies share skill names, and external dirs lose the
   name collision (`agent/prompt_builder.py`), so one copy ends up unreachable. Pick one.

Command shape for either route — the script lives in `~/.hermes/scripts/`, `--no-agent` skips the LLM
and delivers the script's stdout verbatim (empty stdout = silent, so a no-change week says nothing):

```bash
hermes cron create "0 10 * * 1" --name <job-name> --script <name>.sh --no-agent --deliver discord
```

Say which one is being proposed and what it gives up. "Skills auto-update" is a schedule the user runs,
never a property of the install.
