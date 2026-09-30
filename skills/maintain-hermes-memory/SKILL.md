---
name: maintain-hermes-memory
description: Control Hermes' automatic memory and skill writing — the post-turn background review fork and every config knob that gates it. Use when self-improvement writes memory or skills the user did not ask for (a skill appearing after a turn, MEMORY.md changing on its own), or when they want to stop it, slow it down, or require approval first. Covers `auxiliary.background_review.enabled`, `skills.creation_nudge_interval`, `memory.nudge_interval`, `skills.write_approval`, `memory.write_approval`, `display.memory_notifications`, `curator.enabled`, `memory.memory_enabled`, plus `/refine`, `/skills pending` and `/memory pending`. Routes by which write path is involved — full-fork shutdown, skill-only, or approval — then to the memory side or the skill/curator side.
---

# Control Hermes Memory and Skill Generation

Hermes writes memory and skills on its own. **Two** paths do it, and their control points are
completely different — so "turn off the automatic summarization" has at least three different
answers, depending on which path is actually bothering the user.

Provenance: distilled from a note verified **2026-09-29** against the source at
`~/.hermes/hermes-agent/` (the git checkout the app / gateway actually loads, on this macOS
Apple-Silicon machine). Every `file:line` below is that note's citation; blocks marked
*measured on this machine* are real output re-run while writing this skill.

## What is actually writing — the two paths

| 路径 | 谁写 | 受哪个开关约束 |
|---|---|---|
| **前台**（主对话进行中） | 主 agent 自己调用 `skill_manage` / `memory` 工具 | `skills.write_approval` / `memory.write_approval` |
| **后台 review fork**（每轮回答交付后） | `agent/background_review.py` 起一个 fork，重放本轮对话后自行写 | `auxiliary.background_review.enabled` + 两个 nudge interval |

So the first question is never "which key"; it is **"which path"**: is the user annoyed by a write
that happens **after every turn** (the fork → disable it or raise a nudge), or by the **main
conversation doing it mid-turn** (→ turn on `write_approval`)?

## The order — decide, then act

Walk these in order. Each step states the condition that selects it and, explicitly, what it does
**not** cover — the failure mode here is closing one path and believing learning is off.

**1. Confirm the fork is the source — it runs only after delivery.**
The fork spawns **after the turn's answer is delivered**, so it never competes with the user's
task (`agent/turn_finalizer.py:753-763`). Its four conditions: `final_response` exists, the turn
was not interrupted, `agent.skip_background_review` is false, and **at least one trigger fired**.
So "it wrote something" alone does not prove the fork; step 2 decides whether a trigger fired.

**2. Which trigger — skills or memory?**
- **Skill trigger** (`agent/turn_finalizer.py:735-739`): `agent._skill_nudge_interval > 0` **and**
  `agent._iters_since_skill >= agent._skill_nudge_interval` **and** `"skill_manage" in
  agent.valid_tool_names`. On a hit the counter resets to zero (`:741`).
- **Memory trigger**: driven by `memory.nudge_interval` (default 10 user turns) into
  `_should_review_memory`.
The counter that feeds the skill trigger is the key subtlety: it advances one per **tool
iteration**, not per turn, and only while `_skill_nudge_interval > 0`
(`agent/turn_iteration_prep.py:137-138`). The two intervals are therefore in **different units** —
see the skill/curator reference.

**3. Level ① — shut the whole fork off (manual `/refine` still works).**
Condition: the user wants *no* automatic post-turn review at all.
```bash
hermes config set auxiliary.background_review.enabled false
```
This is read at spawn time by `run_agent.py:797` → `load_background_review_settings()`
(`agent/background_review.py:205`), whose key is `auxiliary.background_review.enabled`.
**Does not cover:** the foreground path. The main agent can still call `skill_manage` / `memory`
mid-turn — that is gated only by `write_approval` (step 6).

