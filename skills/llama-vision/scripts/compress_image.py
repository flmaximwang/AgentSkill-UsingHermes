#!/usr/bin/env python3
"""
Compress an image so its longest side ≤ 1280px, preserving aspect ratio.
Saves to a temp file and prints the path to stdout.

Usage:
    .env/bin/python scripts/compress_image.py <input_path> [--max-size 1280]

Exit code 0 on success (path on stdout), 1 on error (message on stderr).
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is not installed. Run: pip install Pillow")


def compress(input_path: str, max_size: int) -> str:
    path = Path(input_path)
    if not path.exists():
        sys.exit(f"File not found: {input_path}")

    img = Image.open(path)

    # Determine orientation and resize
    orig_size = img.size  # (w, h)
    longest = max(orig_size)
    if longest <= max_size:
        out_path = path  # no resize needed, use original
    else:
        ratio = max_size / longest
        new_size = (round(orig_size[0] * ratio), round(orig_size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)

        # Save to temp file
        suffix = path.suffix if path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") else ".jpg"
        fd, out_path = tempfile.mkstemp(suffix=suffix, prefix="vision_")
        os.close(fd)
        # Convert RGBA/P to RGB for JPEG
        if suffix.lower() in (".jpg", ".jpeg") and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(out_path, quality=95)

    # Info on stderr so stdout is clean for the path
    orig_mb = path.stat().st_size / 1_048_576
    out_mb = Path(out_path).stat().st_size / 1_048_576
    print(f"  📐 {orig_size[0]}x{orig_size[1]} → {img.size[0]}x{img.size[1]}  ({orig_mb:.1f}MB → {out_mb:.1f}MB)", file=sys.stderr)

    return str(out_path)


def main():
    parser = argparse.ArgumentParser(description="Compress image for vision model")
    parser.add_argument("input_path", help="Path to the input image")
    parser.add_argument("--max-size", type=int, default=1280, help="Max longest side in px (default: 1280)")
    args = parser.parse_args()

    out_path = compress(args.input_path, args.max_size)
    print(out_path)  # ← this is what the skill reads


if __name__ == "__main__":
    main()
