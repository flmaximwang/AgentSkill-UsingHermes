---
name: maintain-hermes-models
description: "改某个或所有 profile 的默认模型、换模型 provider 时用：一条命令切全库、免重启、按计费字段回读。不负责 profile 的增删与网关服务（转 maintain-hermes-profiles），不负责一个 profile 里其它 config 叶子与 skill 树的批量整理（转 maintain-hermes-profile）。"
---

# 切 profile 的默认模型（一个 / 全库）

一条命令改完 N 份 `config.yaml` 的**顶层 `model:` 块**，免重启生效；再按**计费字段**回读「真在用」，
而不是只把文件读回来。全流程两个脚本、四条命令，秒级。

## When to Use（触发与边界）

- 触发：「把所有 profile 的默认模型换成 X」「这个 profile 换到 ark / volcengine / 某个自建 provider」
  「换模型 provider」「切完 `hermes profile list` 的 Model 列变成 `--`」「怎么证明新模型真的在用」。
- 不负责：profile 的创建 / 改名 / 删除、网关服务与端口、`hermes gateway` 的任何动作（→ `maintain-hermes-profiles`）；
  同一个 profile 里其它 config 叶子（`skills.disabled`、`agent.*`）与 skill 树的批量整理（→ `maintain-hermes-profile`）。

## 最快路径

```bash
S=<本 skill 目录>/scripts

# ① 先探活端点（一行），确认模型别名真的存在 —— 别拿 N 份文件当探针
curl -s --noproxy '*' -m 30 <base_url>/chat/completions \
  -H "Authorization: Bearer <key>" -H "Content-Type: application/json" \
  -d '{"model":"<模型 id>","messages":[{"role":"user","content":"hi"}],"max_tokens":16}'
#   返回体里会带服务端自己的 model 名（例：<id>-260910）——别名存在与否看它

# ② 漂移检查 → 真写（--dry-run 会列出会改谁、谁already；真写前每个文件整份备份）
python3 -B $S/switch-profile-models.py --model <模型 id> --provider <provider 名> \
        --base-url <base_url> --dry-run
python3 -B $S/switch-profile-models.py --model <模型 id> --provider <provider 名> --base-url <base_url>

# ③ 回读三件
hermes profile list                                   # Model 列：应全是目标模型；出现 `--` 就是写坏了
python3 -B $S/verify-profile-models.py --expect-model <模型 id> --expect-base-url <base_url>
```

实测一条（2026-10-08，本机 16 个 profile 从 deepseek 官方全切到 ARK 的 `deepseek-v4-1-flash`）：
`changed 12`（其中 2 个连 `providers:` 段都没有，被脚本补上）+ `already 4`；复跑 `--dry-run` = `changed 0`；
`verify-profile-models.py --expect-model deepseek-v4-1-flash` = 16 个 config 侧就位、3 个 ✅（真实调用已算到
ARK 端点）。数字属于那一次实例，不是通用常量。

## 两个脚本的旗标与退出码

```bash
python3 -B scripts/switch-profile-models.py --model <id> --provider <名> [--base-url <url>]
        [--api-mode chat_completions] [--profiles all|default|a,b] [--home ~/.hermes] [--dry-run]
python3 -B scripts/verify-profile-models.py [--profiles …] [--home ~/.hermes]
        [--expect-model <id>] [--expect-base-url <url>] [--require-live] [--json]
```

| 脚本 | 退出码 | 含义 |
|---|---|---|
| switch | 0 / 1 / 2 | 全部就绪（含「本来就在目标上」）/ 有失败项（逐条打印理由，含坏文件）/ 找不到 home 或没匹配到 profile |
| verify | 0 / 1 / 2 | config 侧都对（给了 `--expect-model` 才判）/ 有 ❌，或 `--require-live` 下没验到运行侧 / 找不到 home |

- 两个脚本**只用标准库**：前台与后台 shell 解析到的 `python3` 可能不是同一个，不能假设 PyYAML 存在。
- verify **只读**打开 `state.db`（`file:…?mode=ro`），不加锁；跑多少遍都不会动数据。

## 回读判据（两层，别互相代替）

| 看到的 | 结论 |
|---|---|
| `hermes profile list` 的 Model 列 = 目标模型 | config 侧落地 |
| Model 列出现 `--`，CLI 提示 "running on your last good settings" | 那份 config 被写出**重复顶层键** → 严格加载器拒收、静默回落 last-good（脚本本来就拒绝在这种文件上继续写） |
| `verify-profile-models.py` 打 ✅ | 该 home `state.db` 里最近一次真实会话的 `billing_base_url` 就是新端点 —— 这是「真在用」的硬证据 |
| 打 ⏳ | config 已就位，但这个 home **还没来消息**（最近一次会话是切换前的；无会话的 profile 也落这里）。不是失败 |
| 打 ❌ | config 侧与目标不符，要动手 |

## 硬规则（每条都在实况里踩过）

1. **只换 `model:` 块的块体，头行原地保留。** 把「带 `model:` 头行的新块」拼在 `lines[:1]` 之后会写出
   **重复顶层键**；PyYAML 的 `safe_load` 对它**静默通过**，而 Hermes 的严格加载器（ruamel）拒收整份文件并
   回落到 last-good —— 症状只有 `hermes profile list` 的 `--` 和一句 warning。判据是**顶层键计数**，不是
   「能不能解析」。脚本已把这条做成写前拒绝。
