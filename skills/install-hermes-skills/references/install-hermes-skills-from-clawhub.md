# Install Hermes Skills from ClawHub

Use this file when the thing you were handed is a ClawHub page or an identifier shaped
`@<publisher>/<slug>` (e.g. `@terrybenedict0515/cangjie-skill`). **ClawHub is a third-party
marketplace, not GitHub** — its packages are repackaged by whoever uploaded them, which changes
what you are actually installing.

## What the source is

`clawhub.ai`, served by the `clawhub` adapter (`tools/skills_hub_clawhub.py`,
`BASE_URL = https://clawhub.ai/api/v1`). Two structural facts:

- **Every package is `community` trust — no exceptions.** The adapter docstring: *"Every skill is
  community trust — the ClawHavoc incident (341 malicious skills, Feb 2026) showed their vetting is
  insufficient."* So the verdict table in `SKILL.md` applies in its strict form: `caution` and
  `dangerous` are both blocked, and `--force` only rescues `caution`.
- A ClawHub install drops an extra `_meta.json` into the skill directory (`ownerId` / `slug` /
  `version` / `publishedAt`) — the only per-install provenance record this source gives you.

## Install

```bash
# 1. inspect first — read-only, and it tells you the trust level
hermes skills inspect "@<publisher>/<slug>"        # measured: Source: clawhub, Trust: community
# 2. install
hermes skills install "@<publisher>/<slug>" -y
# 3. verify against the packaging record, not just the name
hermes skills list --source hub
cat <HERMES_HOME>/skills/<name>/_meta.json
```

Note the honesty flag: the `install` line above is **not** measured — it was deliberately not run on
this machine to avoid installing an extra package; `inspect` and `check` were both run for real.

Maintenance uses the same commands as any hub skill (`check` / `update` / `audit` / `uninstall` — see
`SKILL.md`), with one twist: **`check` takes the lock key, which is not always the name you see.**

## The three traps

1. **Same slug, different thing (the important one).** A ClawHub slug can be a third-party rewrite.
   Read the frontmatter before installing. Measured on `cangjie-skill`:
   - ClawHub's copy (`@terrybenedict0515/cangjie-skill`): frontmatter `name: book2skill`,
     `version: 2.0.0`, author `"花叔 AlchainHust (原版) · mac-openclaw-manager (改造版)"`; has
     `methodology/07-stage5-human-output.md`; **no `scripts/`, no `templates/`**.
   - Upstream `kangarooking/cangjie-skill`: `name: cangjie-skill`, `cangjie.version: 2.5.0`; requires
     `scripts/cangjie.py` and `methodology/03b-stage1.6-promotion-gate.md`.
   - The two `SKILL.md` files are **both 184 lines, but `diff` shows 230 differing lines**.
     **Judgement rule: a `name` and `version` mismatch means a different bloodline, not a version
     bump of the same skill.**
2. **Three names coexist for one package.** Measured: the ClawHub display name (`Cangjie Skill`, the
   `inspect` title), the frontmatter `name:` (`book2skill`), and the hub/lock key + install directory
   name (`cangjie-skill`, from the slug). Consequence: `hermes skills list` shows it as
   `book2skill | local | local | enabled` with a footer of `0 hub-installed, 0 builtin, 40 local`,
   while `hermes skills check cangjie-skill` treats it as a hub entry (`clawhub | up_to_date`).
   **`list` matches by name, so a mismatched name makes the hub entry invisible in the listing** —
   name-based commands use the lock key, the agent's own skill calls use the frontmatter name.
   Anything you script should match on the lock key.
3. **Don't count on search.** The catalog walk has a **12 s budget** for 50k+ skills fetched
   sequentially (`CATALOG_WALK_BUDGET_SECONDS = 12`): measured
   `hermes skills search cangjie --source clawhub` → `No skills found matching your query.`, while
   `inspect` with the complete `@publisher/slug` succeeds. **This route needs a known identifier.**

## Provenance and limits

- **How to trace an already-installed skill**: read `source` + `identifier` in
  `<HERMES_HOME>/skills/.hub/lock.json`, then the directory's `_meta.json`. When `source: clawhub`
  and the identifier looks like `@publisher/slug`, **the `publisher` may not be the upstream
  author** — measured: `@terrybenedict0515` vs upstream `kangarooking`, two different people.
- **Same slug, several publishers**: ClawHub answers `409 AMBIGUOUS_SKILL_SLUG`, and the adapter
  disambiguates with `?owner=` (`_skill_detail`) — that is why the `@publisher` part of the
  identifier is not decoration.
- **Size cap**: `ZIP_DOWNLOAD_MAX_BYTES = 25 MB` per package.
