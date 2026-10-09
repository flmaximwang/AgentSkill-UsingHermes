---
name: hermes-profile-configuration
description: "Use when configuring, naming, or renaming a Hermes profile."
version: 1.0.0
author: Agent
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [hermes, profiles, config, providers, credentials, model, multi-profile, naming, rename]
---

# Configuring a Hermes profile's model / provider surface

Covers which providers a profile's picker shows, their credentials, the default model, the
profile's terminal cwd, and choosing / changing the profile's own name. Scope:
`~/.hermes/profiles/<name>/config.yaml` and `~/.hermes/profiles/<name>/.env`.
Gateway lifecycle / platform setup lives in the user-owned `gateway-operations` skill; creating a
Feishu bot for a profile lives in `lark-cli` → `references/new-profile-feishu-bot.md`.

## Standing rules (this user)

1. **Back up before editing, re-read after.** Copy the config into the profile's `backups/` with a
   timestamp, confirm both checksums match, then re-read the written file and check nothing was
   dropped. Report the changed path, the backup path, and the one-line revert command.
2. **Ask before writing when the target shape is ambiguous** — which endpoint, which providers to
   keep, where the key lives, whether the default model changes. Offer concrete options with a
   recommendation (one form with three questions is fine and gets answered); a guessed write costs a
   revert plus a re-explain.
3. **Never echo secrets.** Copy keys programmatically (load YAML → build dict → dump) and print only
   masked verification, e.g. `ark-5a13…(46 chars)`.
4. **Verify with tool output, not with the YAML you just wrote:** run the scoped listing below and,
   for a model/provider change, one real end-to-end call.

## Profile 命名规则（本用户，2026-09 定）

**定性先于命名。** 判据（用户原话）：**这个 profile 是长期维护一份资产/职责，还是被投放到具体项目里工作？**

| 定性 | 名字形态 | 例 |
|---|---|---|
| **角色型**（长期维护一份职责；有长期节奏） | 岗位名 / 施事名词 `-er/-or/-ant/-ist` | `investment-advisor`、`personal-accountant`、`travel-planner` |
| **技能型**（在具体项目里工作，不长期维护某个项目） | 学科名 / 动作名词，**不带**施事后缀 | `protein-design`、`game-research` |

- 语法依据（Merriam-Webster）：agent noun = "a noun denoting the performer of an action"（inspector/accountant）↔ action noun = "a noun denoting action"（inspection/accounting）。这对形态在现实中都用于蛋白设计：期刊 *Protein Engineering, Design and Selection* 用学科名，公司招聘用 "Computational Protein Designer" 用岗位名——形态确实承载语义。
- 可观测的辅助信号：角色型有长期节奏（cron job / 月度周期）；技能型跟着项目节奏（profile 内 cron = 0）。
- **作用域（单项目/多项目）不编进名字**：数量会变，性质稳定。作用域放 `terminal.cwd`（绑定一个库）和 `profile.yaml: description`；多项目用 `hermes project create` 登记——那才是"多项目 agent"的结构事实，不是名字。
- 禁例：`-desk`/`-lab` 这类作用域后缀（`trading desk` 是金融行话、指"职能单元"而非"单项目"，套到 travel/accountancy 上是生造词）；也不要为了规则自洽去改掉一个本来正确的名字（`protein-designer → protein-lab` 就是这样被否掉的）。
- 定为技能型 ≠ 可以挂一个还没建好的域：名字要指向已存在的能力，否则就是名实不符。先完善 SOUL/skill，再按新名 rename。

## 改名成本的机制（`hermes_cli/profiles.py::rename_profile`）

自动做：停 gateway → 从 multiplexer 解绑 → 目录改名 → Honcho host → 删旧 wrapper / 建新 wrapper（`~/.local/bin/<name>`）→ 重定向 `active_profile` → 迁移 session/routing identity（`agent:<old>:*` 键、heartbeats、投递路由）→ 热加载。

**不**做（改名后必须手工处理）：profile 内部文件里的绝对路径（venv console-script shebang、`scripts/*.sh`、cron `jobs.json` 里的 prompt），vault 笔记里的旧名，以及 **launchd 单元**——只清旧的、不重建新的，所以改完要 `hermes -p <new> gateway start`。

命名硬约束（源码）：`^[a-z0-9][a-z0-9_-]{0,63}$`，保留名 `hermes/default/test/tmp/root/sudo`。

## Profiles are islands

No config, provider or credential inheritance — ever. A provider visible in the default profile is
invisible in a named profile until its `providers.<name>` block is written into that profile's own
`config.yaml`; keys belong in the profile's own `.env`/`auth.json`.

A named profile reads credentials from its own `.env` **and** from the process environment. That is
why a desktop/multiplex backend (launched from the default home) can make default-home keys appear in
a profile's picker, while a launchd/systemd gateway service — started with an empty environment —
cannot (see "Credentials a gateway service needs").

## Recipe: restrict which providers a profile shows

Used when the user says "keep only X and Y" for a profile's provider list.

1. **Read the real picker rows first — never assume.** `hermes model` is interactive-only (no
   non-interactive flag), so script the row builder against the profile's home:

