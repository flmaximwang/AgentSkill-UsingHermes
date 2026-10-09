# The git payload repo that mirrors the profile's `skills/`

The protein-design profile's skills tree is not a lone copy: it is mirrored
both ways with `/Users/maxim/Repositories/Agent-ProteinDesign` (a Hermes
*profile distribution*: `hermes profile install <repo>` recreates SOUL.md +
skills on another machine). Any layout change made in the profile alone is
undone by the next `pull`, so treat the repo as part of the job.

## Repo shape

| Path | Role |
|---|---|
| `distribution.yaml` | profile `name`, version, `distribution_owned:` paths, `env_requires:` (install-location paths the payload references — the only place they belong) |
| `skills/` | the OWNED set only — not a copy of the profile |
| `SOUL.md`, `assets/` | persona + avatar slot |
| `scripts/sync.py` | `push` (profile → repo), `pull` (repo → profile), `check` (both directions, writes nothing) |
| `scripts/skills_owned.py` | classifies every `SKILL.md` in the profile: owned / reproducible-by-Hermes / dot-archived / venv carrier |
| `scripts/skills_excluded.txt` | scope gate: profile-relative paths deliberately out of the distribution. **The only record of an intentional removal** — delete a line there and the next export ships that skill again |

## Semantics that decide what survives

- **`check` first, always.** `python3 scripts/sync.py check` prints both
directions and writes nothing. `pull --dry-run` prints the same for one
direction.
- **`pull` DELETES from the profile** everything the repo does not own (and
everything listed in `skills_excluded.txt`). Never run a real `pull` right after
a profile-side change: read the dry-run's removal list first, and include the
repo-side half of the change in the same pass.
- **`push` mirrors entries it can classify, so a path that vanished from the
profile by a MOVE is not reliably removed in the repo.** Observed: `push`
reported `N added/updated, 0 removed` while the old root `SKILL.md` was still
sitting in the repo, so pushing alone leaves a duplicate stale copy. After any
layout move, `git -C <repo> status` and `git rm` (or `git mv`) the stale paths
explicitly, then re-run `check` — it should report only expected drift.
- **Classification is keyed on the `SKILL.md`'s parent dir name and its
skills-relative path** (`skills_owned.py::classify`). Nesting an umbrella
changes its path but not its name, so a still-owned umbrella stays `owned`
(verify with `python3 scripts/skills_owned.py --explain` before exporting) — but
a skill whose dir name matches a bundled or hub-installed name is classified
`reproducible` and silently dropped from the payload.
- **Symlink-free is enforced** (`sync.py` exits non-zero on any symlink under
the repo); skill dirs carrying machine-local venvs (`.env/`, `.venv/`,
`node_modules/`) must not be copied in — the script reports them as venv
carriers.

## Order for a layout change (e.g. cleaning hybrid buckets)

1. Backup tar the buckets (see the skill's step 5).
2. Clean the profile.
3. Apply the same nesting in the repo (`git mv` the umbrella `SKILL.md` +
   support dirs into `<H>/<H>/`, `git rm` anything left at the old path).
4. Update the repo's own prose in the same commit: the README table that lists
   owned sub-directories, and any `distribution.yaml` / `sync.py` comment that
   names the old path.
5. `python3 scripts/skills_owned.py --explain` → the umbrellas must still show
   as `owned`; `python3 scripts/sync.py check` → only drift you expect.
6. Leave the commit to the user unless asked: `push` writes the export, review
   `git status`, commit.
