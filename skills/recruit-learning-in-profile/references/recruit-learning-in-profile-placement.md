# Where the skill lands, and which end state it is delivered into

The decision half of `recruit-learning-in-profile`. The audit that feeds it — container mapping,
claim-by-claim overlap, the *already there* / *net-new* two lists — is
`maintain-hermes-skills` → `references/maintain-hermes-skills-overlap-and-merge.md`, and this file does not
repeat it; what follows is the choice it produces, the pack to create when nothing fits, and the two end
states the same migration has been delivered in on this machine.

Contents: §1 The three landing places · §2 A pack of its own · §3 The end-state fork · §4 The one clarify
· §5 What the receiving side must not inherit · §6 After the move — who owns the content

## §1 The three landing places

| Landing place | What Phase 2 writes | Completion test |
|---|---|---|
| **merge into an existing skill** | no new skill: the source's depth folded into the receiving umbrella's topical reference; its `description:` and route row name the new entry point in the same edit | `hermes skills update <umbrella>` → `up_to_date`, then the source copy retires |
| **a new skill in an existing pack** (the common case) | `skills/<name>/` in the pack the user already keeps for that topic family, in pack shape + the README index row | a lock entry for `<name>` in a pack that already has one per skill |
| **a pack of its own** | a new repo (§2) — for a topic no existing pack covers | the repo exists, its README carries the install command, and §3's end state is settled |

**One shape leaves this table: a skill that already has an upstream.** A directory shipping `_meta.json` /
`skill-card.md` (ClawHub markers), stating `GitHub: <url>` in its own body, or carrying upstream-shaped paths
(`.claude/skills/<name>/`) is not a skill with *no home* — its home is the upstream repo, and its delivery is
`hermes skills install "<source>/<owner>/<repo>/<skill>"`, not a pack. Recruiting it forks a maintained
third-party skill into the user's own tree and cuts it off from upstream releases (measured 2026-10-10:
`darwin-skill` was recruited into `AgentSkill-UsingHermes` and had to be migrated back out — upstream
`alchaincyf/darwin-skill`, install `skills-sh/alchaincyf/darwin-skill/darwin-skill`). Say "install from
upstream" with the identifier and move to the next skill.

The **name** comes from the pack's `README.md` verb vocabulary, never from your reading of what the skill
"really does" — the pack is the naming authority, and a name that avoids the vocabulary is re-litigated at
the next request. The **category** is the one the pack's skills already occupy (one category per pack is
this machine's convention): `obsidian`, `git`, `hermes`, `agent-evolution`, `agent-orchestration`, `lab`,
`research`, `secretary`.

Send the *mechanics* of a merge to their owners: the audit method stays in `maintain-hermes-skills`, the
install/update/remove of whatever receives the content stays in `install-` / `update-` /
`remove-hermes-skills`. This pipeline owns the order and the gates, not a second copy of those rules.

## §2 A pack of its own

Measured on the four packs created this way (`AgentSkill-JobHunt`, `AgentSkill-LabProject`,
`AgentSkill-AgentOrchestration`, `AgentSkill-AgentEvolution`):

1. **Create the repo, then fix the remote before the first push.** `gh repo create <owner>/<name>
   --private|--public --description "…"` leaves an **https** origin; a bare `git push` then blocks on a
   credential prompt (osxkeychain holds no `github.com` entry) until it times out. Either
   `git remote set-url origin git@github.com:<owner>/<name>.git` or `gh auth setup-git`.
2. **The README is part of the deliverable**, not documentation: it carries the index table, the
   three-segment install command, and — for a private repo — the note that installing elsewhere needs a
   PAT readable in that profile's secrets. State the pack's own end state in it, verbatim from the
   JobHunt precedent:

   > **当前状态：默认 profile 里未安装。** 迁移 = 把这个 skill 从 profile 移出，本仓库是它唯一的 source of truth；要用的时候跑上面那条安装命令，改完内容 `git push` 后再 `hermes skills update <name>`。

3. **Layout decides the identifier.** A family pack uses `skills/<name>/SKILL.md` per skill; a
   one-skill repo uses a root `SKILL.md`. The identifier is always three-segment
   (`<owner>/<repo>/skills/<name>` or `<owner>/<repo>/` for a root skill) — a two-segment `owner/repo` is
   accepted by nothing.
