---
name: maintain-hermes-profile-skill-parity
description: "Use when one bot or profile lacks a skill another one has — why a skill lives in one Hermes profile's tree and not another, how to prove which profile actually carries it, and the per-profile install that closes the gap."
---

# Skill parity across Hermes profiles

## When to Use

- "为什么只有你有 X / 另一个 bot 没学到 X" — one bot or profile has a skill (or a capability born
  from one) and another does not.
- "把这个 skill 也装到 <profile>" — the same skill has to exist in several profiles.
- Before telling the user a given bot can do something: the capability lives per profile, so the claim
  is only true for the profile you just checked.

Mechanics of installing, updating and removing a skill are the `install-` / `update-` /
`remove-hermes-skills` siblings; this skill owns **fleet state** — which profile carries what, why one
of them does not, and how to prove it.

## The fact that answers most of these questions

Skills are per-profile directory trees, and nothing copies between them:

- default profile: `$HERMES_HOME/skills/`
- named profile: `$HERMES_HOME/profiles/<profile>/skills/`

`hermes skills install` writes into the **active** profile only; `skill_manage` writes into the tree of
whichever profile the session runs as; `skills.external_dirs` is the only shared root, and it is
read-only to the curator. So a skill an agent authored mid-session in one profile is a file in that one
tree — there is no propagation step that could have failed, and none that could be "not learned".

State that as the answer: **the capability is a file path, not a memory.** Never explain the gap as
forgetting, training, or a bot not paying attention.

## Audit the fleet

```bash
# profiles on disk, and which ones the running gateway actually serves
ls -1 "$HERMES_HOME/profiles/"
python3 -m json.tool "$HERMES_HOME/gateway_state.json" | grep -E '"<profile>:<platform>"' | head -40

# profile -> bot identity: each profile carries its own token; ask the platform who it is
for f in "$HERMES_HOME/.env" "$HERMES_HOME"/profiles/*/.env; do
  tok=$(grep -m1 '^DISCORD_BOT_TOKEN=' "$f" | cut -d= -f2- | tr -d '"')
  [ -n "$tok" ] && { curl -s -H "Authorization: Bot $tok" https://discord.com/api/v10/users/@me \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id"), d.get("username"))'; \
    echo "   ^ $f"; }
done

# does profile P carry skill X (0 hits = absent), and where did it come from
find "$HERMES_HOME/profiles/<profile>/skills" -maxdepth 6 -type d -name '<skill-name>'
python3 -c "import json,pathlib; d=json.loads((pathlib.Path('$HERMES_HOME/profiles/<profile>/skills')/'.hub/lock.json').read_text())['installed']; print(json.dumps(d.get('<skill-name>'), indent=1))"
```

Read three files per profile when provenance matters, because each answers a different question:

- `skills/.hub/lock.json` — hub-installed only: `install_path`, `content_hash`, `source_revision`. A
  profile with no lock entry for the name either never installed it or holds a hand copy.
- `skills/.usage.json` — `created_by` / `created_at` / `state`. `created_by: agent` means the agent
  authored or a curator seeded it locally; absence means the skill never existed in that tree.
- `discord_threads.json` plus `logs/agent.log` — which threads that bot is actually in (`session=` on
  the inbound line pins the session). A bot that was not in the thread never received the message, so
  it had nothing to be missing: report that before proposing any install.

Headless equivalent of the inventory, one profile at a time: `hermes -p <profile> skills list`
(`--enabled-only` for the enabled set). Never generalize a listing from one profile to the fleet — an
in-session list shows the session's own profile.

## Remedy: install per profile, and re-supply the category

```bash
hermes -p <profile> skills install "<owner>/<repo>/skills/<name>" --category <cat> -y
```

- `--category` is read at install time only; a per-profile reinstall needs it every time. Changing a
  category is uninstall + install, never `update` (relocation recipe: `install-hermes-skills`).
- A local skill with no lock entry has no cross-profile mechanism at all. The two supported routes:
  publish it to a pack repo and install it per profile (lock entry, so check/update/uninstall work),
  or point each profile's `skills.external_dirs` at one shared directory — read-only to the curator.
- A hand copy between profile trees is discovered but has no lock entry, so `check` / `update` /
  `uninstall` never see it again. Name that cost if the user asks for it; do not present it as sync.
- After a hub install that replaced a loose copy, delete the loose one — two directories holding the
  same skill name inside one tree is the state to check for, and `hermes skills list` shows both.
