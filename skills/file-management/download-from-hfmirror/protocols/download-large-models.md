# Download Large Models

**Always use `hfd.sh` to download large models from hf-mirror.com.**

**⚠️ hfd.sh does NOT verify checksums.** Corrupted downloads produce silent garbage. Always verify SHA256 after download completes.

## Configurations

- `HF_ENDPOINT=https://hf-mirror.com`
- `MODEL_DIR=/Library/Models`
- `SCRIPT=<SKILL_DIR>/scripts/hfd.sh`

## Procedures

1. Create target directory with correct permissions.
2. Start `hfd.sh` in background with logging.
3. **Check progress** via `tail -20` on the log (aria2c writes progress lines to stderr which hfd.sh redirects into the log).
4. **Set up cron monitoring** for long downloads (> 500 MB — **required**).
5. **Verify SHA256** against the mirror's LFS pointer.
6. Clean up: delete cron + confirm file integrity.

### 1. Create target directory

```bash
TARGET_DIR=$MODEL_DIR/<ModelFamily>
sudo mkdir -p $TARGET_DIR
sudo chmod -R 775 $TARGET_DIR
```

### 2. Download (background + log)

aria2c uses `.aria2` control files for resume — **NEVER delete them**. If interrupted, just re-run the same command; aria2c auto-resumes.

```bash
export HF_ENDPOINT=https://hf-mirror.com
$SCRIPT <REPO_ID> \
  --include <MODEL_FILE> \
  --local-dir $TARGET_DIR \
  >> $TARGET_DIR/<MARKER>.log 2>&1 &
```

### 3. Check progress

aria2c writes lines like `[#gid X.XGiB/Y.YGiB(ZZ%) CN:N DL:SPEED ETA:...]` to stderr, which hfd.sh redirects into the log file:

```bash
tail -20 $TARGET_DIR/dl_<MARKER>.log
```

Progress line format: `[#69c7f1 3.1GiB/20GiB(15%) CN:4 DL:859KiB ETA:5h58m53s]`

| Token | Meaning |
|-------|---------|
| `X.XGiB/Y.YGiB(ZZ%)` | Downloaded / Total (percent) |
| `CN:N` | Number of connections |
| `DL:SPEED` | Current download speed |
| `ETA:TIME` | Estimated time remaining |

- If `DL:0B` persists for several minutes and `CN:0`, it's stalled. Kill and restart:
- If `(ERR)` was observed in the final lines, it's stalled. Kill and restart.

```bash
pkill -f "hfd.*<REPO_ID>" 2>/dev/null
pkill -f "aria2c.*<REPO_ID>" 2>/dev/null
sleep 2

export HF_ENDPOINT=https://hf-mirror.com
$SCRIPT <REPO_ID> --include <MODEL_FILE> --local-dir $TARGET_DIR \
  >> $TARGET_DIR/dl_<MARKER>.log 2>&1 &
```

### 4. Cron monitoring (for downloads > 500 MB, REQUIRED)

Set up **immediately** after launching.

| File size | Cron interval |
|-----------|---------------|
| 500 MB – 5 GB | 1 minute |
| 5 – 20 GB | 3 minutes |
| 20+ GB | every 10 minutes |

Use the agent's cronjob tool (`schedule` must include `every` for recurring):

```json
{
  "action": "create",
  "name": "<Family>-download-monitor",
  "schedule": "every <INTERVAL>",
  "prompt": "Check download progress of <MODEL_FILE> at $TARGET_DIR/.\\nRead the last 20 lines of $TARGET_DIR/dl_<MARKER>.log with tail -20.\\nCheck if aria2c process is running.\\nReport current progress, speed, ETA.\\nIf DL:0B for extended time, suggest restart.\\nDeliver result back to origin.",
  "enabled_toolsets": ["terminal"]
}
```

### 5. SHA256 verification (REQUIRED — hfd.sh does NOT do this)

After the download completes, use `scripts/verify_sha256.py`. See `protocols/verify-sha256.md` for the detailed procedure.

### 6. Clean up

After SHA256 passes:

```bash
# Delete cron monitoring job via cronjob tool: action='remove', name='<Family>-download-monitor'
# Confirm file: file $TARGET_DIR/<MODEL_FILE>  # should show "GGUF" or "data"
```
