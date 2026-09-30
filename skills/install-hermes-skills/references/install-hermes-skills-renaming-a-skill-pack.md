# Renaming a skill (or a whole pack)

A skill's name is not a label. It is the directory name, the frontmatter `name:`, the prefix of every
reference the skill owns, the target of every cross-skill pointer, the heading of its generated tree —
and, in any profile that already has it, the address of its install record. A rename that stops before
the last of those ships a pack whose own instructions name skills that no longer exist.

## 1. Fix the vocabulary before touching a file

Read the pack's `README.md` first: it is the naming authority, not your judgement of what the verb
"should" be. In `AgentSkill-UsingHermes` the accepted vocabulary is **install / remove / maintain /
update**, one definition each. Settle the whole mapping in **one** `clarify` — old name → new name for
every skill, plus what happens to the verbs that are not in the accepted list. A rename requested in one
line can still be seven renames plus their cascades, and the answer decides both the sweep and the commit
split.

## 2. Enumerate the cascade

For each renamed skill, the change has to reach:

1. the directory — `git mv`, so history follows the file;
2. `name:` in `SKILL.md` frontmatter, which must equal the directory name;
3. every reference filename, whose prefix is the skill name (`<skill>-<topic>.md`);
4. every pointer to those files: in this skill's body and its reference tables, in its siblings, and in
   any other pack that cites it;
5. the generated `## Skill Structure` trees — regenerate them (`scripts/README.md`), never hand-edit the
   block;
6. the install record of every profile that already has the skill (§6).

## 3. One substitution table, applied to names and text alike

Drive directory names, reference basenames and file contents from the **same** table, so text and
filenames cannot diverge. Keep the swap mechanical (replace the verb, keep the object) — that is what
makes the result reviewable instead of rewritten:

```python
SUBSTITUTIONS = [("control-hermes-", "maintain-hermes-"), ("manage-hermes-", "maintain-hermes-"),
                 ("debug-hermes-gateway", "maintain-hermes-gateway")]   # longest/most specific first
```

Apply it to `path.name` as well as to the body, rename the directory first so the reference files are
found under their new path, then print what is **left** in the whole tree. The leftovers are the artifact
that proves the sweep is complete — or that the exemptions in §4 were deliberate.

## 4. Exempt verbatim evidence, and declare the exemptions

Rewriting a name that appears inside a quoted transcript falsifies the receipt the transcript was kept
for. Never sweep, never silently skip — exempt and report:

- captured output and the commands that produced it (`$ hermes skills search <old-name>` … `results: 25`);
- measured tables, error strings, and anything the document introduced as reproduced output;
- history statements: "absorbed from the former standalone `<old-name>` skill" describes the past and is
  *meant* to read as a name that no longer exists.

The test: would the new spelling turn the sentence into a claim that was never true? If yes, keep it and
list it (file + line count) in the report.

## 5. Verify pointers against a pre-change worktree, not against zero

A lint run after the rename cannot separate pre-existing noise from new breakage, and a mature pack
carries plenty of both. Materialise the base commit and diff the two runs:

```bash
git worktree add -q --detach <scratch>/before <base-commit>
python3 scripts/verify-skill-package.py skills/<name>          # run on both trees; diff the two lists
```

Identical counts, with an entry-by-entry diff showing only paths that *moved with the renamed
directories*, is the evidence that the rename broke nothing — state it that way rather than asserting "no
dangling references". Noise the lint reports in **both** runs is not breakage: foreign repos' paths,
generic illustrations (`references/<topic>.md`), files of the Hermes source tree. And resolve the pack's
own cross-skill convention — a backticked sibling name followed by `→ references/<file>` — against
**that sibling's** directory, or every sibling pointer reports as dangling; `verify-skill-package.py`
does this by default (`--skills-root`).

Then confirm the two identities per skill: frontmatter `name:` equal to the directory name (an empty
`SKILL.md` placeholder is skipped, not filled), and `scripts/auto-generate-skill-structure.py --check`
a no-op after the regeneration run.

## 6. Re-install wherever the old name is already known

A hub-installed skill is addressed by the repository path ending in its directory name, so after the
rename the old name is a dead identifier: `hermes skills check <old>` answers **`unavailable`** — not
`orphaned` — because the adapter cannot fetch a path that no longer exists upstream. Per profile:

```bash
hermes skills inspect "<owner>/<repo>/skills/<new>"        # read-only: name + trust, before anything
hermes skills uninstall <old> -y
hermes skills install "<owner>/<repo>/skills/<new>" --category <cat> -y
```

A **local** copy has no lock entry, so nothing migrates it and nothing can uninstall it — but do not
start with a hand copy. When the repo still carries the skill, installing its identifier again
(`hermes skills install "<owner>/<repo>/skills/<new>" --category <cat> -y`) replaces the colliding copy
with the upstream content **and** writes the lock entry the copy was missing, so it becomes updatable
from then on; hand-copying is the residue only when that route is blocked (§7). Either way, check what a
directory rename does *not* do: moving the directory leaves the old `name:` inside the copy — measured on
this pack, a moved hand copy still read `name: debug-hermes-gateway` while living in
`maintain-hermes-gateway/`. Verify the whole installed tree at once
(`grep -m1 '^name:' <home>/skills/<cat>/*/SKILL.md` against the directory names), then let the new names
take effect (`/reload-skills`, or a new session).

Two lock-side rules ride along: `install_path`'s last segment must equal the lock key, or `check` answers
`invalid_install` and updates stop silently (`maintain-hermes-skill-cards` — `scripts/align_skill_card.py`
fixes the three strings), and `update` cannot move a skill to a different source at all
(`update-hermes-skills` § "A source change is uninstall + install").

Poll for drift in the same pass, per skill: `diff -rq <repo>/skills/<name> <home>/skills/<cat>/<name>`.
A copy that differs because it is *ahead* means lessons live only in the installed copy and were never
backported; a hub copy with any local edit is skipped by every later `update`. Report both lists rather
than regenerating over them.

## 7. When a renamed skill cannot be re-installed

Do the directory, frontmatter and content work, then say plainly that the hub route is closed and why — a
`dangerous` verdict is not overridable, and an ignore file cannot exempt `SKILL.md`
(`references/install-hermes-skills-scan-gate.md`). Name what the leftover copy is: local, no lock entry,
invisible to `check` / `update` / `uninstall`. Offer the one real alternative (rewriting the flagged
literals in the repo) with its cost, and let the author choose instead of hand-copying quietly.

## 8. Renaming the pack's repo

- **Renaming the pack repo is a four-point sync.** `gh repo rename <new>` keeps an automatic redirect,
  but it does not touch the local remote, the README's install command, or the repo description: also
  `git remote set-url origin git@github.com:<owner>/<new>.git`, update the install command's repo
  segment (a stale segment is a wrong install command that fetches nothing, not cosmetics), and
  `gh repo edit --description`. Verify with `gh repo view <owner>/<new> --json name,description`. Note
  that a private repo answers 404 to an unauthenticated `curl` — that check proves nothing, `gh` does.
