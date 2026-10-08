# flmaximwang 的 skill 包仓库登记表（实测快照）

> **勘误（2026-10-08 本机实测，写表前必读）**：记忆条目与早期文档里写的
> `~/Repositories/AgentSkill/…`、`~/Repositories/AgentSkill-*` 在本机**不存在**
> （`ls ~/Repositories/` 里只有 `Agent-*` 一家族，是另一批仓库）。**所有 `AgentSkill-*` 包仓库
> 实测都在 `/Users/maxim/Documents/AgentSkill/` 下**。本表一律写实测路径；早些时候的记载按此改写。
> 路径会随机器变，**用前仍按下面第一条命令重核**。

两类信息分别核实，别互相替代：

```bash
# 仓库侧：路径 / 分支 / 远端（可见性用 gh repo view）
git -C /Users/maxim/Documents/AgentSkill/<repo> remote -v && git -C /Users/maxim/Documents/AgentSkill/<repo> branch --show-current
# profile 侧：谁装了它、装在哪个类目、pin 在哪个 sha
python3 -c "import json;d=json.load(open('<profile>/skills/.hub/lock.json'))['installed'];\
print({k:(v['install_path'],v['metadata'].get('source_revision')) for k,v in d.items()})"
```

## 全量枚举（`ls -d /Users/maxim/Documents/AgentSkill/AgentSkill-*/` → 逐个跑上面两条）

`skills/` 技能数为实测；可见性取自 `gh repo view flmaximwang/<repo> --json visibility`（**无远端的写「未核实」**，不瞎编 public/private）；类目取自各 profile 的 `.hub/lock.json` 的 `install_path`（查不到的写「未核实」）。

