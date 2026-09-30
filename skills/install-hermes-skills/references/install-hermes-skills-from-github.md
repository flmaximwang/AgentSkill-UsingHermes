# Install Hermes Skills from Github

Get the github path first. A `github.com` link tells you *where* the skill is, not *what*
`hermes skills install` should be given — the identifier's shape depends on the repo's layout, and
**each shape buys a different amount of the skill**. This file is therefore a **ladder, not a menu**:
three routes ordered by what they actually get you.

**How to choose — walk it from the top, every time:**

1. Identify the repo type (Step 0 below). The type decides which rung is even reachable.
2. Convert the link to the rung 1 identifier for that type and try it. This is the default; get it working.
3. Only when a rung 1 **drop signal** fires (listed at the end of the rung 1 section), step down to rung 2.
4. Only when you have no checkout at all — a single `SKILL.md` and nothing else — step down to rung 3.
5. Say in your report which rung you used, and why the rungs above it were out.

Never drop a rung because it looks simpler or more familiar, and never offer a lower rung as an
"alternative" when a higher one works: the lower rungs lose files or lose maintenance, and they lose
them silently.

## The ladder

| 档 | 方式 | 装到多少 | 维护 | 什么时候用它 |
|---|---|---|---|---|
| **1** | 三段式标识符 `owner/repo/仓库内路径` | **整个技能目录** + pin 到 commit | **hub 全管**：`check` / `update` / `audit` / `uninstall` / `snapshot` 都认它 | **默认档**。类型 3 必用；类型 4 挑定目录后可用；类型 1 用 `<owner>/<repo>/` |
| **2** | 手动复制（先 clone，再 `cp -R`） | 你拷多少有多少——**选对了就是完整目录** | **手工养**：不进 lock，没有版本记录、没有 `update`、没有审计 | 档 1 无法命名目标时：根布局技能、私有仓库、离线、超大仓库只想要其中一部分 |
| **3** | 单个 `SKILL.md` 的 raw URL | 只有 `SKILL.md` + 正文**显式引用**的文件，且只在 `references/ templates/ scripts/ assets/` 四个前缀里 | hub 管，但**没有 commit pin** | **最后手段**：手上真的只有一个 `SKILL.md`（散落单文件、离线拷贝、正文之外什么也拿不到） |

Why this order — the criterion is *the cost you pay later*, not "which command is shorter":

- **Rung 1 is the only route that gets you the whole directory *and* automatic maintenance**, so it
  comes first. Everything below it gives up one of the two.
- **Rung 2 matches rung 1 on install completeness** (you decide what to copy), and gives up
  maintenance: nothing will ever re-sync it, so an upstream change means comparing by hand.
- **Rung 3 is last because it is the only route that can silently hand you a broken skill.** Measured
  on `kangarooking/cangjie-skill`: it brings **4 files / 40 KB** while the body references 14 more under
  `methodology/` (9) and `extractors/` (5) — those are neither in the four allowed prefixes nor
  explicitly referenced, so **all of them are dropped** and the installed skill ships with dangling
  references. **If a directory is reachable at all, do not use rung 3.**

**Self-check before any drop**: is rung 1 genuinely impossible (type forbids it, two-segment
identifier, private repo, verdict BLOCKED), or did I just not work out what the third segment should
be? Only the first answer licenses a drop.

