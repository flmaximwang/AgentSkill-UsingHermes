# Choosing an external memory provider (the `memory.provider` slot)

Scope: picking a provider, or judging whether to keep the one running — triggers: 「换一个更好用的记忆后端」
「这个插件没什么人用，退役它」「我要一个<某个能力>的 memory」— plus the shape to report the shortlist in.
Installing/provisioning a chosen provider: `maintain-hermes-memory-local-model-providers.md`.
One provider's own store and identity bugs: skill `use-limbic`.

## Step 0 — the user's hard conditions first, stars second

Ask for these before naming products. Each one, once answered, can wipe out the entire
high-star shortlist — and "自动遗忘" is the trap, because three different mechanisms all get
called "forgetting" in READMEs:

| 条件 | 要拆到哪一档 |
|---|---|
| **本地** | 零外网零 key ／ 可自建 server ／ 接受云 |
| **自动遗忘** | ① 随时间**衰减排序**（数据还在，只是沉底） ② **噪音清理**（正则/评分判垃圾，人工确认） ③ **真删除/失效**（atrophy、TTL 过期隐藏、图谱边失效） |
| **身份** | 是否要「同一人多平台 ID → 一个桶」；多用户是否需要隔离 |
| 捕获 | 要不要自动吞每轮对话（会带进噪音），还是只由 agent 显式写 |

判据一句话：**先问"他要的是数据消失，还是垃圾不再出现"**。答后者时，排序衰减 + 阈值过滤就够，别硬找会删数据的项目。

**不要替用户把条件收紧。** 他说「本地能跑就行」时不要听成「零依赖 / 零外网」——更严的读法会砍掉大半个候选池，还会让他反问
「你找到的好像都是冷门项目」。同样的收紧错误：「要有个 server」被读成「不能引入任何服务」、「别用云」被读成「不能有任何出网调用」。
每条都可以拆档报价（纯本地 / 自建服务 / 调外部 LLM），把选择权交给用户；只有在更严的读法**会改变结论**时才去问。

## Step 1 — candidate pool = the plugin catalog's `memory` category

```python
import json, pathlib
cat = json.loads((pathlib.Path.home()/"~/.hermes/cache/plugin-catalog.json").expanduser().read_text())
mem = [e for e in cat["entries"] if str(e.get("category", "")).lower().startswith("memor")]
# per entry: name, repo, version, subdir, capabilities.provides_tools / provides_hooks, description, tier
```

The pool is **bounded by the integration surface**: Hermes can only load something that implements
the `MemoryProvider` ABC (`website/docs/developer-guide/memory-provider-plugin.md`). A big framework
with no Hermes adapter is *not* a candidate, and that must be said out loud — otherwise the user
reads the shortlist as "you failed to find mem0/letta/graphiti". Rows with
`capabilities.provides_tools: []` and `subdir: null` are usually Agent-Plugins-v1 packages (MCP +
skills), not memory providers; check `tier`/`version` before quoting them.

## Step 2 — objective scale, then one-hand verification

```bash
gh auth status    # authed = 5000 req/h; a plain anonymous curl to api.github.com is 60/h and
                  # will NOT cover a ~57-repo pool in one sweep — check before fanning out
gh api repos/<owner>/<repo> --jq '{s:.stargazers_count,f:.forks_count,p:.pushed_at,i:.open_issues_count,l:(.license.spdx_id // "none")}'
```

Fan out over the pool (thread pool of ~6), sort by stars, and keep `pushed_at` **separate** from
release dates. This table is what you show the user (see the reporting shape below).

**Verify "it forgets" in the code, not in the README adjective.** Three probes, in this order:

```bash
gh api -X GET search/code -f q='repo:<owner>/<repo> decay'      # or expiration|ttl|atrophy|prune
# then read the two paths that decide: retrieval/search scoring, and session-end/cleanup hooks
```

A feature that exists only under a hosted-platform doc path (`docs/platform/...`) while the local
build raises or ignores it is **not** a local feature. Say which build the capability lives in.

## What one sweep of this pool actually found (re-measure before quoting; the commands above are the point)

