# Distribution package retirement — migrate skills to AgentSkill packs, then retire the repo

A **distribution package** (`~/Repositories/Agent-<Name>/`) is a git repo whose `distribution.yaml → name`
is a profile name. `hermes profile install` consumes it as a payload: SOUL.md + own skills + assets/.
Retiring one means migrating its skills into the appropriate `AgentSkill-*` pack repos, then emptying
the distribution repo and marking it retired.

## When to retire

- The user decides to consolidate: "分发包下线，拆分到 AgentSkill" — distribution packages are
  redundant once their skills live in AgentSkill packs.
- A profile is deleted and its distribution package is no longer needed.
- Multiple distribution packages hold overlapping skill sets (measured: three packages shared 57
  identical `life-science-research/` skills).

## The mapping — by skill category, not by distribution package

Do NOT map distribution package → AgentSkill pack directly. Multiple packages share the same skills;
mapping by package produces duplicates. Instead, collect the **union of all skills** across all
distribution packages, then map each skill by its **category** (first path segment under `skills/`):

| Skill category | Target AgentSkill pack |
|---|---|
| `life-science-research` | `AgentSkill-LabProject` |
| `software-development` | `AgentSkill-SoftwareDev` |
| `research` / `note-taking` / `productivity` / `office` | `AgentSkill-UsingHermes` |
| `github` | `AgentSkill-UsingGithub` |
| `devops` / `mlops` / `data-science` | `AgentSkill-SoftwareDev` |
| `investment` / `finance` | `AgentSkill-QuantInvestment` |
| `accountancy` / `apple` / `autonomous-ai-agents` / `media` | `AgentSkill-UsingHermes` |
| `(root)` | `AgentSkill-UsingHermes` |

Adjust the table to the packs that actually exist on the machine. The principle: **a skill's category
decides its home pack, not which distribution package it came from**.

## Procedure

1. **Inventory** — for each `Agent-*/` repo, walk `skills/**/SKILL.md`, collect
   `{name: (category, abs_path)}`. Deduplicate by name (first occurrence wins).
2. **Check target packs** — for each `AgentSkill-*` repo, collect existing skill names. Skip
   skills already present.
3. **Migrate** — `shutil.copytree(src_skill_dir, dst_pack/skills/<cat>/<name>)`. Create
   parent dirs as needed. Do NOT merge into existing skill directories — copy the whole
   directory or skip.
4. **Commit and push** — for each AgentSkill pack: `git add -A && git commit && git push`.
   If the pack is not a git repo, `git init` + `git remote add origin` + `git push -u origin main`.
   If the GitHub repo doesn't exist, `gh repo create flmaximwang/<name> --private` first.
5. **Retire the distribution repos** — for each `Agent-*/`:
   - `git rm -r --quiet skills/`
   - In `distribution.yaml`, prefix `name:` with `retired-` (e.g. `name: retired-quant-investor`)
   - `git add distribution.yaml && git commit -m "retire: skills migrated to AgentSkill packages"`
   - `git push origin main` (if it has a remote; local-only repos just commit)
6. **Verify** — `find <pack>/skills -name SKILL.md | wc -l` for each target pack;
   `git -C <dist> log --oneline -1` shows the retire commit; `git -C <dist> status` is clean.

## Pitfalls

- **Deduplicate by skill name before migrating.** Three distribution packages may hold the same
  `alphafold-skill/` — migrating all three produces three copies in the target pack. Collect the
  union first, then migrate each unique name once.
- **Check if the target pack is a git repo before committing.** `AgentSkill-QuantInvestment` and
  `AgentSkill-SoftwareDev` were plain directories with no `.git` — `git add` fails silently
  (exit 128). `git init` + `git remote add` + `git push -u origin main` first.
- **Check if the GitHub repo exists before pushing.** `git ls-remote git@github.com:flmaximwang/<name>.git`
  returns "Repository not found" for repos that don't exist yet. `gh repo create` first.
- **The migration script is idempotent** — it skips skills already in the target pack. Safe to
  re-run after a partial failure.
- **Backup before deleting skill directories from profiles.** When cleaning up duplicate skill
  directories across profiles (e.g. five profiles each holding `skills/software-development/`),
  `cp -R` to `~/.hermes/backups/` before `rm -rf`. Use `filecmp.cmp(a, b, shallow=False)`
  to check whether two copies are identical before deleting either.
- **After retiring distribution packages, profile-local skills that already exist in packs are still
  there** — retirement only empties the `Agent-*/` repos, it does not touch profile skill directories.
  A follow-up dedupe pass (`sweep-plan.py dedupe --profile all`) is required to remove the 804+ local
  copies that are identical to (or only differ from) what's now in the packs. The dedupe script
  handles three cases: identical SKILL.md → delete local; local has old profile path references
  the pack lacks → restore to pack first, then delete; pack is newer → delete local.

## Verification

```bash
# Each target pack's skill count
for p in AgentSkill-LabProject AgentSkill-UsingHermes AgentSkill-SoftwareDev; do
  echo "$p: $(find ~/Documents/AgentSkill/$p/skills -name SKILL.md | wc -l)"
done

# Each distribution repo is retired
git -C ~/Repositories/Agent-QuantInvestor log --oneline -1
# → retire: skills migrated to AgentSkill packages

# No skills/ left in distribution repos
ls ~/Repositories/Agent-QuantInvestor/skills/ 2>/dev/null
# → (empty or not found)
```
