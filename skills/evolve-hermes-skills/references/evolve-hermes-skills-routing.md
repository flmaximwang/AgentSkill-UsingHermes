# Routing a finding to its owner

The decision half of `evolve-hermes-skills`: which of the touched skills the user maintains in an external
repo, what the repo route delivers that the in-place route cannot, and the exact sequence for each. The
ladder is a ladder, not a menu: walk rung 1 when it applies, and step down to rung 2 only when the skill
genuinely has no repo.

Contents: §1 detect where each skill lives · §2 the one clarify · §3 rung 1 — the external repo ·
§4 rung 2 — the profile copy, and what it costs · §5 promoting a rung-2 skill · §6 routing failure branches

## §1 Detect where each skill lives

Run this before asking the user anything, so the `clarify` presents a mapping to confirm rather than a
question to answer from memory. Two stores, one per rung.

**The hub lock** — `$HERMES_HOME/skills/.hub/lock.json`, keyed by skill name. A real entry (measured
2026-09-30):

```json
"update-hermes-skills": {
  "source": "skills.sh",
  "identifier": "skills-sh/flmaximwang/AgentSkill-UsingHermes/skills/update-hermes-skills",
  "install_path": "hermes/update-hermes-skills",
  "metadata": {
    "repo_url": "https://github.com/flmaximwang/AgentSkill-UsingHermes",
    "source_revision": "5798d4dd14c92c73f6edf8a345c478eaf8d0191f"
  }
}
```

```python
import json, os
lock = json.load(open(f"{HERMES_HOME}/skills/.hub/lock.json"))["installed"]
e = lock.get(name)                      # name = the skill's own name, i.e. what `skills_list` shows
if e: print(e["source"], e["identifier"], e["install_path"], e["metadata"].get("repo_url"))
```

Three things fall out of one lookup: `install_path` is the installed directory under
`$HERMES_HOME/skills/` (so the edit target is `$HERMES_HOME/skills/<install_path>/SKILL.md`);
`identifier`'s second and third segments are the `owner/repo`; `metadata.repo_url` names the same repo
directly and `source_revision` is the commit the installed copy came from.

**The clone** — the repo the user actually edits. Convention on this machine: `~/Repositories/<repo>`. Do
not assume the path from the lock; confirm the clone is the same repo:

```bash
git -C ~/Repositories/<repo> remote get-url origin      # must name the lock's owner/repo
git -C ~/Repositories/<repo> rev-parse --abbrev-ref HEAD # expected: main
git -C ~/Repositories/<repo> status --short              # other writers' dirty files, before you add yours
```

Measured 2026-09-30: `AgentSkill-UsingHermes` and `AgentSkill-ObsidianManagement` are the two clones that
match hub-installed skills on this profile; both are `main`, both from `flmaximwang`. A repo under
`~/Repositories` with **no** installed skill behind it (there are several) is not this skill's business.

**No lock entry** → rung 2. That covers three shapes, and the fix is the same for all of them: agent-created
skills (`.usage.json` `created_by: "agent"`, no lock entry — including everything the curator creates), a
`cp -R` install the user made by hand (`Source: local`), and skills that live inside another skill's tree.

## §2 The one clarify

**One call, recommended-first, listing every affected skill.** The user handed you a batch; a per-skill
question chain turns a two-minute review into a form. Four questions, in this order:

1. **The mapping** — present the detected repo per skill and ask it confirm-or-correct. This question is
   not optional even though you already know the answer: the lock cannot see a repo the profile never
   installed from, so the user may name one you missed. Recommended choice: *"the detected mapping is
   right"*.
2. **Which findings to apply** — recommended: all of them. The alternatives are "only the repo-backed
   ones" and "show me each finding first", which is the right ladder when the report has findings whose
   receipts the user has not seen.
3. **A rung-2 skill's future** — recommended: edit in place now. Alternative: promote it into a pack repo
   as part of this run (§5). Name the cost of staying local in the question text, in one clause.
4. **Phase 3** — recommended: run `darwin-skill` on the skills that were edited, one at a time with its
   checkpoint. Alternative: only the largest gap; or apply the edits and stop.

