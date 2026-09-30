---
name: evolve-hermes-skills
description: "Harvest one finished session into skill edits. Mines the session's own transcript for the skills it loaded, the gaps where the real process outran them, and the skills that appeared while it ran; settles per skill whether the user maintains an external pack repo (edit the clone, commit, push, `hermes skills update`) or edits the profile copy in place; then feeds each gap through darwin-skill's optimisation loop. Use at the end of a session when the user says 'evolve the skills' / 'evolve-hermes-skills', '把这轮会话的教训存进 skill', '分析这次会话里我调用过的 skill', '看看流程有什么 skill 没覆盖的', 'curator 这轮新建了哪些 skill', or asks which skill to touch after a session."
---

# Evolve Hermes Skills

Every sibling verb in this pack takes **a skill** as its unit — install it, update it, remove it, maintain
it. This one takes **a finished session**: the skills it loaded, the places where the real process outran
them, and the skills that appeared while it ran. The session is the only record of what the agent
actually had to work out for itself, and that record is what makes an edit worth committing.

Three phases, in order, each with a gate:

| Phase | Who does it | Gate before moving on |
|---|---|---|
| 1 Mine | one read-only subagent, holding the session transcript | 🔴 you spot-check two findings against the transcript |
| 2 Route | you, with the user | 🔴 ONE `clarify` covering every finding, recommended-first |
| 3 Optimise | `darwin-skill` | 🔴 its per-skill checkpoint, then the pack's commit rule |

## The one rule: no finding without a receipt

