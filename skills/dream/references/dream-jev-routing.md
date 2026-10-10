# 用 JEV 判归位（本批次的题面与判读）

JEV（TypeSafe System One）是**决策模型**，不生成文本：给一份 `state`（材料）+ 一组有类型的题，回带概率的
结构化答案。归位判断正是它的适用面——一次请求里多题并行，比让 agent 逐条读便宜一个数量级。

**本文件里的题面是协议模板，不是实测样例**：口径与限额来自 JEV 侧通用契约与本机实测的包/候选规模。

**v2 的两条硬口径**（2026-10-10 用户改口径，破坏性）：

1. **没有 `__stay_local__`**：判官的答案空间只有「已有目录」与「新建包」两种，每条候选都必须有落点。
2. **JEV 看不到正文就只配判「轴」**：JEV 是决策模型、不做生成，它的 `state` 只有文本。所以第一段
   （轴：工具还是主题）可以整批交给 JEV；**第二、三段（落点 / 落点技能）要读 SKILL.md 全文**——要么把
   `judge-input-bodies.json` 的正文分块塞进 `state`（一批只放 3–5 条），要么这一段改派会 `read_file` 的子代理。
   **不许把「只看 name+desc 的 JEV 答案」当成已经判完**（这种偷懒判法用户明确驳回过）。

## 1 · 探活（先确认能不能用，再决定走哪条路）

```bash
grep -c TYPESAFE_API_KEY "$HERMES_HOME/.env"          # 只数行数，不回显值
curl -sS -o /dev/null -w '%{http_code}\n' -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" -H 'Content-Type: application/json' \
  -d '{"state":"probe","model":"jev-latest","questions":{"q":{"type":"choice","instructions":"ok?","criteria":{"a":null,"b":null}}}}'
```

- `200` ⇒ JEV 可用；`401` ⇒ 凭据问题；`422` ⇒ 请求体检不过（改题面，重试无用）。
- **`451`** ⇒ 官方回 `Typesafe is not available in your region`（本机 2026-10-11 实测就是这个）：与超时同样算
  **不可用**，直接走 §6 子代理路线，**别重试到超时**（它与限流不是一回事）。
- **代理不通表现为超时**，不是 key 失效：本机对 `api.typesafe.ai` 的调用走本地代理端口，先确认代理在跑。
- `429`/`529` ⇒ 按 3 s、6 s 退避重试两次，仍失败就落「无法判定」并走 §6 降级。
- key 只从 `$HERMES_HOME/.env` / 环境变量 / `--key-file` 取；**永不进聊天、不进产物、不进 git**，也不要
  在报告里回显前缀。

## 2 · 请求形状（两轴先判，再问落点）

JEV 的 `state` 只放文本，所以**先发一次只判轴、正文不进 state 的请求**（便宜、可整批并行），再对「轴已定」的
行发第二次、这次把该条的正文放进 `state`：

```json
{
  "state": "候选技能 P12 的名称：pymol-headless-rendering；描述：用 PyMOL 无头出图时用…",
  "model": "jev-latest",
  "questions": {
    "P12": {"type": "choice",
            "instructions": "这条技能的**主语**是「某个软件/工具」还是「一类任务/学科/项目」？",
            "criteria": {"tool": "主语是某个具体软件/工具（PyMOL、Dolt、git-annex、ComfyUI …）",
                         "topic": "主语是一类任务、学科或项目（做 SAXS 分析、整理笔记库、跑本地批处理 …）"}}
  }
}
```

第二次（轴=tool 时；轴=topic 同理，选项换成 `answer-space.json` 的 `topic_dirs`）：

```json
{
  "state": "<该条 SKILL.md 全文>",
  "model": "jev-latest",
  "questions": {
    "P12": {"type": "choice",
            "instructions": "读完整篇正文后：它该归到下面哪一个目录？没有合适的就答 new。",
            "criteria": {"AgentSkill-UsingPyMOL": {"what": "PyMOL 出图这一族", "not_for": "结构建模与打分"},
                         "AgentSkill-UsingRosetta": {"what": "Rosetta/PyRosetta 一族", "not_for": "纯出图"},
                         "new": {"what": "现有目录都不覆盖它；正文认的是工具名或学科主题"}}}
  }
}
```

- **选项来源是 `answer-space.json`（`tool_dirs` / `topic_dirs`），别手抄目录名**；选项的 `criteria` 用对象写
  （`what` / `not_for` / `examples`）比一句话准；话题相邻的目录必须写 `not_for`（最容易混的几对：git 与
  git-annex、Obsidian 管理与别的 vault、PyMOL 与 Rosetta）。
