# Install Hermes Skills from Github

Get the github path first.

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

四种链接形态跨类型通用的一条：`blob` 链接**一律不能用**（`UrlSource` 会抓回 HTML → 判 `DANGEROUS`，`--force` 也越不过）；`tree` 链接能直接切；`raw` 链接走 `url` 源；仓库根链接的可用性取决于类型。