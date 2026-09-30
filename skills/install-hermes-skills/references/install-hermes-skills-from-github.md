# Install Hermes Skills from Github

Get the github path first. A `github.com` link tells you *where* the skill is, not *what*
`hermes skills install` should be given: the installable identifier depends on how the repo is laid
out, and the wrong shape installs the wrong thing — a sub-skill instead of the root skill, or 73 MB
of unrelated files. So the order is always: identify the repo type → convert the link → `inspect` →
install.

**Contents**
- Step 1 — identify the repo type (`gh api` one-liner, the browser fallback, the 4 types with real outputs)
- Which link forms survive (`raw` / `tree` / `blob` / repo root)
- Step 2 — convert the link into an install target (types 1–4, and what to do when no identifier fits)
- Known misjudgments — the four failures whose error text does not say what went wrong
- Step 3 — install and verify (Route A raw URL, Route D manual copy)
- FAQ — `blob` links, the four-segment raw URL, silently lost files, and the SSRF/`fake_ip_ranges` `unavailable` case

## Step 1 — Identify the repo type

List all `SKILL.md` to identify the type of this repo with the command below.

```sh
gh api "repos/<owner>/<repo>/git/trees/HEAD?recursive=1" --jq '.tree[] | select(.type=="blob") | .path' | grep -F "SKILL.md"
```

Repos fall into 4 types below.

| 类型 | 判据（列表长什么样） | 例（实测） |
| --- | --- | --- |
| **1 单技能仓** | 只有一行裸 `SKILL.md`（没有目录） | `orzcls/win-disk-cleaner`：**1 条** |
| **2 根技能 + 子技能** | 第一行是裸 `SKILL.md`，后面还有若干 `…/<x>/SKILL.md` | `alchaincyf/nuwa-skill`：全树 **16 条**（根 1 + `examples/` 15），212 条目 / 38.6 MB |
| **3 聚合仓** | 全是 `skills/<name>/SKILL.md`（可再嵌套） | `jmiao24/Paper2Agent`：**4 条**，都在 `skills/paper2agent/` 之下 |
| **4 非标准 / 深嵌套** | 其他（`benchmarks/…`、目录名与技能名不符、根 + 多处子目录） | `kangarooking/cangjie-skill`：**36 条**（根 1 + `benchmarks/naval/…`） |

四个仓库的**真实输出**（同一条命令）：

```
$ gh api …/jmiao24/Paper2Agent …            → 类型 3（4 条）
skills/paper2agent/SKILL.md
skills/paper2agent/paper2agent-paper/SKILL.md
skills/paper2agent/paper2mcp/SKILL.md
skills/paper2agent/paper2skill/SKILL.md

$ gh api …/alchaincyf/nuwa-skill …          → 类型 2（16 条）
SKILL.md                                     ← 裸的 = 根技能（女娲本体）
examples/andrej-karpathy-perspective/SKILL.md
examples/elon-musk-perspective/SKILL.md      … examples 共 15 条

$ gh api …/kangarooking/cangjie-skill …     → 类型 4（36 条）
SKILL.md
benchmarks/naval/prototypes/compact-pack/decision-heuristics/SKILL.md
benchmarks/naval/prototypes/compact-pack/hourly-rate-time/SKILL.md

$ gh api …/orzcls/win-disk-cleaner …        → 类型 1（1 条）
SKILL.md
```

### In the browser, when `gh` is unavailable or unauthenticated

1. **Read the repo home page's root listing** — top-level files vs directories are visible at a
   glance. On `alchaincyf/nuwa-skill` (measured): directories `.github/ assets/ examples/ promo/
   references/ scripts/`, files `SKILL.md README.md README_EN.md COMMUNITY.md CONTRIBUTING.md LICENSE …`.
   - root has `SKILL.md` → type 1 or 2.
   - root has **no** `SKILL.md` → type 3 or 4: the third segment lives inside a subdirectory.
2. **Click into the suspicious directory** — every subdir under `skills/` holding a `SKILL.md` →
   type 3; `examples/` full of `<person>-perspective/SKILL.md` → **type 2** (the root `SKILL.md` is
   the main skill, these are sub-skills — easy to install the wrong one).
3. **See the whole repo at once** — on the repo home page press `t` (or *Go to file*) → type
   `SKILL.md` → every `SKILL.md` in the repo is listed. This is the web twin of the `gh api` command
   above (the page fetches the tree via `/tree-list/`; curling that endpoint directly returns 400, so
   this step belongs in the browser).

**判据速记**：

