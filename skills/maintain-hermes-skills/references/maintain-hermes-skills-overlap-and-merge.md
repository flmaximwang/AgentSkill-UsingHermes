# Overlapping skill material — what merges, where it lands, what retires

A request that a skill's material "belongs in" another one is a decision request, and the decision has four
parts: map each name to its container, prove the overlap fact by fact, choose the landing place, then deliver
in the repo's order before retiring anything. Nothing in this file is new machinery — it is the order of
operations, plus the split that decides which skill a block of prose belongs to.

## 1. Map ownership before comparing content

Read the container off `skills/.hub/lock.json` → `installed.<name>`, never off the name or the directory
(every store that answers it: `references/maintain-hermes-skills-inventory-and-availability.md`). An entry
carries `install_path` (the directory under `$HERMES_HOME/skills/`), an `identifier` whose second and third
segments are `owner/repo`, `metadata.repo_url`, and `metadata.source_revision`.

Write that mapping onto the **three kinds this skill already names** — bundled / hub-installed / local —
because those are what decide what may be done to a name. Do not introduce a second taxonomy: a
repo-delivered skill's installed tree is a build artifact, and a name with no lock entry is profile-local
(agent-created, a `cp -R`, or a child inside another skill's tree), so nothing can check, update or
uninstall it. An *external* pack — one of the user's other repos, a registry — is not a fourth kind in that
table: it is a different repo, whose own conventions decide where its content is edited and whose copy
re-owns the material the next time it is installed (sibling `maintain-hermes-profile`).

A skill that has never been installed has no source of truth any tool can see, so writing new material into
a pack starts with a *first delivery*: the create-and-install, not an update, is what puts a lock entry
behind it (sibling `install-hermes-skills`).

## 2. Prove the overlap fact by fact, never by title or domain

Grep the **claims**, not the vocabulary: a table heading, a measured number, a command flag, a source path.
One line per source, and a hit on the receiving side counts as *stated* — quote its `file:line`:

```bash
for k in "<claim-keyword>" "<code-site>" "<measured-number>"; do
  printf '%-28s ' "$k"
  printf 'local: '; grep -rl -- "$k" <local-skill-dir> | tr '\n' ' '; echo
  printf 'pack:  '; grep -rl -- "$k" <pack-root>/skills | sed 's|.*/skills/||' | tr '\n' ' '; echo
done
```

The same keyword can carry a different meaning on each side — read the hits before believing them. Report
**two lists, not one**: *already there* (with the receiver's `file:line`) and *net-new*. "They overlap in
places" is not actionable, and it is the shape that produces a second copy of a rule that already exists.

Measured on a real merge (2026-09-30, the profile-local `skill-library-consolidation` → this pack): of 22
facts it stated, 6 were this skill's own subject, 12 already lived in a sibling, and 10 were duplicates that
had to be **dropped rather than moved**. A merge that carries every line across doubles always-loaded
context and buys nothing.

## 3. Decide the landing place before writing

1. `<pack>/README.md` — the naming authority. The verbs are fixed by it (`install` / `remove` / `maintain` /
   `update`, plus `evolve`); your reading of what a block "really is" is not a verb.
2. The receiving umbrella's `SKILL.md` route table and its `references/` filenames — merge into an existing
   reference when one already owns the subsystem.
3. Only then a new reference, named `<skill>-<topic>.md`.

**Split by subject, not by source file.** A merge usually carries two halves. The *decision* procedure
(container mapping, the overlap audit, the landing place, the two-list report) belongs to this skill; the
*mechanics* — uninstall + install for a category move, the `--force` conditions, upstream-diff audits, the
delivery read-backs — belong to the sibling that already owns them (`install-hermes-skills`,
`remove-hermes-skills`, `update-hermes-skills`). Sending mechanics into this body duplicates an owner that
exists, and this skill's own scope note would then disclaim itself.

The merge is not done when the file lands: the route row **and** the `description:` of the receiving skill
have to name the new entry point in the same edit
(`references/maintain-hermes-skills-authoring-conventions.md` § Structure and house style). Depth behind a
route row nobody reads never loads.

## 4. Deliver in the repo's order, retire last

Edit the clone → run the generator → `verify-skill-package.py` → commit (pathspec per skill, Conventional
Commits with a Chinese subject) → push `main` → `hermes skills update <name>` → read the entry back. The
commands are the sibling's: `install-hermes-skills` § Replacing an installed skill with a better bloodline
plus its relocation reference, and `update-hermes-skills` § Cost. Nothing reaches any profile until the
update runs, so an edit that stops at the clone is not delivered.

Retire the duplicate **only after** the delivery is verified: a local copy is a plain delete once the lock
has been grepped to prove it holds no entry, a hub-installed one goes through
`hermes skills uninstall <lock key>` (sibling `remove-hermes-skills`). Never delete content you have not
placed.

## 5. What the receiving side must not inherit

- **A second container table.** The kinds are one taxonomy, and §1 says which one; a merge that copies the
  source's table in produces two disagreeing "three things" lists in the same hierarchy.
- **A scope disclaimer.** "Installing and removing are the siblings" is true of the source; inside this
  skill it disclaims the skill's own subject and has to be rewritten rather than pasted.
- **Frontmatter beyond `name` + `description`** — a local skill's `version`, `author`, `tags` — and a
  `related_skills` list naming the receiving skill itself, which becomes self-referential.
- **Prior-session measurements as if they were re-run.** Every measured claim that enters the package must
  either be re-run now (never against the live profile) or be cited with the session and message id that
  produced it; a number carried across from a local skill loses its receipt in the move.