- 单题选项上限 **255**（291 个目录名放一题会超限 ⇒ 先按轴拆两题，或按首字母分块）；`state` + 全部题 ≤ 64k token、
  `state` + 最长那题 ≤ 32k。
- 一次 5 层分类约几厘钱、单次请求 ~0.4–0.5 s —— 别为了省钱把该一次问完的拆成多次。

## 3 · 分块（按本机实测规模算）

本机实测（2026-10-11）：`judge-input.json` 62,253 B / 99 条（一条 ≈630 B），`judge-input-bodies.json`
1,322,501 B（≈1.32 MB，平均每条正文 13 kb），可选路由包索引 ≈49.6k 字符。

- 判轴那一轮：一条题的 `state` 只有几百字节 ⇒ **一批 25–30 条**是安全区。
- 判落点那一轮要带全文 ⇒ **一批 3–5 条**（13 kb/条 × 5 ≈ 65 kb，已贴近单题 32k token 的上限，按块实测再调）。
- 每块的请求与原始回复都要落盘（`jev-request-<n>.json` / `jev-response-<n>.json`），**永不删除**：
  回复体才有送去模型的原文与全部候选的概率，丢了只能再花一遍钱。

## 4 · 判读 → `verdicts-jev.jsonl`

从回复里逐题取 `choice` / `probabilities` / `confidence`，写成一行一条（v2 形状）：

```json
{"id":"P12","dest":{"kind":"existing","repo":"AgentSkill-UsingPyMOL","dest_skill":"__new__","action":"move"},
 "why":"probabilities 次选是 UsingRosetta 0.09；正文只讲无头出图","evidence":"正文：「装在本机 conda 环境」",
 "confidence":0.87,"source":"jev","model":"<回复体里的 model 字段>"}
{"id":"P31","dest":{"kind":"new","axis":"topic","topic":"RunningLocalBatches","personal":true,
 "boundary":"不吃常驻服务与 cron"},
 "why":"正文讲的是一类任务的通用方法，现有 17 个主题包都不覆盖","evidence":"…","source":"jev","model":"…"}
```

- `action`：`move`（整条迁进包）/ `merge`（内容并进 `dest_skill`）/ `strengthen`（两边头部各加界限声明）。
- **只有回复体自带 `model` 字段的才算 JEV**。第二/三段若改由子代理读正文作答，那一条标 `source: agent`。
- 分离度过低（赢家概率不到次选 2 倍）或置信 < 门限的行 → 在 `why` 里写清并**交给 S3/S4 复核**，
  不要静默取一个结论；报告里把它算进「待复核」那一类（**不是**「留本地」——v2 没有这个答案）。
- **`merge` 会自己拒收错形状**：`dest` 里出现 `__stay_local__`、`repo` 不在 `answer-space.json`、`dest_skill`
  不在该目录的技能清单里、`kind:"new"` 缺 `boundary` —— 任何一种都是 exit 4。所以判读这一步**不要替它兜**
  （别把拿不准的写成 stay local、别猜一个技能名）：让脚本拒收比悄悄写错便宜。

## 5 · 复核队列的口径

低置信 **≠** 判错了。同一份材料重跑会给出不同分数（这是单次运行的产物，不是难度标签）。两类要分开报：
① 置信低于门限的行；② 某一层「险胜」的行。多数命中是后者——报告时说明是哪一种，别把整个队列说成「都判错了」。

## 6 · 降级路径（JEV 不在时）

| 情形 | 做什么 |
|---|---|
| `$HERMES_HOME/.env` 里没有 key | 直接走子代理路线（任务书 A），**不要**去别处找 key、不要向用户索要 key |
| 探针 `451` | 报「JEV 不可用（区域限制）」，**立刻**走子代理路线；不要重试到超时 |
| 探针 `401`/`422` | 报「JEV 不可用（凭据/请求体检）」，走子代理路线；不要重试到超时 |
| 探针超时 | 先确认代理端口在跑，再重试一次；仍不通就走子代理路线并在报告里注明「已重试」 |
| `429`/`529` | 3 s、6 s 退避两次；仍失败走子代理路线 |
| 跑到一半失败 | 已落盘的分块结果保留（它们是真机答案），剩下的分块改走子代理；报告里**两组人数分开写** |

降级时口径不变：子代理的判定标 `source: agent`，与 JEV 的数字**并排但不混算**，不许把 agent 的结论写成
「JEV 判的」。子代理每批 **8–12 条**（要读全文，比只给 name+desc 贵得多），任务书见 `dream-agent-roster.md` 的
任务书 A。