Each of those has a drop signal: drop Q3 when no finding touches a rung-2 skill, and drop Q4 when nothing
was edited.

## §3 Rung 1 — the external repo (the complete route)

The repo is the source of truth; the profile is a build artifact. So the edit lands in the clone and the
profile is refreshed from it. Order matters — nothing in the profile changes until the update runs.

```bash
cd ~/Repositories/<repo>
git status --short                        # snapshot other writers' files before you stage anything
# 1. edit skills/<name>/SKILL.md and its references
python3 scripts/auto-generate-skill-structure.py <name>    # regenerates the ## Skill Structure block
python3 scripts/verify-skill-package.py skills/<name>      # tree counts + pointer lint, exit 1 on any problem
git add skills/<name>                                      # pathspec-scoped: never `git add -A`
git commit -m "docs(skills): <what changed>"
git push origin main
hermes skills update <name>                                # profile copy ← pushed revision
hermes skills check <name>                                 # read back: expect up_to_date
```

Three facts about that last pair, from the sibling skill measuring them (`update-hermes-skills`):

- `update` **skips a skill whose installed copy has local edits** and still exits 0. Since the repo is the
  source of truth, `--force` is correct here — but only after the push, never before, or the fix dies in
  a directory the next update replaces.
- `update` **pins the recorded source**, so it only ever moves a skill forward inside its own lineage; a
  finding that says the skill should live in a different repo is an uninstall + install, not an update.
- The category is read from `install_path`'s parent, so the update keeps the skill where it is.

### Reconciling a drifted installed copy

`update` is one-directional: it moves a *pushed* revision into the profile and can never publish a local edit
outward. So a non-empty

```bash
diff -rq ~/Repositories/<repo>/skills/<name> "$HERMES_HOME/skills/<install_path>"
```

is not a state to overwrite — it is a finding to judge, and it belongs to this run, not to `update`:

1. **Read the diff before touching anything.** Two ordinary causes look identical in the output: the
   installed copy is *behind* (normal right after a push — the update is the whole fix), or it is *ahead /
   different* — content the clone does not have, written into the profile tree mid-session by an agent, the
   curator, or a hand fix. `__pycache__/` and other build residue are neither: name them and move on.
2. **Judge the block, never the direction.** Content only the installed copy holds may be exactly the
   optimisation this run was called to find, or a stale experiment. Read it against the clone's text and
   say which, with the reason — a user correction from this session is the best evidence available to you.
3. **Keep it by backporting into the clone, byte-exact.** Match the block by a unique prefix, take the
   replacement's exact bytes from the installed copy so quoted measurements stay identical, regenerate the
   tree, commit **the backport alone** (pathspec), push.
4. **Only then refresh the profile:** `hermes skills update <name>`. Expect
   `kept your local edits` and pass `--force` — the skip test compares the *recorded* hash against the
   copy's bytes, so any copy that was ever edited is skipped even after the backport made the two trees
   identical. `--force` here is safe *because* step 3 already put that content in the pushed revision.
5. **Read back three things:** `diff -rq` empty (ignoring `__pycache__`), `hermes skills check <name>` →
   `up_to_date`, and the lock's `metadata.source_revision` equal to the clone's `HEAD`.

A reconcile that stops at step 3 leaves the profile on the old revision; one that jumps to step 4 destroys
the foreign content. Name the foreign content in the report — never commit another writer's work silently.

**A repo-backed skill with no lock entry yet** (the first delivery of a new skill): install once, and the
lock entry appears —

```bash
hermes skills install <owner>/<repo>/skills/<name> --category hermes -y
```

For this pack the identifier form is the three-segment `flmaximwang/AgentSkill-UsingHermes/skills/<name>`
(`skills.sh` adapter), and the category is the skills-root directory the skill should occupy
(`hermes` for this family).

**A running session does not see the new files until its next session** (CLI `update` clears the cache as
it writes; a gateway/desktop session picks them up on the following session, or immediately with
`/reload-skills`). Say which one the user is in when reporting.

## §4 Rung 2 — the profile copy, and what it costs

```bash
$HERMES_HOME/skills/<install_path or bare name>/SKILL.md     # edit; then the sibling files
```