| 页面上看到 | 类型 |
| --- | --- |
| 根只有 `SKILL.md`，没有别的目录里也放 `SKILL.md` | 1 单技能仓 |
| 根有 `SKILL.md`，且 `examples/`（或别的目录）里还有 `SKILL.md` | 2 根技能 + 子技能 |
| 根没有 `SKILL.md`，是 `skills/<name>/SKILL.md` | 3 聚合仓 |
| 其它（深嵌套、`benchmarks/…`、多级混合） | 4 非标准 / 深嵌套 |

README 也值得扫一眼：作者常写明这是"一个 skill"还是"技能集合"，有的直接给安装命令。

### Which link forms survive

四种链接形态跨类型通用的一条：`blob` 链接**一律不能用**（`UrlSource` 会抓回 HTML → 判 `DANGEROUS`，`--force` 也越不过）；`tree` 链接能直接切；`raw` 链接走 `url` 源；仓库根链接的可用性取决于类型。

| 你手上的链接 | 结果 |
| --- | --- |
| `raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>/SKILL.md` | ✅ 走 `url` 源，**必须四段**（见 FAQ） |
| `github.com/<owner>/<repo>/tree/<ref>/<dir>` | ✅ 删掉 `https://github.com/` 和 `tree/<ref>` → 三段式 |
| `github.com/<owner>/<repo>` | 看类型：1 尾斜杠、2 raw URL、3 补第三段 |
| `github.com/<owner>/<repo>/blob/<ref>/<path>` | ⛔ 抓回整个 HTML 页面 → `DANGEROUS` → `BLOCKED` |

## Step 2 — Convert the link into an install target

### Type 1 — single-skill repo (`SKILL.md` at the root, nothing else)

- `github.com/<owner>/<repo>` → **`<owner>/<repo>/`（带尾斜杠）**: an empty third segment means
  "skill dir = repo root" (`_skill_file_path('')` returns `SKILL.md` directly; the docstring states
  this is the designed way to say it).
- `github.com/<owner>/<repo>/tree/<ref>/SKILL.md` → same `<owner>/<repo>/` (a bare two-segment
  `owner/repo` is rejected by `_split_repo_id`).
- `raw.githubusercontent.com/<owner>/<repo>/<ref>/SKILL.md` → pass as a URL.

```bash
hermes skills install "<owner>/<repo>/" -y
```

Cost: the trailing slash means **skill dir = the entire repo** — everything is packaged except
dotfiles and `.pyc`. Weigh the size when a repo has one `SKILL.md` but lots of other content
(measured: the cangjie-style repo is 73 MB / 367 files). `owner/repo/.` fails with
`Unsafe skill name: .`.

### Type 2 — root skill + sub-skills

- `github.com/<owner>/<repo>` → ⛔ **no identifier expresses this**: the identifier grammar cannot
  say "the root skill only". Use the raw URL of the root `SKILL.md` instead — take
  `github.com/<owner>/<repo>/blob/<ref>/SKILL.md`, switch the host to `raw.githubusercontent.com`
  and drop `blob/`:

```
https://raw.githubusercontent.com/<owner>/<repo>/<ref>/SKILL.md
```

- `github.com/<owner>/<repo>/tree/<ref>/examples/<x>` → `<owner>/<repo>/examples/<x>`
  (three-segment) — that is the **sub-skill**, not the repo's main skill.
- The trailing slash `<owner>/<repo>/` is syntactically valid but measured expensive
  (`alchaincyf/nuwa-skill`): **93–117 s** download+scan → `Verdict: CAUTION` →
  **`Decision: BLOCKED`（community + caution, 29 findings, incl. a HIGH `exfiltration` at
  `.github/scripts/community_check.py:172`）** → needs `--force`, and installs **156 files /
  33.69 MB**.

The correct route, measured:

```bash
hermes skills install "https://raw.githubusercontent.com/alchaincyf/nuwa-skill/main/SKILL.md" --category nuwa -y
# → Installed: nuwa/huashu-nuwa
# → 3 files / 52 KB (SKILL.md + references/extraction-framework.md + references/skill-template.md)
```

The cost: you get only `SKILL.md` and the files its body **explicitly references** — nothing else.

Pitfall: on a machine that has not declared `fake_ip_ranges`, this URL reports
`Could not find 'https://…' in any source.` (see the FAQ at the end of this file).

### Type 3 — aggregate repo (`skills/<name>/SKILL.md`)

- `github.com/<owner>/<repo>/tree/<ref>/skills/<name>` → delete `https://github.com/`, delete
  `tree/<ref>`, delete a trailing `SKILL.md`; what's left, `<owner>/<repo>/skills/<name>`, is the
  identifier.
