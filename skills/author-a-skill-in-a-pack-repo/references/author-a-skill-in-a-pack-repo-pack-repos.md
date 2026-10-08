# 包仓库速查（快照，随仓库增长会过时）

**先核实再照抄**，两类命令足够判断现状：

> **clone 基路径（2026-10-03 本机实测）**：`~/Documents/AgentSkill/<repo>`。本文件表格里此前写的是
> `~/Repositories/AgentSkill/...`，该目录在本机**不存在**（`ls -ld` → No such file or directory）；
> 表里十个仓库全部落在 `~/Documents/AgentSkill/` 下。别与 `~/Repositories/Agent/`（`Agent-*` 那一家族，
> 另一批仓库）混。用前仍按下面第一条命令核实 —— 路径换机器就可能变。

```bash
# 仓库侧：路径段必须与 GitHub 实况一致，否则取不到件
git -C ~/Documents/AgentSkill/<repo> remote -v && git -C ~/Documents/AgentSkill/<repo> branch --show-current
# profile 侧：谁装了它、pin 在哪个 sha、装在哪个类目
python3 -c "import json;d=json.load(open('<profile>/skills/.hub/lock.json'))['installed'];\
print({k:(v['install_path'],v['metadata'].get('source_revision')) for k,v in d.items()})"
```

## 本机实测（截至最近一次核实）

| 仓库 | 可见性 | clone | 类目 `--category` | 目标 profile |
|---|---|---|---|---|
| `AgentSkill-LabProject` | private | `~/Documents/AgentSkill/AgentSkill-LabProject` | `lab` | `rdm-assistance` |
| `AgentSkill-DoingSAXS` | public | `~/Documents/AgentSkill/AgentSkill-DoingSAXS` | `saxs` | `default` |
| `AgentSkill-UsingATSAS` | private | `~/Documents/AgentSkill/AgentSkill-UsingATSAS` | `mals` | `default` |
| `AgentSkill-ObsidianManagement` | public | `~/Documents/AgentSkill/AgentSkill-ObsidianManagement` | `obsidian` | `obsidian-maintenance`（按需装） |
| `AgentSkill-UsingHermes` | public（已是 tap，路径段 `skills/`） | `~/Documents/AgentSkill/AgentSkill-UsingHermes` | `hermes` | **只有 `default`** —— 2026-10-08 用户定：其他 profile 不需要会维护 Hermes 框架本身，别再往它们铺（已在 plasmid-engineer 装过的那批不下架，属于那台 profile 的既有状态） |
| `AgentSkill-AgentOrchestration` | public | `~/Documents/AgentSkill/AgentSkill-AgentOrchestration` | `agent-orchestration` | **全部 profile** |
| `AgentSkill-AgentEvolution` | private（origin=SSH） | `~/Documents/AgentSkill/AgentSkill-AgentEvolution` | `agent-evolution` | `default` |
| `AgentSkill-JobHunt` | private | `~/Documents/AgentSkill/AgentSkill-JobHunt` | —— | **不装**：仓库即 source of truth，profile 里不留副本 |
| `AgentSkill-UsingBioXTASRAW` | 本地无 remote | `~/Documents/AgentSkill/AgentSkill-UsingBioXTASRAW` | —— | 未安装（历史包） |
| `AgentSkill-UsingGitAnnex` | private（origin=SSH） | `~/Documents/AgentSkill/AgentSkill-UsingGitAnnex` | `git-annex` | `default`（**11 条**已装：10 个主题 skill + `cheatsheet-for-git-annex`；各条 `source_revision` **混合**——实测 5 种提交，`check` 按内容判、全部 `up_to_date`） |
| `AgentSkill-PlasmidEngineer` | private（origin=SSH，2026-10-05 建） | `~/Documents/AgentSkill/AgentSkill-PlasmidEngineer` | `plasmid` | `plasmid-engineer`（**7 条**已装：SnapGene 读写 / Tm / 二聚体 / 结合位点 / Gibson 设计 / PCR 台账 / 调参；台账库 `plasmid_engineer` 跑在本机既有 dolt sql-server 上） |
| `AgentSkill-UsingAliyunpan` | private（origin=SSH） | `~/Documents/AgentSkill/AgentSkill-UsingAliyunpan` | `cloud-drive` | `default`（1 条：`use-the-aliyunpan-cli`） |
| `AgentSkill-UsingBaiduwp` | private（origin=SSH） | `~/Documents/AgentSkill/AgentSkill-UsingBaiduwp` | `cloud-drive` | `default`（1 条：`use-baidupcs-go`；**包名 `Baiduwp` 是用户指定的，内层 skill 名按要敲的命令叫 `baidupcs-go`**） |

## 三条固定口径

- **仓库是唯一 source of truth**：改内容 = 改 clone → commit → push `main` → `hermes skills update <name>`（无 lock 条目的旧手拷先做一次带 `--category` 的 install）。**手拷产物没有 lock 条目，check/update/uninstall 永远看不见**——这是要明说的代价，不能拿手拷当答案。
- **private 仓库靠凭据**：三段式标识符 + skills.sh 适配器取件，凭据来自 profile secrets / 机器级 gh keyring；取件失败先确认凭据来源，再怀疑标识符。
- **新建包 = 把 skill 移出 profile**（仓库为唯一 source of truth，README 只写安装命令）：例外是那些「按需装回」的包（如 ObsidianManagement 按 `--category obsidian`）。删 profile 里的副本：有 lock 条目走 `hermes skills uninstall`，没有就直接删目录。

## 装完必须回读三件

`diff -rq <clone>/skills/<name> <profile>/skills/<类目>/<name>` 为空 · `hermes --profile <p> skills check` 报 `up_to_date` · 从**profile 里那份**跑一次脚本。缺一件就不算装上。
