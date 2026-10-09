---
name: video-transcript-summarization
description: Use when 总结视频/音频内容（B站/YouTube/本地）。
version: 1.0.0
author: hermes-curator
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [media, video, audio, transcript, asr, whisper, bilibili, youtube, yt-dlp]
    related_skills: [obsidian-investment-notes, strategy-backtesting]
---

# 视频/音频 → 转写 → 总结

把视频（B站/YouTube）或本地音视频变成文字，再按用户要的格式产出摘要/章节/观点提炼。
**核心：先探路（有没有现成字幕），再决定用不用 ASR。**

## When to Use

- 用户丢来视频/音频链接或文件（BV 号/av 号、bilibili 或 youtu.be 链接、本地 mp4/mp3）要求「总结 / 讲了什么 / 转成文字 / 提炼观点」
- 要把某 UP 主的视频内容归档成笔记（投资类 → 配合 `obsidian-investment-notes`）
- 需要逐字稿或时间戳章节作为后续统计/回测/复盘的输入
- 没指定格式时默认出摘要；用户点了格式（章节/thread/blog/引言）再按那个格式出

## 工具链（一次性安装，二进制落 `~/.local/bin`）

```bash
uv tool install yt-dlp          # 下载 + 平台解析（自带 wbi 签名，比手写 API 稳）
uv tool install mlx-whisper     # Apple Silicon 本地 ASR（M 系列）
export PATH="$HOME/.local/bin:$PATH"
export PATH="$PATH:$(ls -d $HOME/.hermes/tools/ffmpeg-* | head -1)"   # mlx_whisper 解码音频依赖 ffmpeg
```

ffmpeg 目录名带版本号会变，用 `ls -d ~/.hermes/tools/ffmpeg-*` 现取，别硬编码。

## 取文路线：先选路，再动手

| 路线 | 何时用 | 代价 |
|---|---|---|
| **A 字幕** | 平台有 CC/AI 字幕 **且** 能提供登录态 cookie | 秒级，最省 |
| **B 本地 ASR** | 默认兜底，零登录 | 首次下模型 708M；M1 实测 tiny ≈35×、large-v3-turbo ≈18× 实时 |

实测：B站**匿名拿不到字幕**（`--list-subs` 只列 `danmaku`），但**音频流匿名可下** → 无 cookie 时默认走 B，不要先在字幕上耗时间。

## 步骤

1. **探元信息 + 字幕列表**：`yt-dlp --list-subs <URL>`
   - 有 `Available subtitles` 表（含 `zh-CN`/`ai-zh`）= 路线 A 可行；只有 `danmaku` = 无 CC/AI 字幕可匿名取。
2. **路线 A 下字幕**：`yt-dlp --write-subs --sub-langs "ai-zh,zh-CN" --skip-download -o subs <URL>`
   - 需登录态时加 `--cookies-from-browser chrome`（或 `--cookies cookies.txt`）。
3. **路线 B 取音频**（只下音频流，体积极小）：
   ```bash
   yt-dlp -f "30232/bestaudio" --no-playlist -o audio.m4a <URL>   # B站 30232 ≈76k m4a；YouTube 用 -f bestaudio
   ```
   实测 B站：129 秒视频音频仅 1.17 MiB，1.7 秒下完（4.9 MiB/s）——音频体积约 **0.5 MB/分钟**，长视频也不怕。
4. **转写**：
   ```bash
   mlx_whisper audio.m4a --model mlx-community/whisper-large-v3-turbo \
     --language zh --initial-prompt "以下是普通话的句子，请输出简体中文。" \
     --output-format txt --output-dir out
   ```
   - 中文成稿**必须** large-v3-turbo（tiny 只能用来验证链路）。实测 turbo：129.4 秒音频 → **7.2 秒墙钟（≈18× 实时，含模型加载）**，模型 708M 下一次下载长期复用。
   - 要时间戳章节就把 `--output-format` 换 `srt`（实测可用：129 秒音频出 16 条带时间戳字幕）；纯文字用 `txt`。
   - 长音频先分段（约 30 分钟/段）再逐段转写，别一次性长跑。
5. **总结**：默认产出摘要；用户点明时再给时间戳章节 / 观点清单 / thread / blog。
   - 转写 >50K 字符先分块（~40K 带 2K 重叠）逐块摘要再合并。
6. **落地**：投资类视频额外抽「标的 / 信号 / 仓位 / 止损 / 时间」字段，笔记规范见 `obsidian-investment-notes`（信号日、source、frontmatter v2 都按那边来）。

## 陷阱（实测）

- **B站匿名没有字幕**：`x/player/v2` 的 `subtitles` 返回 `[]`，`--list-subs` 只给 `danmaku`。要 SESSDATA 才有 CC/AI 字幕；没 cookie 直接走 ASR。
- **1080P 以上高码率需大会员 cookie**，但音频流不受影响 —— 音频路线无需登录。
- **B站搜索接口匿名会被风控**：`x/web-interface/wbi/search/type` 返回 412 / `v_voucher`。改用 yt-dlp 内置搜索（自带 wbi 签名）：`yt-dlp --flat-playlist --print "%(id)s|%(url)s" "bilisearch5:关键词"`；**连打第二次就 412**，调用间隔 sleep 数秒，拿到 id 后用 `https://www.bilibili.com/video/av<id>` 形式访问。
- **whisper tiny 中文不可用**：会把「成长股价值」听成「成長武士戒」。中文一律 large-v3-turbo；输出偏繁体/错字时用 `--initial-prompt`「以下是普通话的句子，请输出简体中文。」压简体。
- **大模型 708M（不是 1.6G，实测 `du -sh`），别在前台等**：放后台任务 + notify；HF 缓存断点续传，被前台超时杀掉后重跑即续（用 `du -sh ~/.cache/huggingface/hub/models--mlx-community--*` 看下了多少）。
- mlx_whisper 解码依赖 ffmpeg 在 PATH，否则直接报错。
- **`--cookies-from-browser chrome` 未实测**：cookie 传法目前只是文档层面成立，首次用要先验证（macOS 下读浏览器 cookie 还可能触发 TCC/钥匙串授权）。
- **`~/Documents`、`~/Desktop`、`~/Downloads` 枚举卡死 ≠ 目录坏了**：实测是 macOS TCC 权限（执行进程无「文稿」访问权），症状是 `ls` 数秒零输出直到超时，而 `~/Repositories` 之类正常列出。给执行进程开「完全磁盘访问权限」后才能动 vault。

## 工作纪律（用户偏好）

- 先给**完整计划**待确认再动手，勿抢跑；但探测性实测（探接口/试链路）可以直接做，因为它喂给结论。
- 结论必须基于**实测数据**（体积/耗时/接口返回码），不要凭猜。
- 平台接口细节见 `references/bilibili-anonymous-access.md`；输出格式样例（含投资信号字段抽取）见 `references/example-output.md`。