- `github.com/<owner>/<repo>` → find `<name>` first with the Step 1 command (one repo can have
  several installable targets: `Paper2Agent` measured 4).

Why the third segment can itself contain `/`: `_split_repo_id` splits **twice**
(`identifier.split("/", 2)`), so the third segment is "everything else". But `_skill_file_path`
builds `f"{skill_path}/SKILL.md"`, so the third segment must **stop at a directory** and never
carry the file name.

```python
parts = identifier.split("/", 2)                        # owner / repo / 其余全部
return (f"{parts[0]}/{parts[1]}", parts[2]) if len(parts) >= 3 else None   # _split_repo_id
```

Measured: `hermes skills inspect flmaximwang/AgentSkill-ObsidianManagement/skills/organize-obsidian-notes`
→ `Source: skills.sh`, whole directory = 6 files, pinned to commit `7884d88d`. (This identifier
shape is claimed by the `skills.sh` adapter, which proxies GitHub and relabels the result — see
`install-hermes-skills-from-skill-sh.md`.)

### Type 4 — non-standard / deep nesting

- List every `SKILL.md` with the Step 1 command → pick the directory you want → **strip the trailing
  `/SKILL.md`** → prepend `<owner>/<repo>/<that relative path>`.
- Measured: `alchaincyf/nuwa-skill/examples/naval-perspective` inspects fine (body 452 lines) — but
  that is a sub-skill. For a repo shaped like `kangarooking/cangjie-skill` (root + deep nesting),
  the root skill goes through the raw URL and the sub-directory skills go through three-segment
  identifiers; no single identifier covers the whole repo.
- Pitfall: the deeper the directory, the easier it is to install a target you did not mean. And the
  raw-URL route for a root layout only takes explicitly referenced files (measured: the cangjie root
  skill = 4 files / 40 KB, all 14 `methodology/` files referenced by its body were dropped).

### When no identifier can express the target

- **Fallback A — raw URL**: with a raw address for `SKILL.md`, any type installs (gets `SKILL.md` +
  the files its body explicitly references).
- **Fallback B — manual copy**: private repos, huge repos, or "I only want part of this tree" —
  clone, then `cp -R <clone>/<dir> <HERMES_HOME>/skills/[<category>/]<name>/`. The cost is real:
  it never enters the lock, so `check` / `update` / `uninstall` cannot see it (see Route D below).

### Known misjudgments — the failures that do not say what went wrong

1. **URL route, no `fake_ip_ranges` declared**: the CLI prints
   `Could not find 'https://…/SKILL.md' in any source.` — not a self-explaining "the SSRF guard
   blocked this", so it reads as "that skill does not exist". Declaring both fake-IP ranges in the
   config makes the same command succeed (see FAQ).
2. **Search**: the default `search` will happily show you same-name imitations —
   `hermes skills search nuwa` returns 12 rows, **all from `clawhub`** (`nuwa-dual-mode`,
   `nuwa-video-gen`, …), not one of them this GitHub repo (without `--source`, the GitHub source is
   skipped entirely — see `install-hermes-skills-from-names.md`).
3. **Three-segment written with the file name** (`<owner>/<repo>/…/SKILL.md`) →
   `Could not find '…' in any source.`
4. **Two-segment identifier — `install` and `inspect` report it differently** (measured 2026-09-30):
   - `hermes skills install alchaincyf/nuwa-skill` → `Fetching: alchaincyf/nuwa-skill` →
     `Error: Could not download 'alchaincyf/nuwa-skill'.`, plus advice to run
     `hermes skills search nuwa-skill` and `hermes doctor` — **both suggestions are dead ends**
     (search does not find it either; doctor finds nothing wrong).
   - `hermes skills inspect alchaincyf/nuwa-skill` → `Error: Could not find
     'alchaincyf/nuwa-skill' in any source.`
   - Both are **one fact, two subcommand failure branches**: `install` goes
     `do_install → _resolve_source_meta_and_bundle`, walking all 9 adapters (`inspect` + `fetch`),
     **every one returns None with no metadata at all** → falls through to `_print_fetch_failure`'s
     generic text (the "it is in the index but gone upstream" wording only appears when metadata
     exists).
   - Of those 9 adapters only **2 actually sent HTTP**: `skills-sh` → `GET
     https://skills.sh/alchaincyf/nuwa-skill` → **308** (that is the repo page, not a skill page),
     and `lobehub` → `https://chat-agents.lobehub.com/alchaincyf/nuwa-skill.json` → **404**; the
     other 7 (`official`/`hermes-index`/`well-known`/`url`/`github`/`clawhub`/`browse-sh`)
     short-circuit at the identifier-shape check (`github` requires ≥3 segments).
   - **Conclusion: no source claims a two-segment identifier. Do not go spelling-hunting or run
     `doctor` on the error's advice — switch to the type 1/2 route (trailing slash or raw URL).**