- **Renaming the pack repo is a four-point sync.** `gh repo rename <new>` keeps an automatic redirect,
  but it does not touch the local remote, the README's install command, or the repo description: also
  `git remote set-url origin git@github.com:<owner>/<new>.git`, update the install command's repo
  segment (a stale segment is a wrong install command that fetches nothing, not cosmetics), and
  `gh repo edit --description`. Verify with `gh repo view <owner>/<new> --json name,description`. Note
  that a private repo answers 404 to an unauthenticated `curl` — that check proves nothing, `gh` does.

## Absorbing a profile copy into the pack (where each half goes)

When a profile-local skill and a pack skill cover the same ground and the user chooses "merge", the merge
has two destinations, and the split is the point:

1. **The method belongs in the pack.** Read the whole profile copy first — SKILL.md, every
   `references/` file, every `scripts/` file — then fold its depth into the pack skill: extend the
   existing topical reference instead of adding a parallel one, copy its scripts into the pack's
   `scripts/`, rescan the result. Deleting a copy you only skimmed loses material nothing else holds.
2. **Machine-local detail belongs to the project it operates on.** Real paths, ports, script locations,
   connection strings, current object/test counts, the operator's own habits go into a dated record in
   that project's own store — for a lab project, a `Logs/<YYYY>/<MM>/<DD>/<Type>. <title>.md` entry in
   its vault. Write it the way that store writes records: read its `README.md` first, reuse the type
   wording already in use there (never invent a new type name), copy the frontmatter shape from a
   sibling entry, and mark a non-experiment record with the store's "deliberately not in the paper
   notebook" form of `archive-id`. Keep local paths out of the skill, and leave a pointer between the
   record and the pack skill so each side finds the other.
3. **Then remove the duplicate — backed up.** `tar czf <scratch>/<skill>-backup-<date>.tar.gz` the copy
   before deleting it and state where the backup is. Two copies of one skill name is the drift state the
   user rejects; a restorable archive is not a copy.

Commit each half where it lives: the pack repo, each project repo (its own message convention), and a
file under no version control (a profile `README.md`) as an edit you report but cannot commit. A fix-up
round like this spans several repos at once — read two `git log` lines of each repo first, because the
`<type>(<scope>): <subject>` vocabulary differs per repo and a foreign message style shows up in the
history the user reads. Rename a skill directory with `git mv`, then **re-read the file at its new path
before editing it**: the write guard keys content per path and refuses the first write after a move.

## Verify before saying "installed"

- Name the profile: `-p <profile>`, or print `$HERMES_HOME` in the same command as the install when the
  target is the default profile. An install into the wrong home is a failure, not a partial win.
- Lock entry: `install_path` under the intended category, plus `content_hash` and `source_revision`.
- `hermes skills check <name>` → `up_to_date`. The hub answers `No hub-installed skills to check.` for a
  plain local copy — that means "no lock entry", not "nothing to do".
- For a repo-installed skill, `diff -r <clone>/skills/<name> <profile tree>/<cat>/<name>` identical.
- Confirm exactly one copy on disk for that profile before reporting.

## Pitfalls

- A hub lock is per profile: no entry in profile P says nothing about profile Q, and every profile has
  its own `.hub/lock.json`, `.usage.json`, `logs/`, `cron/`, `memories/`.
- Do not infer fleet state from message order or from who answered last in a multi-bot thread — every
  bot @-mentioned receives the message, and attributing by content instead of author id misassigns the
  work (identity loop for a shared task: the multi-agent handoff skill in `flmaximwang/AgentSkill-AgentOrchestration`).
- Publishing a self-authored skill to a pack repo puts it through the install scan. Predict the verdict
  before pushing and rewrite the literal that trips instead of forcing the install: a profile env file
  written with a home-relative spelling is a critical finding, `dangerous` cannot be overridden by
  `--force`, and the `$HERMES_HOME`-relative form scans clean (the scan-gate reference inside the
  `install-hermes-skills` skill holds the trigger table).
- Moving a skill into a pack repo makes the repo the source of truth: later content edits go through the
  clone and a push, then a per-profile update — a profile-side edit dies at the next update.
- When authoring a skill package that will be installed into profile P, do not name another skill in its
  body or `description` unless P is known to carry it: a pointer like "use the `X` skill" is dead text
  for every profile without X, and the reviewer of a delivered package checks exactly this. Write the
  capability neutrally ("use a tool that parses <format>") instead of naming the skill.
- Per-profile facts are also per-machine: profiles exist only under `$HERMES_HOME`, so a bot the user
  mentions may belong to another machine's Hermes home entirely.

## Skill Structure

<!-- Generated by Scripts -->

```
maintain-hermes-profile-skill-parity/
└── SKILL.md  (159 lines)
```

<!-- Generated by Scripts -->
