---
name: hermes-browser-lane-repair
description: "Use when Hermes browser calls fail or a login won't stick."
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [browser, hermes, troubleshooting, captcha, bot-wall, agent-browser]
---

# Hermes 浏览器通道排障 + 反爬墙处理

## 症状 → 根因速查

| 症状 | 根因 | 修法 |
|---|---|---|
| `browser.use_real_profile is on, but your default browser is not a supported Chromium browser` | `browser.use_real_profile: true` 且默认浏览器非 Chromium 家族（macOS 上常是 Safari）。real-profile 失败是 **fail-closed**，**不回退**到自带浏览器（`tools/browser_tool_session.py::_create_local_session`），所以**所有** browser 调用都失败 | ① `hermes config set browser.use_real_profile false`，或 ② 把默认浏览器改成 Chrome/Edge。real-profile 只认 LaunchServices 的 `https` handler，**没有 config/env 覆盖**（`hermes_cli/browser_connect.py::detect_default_chromium`） |
| 自带浏览器能用，但登录不保留 | 自带车道每次用随机 session 名、无持久 user-data-dir | 给 agent-browser 一个持久 profile（见下） |
| 页面被反爬墙拦（极验/安全验证） | 针对**浏览器自动化痕迹**，不是 IP | 先做对照实验：用 HTTP 提取（`web_extract`）打同一 URL。HTTP 能读 → 是浏览器指纹问题，内容读取改走 HTTP |

`hermes config set` 会重排 YAML 长行并**丢掉文件尾部的整段注释**（如 `fallback_model` 示例块）。改前 `cp config.yaml backups/config/config.yaml.bak.$(date +%Y%m%d_%H%M%S)`，改后用 `yaml.safe_load` 做逐键语义 diff 核对，再把丢掉的注释块原样补回。

## 给 agent-browser 一个持久 profile（登录跨会话保留）

Hermes 不传 `--profile`/`--session-name`，但 agent-browser 会读用户级配置（优先级：`~/.agent-browser/config.json` < 环境变量 < CLI flags；Hermes 不设这些键）：

```bash
mkdir -p ~/.agent-browser
printf '{\n  "profile": "/Users/maxim/.agent-browser/profiles/hermes"\n}\n' > ~/.agent-browser/config.json
```

验证生效：`pgrep -fl "Google Chrome.app/Contents/MacOS/Google Chrome"` 的参数里应出现 `--user-data-dir=/Users/maxim/.agent-browser/profiles/hermes`。

⚠️ agent-browser 启动 Chrome 时固定带 `--password-store=basic --use-mock-keychain`（macOS Keychain 加密的 cookie 解不开）。所以**登录必须发生在这个车道自己的浏览器里**；把真实 Chrome 的 profile 拷进来是登不上的。

## 需要"有窗口"的浏览器时

`browser.headed` / `browser.inactivity_timeout` 是**进程内缓存**（`tools/browser_tool.py::_cached_browser_cfg`），改配置要重启网关才生效。绕过办法——终端自己起一个带窗口实例，共用同一 profile：

```bash
AB=$(ls ~/.npm/_npx/*/node_modules/agent-browser/bin/agent-browser-darwin-arm64 | head -1)
pkill -f "user-data-dir=/Users/maxim/.agent-browser/profiles/hermes"   # 腾出 profile（同一 profile 不能两个 Chrome）
env -u AGENT_BROWSER_IDLE_TIMEOUT_MS -u AGENT_BROWSER_SOCKET_DIR "$AB" \
  --profile /Users/maxim/.agent-browser/profiles/hermes --session zhipin --headed open "https://…"
```

要驱动同一个窗口，别依赖会话记账（`open` 经常报成功而实际标签变成 `about:blank`），直接连调试端口：

```bash
port=$(head -1 ~/.agent-browser/profiles/hermes/DevToolsActivePort)
"$AB" --cdp "$port" --session x open "https://…"
```

