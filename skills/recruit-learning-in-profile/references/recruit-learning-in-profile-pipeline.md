# The five-phase runbook — commands, gates, receipts

Depth for `SKILL.md`. The phases are the skill's own subject; the *methods* inside a phase (the overlap
audit, the install routes, the removal rules, the prose conventions) live in the siblings named at each
step, and this file does not restate them.

Contents: §0 Locate · §1 Evaluate · §2 Migrate · §3 Install · §4 Verify and retire · §5 Failure branches

## §0 Locate it, and read which kind it is

```bash
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
NAME='<skill-name>'                                     # every store below is per profile

# 1. where it exists on disk — the default home AND every profile
find "$HERMES_HOME/skills" "$HERMES_HOME"/profiles/*/skills -maxdepth 3 -type d -name "$NAME" 2>/dev/null

# 2. hub-installed?  (a key in the lock)
python3 -c "import json,pathlib;e=json.loads(pathlib.Path('$HERMES_HOME/skills/.hub/lock.json').read_text())['installed'];print(json.dumps(e.get('$NAME'),indent=1))"

# 3. bundled?  (a line '<name>:<md5>' in the manifest)
grep -c "^$NAME:" "$HERMES_HOME/skills/.bundled_manifest"

# 4. when did it appear, and who wrote it
python3 -c "import json,pathlib;u=json.loads(pathlib.Path('$HERMES_HOME/skills/.usage.json').read_text());print(json.dumps(u.get('$NAME'),indent=1))"
grep "\"skill\": \"$NAME\"" "$HERMES_HOME/skills/.curator_ledger.jsonl" | tail -3
```

Measured 2026-10-01 on this machine, which is what makes the cut order matter:

| observation | value | what it means |
|---|---|---|
| `$HERMES_HOME/skills/.bundled_manifest` | 58 lines, `<name>:<md5>` | 58 names have **no** lock entry and are not local |
| `grep -c '^maintain-hermes-gateway:' .bundled_manifest` | `0` | not bundled → lockless ⇒ local, this workflow's unit |
| `grep -c '^obsidian:' .bundled_manifest` | `1` | bundled: a lockless *seeded* skill, not a new one |
| `.usage.json['hermes-session-routing-forensics'].created_by` | `"agent"` | a session wrote it; `action: create` in the ledger names which |
| `.usage.json['maintain-hermes-gateway'].created_by` | `null` | a hand copy writes no `created_by` — absence is not evidence of age |
| `.usage.json['biotech-career-analysis'].created_by` | `"installed"` | **history, not provenance**: that copy was retired and the value stayed |

One ledger line, verbatim (the shape to filter on):

```json
{"id": "dcc01d3155a1", "ts": "2026-09-30T16:35:31.408782+00:00", "actor": "curator", "action": "patch", "skill": "literature-evidence-analysis", "evidence": {"session_id": "20261001_001605_9ab31892", "file_path": "references/rag-literature-synthesis-systems.md"}, "before": [{"path": "…/SKILL.md", "sha256": "89668d99…"}], "after": [{"path": "…/SKILL.md", "sha256": "7675a507…"}]}
```

`action: "create"` is the row that says *this skill did not exist when that session began* — the fastest
answer to 「这个 skill 是哪来的」. The three stores' full map, and why `hermes skills list` shows a category
that is not part of the skill's name, are in `maintain-hermes-skills`
→ `references/maintain-hermes-skills-inventory-and-availability.md`.

**Stop conditions.** A lock entry, or a bundled name, ends this workflow — say which it is and route to the
sibling (`update-hermes-skills` / `remove-hermes-skills`, or the bundled-skill reference). A name found on
disk in *no* profile is not a discovery either: there is nothing to migrate.

## §1 Evaluate it against what already exists

The audit itself — container mapping, claim-by-claim overlap, the *already there* / *net-new* two lists —
is `maintain-hermes-skills` → `references/maintain-hermes-skills-overlap-and-merge.md` §1–§2. Read it and run it;
do not approximate it with a topic comparison.

What this phase has to produce for Phase 2: **one landing place** (merge / new skill in an existing pack /
its own pack — `references/recruit-learning-in-profile-placement.md`) and the wanted **end state**
(repo only, or repo plus an installed copy). Both go to the user in the single `clarify` that checkpoint
prescribes, recommended-first.

A measured shape of how much survives an audit: on the 2026-09-30 merge of a profile-local
`skill-library-consolidation` into `maintain-hermes-skills`, 10 of the 22 stated facts were duplicates that
had to be *dropped rather than moved*. Expect the same ratio — a skill that appeared in a profile is often
mostly a re-derivation of what already ships.

