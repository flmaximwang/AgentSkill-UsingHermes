---
name: load-external-skill-index
description: "Use when surveying a skill repo without installing it — a local directory, owner/repo, or git URL — by building a name+description table of its skills into context and then loading only the chosen SKILL.md. Load is not install — nothing enters the profile, no lock entry exists, and the table does not survive the session."
---

# Load an External Skill Index

Build a name+description index of a skill collection into context, then load only the chosen
SKILL.md. Covers what Hermes loads where (prompt index vs full body), why an ad-hoc catalog must
ride as conversation data, and the measured cost of the index.

## Load is not install

Two different jobs, and the difference is what this skill is about:

| | **Load** (this skill) | **Install** (`install-hermes-skills`) |
|---|---|---|
| writes | nothing — reads a repo's `SKILL.md` frontmatter | `<HERMES_HOME>/skills/<category>/<name>/` |
| gate | none | security scan → verdict, lock entry in `skills/.hub/lock.json` |
| lifecycle | none — `check` / `update` / `uninstall` cannot see it | `check` / `update` / `audit` / `uninstall` |
| cost | the table stays in this conversation; paid again every time it is rebuilt | one row in the system-prompt index, from the next session on, plus `/skill-name` |
| reach | informs the turn that read it | the model can select it by itself in any future turn |

Neither substitutes for the other: loading a repo twice costs the index twice, and installing it once
makes every one of its skills a first-class member of the profile. A request that starts as "what is
in this repo" ends here; a request that ends with "so I can use it later" is an install.

## When to Use

- The user points at a skill collection and asks what is in it — a local directory, `owner/repo`, or a git URL — and none of it is installed.
- You discover a skill repo mid-task and must know its contents before loading anything from it.
- Choosing between overlapping packs, or picking which skill to load or inspect next.
- Installing is a *different* job: hand off to `install-hermes-skills` (identifier routing, scan verdicts, lock entries).

## The loading model — what is cheap, what is impossible

- At session start the system prompt carries an index of **installed** skills only: `## Skills` / `<available_skills>`, one `name: description` row per skill (rendered by `agent/prompt_builder.py:_render_skills_index`). The full SKILL.md enters context only when `skill_view(name)` is called; `skills_list` returns name/description only.
- That index **is part of the system prompt**: built once per agent lifecycle, byte-stable, prompt-cached. Injecting or swapping a catalog mid-session means changing the system prompt = **breaking prompt caching, which Hermes forbids**. So an external catalog is read as **conversation data** — never injected into the prompt, never installed.
- State the consequence every time: the table is gone next session (no profile change, no lock entry, no memory of it). Making it persist is a separate, config-level decision:
  - `skills.external_dirs` in `config.yaml` → scanned into the same prompt index, permanent;
  - project-local `<repo>/.hermes/skills` or `.agents/skills` + `hermes skills trust` → highest precedence, only inside that repo;
  - a real install → `install-hermes-skills`.
- `hermes chat -s <skill>` and `skills.auto_load` are the *opposite* of this skill: they push a chosen skill's FULL text into the session, and only for already-installed skills.
- When a library has outgrown its index: `agent.coding_context: auto|focus|on|off` demotes non-coding categories to a names-only line (`category [names only]: a, b, c` — names kept, descriptions dropped, entries never removed); frontmatter `requires_toolsets` / `fallback_for_toolsets` hides a skill when the matching tools are absent; per-platform enable/disable removes it entirely.

## Procedure

1. **Resolve the source.** Local directory → use it in place. `owner/repo` or a git URL → `git clone --depth 1` into `$HERMES_HOME/cache/scratch/skillrepo-<name>` and reuse the clone if it is already there. Never clone into a vault or another repo's working tree.
2. **Build the index.** `~/.hermes/hermes-agent/venv/bin/python3 scripts/skill-index.py <dir|owner/repo|url>` — walks `**/SKILL.md` (skipping `.git`), parses the YAML frontmatter, dedupes by skill name, and prints one `category/name: description` row per skill plus a stats footer (skills / raw files / index chars / est tokens / full bytes / ratio).
3. **Load only the rows that matter** — then read that SKILL.md in full (`skill_view` for an installed skill, `read_file` on the clone path for an uninstalled one). Never bulk-read bodies "just in case": the whole point is that the index costs 1–2% of the bodies.
4. **Report** counts, cost, and explicitly what was NOT loaded.

## Cost model (measured)

- A 12-skill repo (`flmaximwang/AgentSkill-ObsidianManagement`, 2026-10-01): index 1,250 chars ≈ 625 tokens vs 108,679 B ≈ 27k tokens of full SKILL.md → **~1.2%**.
- 252 unique skills across 14 local repos: 32.4k chars ≈ 16k tokens (raw walk 737 rows → 252 after dedupe by name).
- One row ≈ 50–100 tokens (CJK ≈ 1 token/char, ASCII ≈ 0.25).
- The ceiling is total volume, not the mechanism: past a few hundred skills the index itself is expensive. Index **one repo at a time**, dedupe by skill name, and cap each description at ~110 chars — Hermes' authoring convention is that the first ~57 chars must stand alone as the trigger, so truncation there loses nothing.
- Do not quote the docs' "~3k tokens for the skills list" figure for a real library; compute the number.

## Pitfalls

- **Parse frontmatter with a YAML parser, never a regex.** `description: >-` (folded block scalar) makes a `^description:` capture the literal `>-`; only YAML resolution yields the real text. Measured on `biotech-career-analysis`, whose row read `>-` until the parser changed.
- **Dedupe by skill name before reporting counts.** Repo payload snapshots and profile copies hold the same skill under the same name — a raw walk of 14 repos produced 737 rows but only 252 unique names. When a name appears twice, prefer the pack repo (the skill's source of truth) over a snapshot copy.
- **Skip `.git` when walking, and take the category from `metadata.hermes.category` when present, else the first path segment.** A SKILL.md with no `name:` is listed as skipped — never invent a name for it.
- **Description language is not free.** A CJK description costs roughly 4× its ASCII equivalent; when the index is for the user's eyes rather than for loading, ask before dumping hundreds of rows.

## Verification

Rerun on a known repo and check the row count against `find <repo> -name SKILL.md -not -path '*/.git/*' | wc -l`; the footer prints `raw_files`, `skills` and the index/full ratio. Before quoting instructions from a surveyed skill, confirm its body actually loaded (the clone path exists and reads).

## Answer style (this user)

- Lead with the answer, then the mechanism **and its hard boundary** (the prompt cache is the boundary here), then the numbers from the run just performed — 3 sentences before any detail.
- One route, executed. A capability question answered with a menu of installation paths or alternative approaches is a failure, not a hedge.
- Quote measured output; if a number is an estimate, say which method produced it.

## Files

- `scripts/skill-index.py` — the index builder; usage in its docstring. Needs pyyaml, which the `hermes-agent` venv has (`~/.hermes/hermes-agent/venv/bin/python3`).

## Skill Structure

<!-- Generated by Scripts -->

```
load-external-skill-index/
├── SKILL.md  (94 lines)
├── test-prompts.json  (17 lines)
└── scripts/
    └── skill-index.py  (121 lines)
```

<!-- Generated by Scripts -->
