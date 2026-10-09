---
name: hermes-profile-authoring
description: "Use when editing a Hermes profile's SOUL.md."
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, profiles, soul, persona, configuration]
    related_skills: [hermes-agent, gateway-operations]
---

# Hermes Profile Authoring

Editing the durable identity and configuration of a Hermes *profile* — `SOUL.md`, and the
profile-scoped `config.yaml` / `memories/` that sit beside it. `SOUL.md` occupies slot #1 of the
system prompt and is loaded fresh every message, so anything wrong in it is wrong in every future
session of that profile.

For Hermes-wide configuration, CLI, and architecture facts, defer to the bundled `hermes-agent`
skill and the docs at https://hermes-agent.nousresearch.com/docs — this skill is the *procedure and
pitfalls* for profile-level authoring, not a restatement of the config surface.
To *acquire* a ready-made profile or skill instead of writing one (community profile distributions,
Skills Hub, "is there a downloadable X Profile?" questions), use `hermes-community-extensions`.

## When this applies

- "完善/更新/rewrite the SOUL.md for profile X"
- Creating a new profile's identity, or giving an existing profile a domain identity
- Adding standing rules, environment notes, or tool/skill routing to a profile

## Procedure

### Step 1 — Locate the profile home and read the current file

Profiles live at `~/.hermes/profiles/<name>/` with the same layout as `~/.hermes/` (see
`hermes profile list` / `hermes profile show <name>`). Never assume `~/.hermes/SOUL.md`.

**Read the target file before writing it.** Do not write from your draft alone — see the
content-loss pitfall below. Also read the vault/workspace `README.md` if the persona references it.

### Step 2 — Inventory the profile to ground the content

A persona written from imagination is generic filler. Ground it in what the profile actually is:

```bash
# which skills this profile actually uses, most-used first
python3 -c "import json;d=json.load(open('<profile>/skills/.usage.json'));\
items=d.get('skills',d);rows=[(v.get('use_count',0),k) for k,v in items.items() if isinstance(v,dict)];\
rows.sort(reverse=True);[print(r) for r in rows[:40]]"
```

Also worth reading: `memories/MEMORY.md` + `memories/USER.md` (the profile may already carry the
facts you are about to restate), `config.yaml` (model, MCP servers, enabled toolsets), and
`.env` **key names only** — never print secret values.

Use the usage counts to decide which skills earn a mention. A persona that names the top-used
skills by domain routes future sessions correctly; one that lists all 190 does not.

### Step 3 — Verify every path before you write it

```bash
for p in <path1> <path2> ...; do [ -e "$p" ] && echo "OK   $p" || echo "MISS $p"; done
```

Persona files accumulate environment paths, and a dead path misleads every later session. Fix or
drop whatever comes back MISS; do not copy a path forward on the assumption it still exists.

### Step 4 — Back up with a timestamp

```bash
cd <profile> && TS=$(date +%Y%m%d-%H%M%S) && cp -p SOUL.md "SOUL.md.bak.$TS"
```

Keep the backup inside the profile directory and report the absolute path to the user.

### Step 5 — Write the file

Write the whole file in one `write_file` call, then apply corrections with `patch`. For a
non-English-speaking user, a bilingual structure reads well: English headings with the user's own
language inside for the sections that encode their preferences (讲解方式, 证据纪律).

Sections that have worked:

- **Who I am** — the user's background, credentials, field, what they explicitly do NOT do
- **Tasks** — short bullet list of the profile's job (preserve this section if the original had one)
- **Domain scope** — what this profile is for, in this profile's terms
- **How to explain** — the user's explanation preferences, stated as imperatives
- **Evidence discipline** — how claims must be grounded
- **Rules** — operational constraints (vault paths, backup/read-before-write, no invention)
- **Environment** — verified paths, with a note to re-verify
- **Tools & skills** — domain → skill routing, drawn from Step 2
- **Working style** — pacing, planning, reporting expectations
- **Avoid** — the failure modes to name explicitly

### Step 6 — Verify through the real loader, not by eyeballing

The file existing and being non-empty proves nothing: the loader scans for injection patterns and
truncates over-budget content. Run the actual loader:

```bash
python3 <skill_dir>/scripts/verify_soul.py --profile <name>
```

Expect `loaded: True`, no `blocked`, no truncation. A truncation warning means the persona is over
the char cap and the tail — usually the newest rules — is being silently dropped.

### Step 7 — Report where it is stored

Give the absolute path of the file and of the backup. Then re-check the original for anything
missing (see pitfalls).

## Pitfalls

- **Diff the original against the rewrite before declaring done.** A full rewrite silently drops
  sections the user wrote; a lost bullet is a lost behaviour, not a lost paragraph. After writing,
  re-read the backup and walk its bullets one by one against the new content, reporting each as
  kept or intentionally dropped. Restore anything that was dropped unintentionally.
- **Verify each path with `ls` before writing it in.** Memory and older notes accumulate paths to
  environments and checkouts that have since been renamed, moved, or deleted, and a persona file
  carrying a dead path misinforms every future session of that profile. Batch-check every path
  before the write and fix or drop the misses — do not copy a path forward because it appeared in
  an earlier session's notes, including your own.
- **Do not restate the repo's own `AGENTS.md` content in `SOUL.md`.** `SOUL.md` is loaded only from
  `HERMES_HOME` and applies everywhere; project conventions belong in `AGENTS.md`. The exception:
  when the profile's `workspace/` is empty and it has no repo working directory, `SOUL.md` is the
  only always-loaded file, so environment paths there are the accepted placement — check the
  user's other profiles for the house convention rather than inventing one.
- **Never hardcode `~/.hermes` when writing scripts or commands for profile work.** Resolve the
  profile home explicitly; `hermes -p <name> <cmd>` scopes it, and code paths use
  `get_hermes_home()`.
- **A `SOUL.md` identical to the default profile's means the profile has no identity yet.** Diff
  against `~/.hermes/SOUL.md` before assuming a profile is already customised — an untouched
  profile is a fresh-authoring job, not a tweak.
- **`SOUL.md` is scanned for prompt-injection patterns but is exempt from blocking** (it is the
  user's own file). Keep it focused on persona and rules; do not write phrases that read as
  instruction-override attempts, which produce warnings even when the file loads.

## Standing user preferences (this user)

- **Back up before modifying, and re-read immediately before patching** — the user may have edited
  the file since your last read. Rewrite the patch from current content, never from memory.
- **DO NOT imagine details.** If a requirement is unclear, ask the user; do not fill the gap.
- **After writing, tell the user the absolute path where the file/note is stored.**
- **Factual knowledge → Obsidian note, not memory.** Memory holds only operational facts (paths,
  env quirks, interaction preferences).
- **Report real tool output.** No fabricated paths, citations, or verification results; state
  blockers plainly.
- **Address the user by name** and keep the reply proportional to the ask.
- **When the user asks "how do I do X", give the command, expected output, and verification step —
  do not run mutating operations on their behalf.**

## Support files

- `scripts/verify_soul.py` — load a profile's `SOUL.md` through the real Hermes loader and report
  loaded / blocked / truncated state.