Then run the generator and the lint from **inside the installed package** only if it ships them: an
installed copy keeps whatever `scripts/` the repo had at install time, so a rung-2 skill with a `scripts/`
dir has its own copy and a rung-2 skill without one has no generator at all. Hand-verify the pointer
references by hand in that case, or run the repo's lint against the installed path (it is stdlib-only and
takes a path).

**The cost, to state in the report, not to bury:** a skill with no lock entry is invisible to
`hermes skills check`, `hermes skills update`, `hermes skills audit` and `hermes skills uninstall`. The
edit has no update path, no drift detection and no uninstall; the only backup is the curator's pre-run
`tar.gz` snapshot. Two consequences the user should hear in the same breath: the edit will not survive a
reinstall from a repo that also ships the skill (the hub replaces the directory wholesale), and no future
`evolve-hermes-skills` run can tell whether the file has drifted — there is nothing to drift from.

That is the honest trade, and it is why §5 exists.

## §5 Promoting a rung-2 skill into a pack repo

The upgrade path when the user picks it in the clarify. It is an install, not a copy-in-place, or the
profile ends up with two copies of the same skill competing for the same trigger:

```bash
# 1. copy the skill into the repo, then fix it up as a pack member
cp -R "$HERMES_HOME/skills/<path>/" ~/Repositories/<repo>/skills/<name>/
#    frontmatter = name + description only; references prefixed <name>-<topic>.md; body routed
python3 scripts/auto-generate-skill-structure.py <name>
python3 scripts/verify-skill-package.py skills/<name>
git add skills/<name> && git commit -m "docs(skills): add <name>" && git push origin main
# 2. install it back from the repo (this is what creates the lock entry)
hermes skills install <owner>/<repo>/skills/<name> --category <category> -y
# 3. only now remove the loose local copy, and confirm the install landed first
hermes skills list | grep "<name minus its last 3 chars>"  # one row, source skills.sh, category <category>
rm -rf "$HERMES_HOME/skills/<old path>/"
```

Match a **prefix**, not the full name: `hermes skills list` elides long names (`maintain-hermes-mem…`,
measured 2026-10-02) and has no wide/json flag, so a full-name `grep` finds nothing for a skill that
installed fine — `hermes skills check <name>` prints the name in full, and the lock entry (keyed by full
name) is the authoritative "exactly one" check.

Step 3 is the step to slow down on: the local copy has no lock entry, so nothing will warn about the
duplicate — a leftover copy shows up as a second skill with the same name and the same description, and
which one loads is then a coin toss. Promote, verify the new row, then delete.

Also worth telling the user: a promotion changes the skill's load path and its installed `files` list, so
any note that cites the old path goes stale in that same commit.

## §6 Routing failure branches

| Trigger | First fix | If it still fails |
|---|---|---|
| Lock has no entry, user says a repo exists | confirm `git remote get-url origin` on the candidate clone | install from that repo once (rung 1 step "no lock entry yet") so the lock exists, then edit and update |
| Lock entry exists but the clone is missing | `git clone <repo_url>` into `~/Repositories/<repo>`, then re-check `source_revision` against the clone's log | clone the exact `source_revision` (`git checkout <sha>`) before editing, so the diff is real |
| Clone's `HEAD` is behind the installed revision | `git pull --ff-only`; the installed copy came from a commit the clone has not got | `git fetch && git log --oneline -3` and report the divergence before editing — do not force a merge on the user's repo |
| `git status --short` shows files you did not touch | leave them alone; stage with a pathspec and name them in the report | if one of them is the same file you edited, stop and re-read the file — a concurrent writer owns it |
| `hermes skills update` answers "kept your local edits" | the recorded hash no longer matches the copy — run the copy-ahead `diff -rq` first, backport anything the clone lacks, push, then `--force` (§ *Reconciling a drifted installed copy*) | if the diff shows the installed copy is merely *behind* the clone, `--force` straight away and report which revision is now installed |
| Skill has no `lock.json` entry and no repo, and the user wants neither promotion nor an in-place edit | report it as dropped with its receipts | queue it in the report's "not done" list |
