# FAQs on the skills tap — why `search` cannot find a skill you published

Every item below was measured on this machine on 2026-09-30 (macOS Apple Silicon, code root
`~/.hermes/hermes-agent/`, `gh` authenticated, all commands read-only) while answering exactly this
question about `flmaximwang/AgentSkill-UsingHermes`. The tap for that repo was registered and correct
throughout:

```
$ hermes skills tap list
                Configured Taps
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Repo                             ┃ Path    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ flmaximwang/AgentSkill-UsingHermes │ skills/ │
└──────────────────────────────────┴─────────┘
```

`<HERMES_HOME>/skills/.hub/taps.json`:

```json
{
  "taps": [
    {
      "repo": "flmaximwang/AgentSkill-UsingHermes",
      "path": "skills/"
    }
  ]
}
```

So the tap was never the problem. The answer has **three layers**, and an empty result is explained by
any one of them — do not stop at the first.

## Layer 0 — the command itself

`hermes search <q>` is not a command (`hermes: 'search' is not a \`hermes\` command.`). The discovery
command is `hermes skills search <q>`.

## Layer 1 — an unfiltered `search` never queries the GitHub source, so the tap is not read

`tools/skills_hub_search.py`:

```python
# :84-87
_API_SOURCE_IDS = frozenset({"github", "skills-sh", "clawhub", "lobehub", "well-known"})
# :92  — the fallback pool deliberately keeps github out:
_INDEX_MISS_FALLBACK_IDS = _API_SOURCE_IDS - {"github"}
# :142-153
index_available = effective == "all" and any(
    src.source_id() == "hermes-index" and getattr(src, "is_available", False) for src in sources
)
...
for src in sources:
    sid = src.source_id()
    if effective != "all" and sid != effective and sid != "official":
        continue
    if index_available and sid in _API_SOURCE_IDS:
        continue                     # :150-151 — github included
    active.append(src)
```

The reason is written next to it (`:84-86`): the centralized index already covers those sources, and
querying them anyway costs ~70 GitHub calls per search for an unauthenticated user. The index-miss
fallback (`:156-173`) does re-query the other registries when the index answers a non-empty query with
nothing — **but not github**, on purpose (`:92`: one typo would burn an unauthenticated user's whole
hourly GitHub budget).

Measured, with `--json` so the source column cannot be misread:

```
$ hermes skills search manage-hermes-bundled-skills --json
results: 25
sources: ['skills.sh']
```

Those 25 rows (including `skill-creator`, the prisma/microsoft/expo ones) come from the **central
index**; `skills.sh` is the *upstream provenance recorded on each entry*, not a live skills.sh query.
The tap is invisible on this path by design, no matter how long you wait.

## Layer 2 — `--source github` does query the tap, but the source is cut at 30 s

`parallel_search_sources(..., overall_timeout: float = 30)` (`:225`), which sets
`deadline = time.monotonic() + overall_timeout` (`:250`) and, on expiry, marks every unfinished source
`timed_out` and **discards what it had collected** (`:214-218`). The observable symptom is an empty
result, not a partial one.

Measured — including a query that must match a *default* tap skill, which is the control that proves
this is not a matching problem:

| command | wall time | result |
|---|---|---|
| `hermes skills search manage-hermes-bundled-skills --source github` | 32.2 s | No skills found |
| `hermes skills search skill-creator --source github` (`skill-creator` is in the default tap `anthropics/skills`) | 32.3 s | No skills found |
| `hermes skills search zzzznomatch --source github` | 32.2 s | No skills found |
| `hermes skills search manage-hermes-bundled-skills --source skills-sh` | 2.2 s | 25 rows — **the tapped repo is not among them** |
| `hermes skills search flmaximwang` (unfiltered; the index answers this with nothing, so the fallback pool runs) | — | 0 rows (fallback excludes github, by `:92`) |

All three github runs land at the same 32 s ceiling regardless of the query, which is the timeout, not
a miss.

## Layer 3 — what actually consumes the budget: a *default* tap ahead of yours, 389 skills wide

`GitHubSource.__init__` (`tools/skills_hub_github.py:227`):

```python
self.taps = list(self.DEFAULT_TAPS) + list(extra_taps or [])   # extra taps go LAST
```

and `search()` walks `self.taps` **in order, one at a time** (`:251-259`), calling
`_list_skills_in_repo(tap["repo"], tap["path"], tap["bucket"])` per tap. That helper
(`:382-410`) does one `contents` call and then, **for every skill directory it finds, one
`self.inspect()` call — serially**:

```python
# :399-408
for entry in entries:
    if entry.get("type") != "dir" or entry["name"].startswith((".", "_")):
        continue
    dir_name = entry["name"]
    meta = self.inspect(f"{repo}/{prefix}/{dir_name}" if prefix else f"{repo}/{dir_name}")
    if meta:
        ...
        skills.append(meta)
```

and `inspect()` fetches and parses one `SKILL.md` per call (`:361-368`). So a tap's cost is
`1 + (number of skill dirs)` HTTP round-trips, sequential.

Per-tap measurement (the probe walked the exact list `search()` walks):

| tap | position | skills found | time |
|---|---|---|---|
| `openai/skills` (`skills/.curated/`, `skills/.system/`), `anthropics/skills`, `huggingface/skills` | 1-4 | 39 / 5 / 19 / 25 | **0.00 s each** — served from the on-disk tap cache |
| `NVIDIA/skills` | **5** | — | **hung past 160 s** |
| `flmaximwang/AgentSkill-UsingHermes` (the tap in question) | **25 of 25** | 7 dirs | ~6 s (7 × 0.87 s) — never reached |

Why tap 5 hangs: `NVIDIA/skills` has **389** skill directories under `skills/`, and one `inspect()`
measured **1.06 s** → that one tap needs roughly **411 s** on its own. The 30 s budget is gone long
before it, so the whole source — including any tap after it — is discarded. Your tap is last, so it is
the first casualty. It is not too big; it is behind something too big.

## Ruled out (so the explanation is not oversold)

| Suspect | Measurement | Verdict |
|---|---|---|
| Network / proxy | `GitHubSource._github_get` timed directly: `contents/` and `git/trees/HEAD?recursive=1` for **both** repos — 1.20 s / 0.92 s / 0.93 s / 1.14 s, all HTTP 200 | not it |
| Auth | `Authorization` header present on the request; token resolved from the `gh` CLI (`_try_gh_cli`, `:115-125`). `gh auth status` → logged in | not it |
| Repo contents / push state | `origin/main` == local `HEAD` (`af6b58a`), 35 blobs under `skills/` including the new skill dirs | not it |
| The skill files themselves | `GitHubSource.inspect()` on `flmaximwang/AgentSkill-UsingHermes/skills/{manage-hermes-bundled-skills,control-hermes-memory,install-hermes-skills}` → all three returned the right `name` + `description` | not it |
| skills.sh catalog | `--source skills-sh` returned 25 rows, none from this repo | it is a *second* dead end, not the answer |

## What to do instead — the path the tap was never needed for

A three-segment identifier resolves through the skills.sh adapter (which proxies GitHub), so preview
and install work with no search and no tap involved:

```bash
hermes skills inspect flmaximwang/AgentSkill-UsingHermes/skills/manage-hermes-bundled-skills
hermes skills install flmaximwang/AgentSkill-UsingHermes/skills/manage-hermes-bundled-skills --category hermes -y
```

Measured `inspect` output begins:

```
╭───────── Skill: manage-hermes-bundled-skills ─────────╮
│ Name: manage-hermes-bundled-skills                    │
│ Description: Use when Hermes' bundled (built-in) …    │
│ Source: skills.sh                                     │
│ Trust: community                                      │
│ Identifier: skills-sh/flmaximwang/AgentSkill-UsingHermes/skills/manage-hermes-bundled-skills
│ Repo: https://github.com/flmaximwang/AgentSkill-UsingHermes
╰───────────────────────────────────────────────────────╯
```

So: **install/inspect by identifier; treat the tap as an optional discovery nicety, not a
prerequisite.** If the user's goal is "let others discover my repo with a keyword", the honest answer is
that this path is closed today for a personal tap.

## Two observations to carry forward (both marked, not asserted)

1. **The tap cache is per-tap and persists** (taps 1-4 answered in 0.00 s from `_cached_metas`). If the
   blocking tap ever completes once, it is cached, and later taps become reachable inside the budget.
   Completing it needs ~411 s uninterrupted, which the 30 s CLI path cannot do — likely only a
   long-running index build could. *This is an inference from the timings, not a measurement: nobody has
   warmed that cache here.*
2. **Two upstream changes would each fix the user-visible symptom**: batch/parallelise the per-skill
   `inspect()` inside `_list_skills_in_repo` (read the repo tree once and parse all `SKILL.md` from it),
   or give the tap walk a per-tap budget so one 389-skill default tap cannot consume the whole source's
   share. Neither exists as of this measurement; nothing in this repo can work around it locally.
