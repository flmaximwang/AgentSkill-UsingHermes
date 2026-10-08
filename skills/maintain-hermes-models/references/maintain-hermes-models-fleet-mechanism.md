# 全库换模型：机制与实测

本文件是 `maintain-hermes-models` 的证据层。SKILL.md 只留动作与判据，这里存**为什么**和**当时测到了什么**。

## 一、为什么不用重启网关（2026-10-08 在本机代码里核过）

链子（本机安装的源码树，`~/.hermes/installs/<id>/environments/<id>/workspace/`）：

1. 网关**每轮**从磁盘读 config：`gateway/run.py::_load_gateway_config()` →
   `hermes_cli/config_effective.py::load_user_config_effective(<home>/config.yaml)`，
   而 `hermes_cli/config.py` 的 `_LOAD_CONFIG_CACHE` 以 **stat 签名（mtime/size）** 作缓存键
   —— 文件一改，签名变，缓存失效。
2. 模型从这份 config 里取：`gateway/run.py::_resolve_gateway_model(config)`
   = `config["model"]["default"]`（或 `.model`）。
3. 解析出来的 model 与 provider/base_url/api_mode/凭证哈希一起进**缓存 agent 的签名**：
   `gateway/run_agent_cache.py::_agent_config_signature(model, runtime, …)` 把它们 `sha256` 后当 key
   —— 模型变了就重建 agent，不会复用旧的那个。
4. `model.default` **故意不在** `gateway/run.py::_CACHE_BUSTING_CONFIG_KEYS` 里：
   那份清单装的是「构造时就烤进 agent、改了必须重建」的设置（`compression.*`、`memory.provider`、
   `checkpoints.*`、`model.context_length`）。`model.default` 不在其中，正是因为它是每轮解析的。

结论：**改 `model:` 块 = 该 profile 下一条消息就是新模型**。主机上的网关是一个多路复用进程
（`hermes gateway list` 里每行都是 "served by the default multiplexer"），为「换模型」重启它会打断其它
profile 在跑的轮次 —— 没有收益的破坏。

实测（同一台机，替换前后各做一次一次性会话，回读各自 home 的 `state.db`）：

```
artist        20261008_131041_27f624  model=deepseek-v4-1-flash  billing_provider=custom
                                       billing_base_url=https://ark.cn-beijing.volces.com/api/plan/v3
game-research 20261008_131105_b227b4  model=deepseek-v4-1-flash  billing_base_url=…/api/plan/v3
default       20261008_131122_78f746  model=deepseek-v4-1-flash  billing_base_url=…/api/plan/v3
```

同一批 profile 切换前的最近会话记的是 `model=deepseek-flash` + `billing_base_url=https://api.deepseek.com/v1`
—— `sessions.billing_provider` / `billing_base_url` 是**那次调用实际算钱到的端点**，所以它才是「真在用」的
判据；`sessions.model`、`session_model_usage`（按 model 分行的用量表）同源可查。
这三条会话的 `source` 都是 `oneshot`（`hermes -p <profile> -z "…"` 造的探针），报告里要点名。

## 二、重复顶层键：静默回落 last-good（本次踩坑的完整实况）

第一版脚本把「带 `model:` 头行的新块」拼在 `lines[:1]`（原本那行 `model:`）之后，于是每份文件开头变成：

```yaml
model:
model:
  default: deepseek-v4-1-flash
  …
```

- **PyYAML 的 `safe_load` 不报错**（重复键取后者），所以「解析一下就过」的自检通过了；
- Hermes 的加载器是**严格模式 ruamel**，直接拒收，并打印：

  ```
  Your settings file (<home>/config.yaml) has a formatting error at line 2.
  Hermes is running on your last good settings until it is fixed, so recent changes are not applied.
  Details: found duplicate key "model" with value "{}" (original value: "None")
  ```

- 症状是**静默的**：`hermes profile list` 那一列变成 `--`（16 行里 12 行 `--`，另外 4 行本来就在目标上）。
  没有任何命令会主动报「这份 config 坏了」，除非你去跑 `hermes config check`。

