---
name: install-a-hermes-plugin
description: "装 Hermes 插件、或插件的 Python 依赖装不上（uv 报 has no publish time / No solution found）时用：依赖同意、PM 新建整套 environment、索引缺 upload time 的坑与修法、装完必重启；也给已装插件补装只活在某个 environment 里的运行时数据（spaCy 模型）。删/更新插件与删 skill 是兄弟技能。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, plugins, dependencies, environment, pypi-mirror, restart, spacy]
---

# 装一个 Hermes 插件（并让它真的生效）

## When to Use

- 用户说「装 <插件>」，或要解释 `hermes plugins install <name>` 的产物。
- 安装的收尾报 `✗ Could not prepare <name>'s dependencies: venv: uv lock exited 1` /
  `✗ Resolving Python dependencies failed`，随后一句 `memory.provider is unchanged`。
- uv 的报错里出现 `has no publish time`、`No solution found when resolving dependencies for split`、
  `was filtered by exclude-newer`。
- 安装报 `Plugin '<name>' is unavailable: plugin.json declares an unsupported or missing Agent Plugins
  schema`（原生插件带了一份别的平台的 `plugin.json`；`--force` 也越不过，走 §1.5）。
- 插件「装上了但没反应」——要分清 install / enable / 选为 memory provider / 重启四件事。
- 给已装插件补装**运行时数据**（spaCy 模型、词典这类索引里没有的东西），或升级后发现某个功能
  静默变弱（实体抽取没了之类）。

不属于本技能：删插件（→ `remove-a-hermes-plugin`）；装/更新 skill（→ `install-hermes-skills` /
`update-hermes-skills`）；网关服务本身起不来（→ `maintain-hermes-gateway`）。

## 一次 install 到底改了什么

1. 插件目录**每 profile 一份**：`$HERMES_HOME/plugins/<name>`。
2. 插件声明了 Python 依赖（`plugin.yaml` 的 `pip_dependencies`，或插件自带 `pyproject.toml`）时，
   PM 把「Hermes core + 每个已选插件」拼成一个 workspace，**新建一整套 environment**，成功后把
   选择切过去。它的形状是
   `<hermes root>/installs/<install id>/environments/<generation>/venv`，
   旧 generation 留到 `hermes pm gc` 才清。
   ⇒ **装在 venv 里的东西跟着 generation 走，不跟着 profile 走**：下次重建就没了。
3. 依赖装不装是一道 y/N 同意；非交互（SSH、CI、Discord 里的会话）默认拒绝 ⇒ 插件装上但没依赖、
   留在 disabled。`--yes-deps` 是替用户回答这道题，不是绕过安全检查。
4. `install ≠ enable ≠ active`。memory provider 类插件还要 `hermes memory setup <name>` 才写进
   `config.yaml` 的 `memory.provider`；`kind: exclusive` 的插件会把原来那个同类插件挪进
   `plugins.disabled`（副作用，要主动告诉用户）。
5. 新 generation 只有**下一个进程**会用 ⇒ 运行中的 gateway 必须重启才吃到新依赖。

## Procedure

### 1 · 装

```bash
hermes plugins install <name>              # catalog 名 / owner/repo / git URL
hermes plugins install <name> --yes-deps   # 非交互场景替自己回答依赖同意
hermes plugins show <name>                 # 装完先读 Status / 版本 / 来源
```

### 1.5 · 装不上：`Plugin 'X' is unavailable: plugin.json declares an unsupported or missing Agent Plugins schema`

实测（2026-10-08 · v0.21.5+9287 · ponytail）。一个**原生**插件（有 `plugin.yaml`）同时带着给别的
agent 平台用的 `plugin.json`，而那份 json 没有 `$schema` 时，install 会硬拒——**加 `--force` 也不放行**。
原因在 `hermes_cli/plugins_cmd_install.py:_refuse_unavailable_portable_plugin()`：只要插件根目录存在
`plugin.json` 就无条件走便携包校验（`agent_plugins._validate_manifest` 要求
`$schema == https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`），与「原生 manifest 已读成功」无关。

