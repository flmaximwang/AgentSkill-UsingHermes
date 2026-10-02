---
name: maintain-hermes-skills
description: Manage the skills inside a Hermes profile — where they come from (bundled, hub-installed, local), why a query-based `hermes skills search` cannot find a skill you published yourself even after `tap add`, how bundled-skill seeding is turned on and off, and which home a block of overlapping skill material belongs in. Use when a search for a skill returns nothing or the wrong thing, when someone asks whether adding a tap is needed, when bundled (built-in) skills are missing or keep not updating — including a built-in you edited yourself, which stops updating forever until `hermes skills reset --restore` puts the stock copy back — when a profile should stop seeding them, or when a local skill's material seems to belong in a delivered one (does it overlap, what is genuinely net-new, where does it land, what retires). Installing, updating and removing skills themselves are the sibling skills.
---

# Manage Hermes Skills

Three kinds of skill live in a profile, and **which kind it is decides what can manage it** — that is
the distinction every question here runs into:

| Kind | Where it comes from | Managed by |
|---|---|---|
| **bundled** | copied out of the code root's `skills/` by `tools/skills_sync.py` | seeding controls (`hermes skills opt-out` / `opt-in`) |
| **hub-installed** | downloaded from a source adapter (github, skills.sh, clawhub, url …) | the hub: `check` / `update` / `audit` / `uninstall` |
| **local** | you copied it into `<HERMES_HOME>/skills/` yourself | nothing — you |

The sibling skills own the install/update/remove lifecycles (`install-hermes-skills`,
`update-hermes-skills`, `remove-hermes-skills`); the write path that creates skills by itself is
`maintain-hermes-memory`. This skill covers the three questions that sit *behind* those: **discovery**
(why a search cannot see a skill you published), **seeding** (where bundled skills come from and
how to switch that off), and the **merge decision** — which container a name is in, and where a block of
overlapping material lands (`references/maintain-hermes-skills-overlap-and-merge.md`). 🔴 CHECKPOINT on that
one: a merge deletes nothing on the strength of a plan — the duplicate retires only after the delivery has
been read back, and the landing place is confirmed with the user first (reference §3/§4).

Provenance: composed 2026-09-30 from two sources — a measured investigation of the tap/search path
run on this machine (macOS Apple Silicon, code root `~/.hermes/hermes-agent/`, all commands read-only)
for the discovery reference, and a note verified 2026-09-29 for the bundled-seeding reference. Each
reference states its own evidence and its own re-checks.

## Route by what was asked

| The question is | Read |
|---|---|
| "I published a skill on GitHub and added a tap — why does `search` not find it?" — also: what the tap actually feeds, and what to use instead | `references/FAQs-on-hermes-skills-tap.md` |
| "My bundled/built-in skills are missing or never update", "where do bundled skills come from", "I edited a built-in skill and now it never updates — get the stock copy back", "how do I stop (or restore) seeding in a profile" | `references/maintain-hermes-bundled-skills.md` |
| "why does the Skills page list N skills", "why can't I turn this one off", "where did this hub entry come from", "is there a skill for X" — every store that answers it, the provenance rules, the venv-python probe that reproduces a UI toggle, and the four levers that mutate a skills tree with no user action | `references/maintain-hermes-skills-inventory-and-availability.md` |
| how to write or extend a skill *in this pack* — prose and evidence rules, the pack's naming house style, description triggering, the frontmatter failures, pointer linting, commit and report discipline | `references/maintain-hermes-skills-authoring-conventions.md` |
| a skill's material seems to belong in another one — which container each name is in, what is *already there* vs *net-new*, where a block lands (this skill vs a sibling's mechanics), what retires, and absorbing a profile copy into the pack (which half goes to the pack, which to the project's own record, and backing the copy up before it retires) | `references/maintain-hermes-skills-overlap-and-merge.md` |
| how to *install*, *update* or *remove* a skill | the sibling skills `install-hermes-skills`, `update-hermes-skills`, `remove-hermes-skills` |

## Two facts that resolve most of these questions

**1. A tap is discovery-only, and discovery is the half that is broken.** `hermes skills tap add
<owner>/<repo>` writes an entry into `<HERMES_HOME>/skills/.hub/taps.json`, which
`GitHubSource(extra_taps=TapsManager().list_taps())` reads to *list* the repo's skills during a search.
It never participates in an install: `hermes skills install <owner>/<repo>/<path>` works on a repo
nobody has tapped. So when a search comes back empty, the identifier route is not a fallback, it is the
primary route the tap was never needed for.

**2. A silent `0 new / 0 updated` from bundled seeding means "no source", never "already current".**
`sync_skills()` early-returns when the current code root has no `skills/` directory, and the caller
renders that as zero copies. Which source that is depends on the launch chain — the same machine has
several, and only some of them carry the code tree's `skills/`. The diagnostic in the reference
resolves it per chain.

## The answer shape for "search can't find my skill"

Do not guess and do not tell the user to re-check the repo name. The measured chain is: unfiltered
`search` never asks the GitHub source at all (index-first design), and the explicit
`--source github` path does ask it but blows its 30 s budget on the *default* taps queued ahead of any
personal tap. Both halves, with the numbers and the code sites, are in
`references/FAQs-on-hermes-skills-tap.md`; the practical consequence is one line —
**`hermes skills inspect|install <owner>/<repo>/<skill-dir>` is what to use.**

## Skill Structure

<!-- Generated by Scripts -->

```
maintain-hermes-skills/
├── SKILL.md  (82 lines)
├── test-prompts.json  (17 lines)
└── references/
    ├── FAQs-on-hermes-skills-tap.md  (189 lines)
    ├── maintain-hermes-bundled-skills.md  (429 lines)
    ├── maintain-hermes-skills-authoring-conventions.md  (165 lines)
    ├── maintain-hermes-skills-inventory-and-availability.md  (354 lines)
    └── maintain-hermes-skills-overlap-and-merge.md  (163 lines)
```

<!-- Generated by Scripts -->
