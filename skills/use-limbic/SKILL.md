---
name: use-limbic
description: "limbic（Hermes 的自我组织记忆插件）的记忆怎么查看/导出/删、模型文件下载卡住、user_id 落到谁名下、多个 profile 是否共享、改完配置要不要重启时用。装插件与它的依赖解析不属于本 skill（→ install-a-hermes-plugin）；Hermes 记忆总开关与 nudge 不属于（→ maintain-hermes-memory）。"
version: 1.0.0
author: Hermes Agent
license: MIT
---

# use-limbic —— 用、查、排错 limbic 这个 memory provider

limbic 是 Hermes 的插件式记忆后端：本地 SQLite + 自学习信任分 + 不用就萎缩。
**它跟内置 MEMORY.md 是两套东西**，本 skill 只管 limpib 自己这一套。

## When to Use

- 「limbic 现在能用了吗 / 为什么 remember 报 Embedding generation failed」
- 「limbic 的记忆怎么查看 / 导出 / 删一条」
- 「多个 profile 是共享一套记忆还是各一套」「这条 fact 记在谁名下」
- 换 profile 装它、或模型文件下载/校验卡住（2GB 级 ONNX 拉不动）
- 不属于本 skill：装插件本体、依赖解析失败（uv `has no publish time`）、补装 spaCy 模型 → `install-a-hermes-plugin`；
  Hermes 记忆总开关 / nudge / write_approval → `maintain-hermes-memory`；装/更新 skill → `install-hermes-skills`。

## 路径与隔离（先认清，后面的结论都由它推出）

| 东西 | 位置 | 备注 |
|---|---|---|
| 事实库 | `$HERMES_HOME/limbic.db` | provider 里**硬拼**这个路径；`memory setup` 会问的 `db_path` 配置项**只被写、从不被读** |
| 自适应参数 | `$HERMES_HOME/limbic_params.json` | 衰减半衰期、相关度下限等，引擎自己学出来的 |
| 配置 | `$HERMES_HOME/limbic.yaml` | 覆盖插件目录里的默认值 |
| 身份清单 | `$HERMES_HOME/users.yaml` **>** `<插件目录>/users.yaml` | 先命中者的整个文件生效，不合并 |
| 模型缓存 | `~/.cache/limbic/{embedding,nli}/` | **在 HERMES_HOME 之外** ⇒ 装第二个 profile 不重复下载 |

- **记忆 per-profile 完全隔离**：default profile 的 `$HERMES_HOME` 是 `~/.hermes`（不是 `profiles/default/`），命名 profile 是 `~/.hermes/profiles/<name>/`。想共享只有软链同一个 `limbic.db`——但那会让所有 profile 的事实混进同一张 `facts` 表（`collection` 字段不参与分区），且并发写走 `limbic.db.writer.lock` 串行化。**不要这么干**，跨 profile 搬记忆用 `export` + `seed`。
- 插件本体同样是 per-profile：文档里 `~/.hermes/plugins/` 那行写成 "User / Personal plugins" 容易误读成全局目录，实测它就是 default profile 自己的 home，**别的 profile 看不到它里面的插件**。
- `reindex.py` 只认 `profiles/<agent>/limbic.db`，对 **default profile 会找不到库**（它的库在根 home）。

## Procedure

### 1 · 模型文件：装齐 + 校验（最容易卡在这）

pin 表在插件自己的 `model_pins.py`：Arctic Embed 2.0 L（`model.onnx` 686 KB + `model.onnx_data` 2.11 GiB）与 NLI（MiniLMv2-L6-mnli-xnli，408 MiB），每个文件带 sha256/sha1。检查与补齐：

```bash
python3 -B scripts/fetch-pinned-models.py                 # 只校验，逐个打印 OK/BAD
python3 -B scripts/fetch-pinned-models.py --repair         # 校验 + 补齐
```

三个已经踩过的坑（每条都有实测）：

- **预置两个大 ONNX 会绕过插件自己的下载器**：`embeddings.py:_ensure_model` 只在 `model.onnx` / `model.onnx_data`
  **缺失**时才调 `_download_model()`，所以手动把那两个大文件摆好之后，同目录的
  `tokenizer.json` / `config.json` / `sentencepiece.bpe.model` **永远不会被拉**，症状是
  `Tokenizer.from_file` 报 `No such file or directory (os error 2)`。
  ⇒ 要么全都不预置，要么**一次把 pin 里列的文件全部摆齐**（脚本就是这么做的）。
- **它自己的下载器不支持断点续传**：`_urlretrieve_atomic` 一失败就删临时文件、下次从 0 开始；
  国内单流实测 0.28–0.31 MB/s 且会在 100 MB ~ 1.5 GB 处断 ⇒ 2.11 GiB 那份**永远装不完**。
  脚本用 6 路并行分段，实测聚合 1.7–4.7 MB/s。
- **pin 的哈希规矩**：LFS 文件 = **文件内容原文**的 sha256；只有 `sha1:` 开头的才是 git-blob
  （`blob <size>\0` 前缀再 sha1）。把 LFS 文件也套上 git-blob 头去比，会把**完好**的文件判成坏的、
  拿去重下并截断（本机踩过：把一份好的 2.11 GiB 文件重下成 1.37 GiB，onnxruntime 报
  `Deserialize tensor ... are out of bounds`）。

### 2 · 模型就位之后：**重启 gateway 才生效**