判据：报错里出现 `is unavailable:` + `plugin.json`，而 `hermes plugins doctor <name>`（若手边有同版本的
副本）一切正常 ⇒ 别去查依赖、别查索引，是这道门。

绕法（官方支持、留 provenance）：

```bash
TMP=<scratch>/<name>-clone
GIT_TERMINAL_PROMPT=0 git clone https://github.com/<owner>/<repo>.git "$TMP"
git -C "$TMP" checkout <40-char-SHA>      # 想钉版本就钉；不钉=默认分支 HEAD
mv "$TMP" "$HERMES_HOME/plugins/<name>"   # 同一分区，mv=原子改名，别让半成品被扫描到
hermes plugins adopt <name>                # 读 git origin，写 provenance，变成受跟踪的 git 安装
hermes plugins enable <name>
```

`adopt` 的产出行：`.install-metadata.json` 里 `{"pinned": false, "revision": <sha>, "source": <url>.git}`，
之后 `hermes plugins check-updates` 认它（`git e3ba2aa… → b088b2d… update available`）。
`enable` 会**热重载**正在跑的网关，不用重启：终端回 `Gateway reloaded plugins — active in the running
gateway now: gateway_commands, gateway_transforms, hooks.`，`logs/gateway.log` 里对应
`gateway.run_plugin_rewire: Re-wired plugin handlers on N adapter(s)`。

端到端验证（在网关会话里就能做，不用等重启）：`skill_view('<name>:<skill>')` 能取到
`<HERMES_HOME>/plugins/<name>/skills/<skill>/SKILL.md` ⇒ 插件的 skill/hook 真的挂上了。

⚠ 插件扫描（`plugins.scan_on_install`）对社区源默认给出 `Verdict: CAUTION` 并**阻断**，要 `--force` 越过。
先看严重度分布再决定：实测 120 条里 2 HIGH 是 `SKIP_DIR` 排除目录的正则（误报），90 MEDIUM 基本落在
`benchmarks/`、`.github/workflows/`，与运行时无关。`--force` 只越过扫描闸，越不过上面那道 portable 门。

### 2 · 依赖解析失败：先读那句话，再查索引

报错原文 → 含义：

- `Because <pkg>{…}==<ver> has no publish time and hermes-agent depends on <pkg>==<ver>` →
  索引**没有**该文件的发布时间，而 core 的 `[tool.uv] exclude-newer = "14 days"`（发布隔离期）
  必须靠发布时间判断 ⇒ 精确 pin 的包永远选不出来。
- `hint: <pkg> was filtered by exclude-newer to only include packages uploaded before <时刻>` →
  同一机制的另一半：该版本比隔离线新。
- `No solution found when resolving dependencies for split (markers: …)` 加
  `your workspace requires hermes-agent[acp]` → 上面那条的收尾，**报错里不会出现插件名**，
  这就是为什么「装插件失败」看起来像 core 坏了。

诊断（为什么是索引）：

```bash
# PM 把谁当索引：它读 pip 的配置并把 index-url 桥接成 uv 的索引
grep -n "index-url" "${HOME}/.config/pip/pip.conf" 2>/dev/null
# 该索引的 simple 页有没有发布时间（国内镜像实测 0；pypi.org 有）
curl -s "<index>/simple/<pkg>/" | grep -c "data-upload-time"
```

⚠️ `${HOME}/.config/uv/uv.toml` 里的 `index-url` 在 uv 0.11 **不生效**（uv 仍走 pypi.org），
别拿它当证据；真正的桥接来源是 pip 的配置。

修法（换成自带发布时间的 PyPI）：

```bash
UV_DEFAULT_INDEX=https://pypi.org/simple hermes plugins install <name> --yes-deps
```