```bash
cd ~/.hermes/hermes-agent && set -a && . ~/.hermes/.env && set +a   # reproduce the creds a desktop backend supplies
HERMES_HOME=~/.hermes/profiles/<name> venv/bin/python3 -c "
from hermes_cli.config import load_config
from hermes_cli.model_switch_providers import list_authenticated_providers as L
cfg = load_config()
for r in L(current_provider=cfg['model'].get('provider',''), current_model=cfg['model'].get('default',''),
           user_providers=cfg.get('providers'), for_picker=True, probe_custom_providers=False):
    print(r['slug'], '|', r['name'], '|', r['is_current'], '|', r['total_models'])"
```

2. **Copy any provider the profile must have** from the default `config.yaml` — the whole
   `providers.<name>` block, `api_key` included.
3. **Hide the others with stubs** (no credentials, fully reversible):

```yaml
providers:
  volcengine-agent-plan: {api_key: …, base_url: …, model: ark-code-latest, models: […], name: …}
  zai: {enabled: false}
  copilot: {enabled: false}
```

   Mechanism (source-verified): `config_providers.is_provider_enabled` defaults to enabled and only
   an explicit `enabled: false` hides; `model_switch_providers._finalize_picker_rows` then drops rows
   matching **slug AND provider_id**, so built-in providers (`zai`, `copilot`, `opencode-*`) are
   hidden too, not just custom endpoints. A stub carries no `base_url`, so
   `get_compatible_custom_providers` and the desktop Custom-endpoints pane skip it — no half-broken
   endpoint in the UI. Credentials are untouched, so deleting the stub reverts the change.
4. **Verify rows, then verify end-to-end:**

```bash
hermes -p <name> chat -q '只回复两个字：可用' --provider <slug> -m <model> -Q
```

5. Tell the user the desktop picker is per session: a new session (or reopening that profile's
   window, which restarts its backend) shows the new list.

## Recipe: copy a provider block from the default profile into a named profile

Used when the user says "把一个提供商的配置从 default 复制过去".

1. **Diff the two blocks field by field before writing anything** — the target profile often already
   has the block, and only one field diverges (usually the hand-curated `models` list, since Ark-plan
   endpoints return 404 on `GET /models` so nothing is auto-discovered). Compare parsed dicts AND the
   raw text sha of the whole `providers:` section; a matching `api_key` fingerprint (sha256 prefix,
   never the value) proves the credential is already the same one.
2. **Replace only the diverging line range**, located by anchor lines (`    models:` up to the next
   `    <key>:` at that indent), then write via `path.tmp` + `os.replace` and restore mode 600.
   Copying the block's raw text never puts the secret in the transcript (a `patch` call would).
3. **Verify with tool output:** raw-text sha of both `providers:` sections equal, profile-scoped
   picker row present with the right model count, and one real end-to-end call
   (`hermes -p <name> chat -q '只回复两个字：可用' --provider <slug> -m <model> -Q`).
4. Tell the user to reopen that profile's window (or start a new session) — the picker is per session.

## Credentials a gateway service needs

`hermes -p <name> gateway start` installs a launchd/systemd service that starts with an **empty
environment**: copy every key the bot needs (the model provider's key, plus any `key_env`-referenced
provider key) into the profile's `.env`, then `chmod 600` it. A provider whose `api_key` is inline in
that profile's `config.yaml` needs nothing extra.

## Verifying which model ids a hand-curated endpoint really serves

Ark-plan style endpoints (`/api/plan/v3`) return **404 on `GET /models`**, so the `models` list is
hand-curated and nothing auto-discovers it. To get evidence instead of guessing, probe each id with a
1-token chat call (costs a token, changes nothing):

```bash
curl -s -m 45 -o /tmp/p.json -w "%{http_code}" -X POST <base_url>/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d "{\"model\":\"<id>\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":1}"
```

Run the id list through `xargs -P 6` so 18 ids finish in one pass. A 200 means the id is live.
Note the list is *additive history*: ids the user dropped usually still return 200, so "live" ≠
"should be listed" — only the user's current list defines membership. `arkcli models list/search`
(control-plane, foundation models like `doubao-seedance-*`) does NOT map to plan chat model ids.

## Symptom: one profile's bot 404s every turn while another profile on the same provider works

Root cause class: a mistyped model id was persisted by a `/model <name> --global`. Hermes does NOT
validate an explicitly named model against the provider's list — a nonexistent id is written happily
and every later turn fails with the provider's error (Ark plan: 404 `UnsupportedModel` "does not
support the agent plan feature"). **Never conclude "the provider is down" or start re-curating the
`models` list from this error; probe the id instead.**

One `/model --global` write lands in TWO places, and the session-level one wins:

1. `<profile>/config.yaml` → `model.default` (+ `provider`, `base_url`, `api_mode`)
2. the session row → `model_override` in `<profile>/sessions/sessions.json` **and** columns `model` /
   `model_config` of the `sessions` table in `<profile>/state.db`

Diagnose from the logs, not from the config file (the config can be correct while the session row is not):

