# Surya Model Download Recipes

> Concrete download procedures for marker-pdf / surya OCR models at a custom cache path.
> Use these when `create_model_dict()` auto-download fails or when provisioning models
> ahead of time (e.g. via cron job).

## Quick Reference

| Model | Version | Weight file | Size | Download URL |
|-------|---------|------------|------|-------------|
| layout | 2025_09_23 | model.safetensors | ~1.35 GB | `https://models.datalab.to/layout/2025_09_23/model.safetensors` |
| text_recognition | 2025_09_23 | model.safetensors | ~1.34 GB | `https://models.datalab.to/text_recognition/2025_09_23/model.safetensors` |
| text_detection | 2025_05_07 | model.safetensors | ~73 MB | `https://models.datalab.to/text_detection/2025_05_07/model.safetensors` |
| table_recognition | 2025_02_18 | model.safetensors | ~201 MB | `https://models.datalab.to/table_recognition/2025_02_18/model.safetensors` |
| ocr_error_detection | 2025_02_18 | model.safetensors | ~258 MB | `https://models.datalab.to/ocr_error_detection/2025_02_18/model.safetensors` |

**Total**: ~3.3 GB

## Full Provisioning Script (cron-safe)

Use this pattern in a cron job or one-shot terminal command. It reliably handles the
multi-GB downloads that the built-in Python downloader often fails on.

```bash
SKILL_DIR=~/.hermes/skills/productivity/ocr-and-documents
CACHE_DIR=/Library/Models/Surya
source "$SKILL_DIR/.env/bin/activate"
export MODEL_CACHE_DIR="$CACHE_DIR"

# Step 1: Let Python download small models + config files
# This downloads text_detection, table_recognition, ocr_error_detection
# and all config/metadata files for text_recognition and layout.
# It WILL fail on the big model.safetensors files — that's expected.
python3 -c "from marker.models import create_model_dict; m = create_model_dict()" 2>/dev/null

# Step 2: Download/recover big model.safetensors files via curl
# These are the ~1.3 GB files that the Python downloader drops.
for model_path in \
  "text_recognition/2025_09_23/model.safetensors" \
  "layout/2025_09_23/model.safetensors"; do
  url="https://models.datalab.to/$model_path"
  dest="$CACHE_DIR/$model_path"
  
  # Remove partial/corrupt file if present
  rm -f "$dest"
  
  echo "Downloading $model_path..."
  curl -L -C - --retry 5 --retry-delay 10 -o "$dest" "$url"
done

# Step 3: Verify
python3 -c "
from marker.models import create_model_dict
m = create_model_dict()
print(f'Models loaded: {list(m.keys())}')
"
```

## Detecting the IncompleteRead Failure

The Python downloader logs this when it fails:

```
[ERROR] surya: Download error for file https://models.datalab.to/text_recognition/2025_09_23/model.safetensors:
  ('Connection broken: IncompleteRead(X bytes read, Y more expected)', IncompleteRead(...))
[ERROR] surya: Error downloading model from text_recognition/2025_09_23. Attempt 3 of 3.
```

After 3 attempts, the model is absent or partially downloaded. Delete the partial file
and use `curl -C -` to retry.

## Cleanup After Partial Download

```bash
# Remove incomplete model.safetensors from specific models
rm -f "$CACHE_DIR/text_recognition/2025_09_23/model.safetensors"
rm -f "$CACHE_DIR/layout/2025_09_23/model.safetensors"
```
