# B站匿名访问能力边界（实测）

未登录状态（无 SESSDATA）下各接口实测结论 —— 决定该走字幕腿还是 ASR 腿。

| 接口 / 用法 | 匿名可用 | 说明 |
|---|---|---|
| `x/web-interface/view?bvid=...` | ✅ `code:0` | 拿 title/desc/cid（cid 是后续接口的必需参数） |
| `x/player/playurl?bvid=&cid=&fnval=16` | ✅ `code:0` | 拿到音视频流地址；音频 only 流足够转写 |
| `x/player/v2?bvid=&cid=` | ⚠️ `code:0` 但 `subtitle.subtitles=[]` | 匿名字幕列表为空 → **字幕需登录态** |
| `x/web-interface/wbi/search/type` | ❌ | 风控：返回 412 / `v_voucher`（需 wbi 签名 + cookie） |
| `yt-dlp --list-subs <URL>` | ✅ 可跑 | 结果只列 `danmaku xml` = 该视频无 CC/AI 字幕可取 |
| `yt-dlp -f 30232 <URL>` | ✅ | 音频流匿名可下，约 **0.5 MB/分钟** |
| `yt-dlp bilisearchN:关键词` | ✅ 但限速 | yt-dlp 自带 wbi 签名，能返回 id 列表；**连续调用第二次 412**，间隔 sleep |
| 1080P 高码率 | ❌ | 需大会员 cookie；不影响音频/低清晰度 |

## 结论

- 想「秒级拿文字」= 需要用户提供 B站 登录态（`--cookies-from-browser chrome` 或 `cookies.txt`，字段 SESSDATA）。
- 不给 cookie 就**不要先去试字幕**，直接：`yt-dlp -f 30232/bestaudio` 取音频 → `mlx_whisper` 转写。
- 判断某视频有没有 CC 字幕，先跑 `--list-subs`：出现除 `danmaku` 以外的语言才是真有字幕。

## 与本仓库既有资产的关系

- vault `Samples/` 已有长赢之道研究院**文字动态/文章**全量归档（见 `obsidian-investment-notes` 的 `references/bilibili-dynamics-archive.md`）——那是**动态文本**，不是视频；做该 UP 主视频总结时不要重复爬动态。
- 历史 UP主/开源工具查证套路的归档版（已 archived）：`.archive/bilibili-content-research/`。
