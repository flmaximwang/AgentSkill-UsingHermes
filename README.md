# Agent Skill for Using Hermes

Verb keywords: install, remove, maintain

- Install: Add new things
- Remove: Remove things already existed
- Maintain: Move and check things already existed. Also modify existed content without contacting remote.
- Update: Contact with remote and modify existed content.
- Evolve: Analyze the current situation, and modify existed content or add new things.
- Load: Read something that exists elsewhere into context — no profile directory, no lock entry.

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

## Workflow

- Run `scripts/auto-generate-skill-structure.py` in the end to generate structures for every SKILL.md.
- Run `scripts/verify-skill-package.py skills/<name>` on the skills you touched (tree counts vs disk, and
  pointers), then commit both in the same commit as the edit. Details: `scripts/README.md`.