## Step 3 — Install and verify

Route B (three-segment, the common case) is `install-hermes-skills-from-skill-sh.md`; Route C (tap)
only changes *discoverability* and lives in `install-hermes-skills-from-names.md`. The two routes
that come out of a link conversion are:

### Route A — raw URL (one `SKILL.md` + its explicit references)

```bash
# 1. the link must be raw: .../<owner>/<repo>/<ref>/<path>
# 2. install (-y is required in non-interactive contexts)
hermes skills install "https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md" -y
# 3. if the name does not match ^[a-z][a-z0-9_-]*$ or frontmatter has no usable name:, pass --name
hermes skills install "<raw URL>" --name my-skill -y
```

Measured (25.4 s):

```
Fetching: https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md
Quarantined to .hub/quarantine/skill-creator
Running security scan...
Scan: skill-creator (...url/community)  Verdict: SAFE
Decision: ALLOWED — Allowed (community source, safe verdict)
Installed: skill-creator
Files: SKILL.md, assets/eval_review.html, references/schemas.md
```

Verify with `hermes skills list`: expect `Source: url`, `Trust: community`, landing at
`<HERMES_HOME>/skills/<name>/` (**flat, no category layer**).

Maintenance note specific to this route: a `url` lock entry has **no commit pin** — there is no
`metadata.source_revision`, so `check` must re-download every time, and a floating `/main/` ref means
you cannot roll back. Pin the ref to a commit or tag if you need reproducibility.

### Route D — manual copy (never in the hub)

```bash
# 1. get the directory
git clone <repo>            # or reuse an existing checkout
# 2. copy the layer that contains SKILL.md (two levels if you want a category)
cp -R <clone>/skills/foo "$HERMES_HOME/skills/<category>/foo"
# 3. verify — it shows up as `local`
hermes skills list --source local
# 4. take effect: discovery is directory-based, nothing to register; in-session /reload-skills rescans
```

Measured consequences of not being in the lock:

```
$ hermes skills check
No hub-installed skills to check.
$ hermes skills uninstall obsidian -y
Error: 'obsidian' is not a hub-installed skill (may be a builtin)
```

The trade: this is the **only route that `update` will never overwrite** (so it is the right one for
a skill you intend to keep editing), and in exchange you get no version record, no audit log, no
diff — when upstream moves you compare by hand. Deletion is
`rm -rf <HERMES_HOME>/skills/<cat>/<name>`; `uninstall` will not touch it.

## FAQ

- **Why can't I use a `github.com/.../blob/...` page link?** `UrlSource` claims a URL by "path ends
  in `.md`" (`tools/skills_hub_sources.py:156-184`), so it drags back the **whole HTML page** as if it
  were `SKILL.md`; the scan judges `DANGEROUS` (`hidden_div`, `translate_execute`, `oversized_file`,
  13 findings) → `BLOCKED`, `--force` does not override it, **nothing gets installed**. Use
  `raw.githubusercontent.com`.
- **The raw URL must have four segments**: `https://raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>`.
  Measured on one repo: `…/kangarooking/cangjie-skill/SKILL.md` (no ref) → **HTTP 404**; adding
  `main` / `master` / `HEAD` → **HTTP 200**. Hermes' error is the generic
  `Could not download '<url>'. Check the name with hermes skills search SKILL.md and check your
  internet connection. If it keeps failing, run hermes doctor.` — **you cannot tell a 404 from a
  typo**. Check it yourself first: `curl -s -o /dev/null -w '%{http_code}' "<url>"`.
- **Why did I only get 3 files?** The URL route downloads the files the body **explicitly
  references** under `references/ templates/ scripts/ assets/` (same file, `:210-240`). Same skill,
  measured: URL route 3 files vs tap route 18 — the difference is the unreferenced `scripts/`,
  `agents/`, `eval-viewer/`.
- **⚠ The URL route builds a broken skill for "repo root is the skill" repos.** Measured on
  `kangarooking/cangjie-skill`: `Files: SKILL.md, scripts/cangjie.py, scripts/validate_skill_pack.py,
  templates/BOOK_OVERVIEW.md.template` (**4 files / 40 KB**), while the body references
  `methodology/` (9) + `extractors/` (5) = **14 files** — those two directories are not among the
  four allowed prefixes, so **all of them are lost**. Such repos should go through B/C or manual (D).
