# Profile naming and renaming — depth

## Grounding a naming proposal before you write options

Run these *first*, then propose; put the counts in the answer so the user can check them:

```bash
hermes profile list                                     # names, model, gateway state, alias, token-conflict warnings
grep -rn 'profiles="' ~/.hermes/hermes-agent/website/docs/user-guide/multi-profile-gateways.md   # the docs' own example vocabulary
ls ~/.hermes/profiles/.deleted/                          # names this user already tried and dropped
ls ~/.local/bin | grep -v -E '^(python|pip|uv|node|npm)' # wrapper scripts = every profile that ever existed
```

A candidate name is proposable only when it traces to (a) the docs' example vocabulary, (b) a name the user
already uses (profile, vault, repo, lab), or (c) a measured fact. Anything else is a placeholder — say so
explicitly or leave it out. Suffixes invented on the spot to carry a meaning are the failure mode the user
tests for.

## Where "scope" (single-project vs multi-project) belongs

| Carrier | Holds | Why not the name |
|---|---|---|
| `terminal.cwd` in `config.yaml` | the one project root a dedicated profile owns | structure, invisible in the name |
| `profile.yaml: description` | one-line 职责 + scope label (`hermes profile describe <name> -m "…"`) | shown in the picker / kanban, editable without a rename |
| `hermes project create/add-folder` | the several workspaces a multi-project profile serves (desktop session grouping, kanban worktree convention) | `projects.db` state is per profile; audit with `sqlite3 <profile>/projects.db 'select count(*) from projects;'` |
| the profile name | nothing but the stable 职责域 | a rename costs gateway downtime + hardcoded-path fixups; naming by scope means renaming every time the scope changes |

An empty `projects` table means the profile is *not* structurally multi-project yet, whatever its content
spans — say that instead of confirming the user's framing. Registering the projects is the fix, not a rename.

## Reading the rename audit output

`grep -rl … "profiles/<old>" ~/.hermes/profiles/<old>` classifies the hits:

- **Executable/config → must fix.** profile-local `venv/bin/<console-script>` shebangs, `venv/bin/activate*`
  (one `VIRTUAL_ENV=` line), `cron/jobs.json` prompts holding `bash /Users/…/profiles/<old>/scripts/…`,
  `scripts/*.sh` that grep the profile's `.env` by absolute path. Rebuild the venv or rewrite the shebangs;
  edit the job prompt via `hermes -p <new> cron`.
- **State/machine-written → ignore.** `gateway.pid`, `gateway.lock`, `gateway_state.json`,
  `.curator_backups/`, `skills/.curator_ledger.jsonl`, `checkpoints/store/*.json`, `sessions/`, `logs/`.
  Excluding these is what makes the count mean something.

Ranking is the deliverable: a profile with a local venv, live cron jobs and a running gateway is a
multi-step migration; one with zero hits is a two-command rename.

## Post-rename checklist

1. `hermes profile list` — new name present, old name gone, no token-conflict warning.
2. Grep the moved profile for the old name (the audit command again, now expecting zero) and fix SOUL.md's
   self-name plus the vault `README.md` header, which are the two files a rename never touches.
3. Restart the gateway if that profile had one (`hermes -p <new> gateway start`); a launchd/systemd unit is
   not re-created by the rename.
4. One real call: `hermes -p <new> chat -q '只回复两个字：可用' -Q`.
5. Reopen that profile's desktop window — the picker and session grouping are per session.

## Housekeeping before reusing or trusting an old name

- A leftover stub directory for a previous name (`profiles/<old>/` containing only `auth.lock`) makes `-p
  <old>` resolve to a half-profile; delete it.
- `profiles/.deleted/<name>` is a tombstone, not a profile — and `gateway_state.json` can keep mentioning a
  deleted profile ("still run their own gateway") long after its unit is gone. Treat those lines as stale
  unless `launchctl list | grep hermes` confirms the unit.
- Two profiles sharing a `(platform, token)` pair blocks `hermes gateway migrate --multiplex`; a rename does
  not fix that — the duplicate needs its own bot token or the token removed.
