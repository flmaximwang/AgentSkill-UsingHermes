# Surya Settings Reference

Source: `surya/settings.py` (pydantic_settings `BaseSettings` — all overridable via env vars)

## Model Cache

```python
MODEL_CACHE_DIR: str = str(Path(user_cache_dir("datalab")) / "models")
# macOS default: ~/Library/Caches/datalab/models/
# Linux default: ~/.cache/datalab/models/
# Override: export MODEL_CACHE_DIR=/path/to/models
```

## All Model Checkpoints

| Setting name | S3 path | Estimated size |
|---|---|---|
| `DETECTOR_MODEL_CHECKPOINT` | `s3://text_detection/2025_05_07` | ~50 MB |
| `RECOGNITION_MODEL_CHECKPOINT` | `s3://text_recognition/2025_09_23` | ~1.3 GB |
| `LAYOUT_MODEL_CHECKPOINT` | `s3://layout/2025_09_23` | **1.35 GB** |
| `TABLE_REC_MODEL_CHECKPOINT` | `s3://table_recognition/2025_02_18` | ~100 MB |
| `OCR_ERROR_MODEL_CHECKPOINT` | `s3://ocr_error_detection/2025_02_18` | small |

Models are downloaded from `https://models.datalab.to` (S3-backed CDN), NOT HuggingFace.

## Other Notable Settings

| Setting | Default | Notes |
|---|---|---|
| `TORCH_DEVICE` | auto-detect | `cuda`, `mps`, `cpu` — can force via env var |
| `IMAGE_DPI` | 96 | For detection, layout, reading order |
| `IMAGE_DPI_HIGHRES` | 192 | For OCR, table recognition |
| `DETECTOR_BATCH_SIZE` | auto (2 for CPU/MPS, 32 for CUDA) | |
| `RECOGNITION_BATCH_SIZE` | auto (8 for CPU/MPS, 256 for CUDA) | |
| `S3_BASE_URL` | `https://models.datalab.to` | Model server base |
| `PARALLEL_DOWNLOAD_WORKERS` | 10 | Parallel download threads |
| `COMPILE_DETECTOR` | False | Enable torch.compile |
| `COMPILE_LAYOUT` | False | Enable torch.compile |
| `COMPILE_FOUNDATION` | False | Enable torch.compile |

## Marker Settings

From `marker/settings.py` — much simpler, mostly paths and device config.

| Setting | Default | Notes |
|---|---|---|
| `ARTIFACT_URL` | `https://models.datalab.to/artifacts` | For additional artifacts |
| `OUTPUT_IMAGE_FORMAT` | JPEG | |
| `TORCH_DEVICE` | auto | MPS is detected but may not work for text detection |