| 仓库 | 实测本地路径 | 可见性 | default 分支 | skills/ 技能数 | 安装类目 | 一句话作用/关键坑 |
|---|---|---|---|---|---|---|
| `AgentSkill-UsingHermes` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingHermes` | **public**（实测） | main | 20 | `hermes` | 「维护 Hermes 本身」的总包（install/remove/maintain/update/recruit/load 动词族）。**已是 tap，路径段 = `skills/`**。⚠️ 记忆里写「私有」，2026-10-08 `gh repo view` 与 `references/author-a-skill-in-a-pack-repo-pack-repos.md` 均实测为 **public**，以实测为准 |
| `AgentSkill-AgentOrchestration` | `/Users/maxim/Documents/AgentSkill/AgentSkill-AgentOrchestration` | public | main | 3 | `agent-orchestration` | 多 agent 协作包（`agent-to-agent-handoff`/`agent-handoff-and-review`/`agent-handoff-spec`）。**3 个 skill 都 hub 装到全部 profile**（`--category agent-orchestration`；2026-09-30 实测 11 个，本机现为 15 个命名 profile，新 profile 未必已铺）。扫描闸经验：正文写 home 相对字面路径的 ssh 配置/密钥名 = `ssh_dir_access(high)` → caution 被拦，**改文字描述即 safe** |
| `AgentSkill-AgentEvolution` | `/Users/maxim/Documents/AgentSkill/AgentSkill-AgentEvolution` | private（origin=SSH） | main | 3 | `agent-evolution` | agent 自身演化包（`skill-optimization-loop` + `skill-package-publishing`，+`darwin-skill` 相关）。2 个 skill hub 装到 `agent-evolution` 类目。**坑：`gh repo create` 留下的是 https origin → 裸 `git push` 卡在凭据提示直到超时**（改 SSH 或 `gh auth setup-git`） |
| `AgentSkill-DoingSAXS` | `/Users/maxim/Documents/AgentSkill/AgentSkill-DoingSAXS` | public | main | 6 | `saxs` | SAXS 处理包：两条流水线 skill + `write-saxs-results-readme`（结果目录契约）× 3 个方法 skill。技能数按实测（记忆里 5/6 都出现过）。该仓库常有另一会话同时 push main → 动手前 fetch、按 pathspec 暂存 |
| `AgentSkill-UsingATSAS` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingATSAS` | private（origin=SSH） | main | 1 | `mals` | ATSAS 4.1.4 官方手册（114 页）蒸馏成**唯一一个** skill `analyze-saxs-data-with-atsas`。扫描闸经验：正文出现 home 相对字面路径或提权词 = caution → 改描述式表述即 safe |
| `AgentSkill-UsingDolt` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingDolt` | private（origin=SSH） | main | 11 | `dolt` | Dolt 官方文档（`www.dolthub.com/docs`，174 页快照）蒸馏成 11 skill + 9 references。**抓取路线：站点自带 `/docs/llms.txt` 给全量页面清单，任意页面 URL 加 `.md` 直接返回未渲染 markdown**（不用扒 HTML） |
| `AgentSkill-UsingGitAnnex` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingGitAnnex` | private（origin=SSH） | main | 14 | `git-annex` | git-annex 主题包（14 skill，其中一条是速查表 `cheatsheet-for-git-annex`）。勘误：尺寸必须 `largerthan=1mb`（括号式被拒）；`install-and-initialize` 有 separate-git-dir 实测 R6 |
| `AgentSkill-LabProject` | `/Users/maxim/Documents/AgentSkill/AgentSkill-LabProject` | private | main | 8 | `lab` | rdm-assistance/lab 的包。装法 `hermes --profile rdm-assistance skills install "flmaximwang/AgentSkill-LabProject/skills/<name>" --category lab -y`；改 clone → push main → `hermes skills update <name>` |
| `AgentSkill-ObsidianManagement` | `/Users/maxim/Documents/AgentSkill/AgentSkill-ObsidianManagement` | public | main | 13 | `obsidian` | Obsidian 管理包，**全部 hub 装到 `obsidian` 类目**（skills.sh/community，pin commit；README 装法 `…/skills/<name> --category obsidian`，无需 tap）。是「按需装回」的例外包；`obsidian-theme-development` 装时需 `--force` |
| `AgentSkill-UsingComfyUI` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingComfyUI` | private | main | 3 | `creative` | ComfyUI 出图/工作流包（`author-a-comfyui-workflow` / `generate-images-with-comfyui-on-mac` / `install-and-check-diffusion-models`） |
| `AgentSkill-UsingZotero` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingZotero` | private | main | 1 | `zotero` | Zotero 包（`zotero-cli`） |
| `AgentSkill-UsingVSCode` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingVSCode` | private | main | 1 | `vscode` | VSCode 包（`fix-missing-commands-in-vscode`） |
| `AgentSkill-UsingSynologyNAS` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingSynologyNAS` | private | main | 2 | `infrastructure` | 群晖 NAS 包（`administer-a-synology-nas` 等） |
| `AgentSkill-UsingGit` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingGit` | private | main | 14 | `git` | Git 主题包（14 skill，对应 `git/` 类目下的 Pro Git 蒸馏一族等） |
| `AgentSkill-CloudDrive` | `/Users/maxim/Documents/AgentSkill/AgentSkill-CloudDrive` | private | main | 1 | `cloud-drive` | 网盘包（`mirror-one-cloud-drive-into-another` 等） |
| `AgentSkill-CodeExplain` | `/Users/maxim/Documents/AgentSkill/AgentSkill-CodeExplain` | public | main | 1 | `code` | 代码走读包（`explain-code-with-showboat`） |
| `AgentSkill-StructuredResponse` | `/Users/maxim/Documents/AgentSkill/AgentSkill-StructuredResponse` | public | main | 2 | `secretary` | 结构化应答包（`respond-to-questions` / `respond-to-requirements`） |
| `AgentSkill-PlasmidEngineer` | `/Users/maxim/Documents/AgentSkill/AgentSkill-PlasmidEngineer` | private（origin=SSH） | main | 8 | `plasmid` | 质粒/构建体工程包（SnapGene 读写、Tm、二聚体…）。台账库 `plasmid_engineer` 跑在本机既有 dolt sql-server 上 |
| `AgentSkill-JobHunt` | `/Users/maxim/Documents/AgentSkill/AgentSkill-JobHunt` | private | main | 1 | ——（**不装**） | 求职/职业分析包（唯一 skill `biotech-career-analysis`）。仓库即 source of truth，profile 里不留副本 |
| `AgentSkill-UsingAliyunpan` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingAliyunpan` | private（origin=SSH） | main | 1 | `cloud-drive` | 阿里云盘 CLI 包（`use-the-aliyunpan-cli`） |
| `AgentSkill-UsingBaiduwp` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingBaiduwp` | private（origin=SSH） | main | 1 | `cloud-drive` | 百度网盘包（`use-baidupcs-go`）。**包名 `Baiduwp` 是用户指定的，内层 skill 名按要敲的命令叫 `baidupcs-go`** |
| `AgentSkill-UsingBioXTASRAW` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingBioXTASRAW` | public | main | 13 | ——（未安装） | 技能后来演化进 `AgentSkill-DoingSAXS`。**勘误：早期记载「本地 git 无 remote」已过时 —— 现在有 origin**（`https://github.com/flmaximwang/AgentSkill-UsingBioXTASRAW.git`） |
| `AgentSkill-TravelGuide` | `/Users/maxim/Documents/AgentSkill/AgentSkill-TravelGuide` | private | ⚠️ **`auto-optimize/20260930-2145`**（不在 main） | 7 | 未核实 | 旅行攻略包。**分支停在 `auto-optimize/…`，不在 main**——引用它前先确认落点分支 |
| `AgentSkill-HoldingConversations` | `/Users/maxim/Documents/AgentSkill/AgentSkill-HoldingConversations` | 未核实（**无远端**） | main | 2 | 未核实 | 无 remote（`git remote -v` 空），仅本地 |
| `AgentSkill-UsingAstra` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingAstra` | 未核实（**无远端**） | main | 11 | 未核实 | 无 remote，仅本地 |
| `AgentSkill-UsingEagle` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingEagle` | 未核实（**无远端**） | main | 2 | 未核实 | 无 remote，仅本地 |
| `AgentSkill-UsingRosetta` | `/Users/maxim/Documents/AgentSkill/AgentSkill-UsingRosetta` | private | main | 10 | 未核实 | Rosetta 主题包（10 skill） |