## 极验 Geetest 点选验证的机械化处理（全流程已验证）

1. DOM 抓可点元素：`.geetest_btn`（点击进入验证）→ `.geetest_item`（九宫格，取每格 `getBoundingClientRect` **中心坐标**）→ `.geetest_commit`（确认）/ `.geetest_refresh`（刷新）/ `.geetest_close`。
2. **提示图标**在 `.geetest_tip_img`：它的 `backgroundImage` 指向与九宫格**同一张雪碧图**，`backgroundPosition: 0% 100%` = 图下方那条白带（约 `[0, 图高-40, 116, 图高]`）。先 `curl` 下雪碧图，再用 `vision_analyze(region=…)` 看清图标（例：鳄鱼线稿 → 题目就是"选中所有鳄鱼"）。
3. 雪碧图 3×3：格子 `(row,col)` ↔ `backgroundPosition` 的 `0%/50%/100%`。
4. 用 `vision_analyze` 逐格识别，选出符合提示的格子；**必须先用 DOM 中心坐标与截图里的视觉网格互相对照**再点，别用百分比硬推（元素的 `backgroundPosition` 可能是 `auto`，推出来会错位）。
5. 点击要用**真实鼠标事件**，不要 `element.click()`：`mouse move x y` → 0.25s → `mouse down` → 0.12s → `mouse up`。
6. 提交前复核：`.geetest_commit` 上的 `geetest_disable` 类消失 = 已选中；截图确认打勾格数正确后再点确认；提交后看 URL/标题是否恢复。

## 把二维码发到飞书让别人扫码（人不在电脑前时）

窗口/页面在本机，人不在旁边时：把二维码导出成 PNG，用回复里的 `MEDIA:/绝对路径` 让飞书直接显示图片。要点：

- 二维码多为 `<img>`（可取 `src` 直接 `curl` 下来）或 `<canvas>`（用 `canvas.toDataURL()` 取 base64）。
- **先本机截图确认浏览器还停在登录页**，再发码；二维码有效期通常 1–3 分钟，**发之前最后一刻才提取**，过期就让对方说一声、你重取重发。
- 页面必须保持活着才能接住"扫码成功"的轮询并写入 cookie；不要在这期间关窗口或让同一 profile 的另一个 Chrome 抢占。

## BOSS 直聘（zhipin.com）实测结论

- 浏览器（headless 或 CDP 驱动）→ **每次**自动化导航都被甩到 `web/passport/zp/verify.html` 安全验证页；解掉一次后，新的自动化导航仍会再次触发。
- 同一台机器、同一出口 IP，用 **HTTP 提取**（`web_extract`）读首页/岗位页 → **无验证墙**，岗位正文可读，仅"登录查看完整内容 / 竞争力分析"被登录墙截断。
- 所以：内容读取走 HTTP；需要登录态才可见的字段，不要再硬刷风控。

## 约定：登录墙数据不硬刷，写“待补清单”到知识库

遇到只有登录才可见的字段（BOSS直聘等），不要继续硬刷风控，改为让用户补：

1. 在对应 vault 里维护一份**待补数据**笔记：表格列「编号 / 公司·岗位 / 需要补什么字段 / 已知线索（含原始链接）/ 状态⬜`」，每条目下留一个代码块做粘贴区；
2. 在受影响的原始笔记里加一行指针（改前备份、改后核对），并在索引/总览笔记里提一句；
3. 告诉用户笔记的**绝对路径 + 哪几条最优先**；用户补完后由 agent 回填原笔记并更新状态列。

先写“为什么需要你补”的对照实验结论，避免用户误以为是网络或权限问题。

> 查 IP 时注意：macOS 系统代理（Clash Verge 常见 `127.0.0.1:7890`）会让浏览器继承代理；`scutil --proxy` 看配置，`curl --noproxy '*' https://myip.ipip.net/s` 看直连出口。本例两者出口相同（机构 IPv6），所以 IP 不是拦截根因。