**4. Level ② — keep memory summaries, kill only automatic skill creation.**
Condition: the user minds the skills appearing, not the memory notes.
```bash
hermes config set skills.creation_nudge_interval 0
```
`0` disables the skill trigger (its first condition fails) while the memory nudge is untouched —
记忆总结照常. **Does not cover:** memory writes; a very large memory also still gets summarized.

**5. Slower, not off.** Condition: the user wants less of it, not none. Raise `skills.creation_nudge_interval` from 10 to
40 / 80 (**tool iterations**), and raise `memory.nudge_interval` (**user turns**). Units differ —
raising one does not slow the other.

**6. Level ③ — don't forbid the write, require approval of it.**
Condition: the user is willing to keep the writes but wants a human gate.
```bash
hermes config set skills.write_approval true
# then: /skills pending → /skills diff <id> → /skills approve <id> | /skills reject <id>
```
`write_approval` gates **both** origins (foreground *and* the background fork) for that subsystem;
the memory twin is `memory.write_approval`, whose approvals queue at `/memory pending` instead.
This is the **only** lever that reaches the foreground path. Flow and per-subsystem detail live in
the two references.

**7. To sever "learning" completely.**
Condition: the user wants the machine to stop teaching itself entirely. Two more mechanisms run
**outside** the fork and must be considered separately — `curator.enabled` (background maintenance
that marks long-unused self-created skills `stale` and moves them into `.archive/`) and
`memory.memory_enabled` (the master memory switch). Neither is controlled by levels ①–③.

**Rollback** to this machine's prior state:
```bash
hermes config set auxiliary.background_review.enabled true
hermes config set skills.creation_nudge_interval 15   # restore local original value
hermes config set skills.write_approval false
```

## The knobs, at a glance

| 键 | 默认 | 作用 |
|---|---|---|
| `auxiliary.background_review.enabled` | `true` | **总开关**。`false` = 不再自动 spawn fork；注释原文：`enabled=false skips auto spawns (/refine still works)` |
| `skills.creation_nudge_interval` | `10` | 技能 review 的触发间隔（累计工具迭代数）。**0 = 只关自动建技能，记忆总结照常** |
| `memory.nudge_interval` | `10` | 记忆 review 的触发间隔（用户轮）。设很大 = 少总结 |
| `skills.write_approval` | `false` | `true` = 前台+后台所有 `skill_manage` 写操作**强制暂存待批**：`/skills pending`、`/skills diff <id>`、`/skills approve\|reject <id>` |
| `memory.write_approval` | `false` | 同上，作用于记忆写入（后台写进 `/memory pending` 队列） |
| `display.memory_notifications` | `on` | 只控制聊天里那条"记忆/技能已更新"提示的文案（`off` = 提示不显示但 review 照跑 / `on` = 通用 "💾 Memory updated" / `verbose` = 带内容预览）；按平台覆盖：`display.platforms.<platform>.memory_notifications`。**不控制是否运行** |
| `auxiliary.background_review.provider` / `.model` | `auto`（继承主模型） | 把 fork 路由到便宜模型；`auto` = 主模型重放全文（warm cache）。一旦改成别的模型，fork 只重放压缩 digest（注释称约便宜 3–5 倍） |
| `auxiliary.background_review.max_input_tokens` | 由主模型上下文推导 | 限制 review 循环累计输入 token（循环最多 16 次迭代）；`<= 0` = 不限 |

**Path trap — `skills:` is top-level, not `agent.skills.…`.** `agent/agent_init.py:1369-1371` reads
it as `_agent_cfg.get("skills", {})`, where `_agent_cfg = load_config_readonly()` (`:2458-2459`)
holds the **whole** config; the `agent:` section is pulled out separately by
`_cfg_dict(_agent_cfg, "agent")`. The key is also **not registered in `DEFAULT_CONFIG`** —
`hermes config set` prints an "unknown key" warning but still writes it, and the runtime does read
it (the single read point in the tree is `agent_init.py:1371`).

## Measured on this machine (2026-09-29)

`~/.hermes/config.yaml:422-429`:

