#!/usr/bin/env python3
"""OCR an image file using macOS Vision framework (Live Text engine)."""

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
        lang: Recognition language code.
        confidence: Minimum confidence threshold (0.0 - 1.0).

    Returns:
        List of {text, confidence, bbox} dicts.
    """
    url = NSURL.fileURLWithPath_(str(Path(image_path).resolve()))
    img_source = CGImageSourceCreateWithURL(url, None)
    cg_image = CGImageSourceCreateImageAtIndex(img_source, 0, None)

    if cg_image is None:
        raise ValueError(f"Cannot load image: {image_path}")

    results = []

    def handler(request, error):
        if error:
            return
        for obs in request.results():
            if obs.confidence() < confidence:
                continue
            bbox = obs.boundingBox()
            results.append({
                "text": str(obs.text()),
                "confidence": round(float(obs.confidence()), 3),
                "bbox": {
                    "x": round(float(bbox.origin.x), 4),
                    "y": round(float(bbox.origin.y), 4),
                    "w": round(float(bbox.size.width), 4),
                    "h": round(float(bbox.size.height), 4),
                },
            })

    request = VNRecognizeTextRequest.alloc().initWithCompletionHandler_(handler)
    request.setRecognitionLevel_(VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_([lang] if isinstance(lang, str) else lang)
    request.setUsesLanguageCorrection_(True)

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
