# The install scan gate (`skills_guard`) — what blocks a package, and how to predict it

Depth for `SKILL.md` § Trust × verdict. That table — verdict rule, `--force` semantics,
`TRUSTED_REPOS` — stays in `SKILL.md`; this file is the *authoring* side of the same gate: what the
scanner reads, which documented commands trip it, and how to know the verdict before pushing.

## Predict the verdict locally, before pushing

The scanner imports without any Hermes state:

```bash
cd ~/.hermes/hermes-agent && HERMES_HOME=$HOME/.hermes venv/bin/python3 -c "
from pathlib import Path
from tools.skills_guard import scan_skill
r = scan_skill(Path('<skill-dir>'), source='skills.sh')      # a Path, not a str
print(r.verdict)
for f in r.findings:
    print(' ', f.severity, f.pattern_id, f.file, f.line, repr(f.match))"
```

Iterate candidate rewrites on a **copy** of the skills tree (`shutil.copytree` into a scratch dir) and
rescan until the verdict moves; only then edit the repo. After merging one file into another umbrella,
scan **every** skill directory — a merge can make an umbrella you never edited dangerous on its own.

The scanner scores a multi-line command as the joined statement and reports the line that *opened* it,
so a finding can appear above the text that actually matched. Reason over `f.file:f.line`, not over your
own reading of the markdown.

**Only `critical` and `high` findings change the verdict** — the roll-up is `critical → dangerous`,
`high → caution`, and `medium` / `low` alone → `safe` (`tools/skills_guard.py`, `_verdict_from_severities`).
So when reading a findings list, triage by severity first: a package whose worst findings are `medium`
installs `safe` with no `--force`, and rewriting those medium lines buys nothing. Clear every `critical`
and `high`; leave the rest.

## What trips it in documentation

Every `.md .py .sh .json .yaml` file in the package is read — commands and quoted examples included, and
so is a table that merely *names* a blocked pattern. Measured triggers, each with a rewrite that keeps
the meaning:

| pattern | severity | what triggers it | rewrite that clears it |
|---|---|---|---|
| `env_exfil_curl` | critical | a network request carrying an auth header built from a token variable, both on one statement | hoist the header into its own variable, or show a placeholder header |
| `hermes_env_access` | critical | the profile env file written as a literal home-relative path | `$HERMES_HOME/.env` — the same file, and it follows the profile |
| `curl_pipe_shell` | critical | a quoted download-piped-to-shell one-liner inside prose about blocked patterns | describe it ("a pipe-to-shell download") |
| `system_passwd_access` | critical | the system account file path in prose | "a system path outside the workspace" |
| `echo_pipe_exec` | critical | an `echo` of a JSON payload piped into an interpreter | describe the piped invocation |
| `curl_pipe_python` | critical | a `curl` whose output is piped to an interpreter (`| python3 -c …`) — the pipe-to-interpreter sibling of `curl_pipe_shell`, and it fires on a documentation example just as readily | pipe to `jq -r` instead, or describe the parse step |
| `ssh_dir_access` | high | the user's SSH directory written home-relative (a tilde path), e.g. in a key-upload example | show a placeholder path (`<path-to-your-private-key>`) |
| `dump_all_env` | high | a bare environment dump followed by a pipe; a profile-env operand inside a pipeline; **or a markdown table cell that ends with the bare word for the process environment — the table's own column separator supplies the pipe** (measured 2026-10-04) | quote the path (`"$HERMES_HOME/.env"`), read the one variable by name, or word that cell as 「进程环境变量」 instead of the bare word |
| `sudo_usage` | high | the privilege-escalation word anywhere on the line | describe the operation instead of naming the command |
| `python_os_environ` | high | the interpreter's process-environment mapping named outside a comment or docstring — the bare mapping is what scores; a single-variable accessor read (`.get(…)` directly on it) is exempt, and a `#` anywhere *earlier* on the line exempts the line | reads go through the single-variable accessor form; a **write** (removing a variable, setting a re-entry marker) goes through the C-level spellings — `os.unsetenv` / `os.putenv` — which score nothing and still reach the process a later `os.exec*` hands the environment to; a comment *after* the code does not exempt the line; otherwise keep the snippet outside the package |
| `destructive_home_rm` | critical | a recursive delete whose target is written home-relative (a tilde path), **including a fenced example in a reference** — measured on a removal skill's orphan recipe | write the target with the pack's profile placeholder (`<home>/skills/<name>`), which is the convention the rest of these references already follow |