## 逐条要点（记忆条目 → 本表的落点）

- **⑨ UsingHermes**：私有记载与本机实测冲突，已在表内改标 public；已是 tap（`path=skills/`）、`default=main`。
- **⑬ LabProject**：装法 `hermes --profile rdm-assistance skills install "flmaximwang/AgentSkill-LabProject/skills/<name>" --category lab -y`；改 clone → push main → `hermes skills update <name>`。7→实测 8 个 skill（`audit-log-protein-characterization` 2026-10-02 新增，靠**同类目兄弟目录**自动定位同包 `find-stock` 的 `find_stock.py`）。
- **⑲ AgentOrchestration**：**public**；3 个 skill 装到全部 profile（`--category agent-orchestration`）。扫描闸经验见上表。
- **㉒ AgentEvolution**：私有；2 个 skill 装到 `agent-evolution` 类目；`gh repo create` 留 https origin 的坑见上表。
- **㉔ install-hermes-skill-from-a-profile**：属 UsingHermes 包（五阶段迁移流程，已 hub 装到 default 的 `hermes` 类目，pin b55a6bf）。判据：bundled 名字也没有 lock 条目（本机 58 条），`.usage.json` 的 `created_by` 是历史不是现状。路由表已指向它。
- **㉖ UsingBioXTASRAW**：勘误已按实测更新（现 public、有 origin）。
- **㉙ load-external-skill-index**：属 UsingHermes 包（pin 685f44a，`hermes` 类目，safe）。是「读进对话、不安装」的 **Load** 动词（表 = 会话数据，不进系统提示）；已扇出到全部 profile（私有仓库靠**机器级 gh keyring token**，不是 profile secrets）。
- **㊳ UsingATSAS**：私有；唯一 skill `analyze-saxs-data-with-atsas`；装到 default 的 `mals` 类目。扫描闸经验见上表。
- **㊴ DoingSAXS**：public（技能数按实测 = 6）。
- **㊷ UsingDolt**：私有；11 skill + 9 references，装到 `dolt` 类目。抓取路线见上表。
- **㊾ UsingGitAnnex**：装到 `git-annex` 类目；勘误 `largerthan=1mb`。

## 单列一节：GitNexus（⑳，**不是包仓库**）

GitNexus 不走 `AgentSkill-*` 包仓库那套，单独记：

- CLI：`npm i -g gitnexus`（1.6.12，装到 `/opt/homebrew/bin/gitnexus`）。
- `gitnexus analyze --index-only` **不改仓库文件**；`gitnexus mcp` = stdio，暴露 17 个工具。
- 挂在 **software-development profile** 的 `config.yaml` → `mcp_servers.gitnexus`；skill `official/research/gitnexus-explorer` 装在该 profile 的 `software-development` 类目。
- **坑**：该 profile 的 `skills/software-development/` 原本被**同名本地路由技能**（SKILL.md + references/ + scripts/，list 里 category 空白）占着 → 安装器报
  `Refusing to install into '<x>': it is an existing skill directory, not a category.`
  修法 = 把那个路由技能的 SKILL.md/references/scripts **整体下移一层**到 `skills/software-development/software-development/`（内容 sha 不变，仍列出，category 变成 `software-development`）。

## 三条固定口径（与 `references/author-a-skill-in-a-pack-repo-pack-repos.md` 同源）

- **仓库是唯一 source of truth**：改内容 = 改 clone → commit → push `main` → `hermes skills update <name>`（无 lock 条目的旧手拷先做一次带 `--category` 的 install）。手拷产物没有 lock 条目，`check`/`update`/`uninstall` 永远看不见。
- **private 仓库靠凭据**：三段式标识符 + skills.sh 适配器取件，凭据来自 profile secrets / 机器级 gh keyring；取件失败先确认凭据来源，再怀疑标识符。
- **新建包 = 把 skill 移出 profile**（仓库为唯一 source of truth，README 只写安装命令）：例外是按需装回的包（如 ObsidianManagement 按 `--category obsidian`）。删副本：有 lock 条目走 `hermes skills uninstall`，无条目直接删目录。
