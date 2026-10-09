---
name: ocr-on-mac
description: "Use when performing OCR on macOS using the built-in Vision framework (Live Text engine). Covers setup, CLI usage, and common workflows."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [macos, ocr, vision, live-text]
    related_skills: [hermes-agent]
---

# OCR on macOS (Vision Framework)

## Overview

macOS has a built-in OCR engine via the **Vision framework** (`VNRecognizeTextRequest`) — the same engine powering Live Text in Photos, Safari, and Quick Look. It runs **entirely on-device** (no network), uses **Apple Silicon Neural Engine** for acceleration, and supports **15+ languages** including Chinese and English, plus **handwriting**.

## Prerequisites

- macOS 12.0+ (Monterey)
- Apple Silicon recommended (works on Intel but slower)
- `pyobjc-framework-Vision` Python package

## Setup

The skill ships with a standalone `~/.hermes/skills/productivity/ocr-on-mac/` directory containing its own virtual environment.

### Creating the virtual environment

```bash
# Use brew-installed Python
BREW_PYTHON=/opt/homebrew/bin/python3.12
cd ~/.hermes/skills/productivity/ocr-on-mac
$BREW_PYTHON -m venv .env
source .env/bin/activate
pip install pyobjc-framework-Vision
```

### Verify setup

```bash
cd ~/.hermes/skills/productivity/ocr-on-mac
source .env/bin/activate
python3 -c "from Vision import VNRecognizeTextRequest, VNImageRequestHandler; print('OCR engine ready')"
```

## Usage

### Basic OCR script

Save as `ocr.py` in the skill directory:

```python
#!/usr/bin/env python3
"""OCR an image file using macOS Vision framework."""

import sys
import argparse
from pathlib import Path

from Vision import (
    VNRecognizeTextRequest,
    VNImageRequestHandler,
    VNRequestTextRecognitionLevelAccurate,
)
from Cocoa import NSURL
from Quartz import CGImageSourceCreateWithURL, CGImageSourceCreateImageAtIndex


def ocr_image(image_path: str, lang: str = "zh-Hans", confidence: float = 0.3) -> list[dict]:
    """Extract text from an image using macOS Vision framework.

    Args:
        image_path: Path to image file (PNG, JPG, TIFF, etc.)
        lang: Recognition language. Common values:
              'zh-Hans' - Simplified Chinese (default)
              'zh-Hant' - Traditional Chinese
              'en-US'   - English
              'ja-JP'   - Japanese
              'ko-KR'   - Korean
              See Apple docs for full list.
        confidence: Minimum confidence threshold (0.0 - 1.0)

    Returns:
        List of {text, confidence, bbox} dicts
    """
    # Load image
    url = NSURL.fileURLWithPath_(str(Path(image_path).resolve()))
    img_source = CGImageSourceCreateWithURL(url, None)
    cg_image = CGImageSourceCreateImageAtIndex(img_source, 0, None)

    if cg_image is None:
        raise ValueError(f"Cannot load image: {image_path}")

    # Set up recognition request
    results = []
    
    def handler(request, error):
        nonlocal results
        if error:
            return
        for obs in request.results():
            if obs.confidence() < confidence:
                continue
            text = obs.text()
            # Bounding box in normalized coordinates [0,1]
            bbox = obs.boundingBox()
            results.append({
                "text": str(text),
                "confidence": round(float(obs.confidence()), 3),
                "bbox": {
                    "x": float(bbox.origin.x),
                    "y": float(bbox.origin.y),
                    "w": float(bbox.size.width),
                    "h": float(bbox.size.height),
                },
            })

    request = VNRecognizeTextRequest.alloc().initWithCompletionHandler_(handler)
    request.setRecognitionLevel_(VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_([lang])
    request.setUsesLanguageCorrection_(True)

    # Run OCR
    handler = VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
    handler.performRequests_error_([request], None)

    return results


def main():
    parser = argparse.ArgumentParser(description="OCR an image using macOS Vision framework")
    parser.add_argument("image", help="Path to image file")
    parser.add_argument("-l", "--lang", default="zh-Hans",
                        help="Recognition language (default: zh-Hans)")
    parser.add_argument("-c", "--confidence", type=float, default=0.3,
                        help="Minimum confidence threshold (default: 0.3)")
    parser.add_argument("--plain", action="store_true",
                        help="Output plain text only (one line per result)")
    args = parser.parse_args()

    try:
        results = ocr_image(args.image, args.lang, args.confidence)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.plain:
        for r in results:
            print(r["text"])
    else:
        for i, r in enumerate(results, 1):
            print(f"[{i}] ({r['confidence']:.1%}) {r['text']}")
            print(f"     bbox: x={r['bbox']['x']:.3f} y={r['bbox']['y']:.3f} "
                  f"w={r['bbox']['w']:.3f} h={r['bbox']['h']:.3f}")


if __name__ == "__main__":
    main()
```

### Run it

```bash
cd ~/.hermes/skills/productivity/ocr-on-mac
source .env/bin/activate
python3 ocr.py ~/Desktop/screenshot.png --lang zh-Hans
```

Or plain text output:

```bash
source .env/bin/activate
python3 ocr.py ~/Desktop/screenshot.png --plain
```

## Common Language Codes

| Code | Language |
|------|----------|
| `zh-Hans` | Simplified Chinese |
| `zh-Hant` | Traditional Chinese |
| `en-US` | English |
| `ja-JP` | Japanese |
| `ko-KR` | Korean |
| `fr-FR` | French |
| `de-DE` | German |
| `es-ES` | Spanish |

You can pass multiple languages: `["zh-Hans", "en-US"]`.

## Common Pitfalls

1. **Python 3.14 expat issue**: brew Python 3.14's `ensurepip` fails on macOS with a `_XML_SetAllocTrackerActivationThreshold` symbol mismatch between brew's pyexpat and system `libexpat.1.dylib`. This breaks venv creation and pip installation. **Fix**: use a stable brew Python like 3.12 (`/opt/homebrew/bin/python3.12`). Check available versions with `ls /opt/homebrew/bin/python3.*`.
2. **Image format**: Vision framework supports common formats (PNG, JPEG, TIFF, HEIC). Not all formats may load — if `CGImageSourceCreateImageAtIndex` returns None, convert the image first (e.g., with `sips`).
3. **No text found**: Ensure the image has sufficient resolution and contrast. Low-res or noisy images may yield empty results.
4. **Permission**: Reading files in standard locations (Desktop, Documents, etc.) works fine. No special entitlements needed.
5. **Language auto-detection**: Setting `usesLanguageCorrection=True` may cause the framework to wait longer for context. Disable it for speed by setting `usesLanguageCorrection_(False)`.

## Verification Checklist

- [ ] Virtual environment exists in `~/.hermes/skills/productivity/ocr-on-mac/.env/`
- [ ] `pyobjc-framework-Vision` installed in the venv
- [ ] Basic test image returns non-empty results
- [ ] Chinese + English both work
