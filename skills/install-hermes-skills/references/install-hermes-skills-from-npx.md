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
`install-hermes-skills-from-github.md` Route D; project-local skills additionally need
`hermes skills trust` before they load, per `hermes skills --help`).

The measured counterpart is in the GitHub FAQ: the same skill installed through the raw-URL route
(3 files) and through the tap route (18 files) behaves completely differently in `check`, because
only one of them has a lock entry with a commit pin.

**So: keep the npx string as metadata, and install with an identifier.**