**Contents**
- The ladder — the three rungs, in order, with the criterion for each
- Step 0 — which rung this repo can even reach (repo types, link forms, type → rung table)
- Rung 1 — three-segment identifier: conversions per type, install, verify, optional tap, drop signals
- Rung 2 — manual copy: complete install, maintenance is all yours
- Rung 3 — raw `SKILL.md`: last resort, measured losses, the SSRF `unavailable` case
- Error text → meaning (check here first — do not follow the error's own advice)
- FAQ

## Step 0 — Which rung this repo can even reach

Identify the type first, because **the type decides whether rung 1 is usable at all** (a type 2 root
skill can never use it).

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
| `github.com/<owner>/<repo>/tree/<ref>/<dir>` | ✅ 删掉 `https://github.com/` 和 `tree/<ref>` → 三段式（档 1） |
| `github.com/<owner>/<repo>` | 看类型：1 尾斜杠（档 1）、3 补第三段（档 1）、2 的根技能降档 |
| `raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>/SKILL.md` | ✅ 走 `url` 源（**必须四段**）→ 档 3 |
| `github.com/<owner>/<repo>/blob/<ref>/<path>` | ⛔ 抓回整个 HTML 页面 → `DANGEROUS` → `BLOCKED` |

### Repo type → highest reachable rung

| 类型 | 档 1 可用？ | 说明 |
| --- | --- | --- |
| 1 单技能仓 | ✅ `<owner>/<repo>/` | **代价 = 整仓**：除点开头文件和 `.pyc` 外全都打包。小仓库就是最优解；实测 cangjie 型仓库这一档是 **73 MB / 367 文件**（`books/` 96、`benchmarks/` 86、`dist/` 57…）→ 这种体量该降到档 2 挑目录 |
| 2 根技能 + 子技能 | 根技能 ✗ / 子技能 ✅ | 标识符**表达不了"只要根技能"**；尾斜杠能装但实测 **93–117 s → `CAUTION` → `BLOCKED` → `--force` → 156 文件 / 33.69 MB**，比档 2 还差 → 根技能直接降档。子技能走 `<owner>/<repo>/examples/<x>`（档 1） |
| 3 聚合仓 | ✅ | 常规情形，一条命令到位 |
| 4 非标准 / 深嵌套 | ✅（挑定目录） | 越深越容易装到非预期目标；这类仓库的根技能若走档 3 会掉文件 |

## Rung 1 — three-segment identifier (the default; get this one working first)

**What you get**: the whole skill directory, pinned to an upstream commit, recorded in the lock — so
`check`, `update`, `audit`, `uninstall` and `snapshot` all work on it. One command, no tap needed.

### Type 3 — aggregate repo

- `github.com/<owner>/<repo>/tree/<ref>/skills/<name>` → delete `https://github.com/`, delete
  `tree/<ref>`, delete a trailing `SKILL.md`; what is left, `<owner>/<repo>/skills/<name>`, is the
  identifier.
- `github.com/<owner>/<repo>` → find `<name>` first with the Step 0 command (one repo can have several
  installable targets: `Paper2Agent` measured 4).

Why the third segment may itself contain `/`, yet must stop at a directory: `_split_repo_id` splits
**twice** (`identifier.split("/", 2)`), so the third segment is "everything else" — but
`_skill_file_path` builds `f"{skill_path}/SKILL.md"`, so it must never carry the file name.

```python
parts = identifier.split("/", 2)                        # owner / repo / 其余全部
return (f"{parts[0]}/{parts[1]}", parts[2]) if len(parts) >= 3 else None   # _split_repo_id
```

Measured: `hermes skills inspect flmaximwang/AgentSkill-ObsidianManagement/skills/organize-obsidian-notes`
→ `Source: skills.sh`, whole directory = 6 files, pinned to commit `7884d88d`. (This shape is claimed
by the `skills.sh` adapter, which proxies GitHub and relabels the result.) Identifier discovery at
scale, and the batch recipe, are in `install-hermes-skills-from-skill-sh.md`.

### Type 4 — non-standard / deep nesting

List every `SKILL.md` with the Step 0 command → pick the directory you want → **strip the trailing
`/SKILL.md`** → prepend `<owner>/<repo>/<that relative path>`. Measured:
`alchaincyf/nuwa-skill/examples/naval-perspective` inspects fine (body 452 lines) — but that is a
sub-skill. For a repo shaped like `kangarooking/cangjie-skill` (root + deep nesting), the root skill
and the sub-directory skills take **different rungs**; no single identifier covers the whole repo.

### Type 1 — single-skill repo: `<owner>/<repo>/`

- `github.com/<owner>/<repo>` → **`<owner>/<repo>/` (trailing slash)**: an empty third segment means
  "skill dir = repo root" (`_skill_file_path('')` returns `SKILL.md` directly; the docstring states
  this is the designed way to say it).
- `github.com/<owner>/<repo>/tree/<ref>/SKILL.md` → the same `<owner>/<repo>/` (a bare two-segment
  `owner/repo` is rejected by `_split_repo_id`).
- `owner/repo/.` → fails outright with `Unsafe skill name: .`.

```bash
hermes skills install "<owner>/<repo>/" -y
```

**Drop signal**: when the repo holds a single `SKILL.md` but is *large* (measured: 73 MB / 367 files),
weigh it — rung 2 (clone, then copy only the directories you need) is less work here, at the cost of
losing automatic updates.

### Type 2 — why rung 1 cannot express the root skill

- `github.com/<owner>/<repo>` → ⛔ **no identifier expresses this**: the grammar cannot say "the root
  skill only".
- The trailing slash `<owner>/<repo>/` is syntactically valid but measured expensive
  (`alchaincyf/nuwa-skill`): **93–117 s** download+scan → `Verdict: CAUTION` →
  **`Decision: BLOCKED`（community + caution，29 findings，含 `.github/scripts/community_check.py:172`
  的 HIGH `exfiltration`）** → needs `--force`, and installs **156 files / 33.69 MB**. **That is worse
  than rung 2, so the root skill skips rung 1 and drops.**
- **Budget for it** (measured 2026-09-30 in a live session): against such an entry the hub commands
  re-walk the whole repo tree — one `hermes skills check nuwa-skill` cost **178 s**, and three
  `hermes skills inspect <id>` calls against the same entry cost **87 s** (≈29 s each). When you only
  need to know what is installed, read the lock entry or the on-disk tree (`scripts/lock-provenance.py`)
  instead of re-`inspect`ing an installed skill; a repeat `inspect` buys no new fact.
- Sub-skills still use rung 1: `github.com/<owner>/<repo>/tree/<ref>/examples/<x>` →
  `<owner>/<repo>/examples/<x>`.
- With both identifiers and this rung 3 out, the **root skill's only route is rung 2** — do it and
  state the cost instead of reinstalling the whole repo. Measured on `alchaincyf/nuwa-skill`
  (2026-09-30): copying `SKILL.md LICENSE references/ scripts/` out of a clone at the lock's recorded
  revision gives **9 files / 84 KB** in place of **158 files / 34.5 MB**, and the 15 `examples/*/SKILL.md`
  stop being discovered as sub-skills — the reason for the reinstall. Cost: `hermes skills check`
  answers `No hub-installed skills to check.` forever (no lock entry → `check`/`update`/`audit`/
  `uninstall` blind). The upstream fix that would restore rung 1 is a narrow in-repo directory
  (`skills/<name>/`) — say so and offer the PR rather than silently shipping the copy.

### Install and verify

```bash
hermes skills inspect <owner>/<repo>/<path>     # read-only; read Source / Trust first
hermes skills install <owner>/<repo>/<path> --category <cat> -y
hermes skills list                              # verify: Source / Trust / enabled; lands in skills/<cat>/<name>/
```

Several skills in one repo can be batched (still no tap needed):

```bash
for s in <skill1> <skill2>; do hermes skills install <owner>/<repo>/skills/$s --category <cat> -y; done
```

A real measured install (self-built repo, no tap):

```bash
$ hermes skills install "flmaximwang/AgentSkill-ObsidianManagement/skills/organize-obsidian-notes" --category obsidian -y
Decision: ALLOWED — Allowed (community source, safe verdict)
Installed: obsidian/organize-obsidian-notes
Files: SKILL.md, assets/darwin-card-20260930.png, scripts/organize.sh,
       scripts/organize_notes.py, scripts/test_organize_notes.py, test-prompts.json
```

- Lands in `skills/obsidian/organize-obsidian-notes/`; the lock records `source: skills.sh`,
  `source_revision: 7884d88dee7938b47c5115a4d1d91e7e71970de9`.
- **The verdict was `safe`, so no `--force` was needed** even though it reported **9 medium findings**
  (`oversized_file`: `assets/darwin-card-20260930.png` 707 KB > 256 KB; `python_subprocess` ×5;
  `unicode_escape_chain` ×1). **medium ≠ blocked**: community + safe is allowed outright; only
  caution/dangerous goes through `--force`.

### The ref rung 1 fetches is the repo's **default branch**

The identifier grammar has no slot for a ref: the `skills.sh` / GitHub route reads
`repos/<owner>/<repo>/contents/<path>` **without** a `ref`, i.e. whatever the default branch is.
Check that before blaming the path:

```bash
gh repo view <owner>/<repo> --json defaultBranchRef --jq .defaultBranchRef.name
```

Measured 2026-09-30 on `flmaximwang/AgentSkill-ObsidianManagement`: its GitHub default was
`optimize/organize-obsidian-notes` (an empty repo takes the **first branch pushed** as default), so a
skill living only on `main` 404s through rung 1 while an older skill on that branch installs fine.
The fix is repo-side, not route-side — fast-forward `main` and make it the default
(`gh api -X PATCH repos/<owner>/<repo> -f default_branch=main`). A `tree/<ref>` link does not rescue
it: rung 1's conversion deletes the ref, and `blob` links are unusable.

### Want it searchable too? add a tap (optional, does not change the install)

```bash
hermes skills tap add <owner>/<repo>      # → Added tap: …（写 skills/.hub/taps.json，默认 path "skills/"）
hermes skills search "<关键词>" --source github
```

A tap only affects **discovery** (it lets `search`/`browse` list the repo); the install command is
identical. For self-built small repos that search path is currently broken (without `--source` the
GitHub source is displaced by the central index; with it, the 30 s budget usually runs out) — so a tap
is an optional bonus, **not a prerequisite for rung 1**. Details and measurements:
`install-hermes-skills-from-names.md`.

### When rung 1 is out — the drop signals

- **Two-segment identifier `owner/repo`** → no source claims it (error texts in the table below) →
  type 1 adds the trailing slash; types 2/4 drop a rung.
- **Third segment written as a file** (`…/SKILL.md`) → `Could not find '…' in any source.` → drop the
  file name.
- **Private repo**: `skills.sh` always pulls files from the underlying GitHub repo, so **private repos
  cannot pass** → rung 2.
- **Root-layout skill (a type 2 root)** → rung 1 cannot express it → drop.
- **Whole repo too large** (the trailing slash drags the entire tree) → rung 2, copy the directories
  you need.

## Rung 2 — manual copy (complete install, maintenance is all yours)

**Use it when**: rung 1 cannot name the target (a type 2 root skill, a deep nesting with no unique
directory), the repo is private or offline, the repo is too large and you want only part of it, or the
skill is one **you intend to keep editing**.

```bash
# 1. get the directory
git clone <repo>            # or reuse an existing checkout
# 1b. PROVE the clone BEFORE anything is uninstalled — `hermes skills uninstall` has no local-edit
#     guard: it rmtree's the installed directory as it stands, and the lock entry is what you lose.
git -C <clone> log -1 --format=%H          # must equal metadata.source_revision in the lock entry
hermes skills snapshot export "$HERMES_HOME/cache/lock-before-<name>.json"   # whole hub ledger
python3 ~/.hermes/hermes-agent/venv/bin/python \
  <abs path to this skill>/scripts/lock-provenance.py <name>
#   ↑ the script needs HERMES_HOME exported and imports from $HERMES_HOME/hermes-agent: where that
#     tree is absent (a bare sandbox) it cannot run — read $HERMES_HOME/skills/.hub/lock.json directly.
diff -rq <clone>/<skill-dir> "$HERMES_HOME/skills/<path>"   # byte-for-byte; expect no output
# 2. copy the layer that contains SKILL.md into the SAME relative path the old copy had, so the
#    category stays valid and notes citing that path do not rot. Locate it first:
#    `ls -d "$HERMES_HOME"/skills/*/<name>` — the directory name is NOT always the name
#    `hermes skills list` prints (measured: directory `agent-evolution/nuwa-skill` lists as
#    `huashu-nuwa`, its frontmatter name).
DEST="$HERMES_HOME/skills/<category>/<same-dir-name-as-the-copy-you-replaced>"
mkdir -p "$DEST"
cp -R <clone>/<skill-dir>/. "$DEST"/
# 3. verify — it shows up as `local`
hermes skills list --source local
# 4. take effect: discovery is directory-based, nothing to register; in-session /reload-skills rescans
```

Measured 2026-09-30 on `alchaincyf/nuwa-skill`: the clone's `HEAD` equaled the lock's recorded
`source_revision`, `shasum -a 256 SKILL.md` matched the installed copy, `diff -rq references/ scripts/`
was empty — and only then did `hermes skills uninstall nuwa-skill -y` run. Skipping 1b on a type-2 repo
means the good hub copy is destroyed before you know the replacement is complete.

**What you keep**: this is the only route `update` will never overwrite (which is why "I will edit it
myself" points here), and you decide what gets copied — so the result can be far more complete than
rung 3.

**What you give up** (measured):

```
$ hermes skills check
No hub-installed skills to check.
$ hermes skills uninstall obsidian -y
Error: 'obsidian' is not a hub-installed skill (may be a builtin)
```

It is not in `.hub/lock.json`, so every hub maintenance command except `list`
(`check` / `update` / `uninstall` / `audit`) is blind to it and `audit.log` has no record: no version,
no audit, no diff — when upstream moves you compare by hand. Deleting means
`rm -rf <HERMES_HOME>/skills/<cat>/<name>`.

**Drop signal**: you do not even have a checkout — all you hold is a **single `SKILL.md`** (a gist, a
paste, one offline file) → only then go to rung 3.

## Rung 3 — raw `SKILL.md` (last resort, the least complete install)

**Use it when**: a single `SKILL.md` is genuinely all you have. **If a directory is reachable, do not
use this rung.**

```bash
# 1. the link must be raw (four segments: <owner>/<repo>/<ref>/<path>)
# 2. install (-y is required in non-interactive contexts)
hermes skills install "https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md" -y
# 3. if the name does not match ^[a-z][a-z0-9_-]*$ or the frontmatter has no usable name:, pass --name
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

Verify with `hermes skills list`: expect `Source: url`, `Trust: community`, landing **flat** at
`<HERMES_HOME>/skills/<name>/` (no category layer unless you pass `--category`).

**This rung's losses, measured one by one:**

- **Only files the body explicitly references, and only under five prefixes**
  (`_ALLOWED_SUPPORT_DIRS` and `_LOCAL_LINK_RE`, `tools/skills_hub_models.py:254-262`:
  `references/ templates/ scripts/ assets/ examples/`; `tools/skills_hub_sources.py:215` is only the
  caller of `_referenced_support_paths`). Same skill,
  measured: the URL route fetched **3 files**, the tap route **18** — the difference is exactly the
  unreferenced `scripts/`, `agents/`, `eval-viewer/`. **It is the reference *syntax* that decides**, not
  the path: `_LOCAL_LINK_RE` (`skills_hub_models.py:255`) matches a support path only after `](`, a
  backtick, or start/whitespace/quote, so a body that writes `` `python3 [skill目录]/scripts/x.py` ``
  loses that script. Measured on `alchaincyf/nuwa-skill`'s root skill (2026-09-30): **3 files**
  (the root `SKILL.md` plus the two support docs its body links — `extraction-framework.md`,
  `skill-template.md`) while the body
  tells the agent to run four `scripts/*.py|sh` helpers in Phases 1.5 and 4 — installed that way the
  skill is degraded, which is exactly what forbids this rung here.
- **⚠ For "repo root is the skill" repos it produces a broken skill**: measured on
  `kangarooking/cangjie-skill` →
  `Files: SKILL.md, scripts/cangjie.py, scripts/validate_skill_pack.py, templates/BOOK_OVERVIEW.md.template`
  (**4 files / 40 KB**), while the body references `methodology/` (9) + `extractors/` (5) = **14 files**
  — all dropped, so the installed skill ships with dangling references.
  **You can predict this before installing**: check whether the body references any path outside those
  five prefixes. If it does, do not use this rung — go back to rung 1 or 2.
- **No commit pin**: a `url` entry has no `metadata.source_revision`, so a floating `/main/` ref follows
  upstream, the next `update` takes whatever is there, and **there is no version to fall back to**.
  Pin the ref to a commit or tag if you need reproducibility. (Mechanism inferred; not measured by
  moving an upstream ref.)
- It is the only one of the three routes that is "semi-automatic": it enters the lock and works with
  `check`/`update`, but has no commit pin and no integrity guarantee beyond `files`.

### This rung's own trap: `check` reports `unavailable`

(Hit for real on this machine, 2026-09-30.) **The skill is not broken — the download path is blocked
by the SSRF guard.** The chain has four steps:

1. `check` only reads from the adapter matching the recorded source (`_source_matches`,
   `tools/skills_hub_install.py:262-330`; docstring: *"Each entry is fetched ONLY from adapters
   matching its recorded source … a missing adapter reports unavailable"*) → a `url` entry can only be
   fetched by `UrlSource`.
2. A `url` entry has **no** `metadata.source_revision` → the zero-download fast path ("same revision →
   `up_to_date`") is unreachable (`current_revision` is implemented only by `GitHubSource`,
   `skills_hub_github.py:300`; the base class returns `""`, `skills_hub_models.py:154-157`) → it must
   really download.
3. `UrlSource` inherits `GuardedFetchMixin`; downloads go through `hub()._guarded_http_get`
   (`skills_hub_models.py:163-167`) → resolve the host, then check whether it is private. Behind a
   fake-IP TUN proxy, `raw.githubusercontent.com` resolves to **198.18.0.8 (A)** and **2001:2::13
   (AAAA)** — both in benchmarking ranges → blocked.
4. Hence `_load → None → fetch → None → status: unavailable`. Real error text:
   ```
   Blocked request to private/internal address: raw.githubusercontent.com -> 198.18.0.8
   Blocked unsafe Skills Hub URL: https://raw.githubusercontent.com/.../SKILL.md
   ```

**Fix 1 (recommended, whole machine)**: declare the proxy's fake-IP ranges under `security:` in
`~/.hermes/config.yaml` — this is exactly the switch `tools/url_safety.py:183-214` keeps for
Mihomo/Clash fake-ip:

```yaml
security:
  fake_ip_ranges:
    - 198.18.0.0/15      # IPv4 fake-ip
    - 2001:2::/48        # IPv6 fake-ip —— 只写上面那段仍会被拦在 2001:2::13
```

Measured: declaring only `198.18.0.0/15` → still `Blocked … -> 2001:2::13`; **both ranges** →
`is_safe_url → True`, `UrlSource.fetch` succeeds (`files=['SKILL.md']`). Ranges overlapping
RFC1918/loopback/CGNAT are dropped by the guard (`_FAKE_IP_UNDECLARABLE_NETWORKS`,
`url_safety.py:131-135`). Side benefit: `web_extract`, platform attachment downloads and the browser
relay use the same guard, so they are fixed together.
**Fix 2 (this skill only)**: reinstall through a three-segment identifier (back to rung 1) — the source
becomes `skills.sh` (GitHub API, bypasses this guard), `check` works immediately, and you get the whole
directory as a bonus. **Fix 3**: set proxy env vars such as `HTTPS_PROXY` — `url_safety.py:367` has a
"hostname + configured proxy → hand DNS to the proxy" branch (TUN mode usually sets no env, so it is
inactive by default).

## Error text → meaning

Look here first — **do not follow the error's own advice**.

1. **Two-segment identifier `owner/repo`** (the most common rung 1 drop signal) — measured 2026-09-30:
   - `hermes skills install alchaincyf/nuwa-skill` → `Fetching: alchaincyf/nuwa-skill` →
     `Error: Could not download 'alchaincyf/nuwa-skill'.`, plus advice to run
     `hermes skills search nuwa-skill` and `hermes doctor` — **both suggestions are dead ends**
     (search does not find it either; doctor finds nothing wrong).
   - The same identifier via `hermes skills inspect alchaincyf/nuwa-skill` →
     `Error: Could not find 'alchaincyf/nuwa-skill' in any source.`
   - Both are **one fact, two subcommand failure branches**: `install` goes
     `do_install → _resolve_source_meta_and_bundle`, walking all 9 adapters (`inspect` + `fetch`),
     **every one returns None with no metadata at all** → it falls through to
     `_print_fetch_failure`'s generic text (the "it is in the index but gone upstream" wording only
     appears when metadata exists).
   - Of those 9 adapters only **2 actually sent HTTP**: `skills-sh` → `GET
     https://skills.sh/alchaincyf/nuwa-skill` → **308** (that is the repo page, not a skill page), and
     `lobehub` → `https://chat-agents.lobehub.com/alchaincyf/nuwa-skill.json` → **404**; the other 7
     (`official`/`hermes-index`/`well-known`/`url`/`github`/`clawhub`/`browse-sh`) short-circuit at the
     identifier-shape check (`github` requires ≥3 segments).
   - **Conclusion: no source claims a two-segment identifier. Do not go spelling-hunting and do not run
     `doctor` on the error's advice — for type 1 add the trailing slash; for types 2/4 drop a rung.**
2. **`Could not find 'https://…' in any source.` when what you passed was a URL (rung 3)**: on a machine
   that has not declared `fake_ip_ranges`, this is the SSRF guard. Fix it as above. **Do not read it as
   "this skill does not exist".**
3. **`Could not download '<url>'. Check the name with hermes skills search SKILL.md and check your
   internet connection. If it keeps failing, run hermes doctor.` (rung 3)**: Hermes' generic text —
   **you cannot tell a 404 from a typo**. Measured on one repo: `…/kangarooking/cangjie-skill/SKILL.md`
   (no ref) → **HTTP 404**; adding `main` / `master` / `HEAD` → **HTTP 200**. Check it yourself first:
   `curl -s -o /dev/null -w '%{http_code}' "<url>"`.
4. **A `blob` page link (any rung)**: `UrlSource` claims a URL by "path ends in `.md`"
   (`tools/skills_hub_sources.py:156-184`), so it drags back the **whole HTML page** as if it were
   `SKILL.md`; the scan judges `DANGEROUS` (`hidden_div`, `translate_execute`, `oversized_file`, 13
 findings) → `BLOCKED`, `--force` does not override it, and **nothing gets installed**. Switch to
 `raw.githubusercontent.com`.
 5. **`'<owner>/<repo>/<skill-name>' is listed in the hermes-index index, but its files no longer
 exist upstream.` (a three-segment identifier whose third segment is the skills.sh *skill name*)** —
 measured 2026-09-30 on `alchaincyf/nuwa-skill/huashu-nuwa`. skills.sh indexes that name
 (`path: "huashu-nuwa"`, `detail_url: …/alchaincyf/nuwa-skill/huashu-nuwa`) but no such directory
 exists — the skill sits at the repo root. Install therefore resolves hermes-index → skills.sh →
 `_discover_identifier`: the standard `skills/ .agents/skills/ .claude/skills/` candidates, then
 `_find_skill_in_repo_tree` (needs `<token>/SKILL.md`), then `_find_repo_root_skill` (**requires
 EXACTLY ONE `SKILL.md` in the whole tree** — this repo has 16) → nothing → this error. **`inspect`
 prints the index entry anyway, so a clean inspect does not prove an identifier installs** — and
 `--force` does not help. Repo-root skills of multi-skill repos stay unreachable by identifier.

## FAQ

- **Where does the skill name come from?** First the frontmatter `name:`; otherwise the directory
  name/slug in the URL; if neither, an interactive TTY asks you and non-interactive (`-y`) refuses —
  pass `--name`. A frontmatter like `My Skill v2` is unusable; use `--name my-skill-v2`.
- **Can `search` prove a GitHub skill does not exist?** No. Measured: `hermes skills search nuwa`
  returns 12 rows, **all from `clawhub`** (`nuwa-dual-mode`, `nuwa-video-gen`, …), not one of them the
  GitHub repo in question. The discovery/search failure modes are in
  `install-hermes-skills-from-names.md`.
- **Why doesn't a `Source: skills.sh` entry report `unavailable`?** Different HTTP paths: the `url`
  source goes through `_guarded_http_get` (with the SSRF pre-check), while `GitHubSource._github_get`
  goes through `hub()._skills_hub_http_get` (`tools/skills_hub_github.py:446-465`, no pre-check) — and
  `skills.sh`'s own `fetch()` is literally `self.github.fetch(...)`. Same machine, same day:

  ```
  organize-obsidian-notes │ skills.sh │ up_to_date      ← 走 GitHub API
  respond-to-questions    │ url       │ unavailable     ← 走守卫那条路
  respond-to-requirements │ url       │ unavailable
  ```
