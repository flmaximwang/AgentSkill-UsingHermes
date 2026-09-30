# What Hermes changes about itself, and the switch for each

Companion to `maintain-hermes-profile/SKILL.md` §10, §17, §18 and to this skill's own SKILL.md. Four independent mechanisms mutate a profile without a user
command; each has its own lever and default, and the levers live in **three different config
sections**. Read the default from the right section or the answer sends the user to a switch that
moves nothing.

## The four mechanisms at a glance

| Mechanism | Default | What it writes | Lever |
|---|---|---|---|
| Bundled seeding | **on** | `<home>/skills/**` from the package tree | `hermes skills opt-out` (marker `<home>/.no-bundled-skills`) |
| Skill Sync (cloud) | **off** | opted-in skills, in *and* out | `sync.enabled` (+ gate triple below) |
| Curator | **on** | `.curate` state: stale marks, `.archive/`, optional consolidation | `curator.enabled`, `hermes curator pin <name>` |
| Background review fork | **on** | skills (`skill_manage`) and memory, from the conversation | `auxiliary.background_review.enabled`, `skills.creation_nudge_interval` |

Hub-installed skills are the one class with **no** automatic path: `hermes skills check` detects,
`hermes skills update [--force]` applies, nothing schedules either. `plugins.auto_update_check_hours`
(+/`plugins.auto_apply`, git-class plugins only) is the only cadence in the config schema and it never
touches the skills tree.

## The review fork: who spawns it, and where the switches are read

Spawn site: `agent/turn_finalizer.py` — after delivery, and only when the reply is non-empty, the turn
was not interrupted, `agent.skip_background_review` is false (cron sets it) **and** at least one
trigger tripped. Gate: `agent/background_review.py::load_background_review_settings()`, called from
`run_agent.py`. Explicit `/refine` bypasses the enabled gate by design.

| Key | Section | Default | Effect |
|---|---|---|---|
| `enabled` | `auxiliary.background_review` | `true` | false = no automatic fork; `/refine` still works |
| `provider` / `model` / `max_input_tokens` / `reasoning_effort` | `auxiliary.background_review` | inherit (`auto` = main model replaying the conversation) | route or bound the fork instead of switching it off |
| `creation_nudge_interval` | **`skills`** (top level) | 10 | 0 = skill review never triggers; positive = reviews once the counter reaches it |
| `write_approval` | `skills` | `false` | true = every `skill_manage` write (foreground *and* fork) is staged for approval |
| `nudge_interval` | `memory` | 10 (user turns) | memory-side twin of the skill counter |
| `write_approval` | `memory` | `false` | true = foreground memory writes prompt inline, fork writes staged |
| `background_review_notices` | `display` | — | `off` / `on` / `verbose`: notice text only, never start/stop |

Counter semantics (skill side): `agent/turn_iteration_prep.py` increments `_iters_since_skill` once per
tool iteration while the interval is `> 0` **and** `skill_manage` is in `valid_tool_names`; the check at
turn end is `interval > 0 and _iters_since_skill >= interval`. So the trigger is *tool iterations since
the last skill write*, not user turns, and disabling the interval also stops the counter from moving.

Staged writes (either approval gate on) are cleared with:

```
/skills pending            /memory pending
/skills diff <id>          /memory diff <id>
/skills approve|reject <id>
```

## Gotchas that produce a wrong answer

- **`agent.skills.creation_nudge_interval` is not a key.** `agent/agent_init.py::_apply_agent_section`
extracts the `agent` section into `_agent_section` for its other keys, but reads the interval as
`_agent_cfg.get("skills", {})` where `_agent_cfg` is the **whole merged config**
(`hermes_cli.config.load_config_readonly`). Top level `skills:`, or it is dead config.
- **`hermes config set` warning ≠ refusal.** Keys absent from `DEFAULT_CONFIG` (this interval is one;
`skills.write_approval` and `auxiliary.background_review.enabled` are not) print
`… is not a recognized config key — it was saved anyway`. Only the positive wrong-prefix case is
actually refused (`maintain-hermes-profile/SKILL.md` §6). Prove it: `hermes config get <key>`, or parse the YAML leaf back.
- **New session required.** All of these are read at agent init; a running conversation keeps them
(mid-conversation rebinds would break prompt caching). CLI: `/reset`. Gateway: `/restart`.
- **Disabling the fork is not "no skill writes".** Foreground turns still call `skill_manage` from the
agent's own judgement; only `skills.write_approval` gates that. Report both paths.
- Values in a profile home are the profile's own: read them with `HERMES_HOME=<home>` (or
`hermes -p <name> config get …`) or the answer describes the launch profile instead.

## Skill Sync: the gate triple, and how to read it

`tools/skills_sync_client.py` gates every cloud op (`_gate_and_swallow`): a Nous login whose claims
carry an admin role, `sync_feature_enabled()` (`HERMES_SYNC_ENABLED` env → `sync.enabled`, default
`false`), and a resolvable `resolve_sync_base_url()` (`HERMES_SYNC_BASE_URL` → `sync.base_url` →
production plane). Any gate closed = the op is a no-op, silently. The gateway runs it per served
profile from a housekeeping tick (`_housekeeping_skill_sync` → `maybe_pull_skills()`; the org variant
requires real org membership).

```bash
hermes sync status          # nous_admin / logged_in / feature_enabled / base_url / opted_in_skills
hermes sync disable <name>  # exclude one skill (per-skill intent lives in .usage.json)
hermes sync enable <name>   # include it again
hermes sync pull | push | now
```

Inert is the normal state for a solo, unlogged profile: expect
`"feature_enabled": false` and `Not logged into Nous Portal — sync is inert.` Say "off" rather than
claiming the skills are being synced.

## Curator: the switches, briefly

`curator.enabled` (off = no runs at all), `hermes curator pause|resume` (temporary), `hermes curator pin
<name>` (exempt one skill from every automatic transition), `curator.consolidate` (LLM umbrella pass,
off by default; it is the only pass that rewrites skill content in place), `curator.prune_builtins`
(false by default; true lets shipped built-ins age out into `.archive/`). Full lifecycle:
`references/maintain-hermes-curator-archive-lifecycle.md`.
