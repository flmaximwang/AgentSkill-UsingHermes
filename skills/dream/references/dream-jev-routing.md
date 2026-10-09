# 用 JEV 判归位（本批次的题面与判读）

JEV（TypeSafe System One）是**决策模型**，不生成文本：给一份 `state`（材料）+ 一组有类型的题，回带概率的
结构化答案。归位判断正是它的适用面——一次请求里多题并行，比让 agent 逐条读便宜一个数量级。

**本文件里的题面是协议模板，不是实测样例**：本节的口径与限额来自 JEV 侧通用契约与本机实测的包/候选规模，
本 skill 尚未在本机跑过一次完整的 149 条归位（首次跑完请把真实数字补进 SKILL.md 的「实测基线」）。

## 1 · 探活（先确认能不能用，再决定走哪条路）

```bash
grep -c TYPESAFE_API_KEY "$HERMES_HOME/.env"          # 只数行数，不回显值
curl -sS -o /dev/null -w '%{http_code}\n' -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" -H 'Content-Type: application/json' \
  -d '{"state":"probe","model":"jev-latest","questions":{"q":{"type":"choice","instructions":"ok?","criteria":{"a":null,"b":null}}}}'
```

- `200` ⇒ JEV 可用；`401` ⇒ 凭据问题；`422` ⇒ 请求体检不过（改题面，重试无用）。
- **代理不通表现为超时**，不是 key 失效：本机对 `api.typesafe.ai` 的调用走本地代理端口，先确认代理在跑。
- `429`/`529` ⇒ 按 3 s、6 s 退避重试两次，仍失败就落「无法判定」并走 §6 降级。
- key 只从 `$HERMES_HOME/.env` / 环境变量 / `--key-file` 取；**永不进聊天、不进产物、不进 git**，也不要
  在报告里回显前缀。

## 2 · 请求形状（一次请求多题，两层的写法）

```json
{
  "state": "<pack-index.txt 全文：每个包现有的 category/name: desc>",
  "model": "jev-latest",
  "questions": {
    "P12": {"type": "choice",
            "instructions": "技能 `localskill`（classify-* 那一族，管分类号目录树的长路径重排）应当归到下面哪一个技能包？",
            "criteria": {"AgentSkill-ObsidianManagement": {"what": "Obsidian 库管理与分类号/CSS/dataview 这一族", "not_for": "git 与 annex 的内容"},
                         "AgentSkill-UsingGit": {"what": "Git 命令与历史操作一族", "not_for": "笔记库本身的管理"},
                         "__stay_local__": {"what": "没有任何包覆盖它，或材料不足以判断"}}},
    "P13": {"type": "choice", "instructions": "……", "criteria": {"…": null}}
  }
}
```

- **一层一条题**：每题一个 `choice`，选项 = 27 个落点包 + `__stay_local__` + **`__new_pack__`**（值得复用但
  没有包覆盖它 —— 两条判据都满足才准选它：正文认的是工具名/学科主题而不是某个 profile 的私事，且 S3 审计的
  already there 为空或近乎为空）；判到某个包之后，第二层再问
  一条 `choice`：该包已有技能名（从 `pack-index.txt` 抄）+ `__new__`。两层的题**不能放在同一次请求**里
  （不能互为上下文），要发两次。
- 选项的 `criteria` 用对象写（`what` / `not_for` / `examples`）比一句话准；两个包话题相邻时必须写
  `not_for`（实测最容易混的就是 git 与 git-annex、obsidian 管理与管理别的 vault）。
- 单题选项上限 255；`state` + 全部题 ≤ 64k token，`state` + 最长那题 ≤ 32k。
- 一次 5 层分类约几厘钱、单次请求 ~0.4–0.5 s —— 别为了省钱把该一次问完的拆成多次。

## 3 · 分块（按本机实测规模算）

本机实测：包索引 18.8k 字符（≈9k token），冻结候选表 44,526 B / 149 条（一条 ≈300 B）。

- 分块就是让 `state`（一次一份索引）+ 每批题落进 64k token 内。按一条题的题面 ≈150–250 token 估，
  **一批 25–30 条**是安全区；第二批起 `state` 可换成**裁剪过的索引**（只留与这批话题相关的包），
  题面预算就还有富余。
- 每块的请求与原始回复都要落盘（`jev-request-<n>.json` / `jev-response-<n>.json`），**永不删除**：
  回复体才有送去模型的原文与全部候选的概率，丢了只能再花一遍钱。

## 4 · 判读 → `verdicts-jev.jsonl`

从回复里逐题取 `choice` / `probabilities` / `confidence`，写成一行一条：

```json
{"id":"P12","dest_pack":"AgentSkill-ObsidianManagement","dest_skill":"relayer-clc-classification-paths","action":"merge","confidence":0.87,"source":"jev","model":"<回复体里的 model 字段>","why":"probabilities 次选是 UsingGit 0.09；与已有条目话题重合"}
```

- `action`：`move`（整条迁进包）/ `merge`（内容并进 `dest_skill`）/ `stay`（`__stay_local__`）。
- **只有回复体自带 `model` 字段的才算 JEV**。第二层的选择没有概率回填时，那一项标 `source: agent`。
- 分离度过低（赢家概率不到次选 2 倍）或置信 < 门限的行 → 在 `why` 里写清并**交给 S3/S4 复核**，
  不要静默取一个结论；报告里把它算进「待定」那一类。

## 5 · 复核队列的口径

低置信 **≠** 判错了。同一份材料重跑会给出不同分数（这是单次运行的产物，不是难度标签）。两类要分开报：
① 置信低于门限的行；② 某一层「险胜」的行。多数命中是后者——报告时说明是哪一种，别把整个队列说成「都判错了」。

## 6 · 降级路径（JEV 不在时）

| 情形 | 做什么 |
|---|---|
| `$HERMES_HOME/.env` 里没有 key | 直接走子代理路线（任务书 A），**不要**去别处找 key、不要向用户索要 key |
| 探针 `401`/`422` | 报「JEV 不可用（凭据/请求体检）」，走子代理路线；不要重试到超时 |
| 探针超时 | 先确认代理端口在跑，再重试一次；仍不通就走子代理路线并在报告里注明「已重试」 |
| `429`/`529` | 3 s、6 s 退避两次；仍失败走子代理路线 |
| 跑到一半失败 | 已落盘的分块结果保留（它们是真机答案），剩下的分块改走子代理；报告里**两组人数分开写** |

降级时口径不变：子代理的判定标 `source: agent`，与 JEV 的数字**并排但不混算**，不许把 agent 的结论写成
「JEV 判的」。