## §2 Migrate it into the pack

The clone is where content is written from the first commit onward (`~/Repositories/<repo>` on this
machine). Order, with the pack's own rules applied at landing time:

1. `git status --short` and `git log --oneline -3` first — this repo family is worked by several sessions at
   once, and an unqualified commit swallows their staged files.
2. Read the whole copy before rewriting it: `SKILL.md`, every `references/` file, every `scripts/` file.
   Deleted-while-skimming is the failure that loses material nothing else holds.
3. Shape it as a pack member: frontmatter `name` + `description` only; references prefixed
   `<skill>-<topic>.md`; a router body with depth in `references/`; the `README.md` index row and install
   command when the pack has one. The conventions are
   `maintain-hermes-skills` → `references/maintain-hermes-skills-authoring-conventions.md`; the verb
   vocabulary in the pack's `README.md` is the naming authority.
3b. **Run the pack's own gates when it has any** — `AgentSkill-UsingHermes` keeps the routing blind test in
   `docs/routing-blind-tests/` and runs it from the repo root:

```bash
python3 -B docs/routing-blind-tests/make-blind-round.py --round r<N>-<name> --new-skill <name> \
        --decoy-ids <id> --decoy-pick <sibling>      # three self-checks must pass before it writes
# 2 arms × 2 judges via delegate_task — A/C = the arm WITHOUT the new skill, B/D = with it; each judge reads
# one judge-input-<round>-<A|B>.txt and lands its picks in blind-judge{A..D}-<round>.txt (batch summaries
# truncate; score the landed file only)
python3 -B docs/routing-blind-tests/score-blind.py --round r<N>-<name> --new-skill <name>
```

   Carry the skill name in the round name (a bare `rN` is silently overwritten by a concurrent session in
   the same clone), never omit `--new-skill` (its default groups your positives as if they were old
   questions), then write `test-results.md` here and add the round's row to that directory's `README.md`
   **and** the pack `README.md`. All of it belongs in the same revision as the skill.
4. Generate and lint, then predict the verdict **before the push**:

```bash
cd ~/Repositories/<repo>
python3 scripts/auto-generate-skill-structure.py <name>      # last step of the content edit
python3 scripts/verify-skill-package.py skills/<name>        # exit 1 on any tree/pointer problem
cp -R skills/<name> <scratch>/scan-probe/<name>
cd ~/.hermes/hermes-agent && HERMES_HOME=$HOME/.hermes venv/bin/python3 -c "
from pathlib import Path
from tools.skills_guard import scan_skill
r = scan_skill(Path('<scratch>/scan-probe/<name>'), source='skills.sh')
print(r.verdict)
for f in r.findings: print(' ', f.severity, f.pattern_id, f.file, f.line, repr(f.match))"
```

   `community` + `caution` installs only with `--force`; `dangerous` cannot be overridden at all, so a
   `dangerous` verdict on the first push is the point to rewrite the literal rather than push
   (`install-hermes-skills` → `references/install-hermes-skills-scan-gate.md`).
5. Commit by pathspec and push — `git add skills/<name>` then `git commit -m "docs(skills): …"` then
   `git push origin main`. Name any file in the diff you did not touch in the report.

## §3 Install it back from remote

```bash
hermes skills inspect "<owner>/<repo>/skills/<name>"        # read-only: Source + Trust
hermes skills install "<owner>/<repo>/skills/<name>" --category <cat> -y
```

- The identifier is the **three-segment** form `<owner>/<repo>/skills/<name>` (a two-segment `owner/repo`
  is accepted by nothing). For this machine's own packs the adapter is `skills.sh`; private repos resolve
  through the profile's PAT in secrets.
- `--category` is read at install time only and decides `skills/<cat>/<name>/`. A later move is
  uninstall + install, never `update` (`install-hermes-skills`
  → `references/install-hermes-skills-relocating-a-skill.md`).
- Probe an unproven route in a throwaway home, mirroring both `.env` and `config.yaml`, before touching
  `~/.hermes` — and print `echo "${HERMES_HOME:-<unset>}"` in the same command as the real install.
- Redirect long `hermes skills` output to a log file; never pipe it through `head` / `tail` (SIGPIPE kills
  the install mid-write).

**Fan-out — one profile at a time, then confirm each.** Skills are per-profile trees; nothing propagates.

```bash
for p in <profile> [<profile> …]; do
  hermes -p "$p" skills install "<owner>/<repo>/skills/<name>" --category <cat> -y
done
# per profile: a lock entry under the intended category, and check → up_to_date
hermes -p <profile> skills list --enabled-only -p <profile>
```

