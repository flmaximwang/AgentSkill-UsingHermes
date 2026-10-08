# 插件依赖解析：索引、发布隔离期、environment 生命周期

`SKILL.md` 里那张「报错原文 → 含义」表是结论；这里是机制、可复制的诊断命令与完整原文。
本文件里的路径与数字是 2026-10-08 在 `default` profile 上实测的实例值，换机器要重测。

## 一、为什么「索引没有发布时间」会让安装失败

Hermes core 的 `pyproject.toml` 里有：

```toml
[tool.uv]
exclude-newer = "14 days"     # 发布隔离期
```

它的意思是「只接受 14 天以前发布的版本」——为了不被刚推上来、可能带毒或被撤包的版本咬到。
判这个必须知道**每个文件的发布时间（publish time / upload time）**。发布时间有两个来源：

1. 包索引的 simple 页上的 `data-upload-time` 属性（PyPI 有，国内镜像普遍没有）；
2. 已记录的锁文件里的 `upload-time`（只覆盖已经在锁里的包）。

国内镜像（阿里云 / 清华 / 中科大 / 腾讯，2026-10-08 逐个实测）都不带这个属性，
计数一律为 0，所以它们在**有空隔离期**的解析里等于「所有版本都没有发布时间」。
一个被**精确 pin** 的版本（`resvg-py==0.4.0` 这种）再也无法被证明「在隔离线之前」，
uv 只能判无解——报错就是这句：

```
× No solution found when resolving dependencies for split (markers:
│ python_full_version == '3.14.*' and sys_platform != 'android'):
╰─▶ Because resvg-py{python_full_version >= '3.14'}==0.4.0 has no publish
    time and hermes-agent depends on resvg-py{python_full_version >=
    '3.14'}==0.4.0, we can conclude that hermes-agent's requirements are
    unsatisfiable.
    And because your workspace requires hermes-agent[acp], we can conclude
    that your workspace's requirements are unsatisfiable.
```

同一原因的另一副面孔（隔离线是「现在减 14 天」，所以相对写法会出现这半句）：

```
hint: `resvg-py` was filtered by `exclude-newer` to only include packages uploaded before 2026-09-24T10:36:34.13484Z. Consider using `exclude-newer-package` to override the cutoff for this package.
```

以及 uv 在给「没有发布时间的文件」兜底时会打的一大串 warning
(`… is missing an upload date, but user provided: <时刻>`)——**那些 warning 不是病因**，
真正致命的是上面那句 `has no publish time`。

## 二、Hermes PM 是从哪拿到索引的（桥接链）

`pm/index_config.py` 的口径：

- PM 只把**白名单**里的 uv 设置转发给 uv：`UV_INDEX_URL` / `UV_DEFAULT_INDEX` / `UV_INDEX` /
  `UV_EXTRA_INDEX_URL` / `UV_NO_INDEX` / `UV_FIND_LINKS` / `UV_INDEX_STRATEGY`，以及
  `UV_NATIVE_TLS` / `UV_INSECURE_HOST` / `UV_HTTP_TIMEOUT` 这类传输开关。
- 这些都不存在时，它去读 **pip 的配置**（`PIP_INDEX_URL`，或 pip.conf 里的 `index-url`）并把它写成
  `UV_INDEX_URL`——因为 uv 从不读 pip 的配置。
- `UV_EXCLUDE_NEWER` 不在白名单里，**拿它关隔离期这条路走不通**。

本机实测后果：

```
~/.config/pip/pip.conf        index-url = https://mirrors.aliyun.com/pypi/simple/
~/.config/uv/uv.toml          [global] index-url = https://mirrors.aliyun.com/pypi/simple/   ← 无效
```

第二条无效这点要用实况确认，别靠读文件下结论：

```bash
mkdir -p <scratch>/idxprobe && cd <scratch>/idxprobe
printf '[project]\nname="p"\nversion="0.0.0"\nrequires-python=">=3.14"\ndependencies=["resvg-py==0.4.0"]\n\n[tool.uv]\nexclude-newer = "14 days"\n' > pyproject.toml
UV_CACHE_DIR=<scratch>/uvcache uv lock --dry-run -v 2>&1 | grep -E "Sending fresh GET|aliyun|pypi\.org"
```

实测输出是 `Sending fresh GET request for: https://pypi.org/simple/resvg-py/`——即 uv.toml 里那行
没被采纳，uv 走的仍是默认索引。**所以「装不上」不是 uv.toml 造成的**，
而是 PM 从 pip.conf 桥接出来的那个镜像。

反过来验证因果（同一份 pyproject，只换索引）：

```bash
UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/ uv lock --dry-run   # 复现那条 has no publish time
UV_DEFAULT_INDEX=https://pypi.org/simple                 uv lock --dry-run   # Resolved 2 packages
```

