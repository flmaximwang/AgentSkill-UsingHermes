# Install Hermes Skills from an `npx skills add` command

Use this file when what you were handed is a **command**, not a link: `npx skills add <repo> --skill
<name>`. That string shows up on every skills.sh skill page and in many READMEs, and users paste it
as-is. It is not something to run — it is **metadata that tells you which skill inside a repo is the
one meant**, and Hermes itself reads it for exactly that purpose.

## Why the string matters at all

The skills.sh adapter scrapes it off the detail page and lets it **override** the identifier's repo
and skill (`tools/skills_hub_skillssh.py`):

```python
_INSTALL_CMD_RE = re.compile(
    r'npx\s+skills\s+add\s+(?P<repo>https?://github\.com/[^\s<]+|[^\s<]+)'
    r'(?:\s+--skill\s+(?P<skill>[^\s<]+))?',
    re.IGNORECASE,
)
...
install_command, install_match = None, self._INSTALL_CMD_RE.search(html)
if install_match:
    install_command = install_match.group(0).strip()
    install_skill = (install_match.group("skill") or install_skill).strip()
    repo = self._extract_repo_slug((install_match.group("repo") or "").strip()) or repo
```

So when a three-segment identifier resolves to the wrong skill, or the repo layout makes the third
segment ambiguous, **the npx line on that page is the authority on which repo + skill name is
intended** — read it, then build the identifier from it.

## Convert it into a Hermes install

`npx skills add <repo> --skill <name>` gives you two facts: the repo, and the **skill name** (not the
directory). Hermes wants a directory:

```bash
# 1. the repo, from the command
gh api "repos/<owner>/<repo>/git/trees/HEAD?recursive=1" --jq '.tree[].path | select(endswith("SKILL.md"))'
# 2. pick the path that matches <name>, strip the trailing /SKILL.md, prepend owner/repo
hermes skills inspect <owner>/<repo>/<path-to-that-skill>
hermes skills install <owner>/<repo>/<path-to-that-skill> --category <cat> -y
```

If the repo is one where it is obvious, the adapter's own search order tells you where to look first:
it tries `skills/`, `.agents/skills/`, `.claude/skills/` before falling back to full tree/sitemap
discovery (`_STANDARD_BASE_PATHS`, `tools/skills_hub_skillssh.py:56`). (Inference: those mirror the
project-local conventions the `npx skills` CLI itself uses; only the adapter's search order is
verified.)

A repo-root skill has no directory to name — use the raw URL route in
`install-hermes-skills-from-github.md` type 1/2 instead.

## Why not just run the command

Hermes tracks skills it installs in its lock (`<HERMES_HOME>/skills/.hub/lock.json`). Anything
installed outside that path — a manual `cp -R`, or a tool that writes into a project's own
`.hermes/skills` / `.agents/skills` — is a **local** skill: `check`, `update`, `audit` and
`uninstall` cannot see it, and there is no version record (the full consequences are measured in
`install-hermes-skills-from-github.md` rung 2; project-local skills additionally need
`hermes skills trust` before they load, per `hermes skills --help`).

The measured counterpart is in the GitHub FAQ: the same skill installed through the raw-URL route
(3 files) and through the tap route (18 files) behaves completely differently in `check`, because
only one of them has a lock entry with a commit pin.

**So: keep the npx string as metadata, and install with an identifier.**

**The other half of this file is the route itself.** Part 1 above treats an `npx skills add` string as
metadata for a Hermes install. Part 2 is the case where that CLI is doing the installing — the user
already runs it, or the hub route is blocked and this is the documented way around it.

## Part 2 — the route itself (npm `skills`, Vercel Labs)

## What it is

- npm package `skills` (`vercel-labs/skills`, "The open agent skills ecosystem") — run as
  `npx skills <command>`, or `npx -y skills@<version>` to pin.
- skills.sh pages advertise the install as `npx skills add <owner>/<repo> [--skill <name>]`. Hermes'
  own skills.sh adapter parses exactly that string (`tools/skills_hub_skillssh.py::_INSTALL_CMD_RE`)
  to recover the repo from a page — so a user pasting that command is on this route, **not** on
  `hermes skills install`.
- **Hermes is a supported target** (`dist/cli.mjs` agent table):
  `"hermes-agent": { displayName: "Hermes Agent", skillsDir: ".hermes/skills",
  globalSkillsDir: join(hermesHome, "skills"), detectInstalled: existsSync(hermesHome) }` with
  `const hermesHome = process.env.HERMES_HOME?.trim() || join(homedir(), ".hermes")`.

## Commands