Measured on the fleet 2026-10-01, as the reference numbers a report can be checked against:

| pack | skills | profiles carrying a lock entry |
|---|---|---|
| `AgentSkill-AgentOrchestration` | 3 | **11** — every profile in `$HERMES_HOME/profiles/` plus default |
| `AgentSkill-ObsidianManagement` | 12 | 1 (default, category `obsidian`) |
| `AgentSkill-LabProject` | 3 | 1 (`rdm-assistance`, category `lab`) |
| `AgentSkill-AgentEvolution` | 2 | 1 (default, category `agent-evolution`) |
| `AgentSkill-UsingHermes` | 8 | 1 (default, category `hermes`) |
| `AgentSkill-JobHunt` | 1 | **none** — the repo-only end state, by decision |

## §4 Verify, then retire the loose copy

```bash
hermes skills check <name>                                     # up_to_date, and the name printed in FULL
diff -rq ~/Repositories/<repo>/skills/<name> "$HERMES_HOME/skills/<cat>/<name>"   # prints nothing
hermes skills list | grep "<name minus its last 3 chars>"      # one row for this profile
```

The displayed Name column is elided (`hermes skills list` has no wide/json flag), so grepping the full name
of a long skill reports 0 rows for one that is installed — measured 2026-10-02 on
`maintain-hermes-memory` → `maintain-hermes-mem…`. `check <name>` prints the name in full; the lock entry
(keyed by full name) is the authoritative "exactly one" check.

Then, and only then, the copy that is no longer the source of truth:

- **lockless** → prove it: the lock lookup for that name returns `None`. Then
  `tar czf <scratch>/<name>-backup-<date>.tar.gz -C "$HERMES_HOME/skills/<path>" .` and delete the
  directory with `<home>/skills/<path>` spelled out. Nothing can uninstall it, because nothing can see it.
- **hub-installed** → `hermes skills uninstall <lock key> -y` (`remove-hermes-skills`).

The state that misleads: installing into the **same** `--category` the lockless copy already occupied
replaces that directory in place, so a "the profile copy is gone" check that looks at the directory it used
to be in sees the installed tree and reads it as untouched. Report it as *consumed by the install*, and
state the end state that was chosen (repo only, or repo plus installed) — the two measured precedents are
in `references/recruit-learning-in-profile-placement.md` §3.

## §5 Failure branches

| Trigger | First fix | If it still fails |
|---|---|---|
| the profile copy holds text the repo lacks (it was edited in place) | backport it mechanically to the clone, byte-exact, and commit **before** any `--force` install/update | if the backport is not mechanical, ask — do not delete the only copy of the newer text |
| the install probe answers `Could not find '…' in any source.` | check the identifier is three-segment and the path exists in the pushed tree (`git ls-tree --name-only origin/main:skills`) | use the raw-URL route for a single-file skill (`install-hermes-skills`) |
| the first install is blocked (`caution`, oversized bundle, file count) | `--force` once trust × verdict allows it — structural blocks are not content judgements | rewrite the literal that trips the scanner; a `dangerous` verdict is final |
| the skill is already installed in a profile under an older bloodline | treat the install as a bloodline replacement: uninstall by **lock key**, then install with the category re-supplied | — |
| two profiles disagree about whether the name exists | that is normal: every profile has its own lock. Re-run §0 per profile rather than generalizing | if the user asks for parity across profiles, hand off to `maintain-hermes-profile-skill-parity` |
| the clone is missing, or its `HEAD` is behind the installed revision | `git clone <repo_url>` / `git pull --ff-only`; report the divergence before editing | clone the exact `source_revision` from the lock so the diff is real |
| the generator's `--check` fails on a skill you did not touch | name it in the report, touch nothing — another writer owns it | `git status --short` before staging; commit with a pathspec |
| a moved directory still holds the old `name:` in frontmatter | the move did not cascade — the full cascade is in `install-hermes-skills` → `references/install-hermes-skills-renaming-a-skill-pack.md` | verify the whole tree at once with `grep -m1 '^name:' "$HERMES_HOME/skills/<cat>"/*/SKILL.md` |
| the pack's blind-test generator refuses: `skills/<sibling>/SKILL.md 没有可读的 description` | that sibling is unroutable (no description = absent from the routing index); add its frontmatter minimally, commit it **alone**, name the file in the report | if the sibling is another session's in-flight edit, stop and ask — do not widen the candidate table to dodge it |
| `git show --stat` on a minimal sibling fix reports deletions | the edit went through a text-mode read + write, which normalized line endings or control bytes in lines you never meant to touch | redo it byte-exact (read bytes → prepend → write bytes) and amend the unpushed commit |