```bash
grep -rn "does not support\|UnsupportedModel" ~/.hermes/profiles/*/logs/errors.log
# then read the `model=` field of these lines — that is the exact id sent:
grep -n "OpenAI client created\|API call failed" ~/.hermes/profiles/<name>/logs/agent.log | tail
grep -rn "Inbound dm message" ~/.hermes/profiles/<name>/logs/agent.log | tail   # finds the bad /model command
```

The provider's request id in the error is globally greppable and pins the owning profile:
`grep -rl "<request_id>" ~/.hermes/logs ~/.hermes/profiles/*/logs`.

Fix: correct `model.default` in that profile's `config.yaml`, then have the user re-issue
`/model <correct-id> --provider <slug>` **in that chat** (session scope, no `--global`) so the session
row is overwritten by the supported code path. Editing `state.db`/`sessions.json` while the profile's
gateway runs gets clobbered by in-memory session state — only do that with the gateway stopped.

Two red herrings seen in the wild: full-width/em-dash flags (`—provider`, from a Chinese IME
converting `--`) ARE normalized and parse correctly, and a `(probe-down)` context-length warning is
benign. The model-name typo is the only real hazard.

## Renaming a profile, and choosing its name

**Never propose name vocabulary you cannot ground.** Every candidate must trace to something checkable:
the docs' own example profile names (`website/docs/user-guide/multi-profile-gateways.md` uses `coder`,
`personal-bot`, `research` — domain/role nouns, no suffix encoding scope), the user's existing profile and
vault names, or a measured count. An invented coinage gets challenged on the spot ("why that word?") and
one ungrounded option discredits the whole proposal. The same rule kills a suffix whose real meaning is not
the property it is meant to encode: a rule that promises semantics it cannot deliver is worse than no rule,
because it also invalidates names that were already correct.

**Name = the stable 职责域, never a mutable structural property.** Single-project vs multi-project is
structure, and structure changes — put it in `terminal.cwd` (points at the project root), in
`profile.yaml: description` (picker text; the kanban orchestrator reads it too) and, for a genuinely
multi-project profile, in real `hermes project create` entries. Naming rule for this user: a domain
profile is named after its vault (`wangfanlin2_Investment` / `3_Travel` / `4_Accountancy` → `investment` /
`travel` / `accountancy`); a capability profile is named after the capability (`protein-designer` is
already correct — do not "fix" it to satisfy a naming schema).

```bash
hermes profile rename <old> <new>   # name: ^[a-z0-9][a-z0-9_-]{0,63}$, lowercase, not hermes|default|test|tmp|root|sudo
```

`rename_profile` (`hermes_cli/profiles.py`) stops that profile's gateway, unroutes a live multiplexer,
then migrates the directory, the `~/.local/bin/<name>` wrapper, `active_profile`, the Honcho host block and
session/routing identity (`agent:<old>:*`, heartbeats, delivery routing). It does **not** rewrite file
contents and does **not** re-create the launchd/systemd unit — it only cleans the old one — so after
renaming a profile that ran its own gateway: `hermes -p <new> gateway start`.

**Audit the conversion cost before renaming** — absolute paths *inside* the profile survive the move:

```bash
grep -rl --exclude-dir={logs,cache,backups,sessions,home,runtime,.curator_backups} \
     --exclude="*.db*" --exclude="*.jsonl" "profiles/<old>" ~/.hermes/profiles/<old>
```

Expect profile-local `venv/bin/*` shebangs and `activate*` (console scripts stop working), `cron/jobs.json`
prompts hardcoding `bash …/profiles/<old>/scripts/…`, and scripts that read the profile's own `.env` by
absolute path. Rank profiles by that count, rename the cheap ones first, hand-fix every hit plus the
SOUL.md self-name and the vault `README.md` header, then verify with `hermes profile list` and one real
`hermes -p <new> chat -q`.

Depth — audit interpretation, the scope-in-name-vs-structure decision table, post-rename checklist:
`references/profile-naming-and-renaming.md`.

## Pitfalls

- **A key in the process environment does NOT light up a built-in provider row in a named profile's
  picker.** Built-in rows read credentials through `hermes_cli/model_switch.py::_scoped_key_env`
  (`model_switch_providers.py` `_lap_builtin_rows`), which is per-profile scope: the key must sit in
  `~/.hermes/profiles/<name>/.env` (or inline in that profile's `providers` block). Proven A/B: with
  `ARK_API_KEY` set only in the process env the row stayed hidden, while travel-guider's own
  `.env`-keyed providers (deepseek/glm/kimi/opencode) all appeared in the same run.
- Don't add `enabled: true` to kept entries: `enabled` is not in `_KNOWN_PROVIDER_KEYS`, so an entry
  that reaches the normalizer warns about an unknown key. Absence already means enabled.
- Never edit the default profile's `config.yaml` to change a named profile — the write belongs in the
  named profile, even when the value is identical.
- A custom endpoint usually only serves its own model ids: keep `model.provider`, the
  `providers.<name>` entry and `model.base_url` consistent, or the profile authenticates against the
  wrong host.
- Don't trust the GUI as the verification surface: prove the change with the scoped listing and one
  real call, then tell the user the one action they may need (reopen the profile's window).
