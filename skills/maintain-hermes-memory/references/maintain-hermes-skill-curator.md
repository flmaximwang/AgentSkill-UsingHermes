# The skill side — `skills.*` and the curator

Read this when the write the user is unhappy about is a **skill**: a new `SKILL.md` appearing after
a turn, an existing skill edited by the agent, or old self-created skills quietly aging out. The
memory twins live in `maintain-hermes-memory-md.md`.

All `file:line` citations are from the source note, verified 2026-09-29 against
`~/.hermes/hermes-agent/`.

## `skills.creation_nudge_interval` — the auto skill-creation trigger

- **Default `10`. Unit = accumulated tool iterations, NOT conversation turns.** The counter
  `_iters_since_skill` advances by one **per tool iteration** while `_skill_nudge_interval > 0`
  (`agent/turn_iteration_prep.py:137-138`); the trigger fires when
  `_iters_since_skill >= _skill_nudge_interval` **and** `"skill_manage" in agent.valid_tool_names`
  (`agent/turn_finalizer.py:735-739`), after which the counter resets to zero (`:741`).
- **`0` means only that automatic skill creation is off — 记忆总结照常** (memory summarization is
  driven by `memory.nudge_interval` and is untouched).
- To merely *reduce* it, raise the value (10 → 40 / 80 **tool iterations**). It is not a turn count,
  so do not reason about it in turns.
- **Read path trap**: the key lives in the **top-level `skills:`** section, not `agent.skills.…`.
  `agent/agent_init.py:1369-1371` reads `_agent_cfg.get("skills", {}).get("creation_nudge_interval",
  10)`, and `_agent_cfg = load_config_readonly()` (`:2458-2459`) is the **whole** config — the
  `agent:` section is extracted separately via `_cfg_dict(_agent_cfg, "agent")`. The key is **not
  registered in `DEFAULT_CONFIG`**, so `hermes config set` warns but still writes, and the runtime
  does read it (sole read point: `agent_init.py:1371`).

## `skills.write_approval` — stage every skill mutation

- **Default `false`.** Gates `skill_manage` mutations on **both** origins (foreground and the
  background fork). `true` = **ALWAYS stage** — the config comment notes a `SKILL.md` is *"too large
  for an inline prompt"*, so unlike memory there is no inline path
  (`hermes_cli/config_defaults.py:1456-1458`).
- **In-session flow:**
  ```
  /skills pending                 # list staged mutations, background ones tagged [auto]
  /skills diff <id>               # full content diff of one staged mutation
  /skills approve <id>  |  /skills reject <id>
  ```
  Handler and rendering: `hermes_cli/write_approval_commands.py` (`_fmt_pending_list`,
  `handle_pending_subcommand`); the note at `gateway/slash_commands.py:928` distinguishes this from
  `hermes skills diff <name>`, which diffs a *bundled* skill against its stock version — different
  command, different meaning.
- **Staging and replay mechanics**: the gate is `_run_write_gate` in `tools/skill_manager_tool.py`
  (`wa.evaluate_gate(wa.SKILLS)` → `wa.stage_write(...)` returning a `pending_id`); approval replays
  the exact staged kwargs with the gate bypassed (`apply_skill_pending`,
  `tools/skill_manager_tool.py:663-670`). Records are
  `<HERMES_HOME>/pending/skills/<id>.json`.
- **Does not disable skills** or stop the foreground agent from wanting to write — it only forces
  the write through a human gate first.
- **Mirror to memory**: the same machinery serves `memory.write_approval`; the shared gate lives in
  `tools/write_approval.py` and its docstring names both subsystems.

## `curator.enabled` — background skill maintenance (a different mechanism)

- **Default `true`** (`hermes_cli/config_defaults.py:1475-1476`). The curator is background
  maintenance of **agent-created** skills (never hub-installed): it marks long-unused skills
  `stale`, and moves obsolete ones into `~/.hermes/skills/.archive/` — **archives, never deletes**.
- Enable check: `is_enabled()` reads `enabled` defaulting to `True` (`agent/curator.py:106`).
  `should_run_now()` gates on `curator.enabled`, not-paused, and `last_run_at` older than
  `interval_hours` (`agent/curator.py:160`); inactivity-triggered from session start, no cron
  daemon.
- **The staleness transitions** (`agent/curator.py:256-259`): a skill whose latest real activity is
  older than `stale_after_days` moves `ACTIVE → STALE` (`marked_stale`), and one used again moves
  `STALE → ACTIVE` (`reactivated`). `use_count == 0` is treated as *absence of evidence*, not
  staleness — a never-used skill younger than `stale_after_days` is never archived (`:247-249`).
- **Archiving is the maximum destructive action** — the move into `~/.hermes/skills/.archive/`
  (`agent/curator.py:320,774-778`); restore with `hermes curator restore <name>`.
- Relevant defaults (`hermes_cli/config_defaults.py:1475-1490`): `enabled: True`,
  `interval_hours: 24 * 7`, `min_idle_hours: 2`, `stale_after_days: 14`, `archive_after_days: 30`,
  `consolidate: False`, `prune_builtins: False`, `archive_ttl_days: 0`.
- **This is not the review fork.** The curator neither triggers skill *creation* nor is governed by
  `auxiliary.background_review.enabled` or the nudge intervals — it only ages out what already
  exists. When the user says "stop Hermes teaching itself", `curator.enabled` is one of the two extra
  mechanisms to consider alongside `memory.memory_enabled`.

## Measured on this machine (2026-09-29)

`~/.hermes/config.yaml:422-429` — the skill block:

```yaml
skills:
  guard_agent_created: false
  write_approval: false       # 未开审批
  creation_nudge_interval: 15 # 默认 10，本机已是 15 → 每 15 次工具迭代触发一次技能 review
  disabled: [airtable, comfyui, macos-computer-use, polymarket]
```

Re-verified read-only on 2026-09-30:

```
$ hermes config get skills.creation_nudge_interval
15
⚠ 'skills.creation_nudge_interval' is not a recognized config key — Hermes may not read it; the value printed above comes from your config file.
$ hermes config get skills.write_approval  → false
$ hermes config get curator.enabled        → true
$ hermes config get auxiliary.background_review.enabled → true
```

The warning on the first key is the expected consequence of it being absent from `DEFAULT_CONFIG`
(see the path trap above): the value still resolves and the runtime still reads it.

| local value | meaning |
|---|---|
| `skills.creation_nudge_interval: 15` | default is 10; this machine fires a skill review every **15 tool iterations** |
| `skills.write_approval: false` | 未开审批 — skill mutations commit without a gate |
| `curator.enabled` (unset → `true`) | curator runs on its idle/interval schedule and may mark skills stale / archive them |

Keys are read at agent init → a change needs a **new session** (`/reset` in a gateway, quit/reopen on
the CLI).
