---
name: download-from-hfmirror
description: "Use when downloading files available on hf-mirror.com"
version: 1.0.0
author: Hugging Face
license: MIT
tags: [huggingface, hf, hf-mirror, models, datasets, hub, mlops, download]
platforms: [linux, macos, windows]
---

# Download from HF-Mirror

A protocol for downloading models in "China", considering it's hard to connect to Hugging Face directly.

## Configurations

- HF_ENDPOINT=https://hf-mirror.com
- SCRIPT=<SKILL_DIR>/scripts/hfd.sh
- DOWNLOAD_DIR=(未设置时使用 hfd.sh 默认行为 —— 在当前目录下创建以 repo 名命名的子目录。需指定路径时传 `--local-dir "$DOWNLOAD_DIR"`)

## Quick Start

```bash
$SCRIPT gpt2
$SCRIPT bigscience/bloom-560m --exclude *.bin *.msgpack onnx/*
$SCRIPT meta-llama/Llama-2-7b --hf_username myuser --hf_token mytoken -x 4
$SCRIPT lavita/medical-qa-shared-task-v1-toy --dataset
$SCRIPT bartowski/Phi-3.5-mini-instruct-exl2 --revision 5_0
```

## ⚠️ Important

**hfd.sh does NOT verify checksums.** It reports success purely on exit code — a corrupted download (especially 20+ GB GGUF) will load but produce silent garbage (e.g., all token ID 0). Always verify SHA256 after download completes.

- For any file > 500 MB, follow `protocols/download-large-models.md` **without exception**.

aria2c uses `.aria2` control files for resume — **NEVER delete them**. Only delete the `.gguf` itself if SHA256 verification fails.

## 🧠 Model metadata (from repo_metadata.json)

After download starts, parse `.hfd/repo_metadata.json` for info about the repo. Use `scripts/check_file_size.py` to get individual file sizes from LFS pointers.

- `.gguf.total` — sum of ALL GGUF files in repo (not per-file)
- `.pipeline_tag` — `"image-text-to-text"` = multimodal → need `--mmproj`
- `.gguf.architecture` — architecture string (e.g. `"qwen35moe"`)
- `.gguf.context_length` — max context length

**Multimodal models** (pipeline_tag = `image-text-to-text`) require the mmproj GGUF file for llama.cpp inference. Download `mmproj-*.gguf` alongside the main model.

## Protocols
- `protocols/download-large-models.md` — Large files (> 500 MB): aria2c + hfd.sh, progress monitoring, cron, SHA256 verification.
- `protocols/verify-sha256.md` — SHA256 verification via `scripts/verify_sha256.py`.
- `protocols/resume-large-models.md` — Resume interrupted downloads without deleting progress.

## ⚠️ Common Pitfalls (learned the hard way)

1. **Don't fabricate tool behaviour.** The original protocol claimed "aria2c logs at `--console-log-level=error` — progress is NOT in the log." This was written without actually checking the log output. **Always** run the command, look at its actual output, then document, never the reverse.

2. **`.gguf.total` is the sum of ALL GGUF files in the repo**, not a single file's size. Use `scripts/check_file_size.py` to get per-file sizes from LFS pointers.

3. **SHA256 comes from Git LFS pointers, not the API.** The `repo_metadata.json` siblings only have `rfilename` — no size or hash. Use `scripts/verify_sha256.py` which reads the LFS pointer at `raw/main/<file>`.

4. **CDN signed URLs expire.** If hfd.sh stalls with HTTP 403 errors, the signed download URLs have timed out. Recovery:
   ```bash
   pkill -f "aria2c.*<REPO_ID>" 2>/dev/null
   # Delete stale URL list so hfd.sh regenerates fresh ones
   rm -f $DOWNLOAD_DIR/.hfd/aria2c_urls.txt
   # .gguf and .aria2 control file stay — aria2c resumes from them
   # Re-run hfd.sh
   ```
   ⚠️ If `rm -f` on `.gguf` is needed (corruption), first ensure no aria2c process holds the file open, otherwise `rm` frees the directory entry but not the disk blocks. Kill aria2c first, wait, then delete.

5. **Log file goes in the model directory**, not /tmp. This keeps download artifacts together and avoids confusion with stale logs from previous attempts: `$DOWNLOAD_DIR/dl_<MARKER>.log`. The protocol's cron prompt and progress-check commands all reference this path.

6. **macOS APFS sparse files mislead `ls -lh`.** With `--file-allocation=none`, aria2c creates a sparse file on APFS. `ls -lh` shows the full logical size (e.g. 16 GiB) immediately, but actual data is much less (`du -h` shows the real value). **Do not use `ls -lh` on the `.gguf` to judge progress** — read the `X.XGiB/Y.YGiB` value from the log instead.

7. **Protocol log path inconsistency.** The current protocol's download step uses `$DOWNLOAD_DIR/<MARKER>.log` but the progress check and restart steps use `$DOWNLOAD_DIR/dl_<MARKER>.log`. Always use `dl_` prefix for log files to keep them identifiable.

8. **Never delete `.aria2` control files** during a healthy download — they are aria2c's resume state. Only delete them alongside the `.gguf` when starting fresh (corruption recovery or CDN expiry followed by a full restart).

9. **Kill the process before `rm` on .gguf.** If an aria2c process still has the file open, `rm` removes the directory entry but the disk blocks aren't freed until the process exits. Always `pkill -9 -f aria2c`, sleep 2, then delete.

10. **后台下载一律用 log 看进度，不用 `ls`。** hfd.sh 的 aria2c 使用 `--console-log-level=error` —— 只有每 ~2s 的汇总行和错误才会输出到 stdout。在后台模式（`background=true`）下，强行 `process(action='poll')` 几乎拿不到有用的进度信息。正确做法：用重定向包装 hfd.sh，从 log 读取 `184MiB/1.0GiB(16%)` 这类 aria2c 汇总行：
    ```bash
    $SCRIPT ... > /tmp/dl_<MARKER>.log 2>&1
    ```
    **唯一例外：短耗时的小文件用前台下载**（不设 background，直接等结果），不需要 log。
    **例外2（非 GGUF 文件）**：zip、mlmodelc、safetensors 等非 GGUF 文件不是 APFS sparse 文件，`ls -lh` 显示的是真实大小。可以直接 `ls -lh` 看进度。
    **用户问进度时：立刻查** —— 用 log 或 `ls -lh` 看当前文件大小，**不要等 background poll 或 notify_on_complete**。答案一直在文件系统里。

## Reference Webpages

- How to use hfd: https://gist.github.com/padeoe/697678ab8e528b85a2a7bddafea1fa4f
