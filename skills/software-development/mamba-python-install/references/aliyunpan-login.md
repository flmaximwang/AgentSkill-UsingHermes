# aliyunpan（阿里云盘 CLI）登录与使用

## 安装

```bash
brew install aliyunpan
```

二进制位置：`/opt/homebrew/bin/aliyunpan`

## 交互式登录（扫码）

aliyunpan 登录需要**两次授权**：先点击链接授权，再扫码。

### 自动化登录流程

由于 PTY + background 模式无法直接交互，需按以下步骤操作：

1. **启动登录进程（PTY + background）：**
   ```bash
   terminal(background=true, pty=true, command="aliyunpan login")
   ```

2. **获取登录链接：**
   ```bash
   process(action="wait", session_id="...", timeout=5)
   ```
   输出中包含形如 `https://openapi.alipan.com/oauth/authorize?client_id=...` 的链接（每次不同）。

3. **用户操作：** 打开该链接，**扫描二维码**（需要阿里云盘 App）。

4. **提交 Enter：**
   ```bash
   process(action="submit", session_id="...", data="")
   ```
   进程收到 Enter 后完成授权并退出。

5. **验证登录成功：**
   ```bash
   aliyunpan quota
   aliyunpan ls
   ```
   应显示网盘文件列表。

### 已知注意事项

- 每次 `aliyunpan login` 生成的链接都不同，之前的链接失效。
- 链接有效期为 **5 分钟**。
- 登录成功后会话 token 缓存到本地（`~/.config/aliyunpan/` 或类似位置），后续使用无需重复登录。
- 如果进程先退出后再提交 Enter，会返回 `登录失败`。必须确保进程运行时提交 Enter。
- 系统代理（:7890）对 aliyunpan 的登录和上传无干扰（实测正常，与百度网盘不同）。

## 基本上传命令

```bash
# 上传文件到网盘根目录
aliyunpan upload /local/path/to/file

# 上传目录
aliyunpan upload /local/path/to/dir /remote/path/
```

## 注意事项

- 路径嵌套：`aliyunpan upload /src/dir /dst/dir` 会创建 `/dst/dir/dir/`（多一层目录名）。要避免嵌套，需注意目标路径写法。
- 上传大文件通过分片并发，支持断点续传。