2. **profile 不继承主 home 的 `providers:` 段。** provider 是**本机自定义名字**时，该 profile 必须自己有
   `providers.<名字>:`（凭证就地取）；缺了就是「provider 无法解析凭证」。脚本会自动把主 home 那一整块复制进
   脚本会自动把主 home 那一整块复制进缺它的 profile（实测：artist、game-research 在切换时被补上）。
      **profile 里已经有顶层 `providers:`**（本机几乎每份都带着 volcengine 那一段）时，脚本只把 `  <名字>:`
      子块插到那个块的块尾、**不**再拼一个 `providers:` 头 —— 旧版整段插入会造出**重复顶层键**，实测 15 份
      profile 会被写前自检全部拒写（`写后顶层键重复：providers`）。
   **内置 provider（`deepseek` / `openai` / `anthropic` / `gemini` …）是例外**：主 home 里本来就没有
   `providers.<名字>:`，凭证走各 profile **自己**的 `<home>/.env` 的 `<NAME>_API_KEY`，不需要也**不该**注入
   `providers:` 块。脚本遇到主 home 没这一段时返回空表、只改 `model:` 块，并打一行 `note:` 说明
   （2026-10-09 全库切回内置 `deepseek`：主 home 无 `providers.deepseek`，16 份 `.env` 的 key 同值，
   切完 travel-guider 的首条真实调用即计到 `https://api.deepseek.com/v1`）。
3. **不需要重启网关。** 网关每轮从磁盘解析模型（`_resolve_gateway_model(_load_gateway_config())`，mtime 失效
   缓存），且解析出的 model/provider/base_url/凭证哈希是缓存 agent 签名的一部分 ⇒ 该 profile 的下一条消息就是
   新模型。主机上的网关是**一个多路复用进程**，为「换模型」重启它会打断**其它** bot 正在跑的轮次。
4. **`provider: <名字>` 与 `provider: custom:<名字>` 等价**（`hermes profile show` 两种都正常渲染）。不要为了
   好看去「归一化」一个在跑的 profile —— 那是没有收益的改动。
5. **先探活端点再批量写**，并**先 `--dry-run`**：`changed 0` + 一长串 already 才是「本来就在目标上」的证明。
6. **备份与回滚**：每个被写的文件整份备份到 `<home>/backups/model-switch-<ts>/<label>/config.yaml`（回滚见下）。
7. **一次性探针会留痕**：用 `hermes -p <profile> -z "…"` 造一次会话验证时，那个 home 会多一条
   `source='oneshot'` 的会话记录 —— 报告里点名，别让它变成「谁在我库里建了个会话」。
8. **内置 provider 的凭证只证明一次，别给每个 profile 各造一条探针会话。** 每个 profile home 有**自己**的
   `.env`（`profiles/<名>/.env`），内置 provider 的 key 就从那份取。所以先做一次**同值判定**：把
   `<home>/.env` 与每份 `profiles/*/.env` 里那行 `<NAME>_API_KEY` 取 sha256 逐份比 —— **全同值**时，任一份
   实测通过（或该 profile 历史会话的 `billing_base_url` 已是目标端点）就等于全库都能解析，**只给 1 份 profile
   打一次探针**即可；只有异值的那几份才需要各验一次。判据是「同值 + 一份实测」，不是「N 份都发过消息」。

回滚本次切换（只回这一个批次）：

```bash
for d in <home>/backups/model-switch-<ts>/*/; do l=$(basename "$d"); \
  [ "$l" = default ] && cp "$d/config.yaml" <home>/config.yaml \
                     || cp "$d/config.yaml" <home>/profiles/$l/config.yaml; done
```

## 检查点

| 触发 | 动作 |
|---|---|
| 想跳过端点探活直接批量写 N 份文件 | STOP：先打一条 curl，别名写错时你要改的是 N 份文件 |
| 这份 config 有重复顶层键 / 第一行不是 `model:` | STOP：脚本会拒写这一份并打印理由，**先修它**，不要在坏文件上继续 |
| 改完想 `hermes gateway restart`「让它生效」 | STOP：换模型每轮解析、本来就会生效；重启会打断别的 profile 在跑的轮次 |
| 想顺手「统一」`custom:` 前缀或别的字段 | STOP：只改这次要求的字段，一个字节的多余改动都要能在报告里解释 |

## Support files

| 文件 | 承担什么 |
|---|---|
| `references/maintain-hermes-models-fleet-mechanism.md` | 免重启的代码链与实测、重复键静默回落的实况、`providers` 继承边界、2026-10-08 那次全库切换的实测基线 |

## Skill Structure

<!-- Generated by Scripts -->

```
maintain-hermes-models/
├── SKILL.md  (134 lines)
├── test-prompts.json  (27 lines)
├── test-results.md  (46 lines)
├── references/
│   └── maintain-hermes-models-fleet-mechanism.md  (119 lines)
└── scripts/
    ├── switch-profile-models.py  (197 lines)
    └── verify-profile-models.py  (163 lines)
```

<!-- Generated by Scripts -->
