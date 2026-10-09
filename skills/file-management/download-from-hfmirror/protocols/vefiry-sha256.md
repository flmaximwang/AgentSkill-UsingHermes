# Verify SHA256

```bash
python3 <SKILL_DIR>/scripts/verify_sha256.py <TARGET_DIR>/.hfd/repo_metadata.json "<MODEL_FILE>"
```

Output examples:
```
✅ SHA256 MATCH — file is intact
```
```
❌ SHA256 MISMATCH — file is CORRUPTED
```

If corrupted, remove only the `.gguf` file (keep `.aria2` and `.hfd/`):
```bash
rm -f $TARGET_DIR/<MODEL_FILE>
# Then re-run hfd.sh
```