4. **Scan before the first push** — that push decides whether the package can ever be installed
   (`SKILL.md` Phase 2 step 4, and `install-hermes-skills`
   → `references/install-hermes-skills-scan-gate.md`).

## §3 The end-state fork — repo only, or repo plus installed

Both have been the right answer, so it is a question, not a default:

- **Repo only** — the profile ends with **zero** directories of that name and the README's install command
  is the whole delivery. Measured twice: `AgentSkill-JobHunt` ← `biotech-career-analysis` (the thread
  迁移 biotech-career-analysis skill 到 AgentSkill-JobHunt, 2026-09-30) and `AgentSkill-ObsidianForLab`
  ← `zsqlab-lab-records` (`@session:default/20260930_171923_8170df20` msgs 56320/56332 — 「这只是文档里的落点，本次不安装」,
  then the delete assertion counted 0). Re-checked 2026-10-01: neither name appears in any profile's lock.
- **Repo plus installed** — for capability packs that have to be *callable*, not just archived: 12
  `AgentSkill-ObsidianManagement` skills in default (`obsidian`), 3 `AgentSkill-AgentOrchestration` skills
  in all 11 profiles, 3 `AgentSkill-LabProject` skills in `rdm-assistance` (`lab`), 2
  `AgentSkill-AgentEvolution` skills in default (`agent-evolution`). Here the retirement step acts on **the
  copy the install just wrote**, so it is the lock-backed one that gets kept and the lockless one that goes.

Say which one was chosen in the closing report, with the directory count per profile that proves it.

## §4 The one clarify

One call, recommended-first, before anything is written — the pack's own rule for a landing decision. The
four questions, with the drop signal for each:

1. **Landing place** — merge into `<existing skill>` / a new skill in `<existing pack>` / a pack of its
   own. Open by quoting the audit's two lists in one line (net-new facts × already-there facts), so the
   recommendation is checked against evidence rather than asserted.
2. **End state** — repo only, or repo plus an installed copy (§3). Recommend *repo plus installed* for a
   skill the user will call from a profile and *repo only* for a reference/methodology pack; name which
   copy then retires.
3. **Category** — the pack's existing category, or a new one. Drop this question when the end state is
   repo-only (there is no install to place).
4. **Retirement in this run** — retire the loose copy after the read-back, or leave it and report it. Drop
   it when the profile carries no copy of the name at all.

Do not run this as a per-skill chain when the request covers several skills: one call, one row per skill.

## §5 What the receiving side must not inherit

From the merge that measured it (`maintain-hermes-skills` → `references/maintain-hermes-skills-overlap-and-merge.md` §5),
the same list applies to a copy arriving from a profile:

- **A second container table.** bundled / hub-installed / local is one taxonomy; a migrated copy that
  restates it produces two disagreeing lists in one hierarchy.
- **A scope disclaimer** ("installing and removing are the siblings") that was true of the source and
  disclaims the receiving skill's own subject.
- **Frontmatter beyond `name` + `description`** — a local skill's `version` / `author` / `tags` — and a
  `related_skills` list naming the receiving skill itself.
- **Prior-session measurements presented as if re-run.** Cite the session and message id, or re-run it
  now, and never re-run a probe against the live profile.
- **A pointer to a sibling skill the target profile may not carry.** A line like "use the `X` skill" is
  dead text in every profile without `X`; name the capability instead, and check `hermes skills list` in
  the profile the pack installs into before naming any skill.

## §6 After the move — who owns the content

- The repo is the **only** source of truth. Later content edits go clone → `auto-generate-skill-structure.py`
  → `verify-skill-package.py` → commit → push → `hermes skills update <name>`; an edit made under
  `$HERMES_HOME/skills/` looks applied and dies at the next update.
- A **rename** is never local: it cascades into reference filenames, every cross-skill pointer, the
  generated trees, and every profile's install record
  (`install-hermes-skills` → `references/install-hermes-skills-renaming-a-skill-pack.md`).
- A profile copy that is **ahead** of the clone is content the repo lacks, and `update --force` deletes
  exactly that: backport it byte-exact and commit before forcing, and name the foreign content in the
  report.
- Two directories holding one skill name inside one profile is the drift state to check for at the end —
  `hermes skills list` shows both rows, and the report says which one was kept.
