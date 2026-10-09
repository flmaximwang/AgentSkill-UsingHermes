# Surya Model Download — Error Patterns & Workarounds

Captured from a cron-job download of 5 surya models to `/Library/Models/Surya/` (Jun 12, 2026).

## Models and Sizes (actual)

| Model directory | model.safetensors size | Notes |
|---|---|---|
| `text_detection/2025_05_07` | 73 MB | Smallest; downloads quickly |
| `text_recognition/2025_09_23` | 1.3 GB | Largest; takes several minutes |
| `layout/2025_09_23` | 1.35 GB | Was already present |
| `table_recognition/2025_02_18` | 201 MB | Had IncompleteRead error once |
| `ocr_error_detection/2025_02_18` | 258 MB | DistilBert-based; needs tokenizer files too |

## Error 1: IncompleteRead on table_recognition

```
2026-06-12 19:45:05,628 [ERROR] surya: Download error for file
https://models.datalab.to/table_recognition/2025_02_18/model.safetensors:
('Connection broken: IncompleteRead(138012480 bytes read, 73214328 more expected)',
 IncompleteRead(138012480 bytes read, 73214328 more expected))
```

Surya's downloader retried twice. On the third attempt (via `create_model_dict`), it failed with:
```
shutil.Error: Destination path '/Library/Models/Surya/table_recognition/2025_02_18/model.safetensors' already exists
```

The 201 MB file was fully intact — the retry failed only because `shutil.move` refused to overwrite. **Workaround**: verify the file with `ls -lh`. If the size matches expectations and the file is non-zero, it's fine.

## Error 2: Empty directory from failed ocr_error_detection download

After the `create_model_dict()` call crashed on table_recognition, the `ocr_error_detection/2025_02_18/` directory was **empty** (0 bytes). The download for this model never started because `create_model_dict` aborted.

**Workaround**: Download individually using the loader class:
```python
from surya.ocr_error.loader import OCRErrorModelLoader
loader = OCRErrorModelLoader()
model = loader.model()        # triggers download
processor = loader.processor() # triggers tokenizer download
```

## Verification commands

```bash
# Check all model directories exist and have content
find /Library/Models/Surya -maxdepth 3 -type d
ls -lh /Library/Models/Surya/*/2025_*/model.safetensors

# Check for empty directories (failed downloads)
find /Library/Models/Surya -maxdepth 3 -type d -empty

# Total size
du -sh /Library/Models/Surya

# Verify the layout model specifically (largest)
ls -lh /Library/Models/Surya/layout/2025_09_23/
```