所以判据必须是**顶层键计数**（同一键出现两次即坏），不是「能不能 `safe_load`」。
`scripts/switch-profile-models.py` 把它做成写前/写后两次拒绝，并逐份打印理由；坏文件被跳过，其余照改。

## 三、profile 不继承主 home 的 `providers:` 段

`~/.hermes/config.yaml` 里的 `providers.<名字>:` 只属于 default profile。命名 profile 各有各的
`config.yaml`；`model.provider` 写了一个本机自定义 provider 名、而那份 config 里没有对应的
`providers.<名字>:` 时，凭证**无处解析**（这个 provider 段就是放 `api_key` / `base_url` / 可选 `models:` 清单的地方）。

本次切到 ARK 时：`artist`、`game-research` 两份 config **连 `providers:` 顶层段都没有**，脚本把主 home 里
`providers.volcengine-agent-plan:` 那一整块（含 `api_key`、`base_url`、`model`、`models:` 清单、`name`）
原样复制进去；其余 10 份已经有这一段，只改 `model:` 块。

顺带两个实测事实：

- `provider: volcengine-agent-plan` 与 `provider: custom:volcengine-agent-plan` **都解析、都渲染**
  （`hermes profile show` 两种写法都打印 `deepseek-v4-1-flash (…provider…)`）。`travel-guider` 一直是
  `custom:` 写法，切换时它本来就在目标上、**一个字节都没动** —— 可见这一层不是必须统一的。
- 主 home 的 provider 段里那份 `models:` 清单是给模型选择器看的，跟取件/鉴权无关；复制它是为了 profile 内
  也能选到同一个 provider 的其它模型，不是运行必需。

## 四、端点探活：别名写错时你要改的是 N 份文件

```bash
curl -s --noproxy '*' -m 30 https://ark.cn-beijing.volces.com/api/plan/v3/chat/completions \
  -H "Authorization: Bearer <key>" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-1-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":16}'
```

返回体（2026-10-08 实测，`max_tokens` 给 16 时 `content` 空、推理内容进 `reasoning_content`，属正常）：

```json
{"choices":[{"finish_reason":"length","index":0,"logprobs":null,
 "message":{"content":"","reasoning_content":"The user wants me to reply…","role":"assistant"}}],
 "model":"deepseek-v4-1-flash-260910","object":"chat.completion",
 "usage":{"completion_tokens":16,"prompt_tokens":37,"total_tokens":53}}
```

要点：**返回体里的 `model` 是服务端回填的真实版本**（`deepseek-v4-1-flash-260910`）。别名写错时这里会是
404/400，而不是等到 16 份 config 都改完才发现。`--noproxy '*'` 是本机代理环境（`HTTPS_PROXY` 指向本机代理、
常没启动）下必须加的，否则 curl 会静默超时。

## 五、这一次全库切换的实测基线（2026-10-08）

| 项 | 值 |
|---|---|
| profile 总数 | 16（`default` + 15 个命名 profile） |
| 真改的 | 12：default、artist、game-research、job-hunter、plan-weave、plasmid-engineer、profile-development、quant-investor、rdm-assistance、secretary、software-development、value-investor |
| 其中补 `providers:` 段 | 2：artist、game-research |
| 本来就在目标上（一字未动） | 4：obsidian-maintenance、personal-accountant、protein-design、travel-guider |
| 目标 | `deepseek-v4-1-flash` @ `volcengine-agent-plan`（`https://ark.cn-beijing.volces.com/api/plan/v3`） |
| 复跑 `--dry-run` | `changed 0` + 16 个 already（零漂移） |
| 备份 | `<home>/backups/model-switch-<ts>/<label>/config.yaml`（12 份，逐份 md5 与还原用的那份临时备份一致） |
| 回读 | `hermes profile list` 16/16 = 目标模型；`hermes config check` 通过；3 个 profile 的真实会话 `billing_base_url` = ARK 端点 |

这一批里还有一处**没动**、属于刻意的范围边界：`game-research` 的 `auxiliary.model` 仍是 `deepseek-flash`
—— 它管的不是默认模型（是内部辅助任务的模型），本次要求只覆盖「默认模型」。要一起换就显式说，别顺手改。
