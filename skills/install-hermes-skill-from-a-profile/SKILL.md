---
name: install-hermes-skill-from-a-profile
description: "Install a skill that exists only inside a Hermes profile — curator-created, agent-authored mid-session, or hand-copied — by deciding what it is against the skills that already exist, moving it into its pack repo, and installing it back from remote, so a lock entry owns it for the first time. Use when a new skill turns up in some profile (「某个 profile 里出现了新技能」), when a profile-local skill has to become a repo-delivered one, when one skill has to reach several profiles at once, or when a pack repo has to be created for it. Routes each phase to the sibling that owns it — the overlap audit to maintain-hermes-skills, the install mechanics to install-hermes-skills, the fleet fan-out to maintain-hermes-profile-skill-parity, a finished session's own harvest to recruit-learning-in-session — and owns only the sequence and its gates."
---

# Install a skill that lives only inside a profile

The unit is **a skill with no home**: a directory under some profile's skills tree with nothing behind
it — no lock entry, no repo, no update path. Nothing can check it, update it, uninstall it, or copy it
to another profile, and its only backup is the curator's own pre-run snapshot. It is also the shape a
skill is in **when it is created**, so this is the normal first delivery, not a repair.

The deliverable is that same skill living in a pack repo and installed back from remote: a lock entry
where there was none. Five phases, in order, each with a gate:

| Phase | Produces | Gate before moving on |
|---|---|---|
| 0 Locate | the name, the profile, and which of the three kinds it is | read-only — a lock entry, or a name in the bundled manifest, ends the request here |
| 1 Evaluate | one landing place: merge into an existing skill, a new skill in an existing pack, or a pack of its own | 🔴 ONE `clarify` — landing place **and** wanted end state — before anything is written |
| 2 Migrate | the skill inside the pack clone, in pack shape, committed, pushed | 🔴 the scan verdict predicted locally before the push |
| 3 Install | a lock entry pointing at the pack, in every profile that should carry it | 🔴 a throwaway-home probe whenever the route is unproven |
| 4 Retire | exactly one copy per profile | 🔴 the read-back first (`check` → `up_to_date`, `diff -rq` empty) — the delete comes after |

The phases are a pipeline, not a menu. A request that stops at Phase 1 (a placement decision, nothing
moved) is a valid end, and the placement answer is the only thing that licenses Phase 2. Phase 4 is the
one step where being early is destructive.

Commands for every phase, with the measured receipts: `references/install-hermes-skill-from-a-profile-pipeline.md`.
The landing decision and the end-state fork: `references/install-hermes-skill-from-a-profile-placement.md`.

## What this is not

| The request is | Owner |
|---|---|
| harvest a *finished session* into skill edits | `recruit-learning-in-session` — same promotion rung, different input: a session, not a discovered skill |
| install a skill handed over as a github / skills.sh / clawhub / url / bare name | `install-hermes-skills` |
| move an **installed** skill to another category | `install-hermes-skills` → `references/install-hermes-skills-relocating-a-skill.md` |
| close a gap where profile A carries a skill profile B lacks | `maintain-hermes-profile-skill-parity` — that skill owns fleet state; this one owns the first delivery |
| write or edit a skill inside a pack — prose rules, generated trees, lint, commit style | `maintain-hermes-skills` → `references/maintain-hermes-skills-authoring-conventions.md` |
| decide whether a block of material already exists somewhere | `maintain-hermes-skills` → `references/maintain-hermes-skills-overlap-and-merge.md` — it owns the audit method and the container taxonomy |
| delete the loose copy once the delivery is verified | `remove-hermes-skills` |

## Phase 0 — Locate it, and read which kind it is

An appearance has to be pinned to a **profile directory**, not to the word "local": the same machine has
one skills tree per profile, and a name can be hub-installed in one and lockless in another.

```bash
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
find "$HERMES_HOME/skills" "$HERMES_HOME"/profiles/*/skills -maxdepth 3 -type d -name '<skill-name>' 2>/dev/null
```

Then cut three ways, in this order — only the third outcome is this workflow's business:

1. **hub-installed** — the name is a key in `$HERMES_HOME/skills/.hub/lock.json` → `installed`. It already
   has a repo and an update path; the request is a sibling's (`update-`, `remove-`, `install-`).
2. **bundled** — the name is a line `<name>:<md5>` in `$HERMES_HOME/skills/.bundled_manifest`. It was
   seeded from Hermes's own code root, so it is unowned by the user on purpose.
3. **profile-local** — neither. It has no lock entry, no source of truth and no lifecycle.

Two traps in that cut, both measured on 2026-10-01: **"no lock entry" does not mean local** — 58 bundled
names on this machine have none either, so the manifest is the discriminator; and **`created_by` in
`.usage.json` is history, not current provenance** — an uninstalled skill keeps the `installed` value it
was written with (`biotech-career-analysis` still reads `created_by: installed` after its copy was
retired), while `agent` and `null` both appear on genuinely local skills. Read `.usage.json` for *when*
it appeared and `.curator_ledger.jsonl` for *who wrote it* (`action: create` + `evidence.session_id` is
the "this skill did not exist when that session began" row); the store map lives in
`maintain-hermes-skills` → `references/maintain-hermes-skills-inventory-and-availability.md`.

## Phase 1 — Evaluate it against what already exists

