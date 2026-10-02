# 包仓库速查（快照，随仓库增长会过时）

**先核实再照抄**，两类命令足够判断现状：

```bash
# 仓库侧：路径段必须与 GitHub 实况一致，否则取不到件
git -C ~/Repositories/<repo> remote -v && git -C ~/Repositories/<repo> branch --show-current
# profile 侧：谁装了它、pin 在哪个 sha、装在哪个类目
python3 -c "import json;d=json.load(open('<profile>/skills/.hub/lock.json'))['installed'];\
print({k:(v['install_path'],v['metadata'].get('source_revision')) for k,v in d.items()})"
```

## 本机实测（截至最近一次核实）

| 仓库 | 可见性 | clone | 类目 `--category` | 目标 profile |
|---|---|---|---|---|
| `AgentSkill-LabProject` | private | `~/Repositories/AgentSkill-LabProject` | `lab` | `rdm-assistance` |
| `AgentSkill-DoingSAXS` | public | `~/Repositories/AgentSkill-DoingSAXS` | `saxs` | `default` |
| `AgentSkill-UsingATSAS` | private | `~/Repositories/AgentSkill-UsingATSAS` | `mals` | `default` |
| `AgentSkill-ObsidianManagement` | public | `~/Repositories/AgentSkill-ObsidianManagement` | `obsidian` | `obsidian-maintenance`（按需装） |
| `AgentSkill-UsingHermes` | public（已是 tap，路径段 `skills/`） | `~/Repositories/AgentSkill-UsingHermes` | `hermes` | **全部 profile** |
| `AgentSkill-AgentOrchestration` | public | `~/Repositories/AgentSkill-AgentOrchestration` | `agent-orchestration` | **全部 profile** |
| `AgentSkill-AgentEvolution` | private（origin=SSH） | `~/Repositories/AgentSkill-AgentEvolution` | `agent-evolution` | `default` |
| `AgentSkill-JobHunt` | private | `~/Repositories/AgentSkill-JobHunt` | —— | **不装**：仓库即 source of truth，profile 里不留副本 |
| `AgentSkill-UsingBioXTASRAW` | 本地无 remote | `~/Repositories/AgentSkill-UsingBioXTASRAW` | —— | 未安装（历史包） |

## 三条固定口径

- **仓库是唯一 source of truth**：改内容 = 改 clone → commit → push `main` → `hermes skills update <name>`（无 lock 条目的旧手拷先做一次带 `--category` 的 install）。**手拷产物没有 lock 条目，check/update/uninstall 永远看不见**——这是要明说的代价，不能拿手拷当答案。
- **private 仓库靠凭据**：三段式标识符 + skills.sh 适配器取件，凭据来自 profile secrets / 机器级 gh keyring；取件失败先确认凭据来源，再怀疑标识符。
- **新建包 = 把 skill 移出 profile**（仓库为唯一 source of truth，README 只写安装命令）：例外是那些「按需装回」的包（如 ObsidianManagement 按 `--category obsidian`）。删 profile 里的副本：有 lock 条目走 `hermes skills uninstall`，没有就直接删目录。

## 装完必须回读三件

`diff -rq <clone>/skills/<name> <profile>/skills/<类目>/<name>` 为空 · `hermes --profile <p> skills check` 报 `up_to_date` · 从**profile 里那份**跑一次脚本。缺一件就不算装上。