```yaml
skills:
  guard_agent_created: false
  write_approval: false       # 未开审批
  creation_nudge_interval: 15 # 默认 10，本机已是 15 → 每 15 次工具迭代触发一次技能 review
  disabled: [airtable, comfyui, macos-computer-use, polymarket]
```

`auxiliary.background_review` **未设** → 用默认 `enabled: true`（自动 fork 开着）。And
`~/.hermes/config.yaml:249` holds `display.memory_notifications: "on"` — 只影响"记忆已更新"提示文案，本机保持默认。

Re-verified read-only on 2026-09-30 (`hermes config get` resolves the value; the second line is the
tool's own warning):

```
$ hermes config get skills.creation_nudge_interval
15
⚠ 'skills.creation_nudge_interval' is not a recognized config key — Hermes may not read it; the value printed above comes from your config file.
$ hermes config get memory.nudge_interval        → 10
$ hermes config get curator.enabled              → true
$ hermes config get auxiliary.background_review.enabled → true
```

## When a change takes effect

These keys are read at **agent initialization**, so a change applies only to a **new session**:
in Discord / a gateway use `/reset`, or `/restart` the gateway; on the CLI quit and reopen. The
fork's own cost is ~30K tokens per event (`agent/turn_finalizer.py:750-751`), and cron sessions
default to `skip_background_review=True` and skip it.

## Route by what was asked

| The question is | Read |
|---|---|
| memory writes — `memory.nudge_interval`, `memory.write_approval` and the `/memory pending` queue, `memory.memory_enabled`, `display.memory_notifications` (+ the per-platform override), and what each does **not** control | `references/maintain-hermes-memory-md.md` |
| skill writes — `skills.creation_nudge_interval` (unit = tool iterations), `skills.write_approval` and the `/skills pending\|diff\|approve\|reject` flow, `curator.enabled` (stale → `.archive/`), the measured local values | `references/maintain-hermes-skill-curator.md` |
| **whether a skill was ever actually loaded** — "did you use X?", why a broad `description` never fires, and how to reword it so it can: `.hub/lock.json` + `audit.log` for provenance, per-skill load counts out of `state.db`, persona-vs-skill provenance, description rewrites, and the two config keys that bypass the model's judgement (`skills.auto_load`, `channel_skill_bindings`) | `references/inspect-hermes-skill-usage.md` |
| the curator's `.archive/` — `curator.*` thresholds, the `restore` / `pin` / `purge` recipes, what an archive record holds, and the `.archive` vs `skills.disabled` two-list mixup | `references/maintain-hermes-curator-archive-lifecycle.md` |
| every mechanism that mutates a profile with no user command (bundled seeding, Skill Sync, curator, hub updates) — each one's lever, default and off switch | `references/maintain-hermes-self-improvement-controls.md` |
| reading a home's `state.db` directly — which skills were loaded and how often, which prompt text was active per session, dating the install that should have carried a rule | `references/maintain-hermes-session-store-forensics.md` + `scripts/skill-usage-counts.py` |

Two facts to keep straight when answering: **level ① does not stop the main agent from writing
skills** (that is level ③), and **`/refine` bypasses the nudge and `enabled` gate** — the source
docstring says *"Explicit `/refine` (focus set) bypasses this gate — same contract as zeroing the
nudge intervals, which stops automatic forks but leaves manual refine working (issue #87250)"*.

## Skill Structure

<!-- Generated by Scripts -->

```
maintain-hermes-memory/
├── SKILL.md  (185 lines)
├── references/
│   ├── inspect-hermes-skill-usage.md  (264 lines)
│   ├── maintain-hermes-curator-archive-lifecycle.md  (67 lines)
│   ├── maintain-hermes-memory-md.md  (94 lines)
│   ├── maintain-hermes-self-improvement-controls.md  (95 lines)
│   ├── maintain-hermes-session-store-forensics.md  (102 lines)
│   └── maintain-hermes-skill-curator.md  (110 lines)
└── scripts/
    └── skill-usage-counts.py  (66 lines)
```

<!-- Generated by Scripts -->