Do not skip to writing: what the skill *is* decides whether it should exist at all, and the answer is one
of three landing places — merged into an existing skill, a new skill in an existing pack, or a pack of its
own. The audit method (map each container, prove overlap claim by claim, report *already there* vs
*net-new* as two lists) is `maintain-hermes-skills` → `references/maintain-hermes-skills-overlap-and-merge.md`; what this
pipeline adds is the *sequence around* it and the end-state question, both in
`references/install-hermes-skill-from-a-profile-placement.md`.

🔴 CHECKPOINT — **one `clarify`, recommended-first, before anything is written**: the landing place, the
wanted end state (repo only, or repo plus an installed copy), the category, and whether the loose copy
retires in this run. The landing place cannot be inferred from the skill's topic alone, and the end state
is a standing user preference this pack has measured going both ways.

## Phase 2 — Migrate it into the pack

The repo is the source of truth from the first commit onward, so the copy that gets installed later comes
from the clone and never from the profile. Fix the shape on the way in — the pack's own rules apply the
moment it lands: `name` + `description` frontmatter only, references prefixed `<skill>-<topic>.md`, a
router body with depth in `references/`, and the generated tree. Then:

```bash
cd ~/Repositories/<repo>
python3 scripts/auto-generate-skill-structure.py <name>
python3 scripts/verify-skill-package.py skills/<name>
# predict the scan verdict on a COPY before pushing (reference: pipeline §2)
git add skills/<name>          # pathspec — a sibling session may be mid-work in this clone
git commit -m "docs(skills): …"
git push origin main
```

The push is part of Phase 2, not a later courtesy: the hub fetches from GitHub, so an unpushed edit is
invisible to Phase 3 and an install run against it fails in a way that reads like a broken identifier.

## Phase 3 — Install it back from remote

```bash
hermes skills inspect "<owner>/<repo>/skills/<name>"      # read-only: Source + Trust
hermes skills install "<owner>/<repo>/skills/<name>" --category <cat> -y
```

`--category` is read at install time only and decides the landing directory; `community` + `caution`
needs `--force`, and a `dangerous` verdict is not overridable. For more than one profile the command is
re-run per profile (`hermes -p <profile> …`) — skills are per-profile trees and nothing propagates.
Details and the per-profile loop: `references/install-hermes-skill-from-a-profile-pipeline.md` §3.

## Phase 4 — Verify, then retire the loose copy

Nothing is deleted on the strength of a plan. Two read-backs, then the delete:

```bash
hermes skills check <name>                                  # up_to_date, and the name printed in FULL
diff -rq ~/Repositories/<repo>/skills/<name> "$HERMES_HOME/skills/<cat>/<name>"   # prints nothing
hermes skills list | grep "<name minus its last 3 chars>"   # one row — the Name column is elided
```

`hermes skills list` **elides long names** and has no `--wide`/`--json` flag (measured 2026-10-02: an
installed `maintain-hermes-memory` lists as `maintain-hermes-mem…`), so a `grep` for the full name returns
nothing on a skill that is installed fine — it cost three extra round trips the first time it bit. Match a
prefix, or read the lock entry, which is keyed by the full name and is the authoritative "exactly one"
check.

A local copy is a plain delete once `grep` has proved the lock holds no entry for it; a hub-installed one
goes through `hermes skills uninstall <lock key>`. Back the copy up (`tar czf`) before deleting it and say
where the archive is. One state to report rather than misread: installing into the **same** category the
lockless copy already occupies replaces that directory in place, so the original is consumed by the
install instead of left beside it — the profile ends with one directory, which is the goal, not a
missing step. Full five-phase runbook and the failure branches:
`references/install-hermes-skill-from-a-profile-pipeline.md`.

## What not to do

- **Never hand-copy the skill into the repo and stop there.** A copy with no lock entry is invisible to
  `check` / `update` / `uninstall` for the rest of its life, and two directories holding one skill name is
  the drift state to check for at the end.
- **Never edit the installed copy as the delivery mechanism** — the next `update` replaces that directory
  wholesale; edits go to the clone and arrive by `update`.
- **Never retire the loose copy before the read-back.** A delete that outruns its install loses the only
  copy of content nothing else holds.
- **Never install on an inferred landing place.** A skill that "obviously belongs in" a pack still needs
  the one `clarify`: the end state differs per pack by the user's own convention.
- **Never report the fan-out from one profile's listing.** Confirm the lock entry per profile, then say
  which profiles carry it.

## Route by what was asked

| The question is | Read |
|---|---|
| the five phases with commands, gates, scan-verdict prediction, the per-profile install loop, the retire side, and the failure-branch table | `references/install-hermes-skill-from-a-profile-pipeline.md` |
| where this skill should land, whether it needs a pack of its own, the end-state fork (repo only vs repo plus installed), the `clarify` template, and what must not be copied into the receiving side | `references/install-hermes-skill-from-a-profile-placement.md` |
| how a skill is installed, updated, removed, or moved between categories | `install-hermes-skills`, `update-hermes-skills`, `remove-hermes-skills` |
| which profile carries what, and how to prove it | `maintain-hermes-profile-skill-parity` |
| what belongs in a skill in this pack, and how it is written | `maintain-hermes-skills` → `references/maintain-hermes-skills-authoring-conventions.md` |

## Skill Structure

<!-- Generated by Scripts -->

```
install-hermes-skill-from-a-profile/
├── SKILL.md  (177 lines)
├── test-prompts.json  (17 lines)
└── references/
    ├── install-hermes-skill-from-a-profile-pipeline.md  (182 lines)
    └── install-hermes-skill-from-a-profile-placement.md  (118 lines)
```

<!-- Generated by Scripts -->