持久化，免得下次再踩：在 `$HERMES_HOME/.env` 末尾追加一行
`UV_DEFAULT_INDEX=https://pypi.org/simple`（先备份该文件）。PM 只把白名单里的 `UV_*` 转发给 uv，
`UV_DEFAULT_INDEX` 在白名单里，而且它压过 pip 配置那条桥接。
memory provider 走的是另一条入口，同样带这个前缀：`UV_DEFAULT_INDEX=… hermes memory setup <name>`。

### 3 · memory provider 插件多两步

```bash
hermes memory setup <name>   # 写 config.yaml 的 memory.provider
hermes memory status         # Provider: <name> / Plugin: installed ✓ available ✓
```

### 4 · 给插件补装运行时数据（spaCy 模型这类）

模型不在 PyPI 上（发在 GitHub release），而 Hermes 的解析器只从包索引取件 ⇒ 官方也写着
「要手动装」。手动装的那个模型落进**某一个 generation 的 venv**，下次重建 environment 就没了；
症状是功能**静默变弱**加一行 warning，不是报错。

```bash
python3 skills/install-a-hermes-plugin/scripts/install-runtime-model.py --model en_core_web_sm --check
python3 skills/install-a-hermes-plugin/scripts/install-runtime-model.py --model en_core_web_sm
```

脚本自己挑**最新的** generation venv，也接受 `--venv <path>` 指定；`--list` 列出候选，
`--dry-run` 只打印命令。坑在它内部：`python -m spacy download` 是叫 uv 去装的，而 uv 不猜环境，
必须把 `VIRTUAL_ENV=<venv>` 传给子进程，否则报
`error: No virtual environment found; run uv venv to create an environment, or pass --system`。

想现场看一次「重建 ⇒ 数据失效」而**不必卸任何插件**：`hermes pm repair` 会按记录的依赖图
重建一套全新 generation（非破坏性），随后 `--check` 立刻变 missing，补装十秒回来。

### 5 · 重启才生效

- 会话里：`/restart`（先 drain 正在跑的请求）。
- 终端里：`hermes gateway restart`。
- **不要在网关会话里执行重启命令**：它会被 harness 拦下（`SIGTERM` 会先把命令杀掉），
  而且这一轮回复也由那个进程投递。

### 5.1 · 运行中的进程还绑在旧 generation ⇒ 「No module named '<插件依赖>'」

症状不在安装期：**正在跑的** gateway/CLI 反复打
`Failed to load bundled provider plugin <x>: No module named '<dep>'`、
`Memory provider '<p>' initialize failed: No module named '<dep>'`，而那个依赖在磁盘上的当前环境里明明存在。

进程只在**启动那一刻**选依赖环境（`pm.environments.activate_dependencies`），之后不再跟随切换；
而插件/补装的数据跟着 generation 走。所以「装了、更新了、没重启」时，它一直在旧 generation 里找新依赖。

先核它绑在哪套（别先去看文件在不在，数组里最像证据的是这两个）：

```bash
lsof -p <pid> | grep -o 'environments/[0-9a-f]\{32\}' | sort | uniq -c   # 它打开的文件来自哪套 venv
ls -la <environments>/<gen>/.leases/                                     # 有没有它持有的租约（flock 活着才算）
```

再与 `pm.environments.committed_venv(<checkout>)` 返回的当前世代比对——不一致就是这个病。
`hermes gateway restart` / `/restart` 后进程按当前世代重新选环境即恢复（重启前先 drain，别在网关会话里执行重启命令）。

### 5.2 · 想在进程里验证插件 → 用它自己那套 generation 的 python，不是主 venv

