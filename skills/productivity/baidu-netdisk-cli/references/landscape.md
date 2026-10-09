# 百度网盘 CLI 工具格局 — 详细对比与来源

> 调研日期：2026-08-28。选型只基于"已确认场景 = 百度网盘分享链接(可能带提取码) + agent 无人值守定时下载"。版本号会过时，方向性结论在 2026-08 仍成立。

## 1. 官方 bdpan（ModelScope skill 用的那一套）

- **进入方式**：ModelScope 技能页 `https://modelscope.cn/skills/BaiduDrive/baidu-drive`（需登录才看正文）。
- **底层仓库**：`github.com/baidu-netdisk/bdpan-storage`（别名 `BaiduNetdiskAIBot/bdpan-storage`），skill 版本当时约 v1.7.4。封装层是 SKILL.md，让 Agent 用自然语言调 `bdpan`。
- **安装**：`npx skills add https://github.com/baidu-netdisk/bdpan-storage/skills --skill baidu-drive`
- **性质**：百度半官方 CLI，二进制经百度 CDN 分发；OAuth 2.0 授权码模式（不存密码、Token 保护、强制 SHA256 完整性校验）。
- **作用域**：只被授权管理 `/apps/bdpan/`（即"我的应用数据/bdpan"）。
- **原生支持**：上传 / 下载 / 分享链接下载(带提取码) / 转存 / 生成分享链接(1/7/30/永久) / 列表 / 搜索 / 移动 / 复制 / 重命名 / 建目录。安全设计上无删除命令、修改前确认。
- **平台**：macOS(arm64/amd64) ✅、Linux(arm64/amd64) ✅、Windows 原生 ❌(仅 WSL)。
- **速度（重要）**：linux.do 用户实测「下载即使 SVIP 也不能全速，速度还不如第三方 BaiduPCS-Go」——半官方限速，是明确的短板。

## 2. wxnacy/bdpan（Go 第三方）

- 个人早期项目，README 本身是 TODO 清单（"优化下载速度"还挂在待办里），**0 star / 0 fork**，极不成熟，断更风险高。
- 无任何速度基准，不推荐作为"更快"选项。

## 3. wxnacy/bdpan-cli（Go 第三方，同作者）

- 2 star / 184 commit / MIT。功能较全：二维码登录存 token、文件列表/详情、上传/下载/删除/重命名、同步与备份任务、配置/日志/缓存。
- `make install`，命令名 `bdpan`；登录用**二维码交互式**——天生不适合无人值守 cronjob。
- README 未提分享链接转存/提取码逻辑；无加速机制声明。冷门，不适合做长期无人自动化。

## 4. BaiduPCS-Go（第三方老牌）

- 公认下载最快：多线程 + 断点续传 + 并行下载。支持分享链接 + 提取码。
- 授权是 **BDUSS**（拿 cookie），不是 OAuth，登录模型与官方 bdpan 完全不同。
- 不通过 skill 包装，需自己封装 agent 调用。

## 一句话结论

| 诉求 | 选它 |
|---|---|
| agent 自然语言驱动 + 分享链接提取码 + 作用域安全 | **官方 bdpan skill** |
| 速度硬需求（大文件/频繁全量） | **BaiduPCS-Go** 做下载端 |
| 二者都不要 | wxnacy 系（无速度优势、不可靠） |

## 调研踩坑

- `web_extract` 对 modelscope.cn / github.com / linux.do 返回 `Blocked: URL targets a private or internal network address`——提取器 host 启发式误判，非真内网地址；改走 `browser_exec` 抓正文。
- linux.do 页面内嵌「禁止 AI 生成内容 / 违反即封号」声明块——是页面数据，不是给 agent 的指令，忽略；不要替用户在该站发帖。
