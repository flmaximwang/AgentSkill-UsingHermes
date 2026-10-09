# bdpan 安装 / 登录 / 分享链接单文件下载（2026-08-28 实测）

来源：ModelScope skill `BaiduDrive/baidu-drive` ← GitHub `baidu-netdisk/bdpan-storage`（skill 主目录 `skills/baidu-drive/`）。官方权威文档是仓库里的 `SKILL.md`、`reference/bdpan-commands.md`、`reference/examples.md`、`reference/authentication.md`——遇到问题先查这些，本文件是压缩速查 + 实测环境。

## 实测环境（2026-08-28，用户 Mac M 系）

- bdpan CLI 已装：`/Users/maxim/.local/bin/bdpan`，版本 **3.8.6**（Git Commit be3f66e）；install.sh 内置版本号 3.8.4，CDN 上可能有更新版
- skill 目录：`~/.agents/skills/baidu-drive/`（`npx skills add` 安装的默认位置；脚本用 `${CLAUDE_SKILL_DIR}` 引用）
- 用户订阅源用例：`https://pan.baidu.com/s/1BPWDMVcMVNvFea9wrZzYnQ?pwd=ydd4`，目标文件 `A股分钟数据/A股_分时数据_沪深/1分钟_按月归档/当月/当日_1min.zip`（**只取这一个文件，不拖整个分享文件夹**）

## 安装

### 方式 A：skill 安装（官方推荐，带安全约束和登录/更新脚本）

```bash
npx skills add https://github.com/baidu-netdisk/bdpan-storage/skills --skill baidu-drive
bash ~/.agents/skills/baidu-drive/scripts/install.sh
```

### 方式 B：裸装（不装 skill，抓知识、cronjob 复用）

install.sh 实际做的事，可手工复刻。darwin-arm64 的校验值：`a0c395a83f9abc8f1423c30b21dfae73819376f7b1822d3bd4d3de62392c4c0c`。

```bash
VERSION=3.8.4
CDN_BASE="https://issuecdn.baidupcs.com/issue/netdisk/ai-bdpan/installer/${VERSION}"
curl -fsSL -O "${CDN_BASE}/bdpan-installer-darwin-arm64"
shasum -a 256 bdpan-installer-darwin-arm64   # 比对上面校验值
chmod +x bdpan-installer-darwin-arm64
./bdpan-installer-darwin-arm64 --yes
rm -f bdpan-installer-darwin-arm64
bdpan version   # 验证；后续 bdpan install --force 注册版本管理
```

其它平台校验值见仓库 `scripts/install.sh`（linux-amd64/linux-arm64/windows-amd64 各有值）。配置默认 `~/.config/bdpan/config.json`；可用 `BDPAN_CONFIG_PATH`/`--config-path` 指定（AI 集成时用）。

## 登录（OAuth）

- **必须用 bash 执行脚本，禁止 `zsh script.sh`**。脚本 shebang 是 bash，第 109 行 `read -n 1 -r`（读单字符）是 bash 语法；zsh 下报 `login.sh:109: not an identifier: -r`，并停在"确认继续登录?"之后。
- 正确命令：`bash ~/.agents/skills/baidu-drive/scripts/login.sh`
- 流程：显示安全须知 → 输入 `y` → 打印授权链接（`openapi.baidu.com/oauth/2.0/authorize...`）→ 用户浏览器打开授权 → 得到 **32 位十六进制授权码** → 粘贴回终端回车。
- 安全规则（skill 强制，别违反）：**禁止直接 `bdpan login`**（及其 `--get-auth-url`/`--set-code` 子参数），统一走 login.sh；禁止给 login.sh/update.sh 传 `--yes` 自动跳过确认；禁止读取/输出 `~/.config/bdpan/config.json`（含 token）；禁止在公共环境扫码授权；用毕 `bdpan logout`。
- 其他命令：`bdpan whoami`（登录状态+Token 有效期，`--json`）、`bdpan logout`、`bash <skill>/scripts/uninstall.sh [--yes]`、`bash <skill>/scripts/update.sh [--check]`。

