---
name: manage-hermes-cron-jobs
description: "Use when 某个 Hermes cron 定时任务要改投递目标/改模型/排查 fire 失败时用：定位 job 与它属于哪个 profile、改 deliver、把单个 job 钉到另一个模型（只有 CLI 能做）、按层读失败面。不属于本 skill 的：装/更/卸 skill（→ install-/update-/remove-hermes-skills）、网关服务本身（→ maintain-hermes-gateway）、消息投错会话（→ hermes-session-routing-forensics）。"
---

# Hermes cron jobs: find, retarget, verify

## When to use

- "把 `<agent>` 的 cronjob channel 改到 `<channel>`" — the user names an agent or a role, not a job id.
- A job's results stopped arriving, or every fire logs a delivery error.
- **A fire failed** — a `Cronjob Response … failed` notice, a `failure_streak` / "worth a review" line, or the
  user forwarding one. Triage path: §6 → `references/manage-hermes-cron-jobs-triage-a-failing-script.md`.
- You need to know which profile owns a job, or whether a target channel is reachable from it at all.

## 0. Where jobs live, and what the tool can touch

- Running profile: `~/.hermes/cron/jobs.json`. Other profiles: `~/.hermes/profiles/<name>/cron/jobs.json`.
  Same layout on any other machine under its own `$HERMES_HOME`.
- `cronjob_manage` acts on the job store of the profile you are running as — it cannot see or edit another
  profile's jobs. Inspect another profile read-only (python / `search_files` over its `jobs.json`); change it
  only with an explicit scoped command (`hermes --profile <name> cron …`) or an approved file edit.
- Per-job history sits beside `jobs.json`: `cron/output/<job_id>/<date>.md` and `cron/executions.db` — the
  fastest record of what a job actually produced.
- Resolve a channel id to its name from `~/.hermes/channel_directory.json` (platform → id / name / guild /
  type). Cheaper and more reliable than grepping logs for the id.

## 1. The user named an agent — resolve it to a profile before touching anything

Never assume a profile directory by that name exists; report what you actually find. In this order:

1. `ls ~/.hermes/profiles/` and read each `profiles/<p>/profile.yaml`: a rename records the old names under
   `previous_names:` — the only place a nickname the user still uses maps to today's profile.
2. That profile's `.env`: which platform credentials exist (`DISCORD_BOT_TOKEN`, `FEISHU_APP_ID`,
   `DISCORD_HOME_CHANNEL`, …) — i.e. which platforms it can serve at all.
3. `gateway.log`: the `✓ <platform> connected (profile: X)` lines and the bot usernames beside them:
   `grep -oE "Connected as [^ ]+" ~/.hermes/logs/gateway.log ~/.hermes/profiles/*/logs/gateway.log | sort | uniq -c`.
   A bot can also carry a per-guild nickname distinct from its username — compare both fields.
4. Platform side, when guild membership decides it: `discord` `search_members(guild_id, <single-letter
   prefix>)` (prefix search — an empty result proves no member with that prefix), then `discord_admin`
   `member_info(guild_id, user_id)` for the `bot` flag and roles.
5. State the candidates with their evidence and ask ONE decision question. Do not silently "fix" the most
   likely one when the mapping is unresolved.

## 2. Delivery target grammar, and the requirement that bites

- `deliver` accepts `origin`, `local`, `all`, `bot-chat[:profile]`, or `platform:chat_id[:thread_id]`
  (e.g. `discord:1554384083453485086`).
- **The target platform must be configured and enabled in the job's OWN profile.** Otherwise the job runs
  fine and every fire's delivery lane fails with `platform '<x>' not configured/enabled`
  (`cron/scheduler_delivery.py`). A Feishu-only profile can never post to Discord, whatever the job's
  `deliver` says.
- So before promising a channel move, prove the target is reachable from that job's profile: `platforms:` in
  that profile's `config.yaml` **and** the platform's token in its `.env`. If it is missing, the real
  deliverable is "give this profile a bot on that platform first" — the user creates the app in the
  Developer Portal and drops the app id + token into a file; never accept or echo a token in chat.
- `origin` is not portable: it pins the chat the job was created from (often a Feishu chat). Moving output to
  Discord always means an explicit `platform:chat_id`.

## 3. Read the job's health before and after

- `failure_streak` = consecutive failures; `last_delivery_error` carries the adapter's own text.
  `app has been deleted` / `tenant access token failed` means the platform app itself is gone — no Hermes-side
  config fixes it.
