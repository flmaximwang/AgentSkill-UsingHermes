---
name: kimi-moonshot-brotli-fix
description: "修复 kimi-coding-cn / Moonshot 长流式回复中途崩溃：DecodingError 'brotli: decoder process called with data when can_accept_more_data() is False'。hermes update 会冲掉补丁，更新后用本 skill 重打。"
version: 1.0.0
author: Hermes Agent (for Maxim)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hermes, kimi, moonshot, brotli, patch, troubleshooting]
---

# Kimi / Moonshot brotli 流式解码崩溃修复

## 触发条件

使用 kimi-coding-cn（或任何 base_url 为 api.moonshot.cn / api.moonshot.ai 的 provider）时，
长回复生成中途 API 调用失败，报错：

```
DecodingError: brotli: decoder process called with data when 'can_accept_more_data()' is False
```

特征：短回复正常，长回复（长思考、长规划）必挂；重试 3 次同样失败。

每次 `hermes update` 后本补丁可能被冲掉（update 会先 auto-stash 本地改动），
更新后应执行第 1 步检查补丁是否还在，不在就重打。

## 根因（简述）

- hermes venv 装有 brotlicffi 1.2.0.1（为 Discord 附件解码钉的版本，`pyproject.toml` messaging extra）。
- 有它时 httpx（OpenAI SDK 底层）在 Accept-Encoding 声明 br，Moonshot 服务器于是用 brotli 压缩 SSE 流。
- brotlicffi 1.2.0.1 的流式解码有 bug，长流中途解码器状态损坏。
- hermes 官方在 tools/skills_hub.py:3804 对同一报错有注释，其绕过方案同为强制 `Accept-Encoding: gzip`。

## 修复步骤

### 1. 检查补丁是否还在

```bash
grep -n "Accept-Encoding.*gzip" ~/.hermes/hermes-agent/agent/agent_init.py
```

有输出（moonshot 分支）→ 已修复，跳到第 4 步验证。无输出 → 继续第 2 步。

（可选）先看上游是否已官方修复，在就不必再打：
```bash
cd ~/.hermes/hermes-agent && git fetch origin main && git log --oneline HEAD..origin/main --grep="brotli\|Accept-Encoding\|moonshot" -i
```

### 2. 打补丁

文件：`~/.hermes/hermes-agent/agent/agent_init.py`

用 patch 工具，old_string（api.kimi.com 分支，照原样匹配，注意缩进 12 空格）：

```python
            elif base_url_host_matches(effective_base, "api.kimi.com"):
                client_kwargs["default_headers"] = {
                    "User-Agent": "claude-code/0.1.0",
                }
            elif base_url_host_matches(effective_base, "portal.qwen.ai"):
```

new_string：在上述两段之间插入 moonshot 分支：

```python
            elif base_url_host_matches(effective_base, "api.kimi.com"):
                client_kwargs["default_headers"] = {
                    "User-Agent": "claude-code/0.1.0",
                }
            elif base_url_host_matches(effective_base, "moonshot.cn") or base_url_host_matches(effective_base, "moonshot.ai"):
                # brotlicffi 1.2.0.1 (pinned for Discord attachment decoding)
                # has a streaming-decode bug that kills long SSE streams from
                # Moonshot with DecodingError("brotli: decoder process called
                # with data when 'can_accept_more_data()' is False"). Forcing
                # Accept-Encoding: gzip makes the server fall back to gzip —
                # same workaround as tools/skills_hub.py.
                client_kwargs["default_headers"] = {"Accept-Encoding": "gzip"}
            elif base_url_host_matches(effective_base, "portal.qwen.ai"):
```

注意：`base_url_host_matches` 是后缀匹配（utils.py:528），写 "moonshot.cn" 即可覆盖 api.moonshot.cn。

若 patch 失败（上游改了这段代码），先 `grep -n "api.kimi.com" ~/.hermes/hermes-agent/agent/agent_init.py`
找到当前实际内容，在同一 elif 链的任意位置插入 moonshot 分支即可（顺序无所谓，host 互不重叠）。

### 3. 验证补丁

```bash
cd ~/.hermes/hermes-agent && venv/bin/python -m py_compile agent/agent_init.py && echo COMPILE_OK
```

（patch 工具可能对这行报 Pyright reportArgumentType —— 是误报，同链路上 api.kimi.com 等分支用的是一模一样的写法，忽略。）

### 4. 重启生效

运行中的进程已加载旧代码，必须重启：
- CLI：退出 hermes 重开，`hermes -c` 恢复原会话。
- Gateway（如在运行）：`hermes gateway restart`；若在 gateway 内部被 block，用 launchd：
  `launchctl bootout gui/501/ai.hermes.gateway-<profile>` 然后
  `launchctl bootstrap gui/501 ~/Library/LaunchAgents/ai.hermes.gateway-<profile>.plist`

## 备选方案（config.yaml，update 冲不掉，可与补丁并存）

若 config.yaml 有 base_url 为 https://api.moonshot.cn/v1 的 custom_providers 条目
（Kimi 官方指南推荐的 custom:kimi-k3-cn 即是），加 extra_headers 即可，无需源码补丁：

```yaml
custom_providers:
  - name: kimi-k3-cn
    base_url: https://api.moonshot.cn/v1
    key_env: KIMI_CN_API_KEY
    extra_headers:
      Accept-Encoding: gzip
```

原理：`apply_custom_provider_extra_headers_to_client_kwargs`（hermes_cli/config.py:5429）
按 base_url 匹配（不限 provider 名字，内置 kimi-coding-cn 也命中），在源码补丁之后应用、
优先级更高，合并进客户端 default_headers。

## 坑

- 不要试图卸载 brotlicffi：pyproject messaging extra 钉了它，`hermes update` 的 uv sync 会装回；
  且卸载会破坏 Discord gateway 附件解码。
- 不要改用 Google Brotli 包替代：同样影响 Discord 路径，且 lazy_deps 会按需装回 brotlicffi。
- 修复后若仍偶发同类崩溃，下一步是向 NousResearch/hermes-agent 提 issue（引用 skills_hub.py:3804 的官方注释）。
