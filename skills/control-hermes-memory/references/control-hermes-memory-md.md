# The memory side — `memory.*` and the memory notification

Read this when the write the user is unhappy about is a **memory** write: a `MEMORY.md` / `USER.md`
entry appearing on its own, the "memory updated" notice, or a `/memory pending` queue that fills up.
The skill-write twins live in `control-hermes-skill-curator.md`.

All `file:line` citations are from the source note, verified 2026-09-29 against
`~/.hermes/hermes-agent/`.

## `memory.nudge_interval` — how often the memory review fires

- **Default `10`, unit = user turns** (not tool iterations). Read at
  `agent/agent_init.py:1315` as `mem_config.get("nudge_interval", 10)`; the initial default is set
  at `:1291`.
- The counter `_turns_since_memory` advances one per user turn and fires when it reaches the
  interval (`agent/turn_context.py:715-719`); per-session it is hydrated from persisted history as
  `prior_user_turns % interval` (`:709-710`), so it does not restart from zero on resume.
- **Setting it large = 少总结**, not "off". It only changes the frequency of the automatic memory
  review; it is the memory twin of the skill nudge, but the two counters are counted differently.
- **Does not control** whether the memory tool exists, whether memory is injected, or the
  foreground path — those are `memory.memory_enabled` / `write_approval` below.

## `memory.write_approval` — write only with approval

- **Default `false`.** A per-subsystem boolean that gates the agent's cross-session memory writes
  from **both** origins — foreground turn and `background_review` fork
  (`tools/write_approval.py:1-10`).
- `false` → writes freely. `true` → **never commits directly**:
  - **foreground**: prompts **inline** (interactive CLI only) — `evaluate_gate(wa.MEMORY,
    inline_summary=…, inline_detail=…)` at `tools/memory_tool.py:88`;
  - **background fork**: the write is **staged** rather than applied — the tool result says
    `「staged」: true` with a `pending_id` (`tools/memory_tool.py:188-191`). A background review may
    not delete entries unattended; its proposed action is staged too, with the message *"review it
    with /memory pending (approve to apply, discard to drop)."*
- **The `/memory pending` queue.** Staged records are JSON files under
  `<HERMES_HOME>/pending/memory/<id>.json` (`tools/write_approval.py:9,64-65`; `HERMES_HOME`
  defaults to `~/.hermes`). In-session the flow is:
  ```
  /memory pending                       # list staged writes (background ones tagged [auto])
  /memory approve <id>  |  /memory reject <id>
  ```
  Rendering and the apply/reject handlers are in `hermes_cli/write_approval_commands.py`
  (`_fmt_pending_list`, `handle_pending_subcommand`); `hermes_cli/config_defaults.py:1294` states the
  contract as `/memory pending|approve <id>|reject <id>`.
- **Does not disable memory.** The config comment is explicit: the key is *"Intentionally a single
  boolean with no 'block all writes' state — to disable a subsystem use its own enable flag (e.g.
  `memory.memory_enabled`)"* (`tools/write_approval.py:35-36`). Approval changes *who commits* a
  write, never *whether memory exists*.

## `memory.memory_enabled` — the master memory switch

- **Default `true`** (`hermes_cli/config_defaults.py:1290`, alongside `user_profile_enabled: true`).
- It gates whether the built-in store is usable: `get_builtin_memory_store_flags()` returns
  `(memory_enabled, user_profile_enabled)` and an unset/invalid value counts as `True`
  (`tools/memory_tool.py:259-261`); the per-target check is `self.user_profile_enabled if target ==
  "user" else self.memory_enabled` (`tools/memory_tool_store.py:111`).
- **This** is the flag to reach for when the user wants memory gone, not `write_approval`.
- **Does not control** the background review fork. The fork is a separate mechanism gated by
  `auxiliary.background_review.enabled` + the nudge intervals; turning memory off does not turn the
  fork off, and vice versa.

## `display.memory_notifications` — the chat notice only

- **Default `on`.** Modes (`hermes_cli/config_defaults.py:838-840`):

  | value | effect |
  |---|---|
  | `off` | 提示不显示 but **the review still runs** |
  | `on` | generic `"💾 Memory updated"` |
  | `verbose` | includes a content preview |

- Set as a string at init: `agent.memory_notifications = "on"  # "off", "on", "verbose"`
  (`agent/agent_init.py:2398`); the fork passes it through as `notification_mode`
  (`agent/background_review.py:1267`); the gateway normalizes a bool to `on`/`off`
  (`tui_gateway/server.py:1839-1845`).
- **Per-platform override**: `display.platforms.<platform>.memory_notifications`
  (`config_defaults.py:839`). Canonicalization of the shorter `platforms.<name>.<setting>` form into
  `display.platforms.<name>.<setting>` is done by `hermes_cli/config.py:3384-3413` — writing the
  non-canonical path is a silent no-op that looks like a duplicated key.
- **The load-bearing fact: it controls the *wording of the notice*, never whether the review runs.**
  `off` silences the chat line while the fork keeps writing; if the user actually wants fewer
  writes, this is the wrong knob — use the nudge intervals or `write_approval`.

## Put together

| the user wants | key | note |
|---|---|---|
| less frequent memory review | `memory.nudge_interval` (bigger) | unit = user turns |
| approve memory writes first | `memory.write_approval true` | foreground prompts inline (CLI); background → `/memory pending` |
| memory off entirely | `memory.memory_enabled false` | separate from the fork; `write_approval` cannot do this |
| silence the chat notice only | `display.memory_notifications off` | review still runs |

Keys are read at agent init → a change needs a **new session** (`/reset` in a gateway, quit/reopen on
the CLI).
