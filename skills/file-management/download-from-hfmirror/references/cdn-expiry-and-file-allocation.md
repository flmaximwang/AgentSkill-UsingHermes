# CDN Signed URL Expiry & File Allocation

## CDN URL Expiry (HTTP 403)

**Symptom:** aria2c log shows repeated `errorCode=22 响应状态不成功。状态=403` (HTTP 403 Forbidden) on all connections. The process stays alive but `DL:0B` and no progress.

**Root cause:** hf-mirror.com generates time-limited signed URLs to the CDN (cas-bridge.xethub.hf.co). These expire after ~1 hour. If the download takes longer, the URLs in `.hfd/aria2c_urls.txt` go stale.

**Recovery:**
```bash
pkill -f "aria2c.*<REPO_ID>" 2>/dev/null
sleep 1
# Delete stale URL list so hfd.sh regenerates fresh signed URLs
rm -f $TARGET_DIR/.hfd/aria2c_urls.txt
# Keep .gguf and .aria2 — aria2c resumes from them
```

Then re-run hfd.sh. It regenerates fresh signed URLs and auto-resumes.

## File Allocation Behavior

hfd.sh runs aria2c with `--file-allocation=none`, which means:
- **No preallocation** — aria2c writes data sequentially as bytes arrive
- On Linux: the file grows on disk in real-time, matching the `X.XGiB` in progress lines
- On **macOS/APFS**: creates a **sparse file**. `ls -lh` shows the full logical size (e.g. 16 GiB) immediately, but actual disk usage is tracked by `du -h`. This is normal APFS behaviour, not a problem.
  - **Verification:** `du -h <file>` reports real bytes written; `ls -lh` reports the logical (full) size
  
  ```
  $ ls -lh model.gguf      # shows 16G
  $ du -h model.gguf       # shows 55M  ← real data
  ```

- If stale data from a prior run is present (file on disk much larger than both `du` and log report), full recovery:

```bash
pkill -f "aria2c" 2>/dev/null
sleep 2
rm -f $TARGET_DIR/<FILE>.gguf $TARGET_DIR/<FILE>.gguf.aria2 $TARGET_DIR/.hfd/aria2c_urls.txt
# Now restart
```

Note: macOS `rm` removes the directory entry immediately, but if a process still has the file open, the disk blocks aren't freed until the process closes the file descriptor. Always kill the process first, wait, then delete.