- **Where does the skill name come from?** First the frontmatter `name:`; otherwise the directory
  name/slug in the URL; if neither, an interactive TTY asks you and non-interactive (`-y`) refuses —
  pass `--name`. A frontmatter like `My Skill v2` is unusable; use `--name my-skill-v2`.
- **Floating ref risk**: `/main/` follows upstream, so the next `update` takes new content with **no
  version to fall back to**. Pin the ref to a commit or tag for reproducibility. (Mechanism inferred;
  not measured by moving an upstream ref.)
- **Fit of this route**: it is the only one of the four GitHub routes that is "semi-automatic" — it
  enters the lock and works with `check`/`update`, but has no commit pin and no integrity guarantee
  beyond `files`.
- **⚠ `check` on a URL-sourced skill reports `unavailable` — what then?** (hit for real on this
  machine, 2026-09-30) **The skill is not broken; the download path is blocked by the SSRF guard.**
  Four steps:
  1. `check` only reads from adapters matching the recorded source (`_source_matches`,
     `tools/skills_hub_install.py:262-330`; docstring: *"Each entry is fetched ONLY from adapters
     matching its recorded source … a missing adapter reports unavailable"*) → a `url` entry can only
     be fetched by `UrlSource`.
  2. A `url` entry has **no** `metadata.source_revision` → the zero-download fast path ("same
     revision → `up_to_date`") is unreachable (`current_revision` is implemented only by
     `GitHubSource`, `skills_hub_github.py:300`; the base class returns `""`,
     `skills_hub_models.py:154-157`) → it must really download.
  3. `UrlSource` inherits `GuardedFetchMixin`; downloads go through `hub()._guarded_http_get`
     (`skills_hub_models.py:163-167`) → resolve the host, then check for a private address. Behind a
     fake-IP TUN proxy: `raw.githubusercontent.com` → **198.18.0.8 (A)** and **2001:2::13 (AAAA)**,
     both in benchmarking ranges → blocked.
  4. Hence `_load → None → fetch → None → status: unavailable`. Real error text:
     ```
     Blocked request to private/internal address: raw.githubusercontent.com -> 198.18.0.8
     Blocked unsafe Skills Hub URL: https://raw.githubusercontent.com/.../SKILL.md
     ```
  **Fix 1 (recommended, whole machine)**: declare the proxy's fake-IP ranges in
  `~/.hermes/config.yaml` under `security:` — this is exactly the switch
  `tools/url_safety.py:183-214` keeps for Mihomo/Clash fake-ip:

  ```yaml
  security:
    fake_ip_ranges:
      - 198.18.0.0/15      # IPv4 fake-ip
      - 2001:2::/48        # IPv6 fake-ip —— 只写上面那段仍会被拦在 2001:2::13
  ```

  Measured: declaring only `198.18.0.0/15` → still `Blocked … -> 2001:2::13`; **both ranges** →
  `is_safe_url → True`, `UrlSource.fetch` succeeds (`files=['SKILL.md']`). Ranges overlapping
  RFC1918/loopback/CGNAT are dropped by the guard (`_FAKE_IP_UNDECLARABLE_NETWORKS`,
  `url_safety.py:131-135`). Side benefit: `web_extract`, platform attachment downloads and the
  browser relay use the same guard, so they are fixed together.
  **Fix 2 (just this skill)**: reinstall through a three-segment identifier (type 3): the source
  becomes `skills.sh` (GitHub API, bypasses this guard), `check` works immediately, and you get the
  whole directory as a bonus. **Fix 3**: set proxy env vars such as `HTTPS_PROXY` —
  `url_safety.py:367` has a "hostname + configured proxy → hand DNS to the proxy" branch (TUN mode
  usually sets no env, so it is inactive by default).
- **Why doesn't a `Source: skills.sh` entry report `unavailable`?** Different HTTP paths: the `url`
  source goes through `_guarded_http_get` (with the SSRF pre-check), while `GitHubSource._github_get`
  goes through `hub()._skills_hub_http_get` (`tools/skills_hub_github.py:446-465`, no pre-check) —
  and `skills.sh`'s own `fetch()` is literally `self.github.fetch(...)`. Same machine, same day:

  ```
  organize-obsidian-notes │ skills.sh │ up_to_date      ← 走 GitHub API
  respond-to-questions    │ url       │ unavailable     ← 走守卫那条路
  respond-to-requirements │ url       │ unavailable
  ```
