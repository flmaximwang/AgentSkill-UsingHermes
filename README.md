# Agent Skill for Using Hermes

Verb keywords: install, remove, maintain

- Install: Add new things
- Remove: Remove things already existed
- Maintain: Move and check things already existed. Also modify existed content without contacting remote.
- Update: Contact with remote and modify existed content.
- Recruit: 把一份学习成果收编进它该在的地方（分析现状 → 改已有内容或新增）。学到的那份在会话里 → `recruit-learning-in-session`；只存在于某个 profile 里、无仓库无 lock 条目 → `recruit-learning-in-profile`。
- Evolve: Recruit 的旧叫法。`evolve-hermes-skills` 已改名为 `recruit-learning-in-session`、`install-hermes-skill-from-a-profile` 已改名为 `recruit-learning-in-profile`，两者的 description 里都保留旧触发词，所以「evolve 这轮会话」「把 profile 里这个 skill 收进仓库」仍会路由到它们。
- Recruit（批量）: 一次把某个 profile 里**所有没有仓库归属**的本地 skill 收编进包仓库——枚举 → 判断归位（JEV 优先，否则分类子代理）→ 一次批准 → 每包一个 writer 并行写入 → 独立子代理回读 → 整包重装回 profile。→ `dream`（原名 `recruit-profile-skills-in-batch`）。它与单条 Recruit 的判别信号是**「一批 vs 一条」**。
- Load: Read something that exists elsewhere into context — no profile directory, no lock entry.
- Scan: 扫出本机 Hermes 的某种状态并列表（只读，不动任何库）。例：`scan-heartbeat-sessions` 扫所有 profile，列出挂着 heartbeat（会话级循环指令）的 session 及其累计 token。

## Load vs install

- **Load** reads a repo's `SKILL.md` frontmatter and puts a `name: description` table into the conversation. Nothing is written: no profile directory, no security scan, no lock entry, and `check` / `update` / `uninstall` never see it. The table lives only in that session.
- **Install** copies the skill into `<HERMES_HOME>/skills/<category>/<name>/`, scans it, writes a lock entry, and it becomes a normal skill of that profile — a row in the system-prompt index from the next session on, plus `/skill-name`.
- Loading the same repo twice costs the index twice; installing it once costs one prompt row from then on. Neither substitutes for the other.

```bash
# load — no profile change (owner/repo or a git URL is shallow-cloned to scratch first)
~/.hermes/hermes-agent/venv/bin/python3 skills/load-external-skill-index/scripts/skill-index.py <dir|owner/repo|url>

# install — writes the profile and takes a lock entry
hermes skills install flmaximwang/AgentSkill-UsingHermes/skills/load-external-skill-index --category hermes
```

## 路由盲测

改 description 头部（前 57 字符）或新增 skill 之后，跑一轮盲测：两个候选臂（不含 / 含新 skill）各两名互不
相见的判官，对着同一份冻结题面逐条选 skill。生成器、打分器、五件套与完整口径在
`docs/routing-blind-tests/`（README 里另有「本目录实测的口径坑」）。

| 轮次 | 日期 | 新技能 | 臂 B 新能力 | 臂 B 旧题 | 诱饵 | 旧题被新技能抢走 | 结论 |
|---|---|---|---|---|---|---|---|
| r1 | 2026-10-08 | `maintain-hermes-models` | 4/4 | 23/31 | 1/1 | 0 条 | 定版 |
| r2 | 2026-10-08 | `remove-a-hermes-plugin` | 3/4 | 29/37 | 1/1 | 0 条 | 头改 v2 再测（未过的是 P23「桌面 app 的 Remove 按钮」） |
| r3 | 2026-10-08 | `remove-a-hermes-plugin`（头 v2） | 3/4 | 28/37 | 1/1 | 0 条 | 定版；P23 两轮四判官一致投兄弟 → 记为接受的代价（语义双关） |
| r4-diagnose-update | 2026-10-08 | `diagnose-a-failed-hermes-update` | 4/4 | 32/47 | 1/1 | 0 条 | 定版 |
| r5 | 2026-10-09 | `dream`（r5 时名 `recruit-profile-skills-in-batch`） | 4/4 | 41/57 | 1/1 | 0 条 | 定版；4 条正例在臂 A 被判给兄弟 `recruit-learning-in-profile`（相邻，靠「一批 vs 一条」分开） |
| r6-scan-heartbeat-sessions | 2026-10-10 | `scan-heartbeat-sessions` | 4/4 | 40/54 | 1/1 | 0 条 | 定版；4 条正例在臂 A 被判给兄弟 `hermes-session-routing-forensics`（相邻：会话层面最像），诱饵（gateway 活体心跳）两臂两判官全部判给 `maintain-hermes-gateway` |

## 流程图

- 图随 skill 走：`skills/recruit-learning-in-session/assets/` 里有 PNG、交互版 HTML（浏览器打开即可）与源 JSON。
  改图只改源 JSON，再用 archify 的 `finalize` 重生成，不手改 PNG/HTML。
- **HTML 必须用「剥掉字体」的 archify 副本生成**：原模板把 6 段 woff2 以 base64 内联，安装扫描判
  `encoded_exfil`（high），整包会掉到 caution、远端要 `--force` 才装得上。做法：`cp -R` 一份 archify，
  把其 `assets/template.html` 里的 `@font-face {...}` 全删，再用副本的 `bin/archify.mjs` 生成 —— 画面不变
  （中英文字都回落到系统字体），四道闸对的就是这一份文件。

## Workflow

- Run `scripts/auto-generate-skill-structure.py` in the end to generate structures for every SKILL.md.
- Run `scripts/verify-skill-package.py skills/<name>` on the skills you touched (tree counts vs disk, and
  pointers), then commit both in the same commit as the edit. Details: `scripts/README.md`.