provider 在进程内懒加载模型。如果 gateway 启动时文件还缺/是残的，它会卡在半初始化状态，
之后每一轮都报同一句错、**进程内永不恢复**：

```
limbic: embedding generation failed: 'NoneType' object has no attribute 'encode'
Tool remember returned error: {"error": "Embedding generation failed"}
```

判据是「文件已按 pin 校验通过、而它在之后仍报同一句错」⇒ 换新进程。
`/restart`（**别在被这个 gateway 服务的会话里直接调，本轮回复会被一起掐掉**）或到终端 `hermes gateway restart`。

### 3 · 身份：这条 fact 记在谁名下

- 有 `users.yaml` ⇒ multi-user 模式；没有 ⇒ single-user 模式，**raw 平台 ID 直接当桶**。
- **平台键必须与 host 传的值逐字相同**：gateway 传 `platform="discord"`（`Platform.DISCORD == "discord"`），
  而 `resolve()` 是 `(平台, ID)` 元组精确匹配；不写平台的裸 ID **只解析 Matrix 形式**（`@x:y`）。
  写错键名 = 静默不生效，日志只会说 `user <id> not in users.yaml (N known users) — attributing to raw ID`。
- 最小可用清单（`$HERMES_HOME/users.yaml`）：

```yaml
users:
  <canonical>:
    display_name: <canonical>
    scope: adult          # child 会带 guardian 语义
    platform_ids:
      discord: "<snowflake>"
```

- `known_users` 取的是 manifest 的 canonical 名单，还驱动「跨用户重归属」那条启发式——**只有 guardian 能把
  fact 写进别人名下**，没有 guardian 时这条自动关掉。
- 插件目录里那份 `users.yaml` 是 alice/bob 示例模板；home 那份赢过它。**别删 home 那份**，否则退回模板的
  "2 known users"。

### 4 · 看、导出、删

```bash
hermes limbic status                          # 健康 / 配置 / 总量
hermes limbic stats [--user <id>]             # 每用户统计 + atrophy 计数
hermes limbic export --user <id> [-o f.json]  # 导出事实（含 trust/retrieval_count）
hermes limbic forget-fact <fact_id> --user <id>
hermes limbic seed --user <id> --content "<≥60 字符且 ≥3 词的事实>"
hermes limbic reindex / fts-rebuild / languages
hermes limbic <子命令> --hermes-home /path/to/profiles/<name>   # 看别的 profile
```

- **`--user` 要填真实桶名**：Discord 会话写进去的是**平台 ID**（雪花号），除非 users.yaml 映射过；CLI 默认桶是 `general`。
  两者不是一回事，`export --user general` 看不到会话写的事实。
- **`seed` 有 fragment gate**：内容必须 **≥60 字符且 ≥3 词**（空格分词），否则回 `{"status": "rejected_fragment"}`——
  纯中文短句会被判太短。
- 直读库（别拿写锁）：

```bash
sqlite3 "file:$HERMES_HOME/limbic.db?mode=ro" \
  "SELECT fact_id,user_id,round(trust_score,3) trust,retrieval_count hits,
          last_retrieved,matured_at,atrophy_marked_at,substr(content,1,50)
     FROM facts ORDER BY fact_id DESC LIMIT 20;"
```

表：`facts` / `facts_fts`（FTS5）/ `vec_index`（sqlite-vec，cosine）/ `entities` / `mentions` / `contradictions`。

## Verification（三件）

1. `python3 -B scripts/fetch-pinned-models.py` → 每个文件 `OK`、退出码 0（**不是**只看"文件在不在"）。
2. `hermes limbic seed` 一条 → `hermes limbic stats` 计数 +1、`export` 能读回那一行 → `forget-fact` 删掉、计数回 0。
3. 会话侧：重启后再 `remember` 一条 → `recall` 命中 → 删掉。**只跑 CLI 不算数**——CLI 与新进程能过、老 gateway 进程仍可能是坏的。

## 实测基线（2026-10-09 · limbic 0.5.1 · default profile · macOS arm64）

- 12 个 pin 文件校验：11 个一开始就 OK，只有 `embedding/model.onnx_data` 是残的（1.47 GiB / 应 2.11 GiB）。
- 修好的那次：6 路并行分段 2.11 GiB 用 1292 s（≈1.75 MB/s），单流对照组 0.28–0.31 MB/s。
- 验收：`seed` 4.1 s 写入 `fact_id=1`（trust 0.5 / hits 0），`stats` 与 `export` 一致，`forget-fact` 后 `facts` 回到 0 行。
- `remember`（会话内）在模型就位后仍失败，直到重启 gateway；同一时刻 CLI 用同一套代码成功。
- 这些数字属于那一次运行，不是通用常量；本机 profile 数、缓存目录状态会变。

## Support files

| 文件 | 承担什么 |
|---|---|
| `scripts/fetch-pinned-models.py` | 按插件 `model_pins.py` 逐个校验模型文件，`--repair` 时用并行分段补齐；退出码 0/1/2 |
| `test-prompts.json` | 路由题集（4 条正例 + 1 条指向 `install-a-hermes-plugin` 的诱饵） |

## Skill Structure

<!-- Generated by Scripts -->

```
use-limbic/
├── SKILL.md  (158 lines)
├── test-prompts.json  (27 lines)
└── scripts/
    └── fetch-pinned-models.py  (182 lines)
```

<!-- Generated by Scripts -->
