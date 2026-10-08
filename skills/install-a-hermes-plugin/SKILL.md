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

### 5 · 重启才生效

- 会话里：`/restart`（先 drain 正在跑的请求）。
- 终端里：`hermes gateway restart`。
- **不要在网关会话里执行重启命令**：它会被 harness 拦下（`SIGTERM` 会先把命令杀掉），
  而且这一轮回复也由那个进程投递。

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
├── SKILL.md  (165 lines)
├── test-prompts.json  (27 lines)
├── references/
│   └── install-a-hermes-plugin-dependency-resolution.md  (167 lines)
└── scripts/
    └── install-runtime-model.py  (204 lines)
```

<!-- Generated by Scripts -->