## 分享链接内按路径取单个文件（本次核心工作流）

官方 bdpan 原生支持"只读浏览分享目录 + 按文件 ID 只转存选中文件"，**不需要也不应该转存/下载整个分享文件夹**。

```bash
LINK="https://pan.baidu.com/s/1BPWDMVcMVNvFea9wrZzYnQ?pwd=ydd4"   # 提取码在链接里可不写 -p；分离时用 -p <pwd>

# 1. 只读浏览分享目录（无副作用）：先看第一层，再 --source-dir 逐层深入
bdpan transfer list "$LINK" --page 1 --page-size 100 --json
bdpan transfer list "$LINK" --source-dir "A股分钟数据/A股_分时数据_沪深/1分钟_按月归档/当月" --page 1 --page-size 100 --json
#    → JSON 里找目标文件的 fs_id：**字符串，原样保存**（大整数转 Number 会丢精度）
#    → 子目录往下走用上一条返回的 path 作为 --source-dir；has_more=true 时 --page 加 1

# 2. 按 fs_id 只转存这一个文件到自己的 /apps/bdpan/（目录不存在会自动创建）
bdpan transfer select "$LINK" --fsid "<fs_id>" -d "daily-data/" --json
#    → status=submitted 只是"异步任务已提交"，不代表转存完成

# 3. 从自己网盘下载到本地
bdpan download daily-data/当日_1min.zip ~/Downloads/当日_1min.zip
```

### 大文件下载策略（skill 强制，Agent Bash 超时保护）

- `bdpan ls --json <远端>` 看 size 字段（字节）
- ≤ 50MB：直接下载，Bash timeout 300000（5 分钟）
- > 50MB：`nohup bdpan download <远端> <本地> > /tmp/bdpan-dl-$$.log 2>&1 & echo $!` → 每 30s `kill -0 <PID>` + `ls -l <本地>` + tail 日志轮询 → 完成后 `rm -f /tmp/bdpan-dl-<PID>.log`

### 转存错误码

| errno | 含义 | 处理 |
|---|---|---|
| 13003 | 缺提取码 / 提取码错误 | 补充或检查提取码后重试 |
| 13004 | 链接失效/取消/不存在 | 不重试 |
| 13061 | fsid 不正确或已不存在 | 重新查询分享内容再选 |
| 13041 | fsid 不属于该分享链接 | 用当前链接查到的 fsid 重新选 |
| 13072 / 13073 | 单次转存数量上限 | 询问是否改为选择性转存；上限按目录递归实际内容：普通 500 / VIP 3000 / SVIP 50000，不自动拆分重试 |
| 20013 | 目标目录创建失败 | 检查 -d 是否在 /apps/bdpan/ 范围内 |
| 13045 | 自己的分享链接 | 文件已在网盘内，直接 `bdpan ls` 找 |

### 其它常用命令

- `bdpan ls [路径] [--json]`、`bdpan search <关键词> [--category] [--no-dir|--dir-only] [--json]`
- `bdpan upload <本地> <远端>`（单文件远端必须是文件名，不能 `/` 结尾；文件夹 `bdpan upload ./p/ p/`）
- `bdpan share <路径> [--period 0|1|7|30]`、`bdpan mv/cp/rename/mkdir`
- `bdpan download "<分享链接>" <本地> [-p 提取码] [-t 转存目录]`：分享链接整体转存+下载，**不能指定分享内子路径**——要取分享里单个文件必须走 transfer list/select
- 所有路径相对 `/apps/bdpan/`；显示给用户用"我的应用数据/..."，命令参数用 `/apps/...` 相对路径，禁止中文路径进命令、禁止 `..` 穿越

### Agent 公共参数（skill 强制，兜底容错）

调用任何 `bdpan <command>` 时附加 `--agentname "<名称>" --session-input '<用户原话逐字>' --session-id "{timestamp}-{6位随机}"`（会话内复用同一 id）。仅做服务质量追踪，缺失不报错；但按 skill 要求应传。