## 三、PM 生成的工作区长什么样（复现安装失败的最短路径）

插件依赖解析不是在 profile 目录里做的，PM 会把 core 与插件快照进一个临时 workspace 再解析
（`pm/workspace.py::_generate_pyproject`）。要复现一次失败的解析，不必重装插件——直接用 PM 自己的
函数把 workspace 造出来：

```bash
PM=<pm-runtime generation>/bin/python     # 见 installs/*/pm-runtime/generations/*/bin/python
"$PM" - <<'PY'
import sys; from pathlib import Path
sys.path.insert(0, "<hermes-agent 路径>")
from pm.workspace import _generate_pyproject
root, source = Path("<scratch>/ws"), Path("<hermes-agent 路径>")
_generate_pyproject([Path("<HERMES_HOME>/plugins/<name>")], root, source=source)
(root/"uv.lock").write_bytes((source/"uv.lock").read_bytes())
print("generated", root)
PY
cd <scratch>/ws && UV_PYTHON=<managed 3.14 interpreter> uv lock --dry-run
```

要点：

- 生成的 `pyproject.toml` 里，core 的全局 `exclude-newer` 被**改成逐包**的
  `[tool.uv.exclude-newer-package]`（`resvg-py = "14 days"` 这种相对写法），并挂上
  `[tool.uv.workspace].members`。所以报错里的 `hermes-agent depends on …` 就是 core 自己的 pin。
- 解析必须用**运行时那个解释器**（`UV_PYTHON=<…>/bin/python`）。用 PM runtime 自己的 3.11 去跑，
  3.14 那条 resolution split 不参与，失败**不复现**——这一条踩过，差点把方向带偏。
- 每次都往 scratch 造一个新的 workspace 目录：PM 的 `lock_and_sync` 拒绝复用已存在的目录。

## 四、environment 生命周期（为什么手装的东西会消失）

- 布局：`<hermes root>/installs/<install id>/environments/<generation>/{venv,workspace,.leases}`；
  选择记录在 install state 里，旧 generation 保留到 `hermes pm gc`。
- 触发重建的：装/删插件、`hermes update`、`hermes memory setup` 里依赖变化的那一步。
  输入没变化时 PM 会**短路**：第二次 `hermes memory setup <same>` 只打印
  `✓ Dependencies prepared …` 而不新建 generation（实测同一套 generation 被复用）。
- 因此「手装进 venv 的东西」有两个结论：① 装在**哪一套**要说清楚；② 重建后要**补装**。
  症状不是崩溃，是那行 warning + 功能静默退化。
- 判断「运行中的进程用的是哪一套」：

```bash
lsof -p <gateway pid> | grep -oE "/installs/[^ ]*/environments/[a-f0-9]+" | sort -u
```

  它和最新 generation 不一致 ⇒ 还没重启，新依赖没生效。

## 五、spaCy 模型这一类「索引里没有的运行时数据」

- 官方发布在 GitHub release（`https://github.com/explosion/spacy-models/releases/...`），不在 PyPI 上，
  所以进不了依赖声明；插件作者只好写「手动装」。
- 实测的装法（成功输出）：

```
Using Python 3.14.7 environment at: <venv>
 + en-core-web-sm==3.8.0 (from https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl)
✔ Download and installation successful
```

- 不传 `VIRTUAL_ENV` 时的原文：

```
error: No virtual environment found; run `uv venv` to create an environment, or pass `--system` to install into a non-virtual environment
```

  机制：`spacy download` 内部调 uv 装那个 wheel，而 uv 不猜「你要装进哪个环境」。
- 回读（不需要任何模型下载，2 秒）：

```bash
<venv>/bin/python -c "
import sys; sys.path.insert(0, '<HERMES_HOME>/plugins/<插件名>')
from entities import EntityExtractor          # 插件自己的模块名
print('available:', EntityExtractor(['en']).available)"
```

  实测：装前 `False`、装后 `True`，样例文本抽出 `Nous Research/ORG`、`Shenzhen/GPE`。
  （`UserWarning: [W036] The component 'entity_ruler' does not have any patterns defined.` 是插件没配
  `known_entities` 时的正常提示，不是故障。）

## 六、别做的事

- 别去改 Hermes 的 lock 或 pyproject 来「关掉」隔离期：那是 core 的安全策略，改了会在下次更新被覆盖，
  而且 `UV_EXCLUDE_NEWER` 本来就不在 PM 的转发白名单里。
- 别在网关会话里执行重启命令（harness 会拦，且会杀掉这一轮回复）。
- 别把手装的模型当成「已声明依赖」写进说明：它不在任何声明里，重建即失效，要如实说明代价。