- **mem0** — highest star count in the pool, Apache-2.0. Its *Memory Decay* is a **cloud project
toggle** (`client.project.update(decay=True)`, api.mem0.ai) and is a **ranking bias only**: the doc
states it "never filters anything out", floor `0.3×`. In the OSS build, `decay=True` raises
(`get_decay_feature_error_message(..., "project.update", "decay")`); locally there is only
`expiration_date` (YYYY-MM-DD) — expired rows are **hidden** from `search`/`get_all`
(`_payload_is_expired`, unless `show_expired=True`), never deleted, and the date must be supplied by
the writer. ⇒ "local + automatic forgetting" does not hold for mem0.
- **hindsight** — 池子里最大的厂商维护项目（MIT），集成层就在它自己的仓库里（`hindsight-integrations/hermes`，仓库带 Hermes 目录插件）。`local_embedded` = 它自己拉起一个 daemon + **内嵌 PostgreSQL**，用户不用养 server；但抽取仍要一个 **LLM 端点**（`ollama` 或任意 OpenAI 兼容），所以它的正确表述是「存储本地、抽取出网」，不是「本地」的对立面。遗忘侧是真的：retain 后自动 consolidate 成 observations（去重、带证据、矛盾保留演化史、源被删时失效重算），检索层另有 recency 衰减。`bank_id_template` 能按 `{platform}/{user}` 分桶。首次启动要现搭几百 MB 运行时、有超时闸 —— 见 `hindsight-local-embedded.md`。
- **openviking / honcho** — 要自建 server（或云）加 LLM key：picked 之前先问用户愿不愿意养一个常驻进程。
- **graphiti / letta / zep** — the real bi-temporal-invalidation / memory-eviction projects, and
  **absent from the Hermes catalog**: using them means writing a `MemoryProvider` adapter yourself.
  This is the whole reason they are missing, not their popularity.
- **holographic** (bundled with core, nothing to install) — local SQLite + FTS5 + trust;
  `temporal_decay_half_life` acts on **retrieval scoring** (`0.5^(age_days/half_life)`) plus a
  `min_trust_threshold` cut, configured under `plugins.hermes-memory-store`. **Deletes nothing** ⇒
  sinking, not forgetting.
- **mnemosyne** — pure Python + SQLite, zero cloud; forgetting is **noise hygiene**
  (`_score_noise`: terminal output/stack traces 0.85, trivial keywords 0.7, secrets 0.9 →
  delete/archive/flag; audit is read-only, clean needs `--confirm`, archive sets `importance=0` and is
  restorable) plus a sleep/consolidation cycle ⇒ not time decay. Memory is scoped by **bank
  (agent profile)**, not per chat-platform user. `[embeddings]` downloads bge-small-en-v1.5 on first use.
- **openltm** — MIT, `pip_dependencies: []`, local SQLite. Decay **is** the headline design
  (importance × confidence ageing, `importance: 5` = permanent) with an auto-capture rule table that
  guards runtime notifications out. User bucket = the raw `user_id` Hermes passes.
- **Intersection finding: "local + true deletion" only exists in small projects.** Mainstream does
  ranking decay or graph invalidation instead. So never present "local + automatic forgetting" as a
  default-satisfiable pair — put the relaxation choice in front of the user.

## Identity on a gateway: assume nothing, probe it

No provider in the pool resolves *multiple platform IDs of one person into one bucket*; they use the
raw `user_id`/snowflake (openltm, limbic's fallback) or an agent-profile bank (mnemosyne,
holographic). When the user runs a multi-user gateway, that is a real axis — check the provider's
identity code path for the per-turn entry (not just session init) before promising separation, and
report which bucket a fact will land in.

## Reporting shape when the user says "感觉你找到的都是冷门项目"

That is a report defect, not a search defect. Do **not** re-list the same names in new words:

1. Show the **whole pool's star/push table** so "small pool" is visible as data, not as your miss.
2. State the **pool boundary** in one line ("Hermes 只能插 MemoryProvider 插件" ) *before* the list.
3. Give every high-star absentee's **missing hard condition** (cloud / needs server / no adapter) —
   one line each; skipping this guarantees the next round is the same round.
4. Then offer the relaxations: "如果你愿意放宽 X 这一条，池子里就多了 Y" — one option per condition.
5. Finish with one executable next step (install which one, what three things to verify with their
   real data).