`<hermes root>/venv` 是 **core 的**环境；插件的依赖装在各 generation 的 venv 里
（`installs/<id>/environments/<gen>/venv`），而**那套的解释器可能是另一个 Python 小版本**
（实测 core 3.11 / 插件 generation 3.14）。拿 `hermes-agent/venv/bin/python` 去 import 插件、或直接跑
插件目录里的模块，必然 `ModuleNotFoundError: No module named '<插件依赖>'`——这不是依赖没装，是你问错了进程。

```bash
VENV=$(ls -dt <hermes root>/installs/*/environments/*/venv | head -1)   # 最新的 generation
PYTHONPATH=<hermes root>:$VENV/lib/python*/site-packages $VENV/bin/python your_probe.py
```

与 §5.1 分清：**§5.1 是「它往旧 generation 里找依赖」，这条是「你在错的解释器里」**。
写探针脚本时把 `PYTHONPATH` 里的 `<hermes root>` 也带上——插件会 import `agent.memory_provider`、
`tools.registry` 这些 core 模块，它们不在 generation 的 site-packages 里。
插件自己用的 CLI 二进制（如 `hindsight-embed`）也在这套 venv 的 `bin/` 下。

## Verification（三件 + 一件）

```bash
hermes memory status                       # Provider / Plugin installed ✓ available ✓
hermes plugins doctor <name>               # import 与 registration 都过
<新 generation 的 venv python> -c "import <dep>"   # 依赖真的落在装出来的那套里
lsof -p <gateway pid> | grep environments  # 看是哪个 generation ⇒ 判断要不要重启
```

## 实测基线（2026-10-08 · limbic 0.5.1 · Hermes v0.21.5+8607 · default profile）

- 失败原文：`✗ Could not prepare limbic's dependencies: venv: uv lock exited 1`，尾巴是
  `resvg-py{python_full_version >= '3.14'}==0.4.0 has no publish time`。
- 根因实测：`~/.config/pip/pip.conf` 的 `index-url` 指向阿里云镜像，PM 把它桥接进 uv；
  该镜像的 simple 页 `data-upload-time` 计数为 **0**（pypi.org 有）。
- 复现：拿 PM 自己生成的 workspace 跑 `uv lock --dry-run`——索引换成镜像时逐字复现同一句报错，
  换成 `https://pypi.org/simple` 则 `Resolved 330 packages` 通过。
- 修后 6 个依赖全部 import 成功：sqlite-vec 0.1.9 / onnxruntime 1.29.0 / numpy 2.4.3 /
  tokenizers 0.23.1 / pyyaml 6.0.3 / spacy 3.8.16。
- 副作用实测：装 limbic 把 `hermes-memory-ui` 挪进 `plugins.disabled`（exclusive）。
- spaCy 模型实测：装前 `EntityExtractor(['en']).available = False`，装 `en-core-web-sm 3.8.0`
  后为 `True`；样例抽到 `Nous Research/ORG`、`Shenzhen/GPE`。
- **「重建 ⇒ 手装的数据失效」实测**：`hermes pm repair` 新建 generation 后，`--list` 对新那套报
  `MISSING en_core_web_sm`、`--check` 退 3，而上一套仍是 `present`；补装后
  `EntityExtractor(['en']).available` 回到 `True`（同一份脚本、约十秒）。
- 这些数字属于那一次安装，不是通用常量。

## Support files

| 文件 | 承担什么 |
|---|---|
| `references/install-a-hermes-plugin-dependency-resolution.md` | 索引桥接与发布隔离期的机制全文、各类报错原文、generation 生命周期、诊断与改写的完整命令 |
| `scripts/install-runtime-model.py` | 把运行时数据装进指定的（默认最新的）generation venv，并回读验证 |

## Skill Structure

<!-- Generated by Scripts -->

```
install-a-hermes-plugin/
├── SKILL.md  (171 lines)
├── test-prompts.json  (27 lines)
├── references/
│   └── install-a-hermes-plugin-dependency-resolution.md  (191 lines)
└── scripts/
    └── install-runtime-model.py  (204 lines)
```

<!-- Generated by Scripts -->