**This file is the worked example.** Its pattern table describes each trigger instead of reproducing it,
which is why it scans `safe` inside `install-hermes-skills`; re-run the probe above after editing it —
the table is the part of the package most likely to make the package uninstallable.

### A note about a trigger reproduces the trigger

Measured 2026-10-04, shipping a Discord-thread skill: a two-row table comparing where each machine's proxy
comes from ended one cell with the bare word for the process environment, and the table's own column
separator completed the rule's literal shape — **high**, package verdict `safe` → `caution`. Rewording that
cell cleared it. The paragraph explaining the trap then tripped the same rule in its own text, because it
quoted the shape instead of describing it. Two rules follow:

- Re-scan after the rewrite: a table cell is prose to this scanner, and a markdown table's column
  separators are pipe characters.
- When documenting a trigger, **describe** it — which word, immediately followed by what — and never
  quote it.

Two consequences worth stating before spending a round trip:

- **A dev or repair snippet that reads or mutates the interpreter's process-environment mapping cannot ship as
  written** — the rule fires on the mapping's bare name, and a comprehension that iterates the whole
  mapping to build a *modified copy* for a child process is the usual shape. Five ways out, in this order: **first check whether the tool itself takes a flag that removes the need**
  — wanting a doctored environment is the smell, not the solution (measured: a Swift build failed only
  because the runtime exports a `SDKROOT` pointing at a different SDK than the selected toolchain;
  `xcrun --sdk macosx` made the same build succeed against the untouched environment, so the rewrite was
  **deleted** rather than reworded and the verdict returned to `safe`); point *this process*
  at another profile or home through the tool's own override/context setter when that was the goal
  (measured: swapping it in for the env rewrite cleared the finding → `safe`); read one variable through the
  accessor form; do a **removal or marker write** with the C-level spellings instead
  (measured: a re-exec guard's four `high` findings — `safe` → `caution` — cleared back to `safe` with the
  meaning intact, because the exec family carries the current process environment either way); else keep the
  snippet at the repo root as tooling, where no skill directory owns it and the scan never sees it.
- **Rewriting to pass the scan is a content decision, not a mechanical edit.** A token placeholder is no
  longer copy-pasteable, and quoting a scanner false positive in a troubleshooting table is itself what
  trips the rule. Name the lines you would change and what each rewrite costs, and let the author choose
  between that and leaving the skill out of the hub.

## `.skillignore` cannot clear a block on the GitHub route

`scan_skill(dir)` honours a gitignore-style `.skillignore` (or `.clawhubignore`) in the directory it
scans — syntax and a measured verdict flip are in
`references/install-hermes-skills-registry-routes.md` § `.skillignore`. But the ignore file is a
**dotfile at the bundle root**, and the GitHub bundle builder drops root dotfiles before the scan runs
(`tools/skills_hub_github.py:171-174` — `_skip_bundle_file` tests the basename; applied to every bundle
member at `:338`), so a committed and pushed `.skillignore` is not in the quarantine directory
`scan_skill` reads. **Code-verified, not yet reproduced end to end**: the registry-routes claim that
committing the file is enough is the unresolved half, and ClawHub's own publish path is the route to
test if an ignore file ever has to ship. Two consequences:

- The lever is real for a **local** scan — it tells you which files drive a verdict — and it is not how
  a published GitHub/skills.sh package clears a block. Changing what the scanner reads (rewriting the
  literals) is.
- The skip tests the **basename** only, so nested dotfiles still ship: `.github/scripts/x.py` is part of
  the bundle (`references/install-hermes-skills-repo-structure-routing.md`).

## Shipping order

1. Edit the package in the repo; scan every skill directory locally, on a copy.
2. Commit **and push** — the hub fetches from GitHub, so an unpushed edit is invisible to `install`.
3. Install from the repo: `hermes skills install <owner>/<repo>/skills/<name> --category <cat> -y`.
4. Refresh what is already installed: `hermes skills update <name>`, then `hermes skills check <name>` to
   confirm it landed, rather than trusting the printed `Updated N skill(s).`
5. An in-repo rename is not shipped by a push alone — the install identity changes with it:
   `references/install-hermes-skills-renaming-a-skill-pack.md`.
6. A test-only commit that should never have been pushed can be dropped on a single-writer repo with
   `git reset --hard <prev>` followed by `git push --force-with-lease origin <branch>`.