- One job can be `last_status: error` for two independent reasons (the work failed, the delivery failed) —
  quote both fields, not just the status.
- After a change, re-read the job (`cronjob_manage action=list`, or the `jobs.json` entry) and quote the new
  `deliver` value; a tool success message is not the result.
- Say plainly what the change did and what still blocks end-to-end delivery. Never call a retarget "done"
  while the platform is missing.

## 4. Rolling out

- Touch only the jobs the user named: sibling jobs in the same profile often still post to the old target
  deliberately.
- Smallest edit wins: `cronjob_manage action=update job_id=… deliver=…`. For another profile, a scoped
  command plus a read-back of its `jobs.json`.
- Adding a platform to a profile is a gateway change: after writing the token into that profile's `.env` the
  multiplex gateway may rescan on the config/`.env` touch, and otherwise needs `hermes gateway restart` —
  which briefly drops every bot on the machine, so warn before doing it.

## 4b. Pinning ONE job to a different model (agent tool cannot — CLI only)

- Fire-time precedence (`cron/scheduler.py::_load_cron_job_config` + `_resolve_job_runtime`):
  **job's own `model`/`provider` > config.yaml `cron.model`/`cron.model_provider` > main agent model**.
  All three live in the job's `jobs.json` entry.
- `cronjob_manage` `pinned=true` only locks the **current main model** (`_main_model_pin()`); `model`,
  `provider`, `base_url` are deliberately absent from the tool's forwarded args (comment above
  `tools/cronjob_tools.py::_HANDLER_FORWARDED_ARGS`: unattended spend is user-owned). To point a job at a
  *different* model, use the user-facing lane:

  ```bash
  hermes cron edit <job_id> --model <model id> --provider <provider name>
  hermes cron edit <job_id> --model ''   # clear the pin → cron.model → main model
  ```

- `cron edit` has **no `--base-url`**: a named provider's endpoint comes from that profile's
  `config.yaml` `providers.<name>.base_url` (e.g. the custom `monk` provider). `base_url` is for
  hand-edited jobs / programmatic `cronjob()` callers only.
- Read back three things — none of them requires firing the job:
  1. `model`/`provider` in the job's `jobs.json` entry (`hermes cron list` does **not** print the model).
  2. `hermes cron doctor` (structure sane).
  3. Run the *actual* resolution path in Hermes' own interpreter (the block below):
     reports the model, provider class, resolved `base_url`, whether the key resolved, and
     `_job_route_pinned`. A wrong provider name or a profile missing `providers.<name>` fails here
     instead of at 3am.
- Do **not** fire a heavy job to "prove" the pin: the pin takes effect at resolution, and a real fire only
  burns the run and rewrites the job's execution history.
- Subagents inherit the job's model automatically — a pinned job's `delegate_task` children run on the
  pinned model too; nothing extra to set.

Resolution-path read-back (fill in `<home>` / `<job_id>`):

```bash
~/.hermes/hermes-agent/venv/bin/python3 -c "
import json, sys; sys.path.insert(0, '/Users/maxim/.hermes/hermes-agent')
from cron import scheduler as S
job=[j for j in json.load(open('/Users/maxim/.hermes/cron/jobs.json'))['jobs'] if j['id']=='<job_id>'][0]
jc=S._load_cron_job_config(job, job['id'], job['name'])
rt,m=S._resolve_job_runtime(job, job['id'], jc)
print(m, rt.get('provider'), rt.get('base_url'), 'key' if rt.get('api_key') else 'NO KEY')
"
```

## 4c. Creating a job (CLI lane; the agent tool cannot set model/provider)

- Schedule grammar (`cron/jobs.py::parse_schedule`) — the three forms differ in ways `--help` hides:
  - `2026-10-11T02:00:00` (any `YYYY-MM-DD…`, or anything containing `T`) → **one-shot at that wall-clock time**
    in the configured Hermes timezone (`{kind: once, run_at: …}`). Use this when the user names a date + hour;
    never hand-compute a delay.
  - `30m` / `every 30m` / `every 2h` → **recurring interval** (a bare duration is NOT a one-shot).
  - `in 30m` / `in 2h` → one-shot delay. `0 9 * * *` / `every monday 9am` → cron.
  Add `--repeat 1` for the intended single fire.
- Long or multi-line prompt: write it to a file and pass it through the shell —
  `hermes cron create "<schedule>" "$(cat /path/prompt.txt)" --name …` (same for
  `hermes cron edit <id> --prompt "$(cat /path/prompt.txt)"`). Quoted, newlines survive.