| Purpose | Command |
|---|---|
| install into Hermes, global | `npx -y skills@<ver> add <owner>/<repo> -a hermes-agent -g -y` |
| …only one skill of the repo | `… add <owner>/<repo> -a hermes-agent -g -y -s <skill>` (`-s '*'` = all) |
| list what a repo offers, install nothing | `… add <owner>/<repo> -l` |
| list installed | `npx skills list` / `npx skills list -g` |
| update | `npx skills update -g -y` (alias `upgrade`; `-p` = project only) |
| remove | `npx skills remove -a hermes-agent -y` |
| machine-readable | add `--json` |

Other flags: `-g/--global` vs project scope, `--copy` (copy instead of symlink into the agent dir),
`--full-depth` (search subdirectories even when a root `SKILL.md` exists), `--all`, `--subagent`.
Project scope keeps a `skills-lock.json` and is restorable with `experimental_install`.

## Where it writes, and what it records

- Canonical store `~/.agents/skills/<name>`, then **copy or symlink** into each selected agent dir.
  Measured: one install left a real directory at `<HERMES_HOME>/skills/<name>` (367 files / 7.4 MB —
  a repo-root skill is the whole repo, `tests/ dist/ books/ website/` included), while a later
  `update` in a home whose store was local created `<HERMES_HOME>/skills/<name> ->
  ../../.agents/skills/<name>`. Check with `ls -ld`; do not assume which form landed.
- Its own lock, **global**: `~/.agents/.skill-lock.json`, schema v3 —
  `{"version":3,"skills":{"<name>":{"source","sourceType","sourceUrl","skillPath",
  "skillFolderHash","installedAt","updatedAt"}},"dismissed":{}}`. `sourceType` is `github` or
  `well-known`; **`skillFolderHash` is the upstream commit SHA** the copy was taken from, i.e. the
  version record to quote.
- It runs third-party security assessments (Gen / Socket / Snyk, sourced from skills.sh) and prints
  them on install. Hermes' `skills_guard` never runs on this route, so those are the only signals.

## Hermes' hub cannot manage this route

- No `lock.json` entry is written, so `hermes skills list` shows the skill as `local` / `local` and
  `hermes skills check <name>` answers **`No hub-installed skills to check.`** — `update`,
  `uninstall` and `audit` will never touch it, and `hermes skills update` cannot make it fresh.
- **Updates come from the installer**: `npx skills update -g -y` compares each recorded
  `skillFolderHash` against the upstream commit. Measured: after rewriting the hash to all-zeros,
  `update -g -y` printed `Found 1 global update(s) → Updating <name> → ✓ Updated <name>` and wrote the
  real commit back — a genuine re-fetch, not a no-op. With nothing moved it prints
  `Checking skills from source: <owner>/<repo>` then `✓ All global skills are up to date`.
- Answering "can it auto-update?" therefore needs the right noun: yes, but by the CLI, on its own
  schedule — pin it with a cron job (`npx skills update -g -y`) if the user wants it unattended.
- A whole-repo copy also changes what Hermes lists: measured, the installed directory contributed a
  batch of extra `local` / `local` rows (`hermes skills list`), each a nested `SKILL.md` from inside
  the copied tree, grouped under the parent's directory name.

## Sandbox trap — `HOME` alone does not contain it

The target is resolved from **`HERMES_HOME`**, so this sequence writes into the REAL profile:

```bash
export HOME=$PWD/scratch-home          # only the CLI's own store/lock go here
npx -y skills add <owner>/<repo> -a hermes-agent -g -y   # copy lands in ~/.hermes/skills/<name>
```

The result is the worst of both: a directory in the real home whose update record
(`$HOME/.agents/.skill-lock.json`) sits in a scratch dir that gets pruned — it is then managed by
neither side (no hub entry, no installer record). To sandbox, export **both**:

```bash
S=/Users/maxim/.hermes/cache/scratch/skillscli   # one-off dir, new name per run
mkdir -p "$S" && export HOME="$S" HERMES_HOME="$S/.hermes"
```

and after any run verify the real home was untouched:
`ls -ld "$REAL_HERMES_HOME/skills/<name>"`. Restore `HOME`/`HERMES_HOME` in the next command (both
persist between shell calls), and to undo a stray copy: `rm -rf <real-home>/skills/<name>` — there is
no lock entry to uninstall, and its nested `SKILL.md` rows disappear with it.

## When this route is the right answer

- The user already uses it: check `~/.agents/.skill-lock.json` for prior entries before claiming
  they have no updatable sources.
- The identifier route is scan-blocked (`dangerous`, and `--force` cannot override it) and the repo
  will not take a `.skillignore`/layout change soon — this route copies the directory without a
  hub verdict, so the skill is usable and updatable immediately. State the trade honestly: no
  `skills_guard` scan, whole-repo payload, and updates live outside `hermes skills`.
- Never present it as a way to "fix" a hub install: the two records are independent, so a skill can
  end up installed twice (once per route) with different contents.