A finding is a claim that a skill failed this session, so it cites its evidence: a `messages.id`, a
command's real output, or a user correction, quoted verbatim. This is not paperwork — the failure it
prevents is the *plausible* gap, the one the agent can always generate on demand ("this skill should
probably also mention X") for a situation the session never actually hit. Those edits cost a skill its
length budget and its trigger precision, and nothing in the session asked for them.

So a finding without a receipt is dropped in Phase 1, not debated in Phase 2. Two corollaries:

- **A skill that was loaded and caused no friction produces no finding.** Say that in the report; do not
  manufacture one to make the session look productive.
- **A session that never loaded a skill is a valid result** — a Phase 1 answer of "no skill covered this
  work" is the signal to create one, not a failure of the run.

## Phase 1 — Mine the session (read-only subagent)

Spawn **one** subagent for the whole session, not one per skill: the transcript is the shared input, and
a single reader keeps the findings comparable and the severity ranking honest. It is read-only — its
deliverable is the report, never an edit.

Give it, explicitly: `$HERMES_HOME`; the session id (resolve it as below — do **not** let it pick "the
newest session", this machine runs several Discord threads at once); the instruction not to edit
anything; and the report schema. The full brief, the extraction commands and the measured receipts are in
`references/evolve-hermes-skills-session-mining.md` — read it before spawning, and paste the brief rather
than paraphrasing it.

Resolve the session yourself first, so you can hand over an id and can tell the user which session is
being evolved:

```bash
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
python3 -c "import sqlite3; c=sqlite3.connect('$HERMES_HOME/state.db'); [print(r) for r in c.execute(\"select id, datetime(started_at,'unixepoch','localtime'), chat_id, message_count, title from sessions order by last_activity_at desc limit 5\")]"
```

The session whose `chat_id` equals the channel/thread the request arrived in is the answer. If that
matches two rows or none, or you cannot see the channel (a CLI session), fall back to the newest row and
then **assert** it: the tail of that session must contain the evolve request itself. If the assertion
fails, show the user the three newest `id / title` pairs and ask which one to evolve — never guess, and
never merge two sessions into one report.

The subagent extracts four things (commands in the reference):

1. **Which skills were loaded** — the `skill_view` / `skill_manage` calls and their arguments, straight out
   of the transcript. This, not `hermes skills list`, is the session's real skill set.
2. **What the process actually did** — the tool census per session, which is the raw material for gaps no
   skill covers.
3. **Which skills appeared while it ran** — the curator/agent mutation ledger filtered to this session:
   an entry with `action: create` is a skill that did not exist when the session began. These have no
   repo and no lock entry, so they land in Phase 2 rung 2; treat them as first-class findings, since a
   just-created skill is the one most likely to encode the session's mistakes. The ledger is not the only
   source — a skill delivered through a clone plus a hub install leaves no entry in it, so cross-check
   `.usage.json` `created_at` and the clone's `git log` when the query comes back empty.
4. **Provenance per skill** — repo-maintained, hub-installed, bundled, or agent-created. This is the input
   Phase 2's ladder needs, so get it here rather than re-deriving it later.

Then the diff, which is the part no command produces: for each skill it read, where did the session
improvise, get corrected by the user, re-derive a command, or discover a branch the skill does not
state? Classify each as missing step / wrong step / missing failure branch / missing pointer / trigger
never fired, and rank by what it cost the session (a correction from the user outranks a slow path).

**🔴 CHECKPOINT — verify before acting.** The subagent's report is a self-report, not a fact. Re-query the
transcript for two of its findings (the message id and the quote) and confirm both exist and say what the
report claims. Cheap, and it is the only defence against a confidently misread transcript. If a finding
fails the check, drop that finding and say so in the report to the user rather than re-running the whole
subagent.

## Phase 2 — Route every finding to its owner

Before asking anything, detect where each touched skill lives, so the user is confirming a mapping
instead of recalling one. Two rungs, best first; the detection commands and both delivery sequences are in
`references/evolve-hermes-skills-routing.md`:

1. **External pack repo** — the skill is installed from a repo the user maintains. Resolve it through the
   hub lock: the entry in `$HERMES_HOME/skills/.hub/lock.json` whose `install_path` matches the installed
   directory carries an `identifier` of the form `<adapter>/<owner>/<repo>/<path…>`, and the maintained
   clone is the `~/Repositories/<repo>` whose `git remote get-url origin` names that same `owner/repo`.
2. **No repo** — an agent-created or locally copied skill. Edit it in place under
   `$HERMES_HOME/skills/<path>`.

**🔴 Then ONE `clarify`, recommended-first, covering every finding** — the repo mapping, the findings to
apply, whether to promote a rung-2 skill, and whether to run Phase 3. Never a per-skill question: the user
handed you a batch, and a batch is one decision. Ask about the mapping explicitly even though you detected
it, because "does this skill have an external repo" is exactly the question the user may answer with a repo
you cannot see from the lock (a new one, or one not yet tapped).

Walking rung 1 (the complete route): edit the clone → run the generator → run
`verify-skill-package.py` → commit with a pathspec → push `main` → `hermes skills update <name>` → read the
update back. Nothing reaches the profile until the last step, so an edit that stops at the clone is not
delivered.

Walking rung 2 has a cost that must be stated to the user, not buried: a skill with no lock entry is
invisible to `hermes skills check` / `update` / `uninstall`, so the edit has no update path at all and no
backup other than the curator's pre-run snapshot. If the skill is durable and Hermes-related, promotion
into a pack repo is the upgrade to offer in the same `clarify` — the alternative is an edit that no tool
can ever maintain.

## Phase 3 — Optimise with `darwin-skill`

Use `darwin-skill`; reach for `skillopt` only if darwin is unavailable, since the user's stated preference
is darwin-skill > skillopt. What this phase adds to a generic optimisation run is the input a generic run
cannot have — **the session's own evidence**:

- **darwin Phase 0.5 test prompts** ← the session's real user prompts, verbatim, including the ones where
  the user corrected the agent. They are strictly better test data than anything invented at optimisation
  time: they already failed once, against this skill.
- **darwin Phase 2 Step 1 diagnosis** ← the ranked gaps from Phase 1, which name the dimension (missing
  failure branch → dim3, missing checkpoint → dim4, vague step → dim5) instead of leaving the weighted-gap
  scan to guess.
- **darwin Phase 2 Step 4/5 gate** ← the paired same-judge majority (N=3, odd), never the absolute-score
  delta. This is darwin's own rule and it is the only trustworthy part of its ratchet.

Three overrides, because darwin ships for a different ecosystem than this pack: run it on the **clone**, not
the installed copy (its revert/ratchet needs git, and the profile tree is not a repo); replace its
`.claude/skills/*` default paths with the real clone paths; and when its constraints collide with this
pack's authoring conventions — body length, prefixed references, a routed entry point, the generated tree
in the same commit — **the pack wins**, because those conventions are what make the skill installable here
at all.

The sequence, the path overrides and the conflict rules: `references/evolve-hermes-skills-handoff-to-darwin.md`.
Per-skill 🔴 checkpoint after each optimisation, as darwin requires; a `revert` goes back on the ladder as
a finding the user can drop.

## Failure modes

| Trigger | First fix | If it still fails |
|---|---|---|
| Two live sessions could own this transcript (concurrent threads) | resolve by `chat_id` = the request's channel; otherwise newest + assert the tail contains the request | list the 3 newest `id / title` pairs and ask which to evolve |
| A finding carries no message id or quoted output | drop it; do not forward it to Phase 2 | if the whole report is like that, re-brief the subagent with the schema — do not edit anything on that run |
| A reported skill is not on disk any more | check `.usage.json` `state` and `hermes curator list-archived`; if archived, `hermes curator restore <name>` first | report it as un-actionable and drop it |
| A skill has no `lock.json` entry but the user says it has a repo | confirm the repo from `git remote get-url origin`; a repo the profile never installed from is rung 1 only after an install from it | edit rung 2 in place and offer promotion |
| `hermes skills update <name>` answers `kept your local edits` | the installed copy drifted before this run — the clone is source of truth, so `--force` once the pushed edit is what you want | restore the installed copy from the clone and re-run the update |
| darwin reports the skill is not in a git repo | run it against the clone (rung 1); for rung 2 use darwin's file-backup fallback | skip Phase 3 for that skill and say so — an unratcheted rewrite is not an optimisation |
| The generator's `--check` fails on a skill you did not touch | name it in the report and touch nothing — another writer owns it | `git status --short` before staging, and commit with a pathspec |
| The report has more findings than you can apply in one pass | apply and optimise the top 3 by cost to the session | queue the rest in the report's "not done" list with their receipts |

## What not to do

- **Never edit the installed copy of a skill that has a repo.** The next `hermes skills update` replaces
  that directory wholesale, so the edit is lost and looks like it was applied.
- **Never hand-edit an installed package as the delivery mechanism.** Delivery is the hub route — commit,
  push, update — and a hand edit is the change no tool can see.
- **Never let the subagent edit, and never take its report as fact.** Spot-check two findings, minimum.
- **Never invent a gap or a test prompt.** Use the session's real prompts and quotes; an invented one
  optimises the skill against a situation that did not happen.
- **Never use darwin's absolute score delta as the keep/revert gate** — paired same-judge majority only;
  the absolute score is triage.
- **Never report "no gaps" without having run the skill-extraction and the tool census.** A session that
  loaded three skills and ran a dozen tools always produced something; "no gaps" is only credible after
  the queries in the mining reference actually returned their rows.
- **Never ask the user per-skill questions, and never treat the repo mapping question as optional** — one
  `clarify`, recommended-first, mapping included.

## Route by what was asked

| The question is | Read |
|---|---|
| how to read the transcript, the subagent brief, the extraction commands, the report schema, the gap classes | `references/evolve-hermes-skills-session-mining.md` |
| which skills have an external repo, the two delivery sequences, what the no-repo rung costs, how to promote a local skill | `references/evolve-hermes-skills-routing.md` |
| what to hand darwin-skill, which paths to override, how its constraints interact with this pack's | `references/evolve-hermes-skills-handoff-to-darwin.md` |
| how a skill gets installed, updated or removed, or what the hub can and cannot see | the siblings `install-hermes-skills`, `update-hermes-skills`, `remove-hermes-skills` |
| what belongs in a skill in this pack, prose and structure rules, the generator and the lint | `maintain-hermes-skills` → `references/maintain-hermes-skills-authoring-conventions.md` + `scripts/README.md` |
| what the curator does on its own, and what its ledger records | `maintain-hermes-memory` → `references/maintain-hermes-skill-curator.md` — **only where that skill is installed**: it ships in this pack but not every profile has it, so check `hermes skills list` first or install it from the pack; this row dead-ends otherwise |

## Skill Structure

<!-- Generated by Scripts -->

```
evolve-hermes-skills/
├── SKILL.md  (199 lines)
├── test-prompts.json  (12 lines)
└── references/
    ├── evolve-hermes-skills-handoff-to-darwin.md  (125 lines)
    ├── evolve-hermes-skills-routing.md  (178 lines)
    └── evolve-hermes-skills-session-mining.md  (270 lines)
```

<!-- Generated by Scripts -->