- `--model <id> --provider <name>` works at create time too (same resolution as §4b). A sibling job in the same
  profile's `jobs.json` is the fastest proof that a provider name resolves for cron in this profile.
- Deliver into a Discord **thread** by using the thread id as the chat id (`deliver=discord:<thread_id>`) —
  a thread is a channel. Prefer it over the parent channel when the request came from a thread.
- The fired agent has no session context: the prompt must name the skills to `skill_view`, carry the user's
  hard limits verbatim, and end with the acceptance criteria the run has to prove.
- Read back before calling it configured: the `jobs.json` entry (`schedule` / `next_run_at`, `model` / `provider`,
  `deliver`, `enabled`, prompt length), `hermes cron doctor`, and the §4b resolution read-back.

## 5. Answer shape (this user)

- Conclusion first: the resolved profile/job, its current `deliver` value, and what blocks the target — then
  the single decision you need. Mechanism only if asked.
- One decision per round; when two things are pending, ask the blocking one.
- **Ambiguous wall-clock in the request** (a bare hour with no 上午/下午, e.g. 「10.11 2 点」): pick the night
  slot (it matches the existing maintenance jobs) and say it is an assumption with the one-word fix. The work
  gets done either way, so don't spend a round-trip asking.
- If a `clarify` prompt returns `undelivered` on the platform, restate the question as a short numbered list
  in the chat instead of waiting — the question still has to reach him.

## 6. A job failed at fire time

A `no_agent` script job reports only `Script exited with code N` plus the script's own stdout/stderr — there is
no agent transcript to read. Order:

1. **Read the whole run, not the notice**: `cron/output/<job_id>/<date>.md` (stdout+stderr of that fire), then
   the job's `last_error` / `failure_streak` in `jobs.json`, then `cron/executions.db` for the history. A streak
   usually mixes several causes — the symptom changes as each layer is fixed, so do not treat it as one bug.
2. **List every job in that profile's `failure_streak` before fixing anything.** Script jobs share one
   interpreter environment (an app-bundled or mamba/conda env); one broken environment kills several jobs while
   the notice names only the one you subscribe to, and one repair restores them all.
3. **Reconcile the script's own log against the cron output.** If the script's log (`/tmp/<name>.log` or its
   `$LOG`) holds a *successful* run while the cron md shows every step failed, that log belongs to a different
   caller (a human terminal) and the difference is the environment, not the code. Timestamps alone are not a
   causal chain: say which run each file belongs to instead of narrating a story.
4. **Split environment from code with one command**: re-run the same entry point under `env -u PYTHONPATH`.
   Success without the variable and failure with it *is* the diagnosis.
5. **Only then** read the script — data-shape and API errors are a different class from import/exec errors.

Depth (cause table, the inherited-`PYTHONPATH` mechanism with its tell-tale ABI error, the fix shapes for `.py`
and `.sh`, how to phrase the report): `references/manage-hermes-cron-jobs-triage-a-failing-script.md`.

Diagnose read-only, then ask ONE question before editing another profile's `scripts/`: that tree belongs to that
profile's own bot, and a script edit is its call to approve.

## Pitfalls

- "Change the job's model" is not a `cronjob_manage` call: the tool can only lock the current main model
  onto a job. A different model/provider is `hermes cron edit <id> --model … --provider …` (CLI, §4b).
- `grep -r` across `~/.hermes` hangs (huge `sessions/`, `logs/`, browser profiles). Use `search_files` /
  ripgrep scoped to a directory, or bounded greps over named files.
- Grepping `state.db` binaries over-counts: the FTS **trigram** index stores trigrams, so a hyphenated needle
  matches hundreds of lines. Count real messages instead:
  `sqlite3 -readonly state.db "SELECT session_id, count(*) FROM messages WHERE content LIKE '%<needle>%' GROUP BY session_id;"`.
- Which bot a token belongs to: read it with that profile in scope (`hermes --profile <name> …`, or that
  profile's own `.env`) and confirm with `GET /users/@me`. Reading the default profile's env is how a bot gets
  misattributed to the wrong profile.
- A channel name the user types may be stale after a rename — trust the id → name mapping in
  `channel_directory.json` over the name in the request.

## Skill Structure

<!-- Generated by Scripts -->

```
manage-hermes-cron-jobs/
├── SKILL.md  (210 lines)
├── test-prompts.json  (27 lines)
├── test-results.md  (58 lines)
└── references/
    └── manage-hermes-cron-jobs-triage-a-failing-script.md  (91 lines)
```

<!-- Generated by Scripts -->
