# 百度网盘 CLI 工具

该用户环境中的百度网盘命令行工具。

## bypy (Python)

- 安装：`mamba create -p ~/Applications/bypy/.env python=3.12 && chmod -R 775 ~/Applications/bypy && pip install bypy`
- 授权：运行 `bypy quota`，访问打印的 URL，获取授权码后输入
  - 授权码可通过管道传入：`echo "<CODE>" | mamba run -p ~/Applications/bypy/.env bypy quota`
- 文件存储位置：百度网盘 → 我的应用数据 → bypy/ (可通过 `bypy upload <local> <remote>` 上传)
- **已知问题**：大文件上传时频繁出现 "Slice MD5 mismatch" 错误（分片校验失败）。尝试 `--slice` 524288~5242880、`--disable-ssl-check` 均无效。原因可能是百度 API 侧限制或网络代理干扰。**小文件上传正常。**
- 已在此环境完成授权（配额 2.1TB 空闲）

## BaiduPCS-Go (Go)

- 安装：`brew install baidupcs-go`
- 二进制位置：`/opt/homebrew/bin/BaiduPCS-Go`
- 登录方式（多种）：
  - 交互式：`BaiduPCS-Go login`（需要 PTY，用 `terminal(pty=true)`）
  - 用户名密码：`BaiduPCS-Go login --username=<user> --password=<pass>`
  - BDUSS/STOKEN：`BaiduPCS-Go login --bduss=<BDUSS> --stoken=<STOKEN>`
  - Cookies：`BaiduPCS-Go login --cookies="BDUSS=...; STOKEN=..."`
- **已知问题**：用户名密码登录持续返回 `Error 50052（系统繁忙，请稍候再试）`，间隔 15 秒重试也无效。可能是百度侧的风控/防脚本限制。未尝试 BDUSS/STOKEN 或 cookies 方式登录。

## 系统代理

系统 Wi-Fi 代理运行在 `127.0.0.1:7890`。上传百度网盘时此代理可能干扰校验。使用 `NO_PROXY="*"` 环境变量可尝试绕过，但实测对 bypy 的 MD5 mismatch 问题无效。
