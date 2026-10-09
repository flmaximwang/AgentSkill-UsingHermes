#!/usr/bin/env python3
"""Extract file-level metadata from a Hugging Face model repo.

Two data sources:
  1. Local repo_metadata.json (hfd.sh cache) — repo-level info
  2. HF API — sibling file listing; for Git LFS repos (size=0 in API),
     falls back to reading the LFS pointer file directly for real sizes.

Usage:
    python3 check_file_size.py <repo_metadata.json> [file_pattern]

    file_pattern: case-insensitive substring match on rfilename.
                  Omit to show all files.

Examples:
    python3 check_file_size.py /Library/Models/Qwen-3.6/.hfd/repo_metadata.json
    python3 check_file_size.py /Library/Models/Qwen-3.6/.hfd/repo_metadata.json Q4_K_XL

Key notes:
    - .gguf.total in repo_metadata.json = SUM of ALL GGUF files (misleading)
    - totalFileSize = actual storage used on the mirror (closer to real)
    - For individual file size, always check LFS pointer (fallback in this script)
    - multimodal models (pipeline_tag: image-text-to-text) need --mmproj
"""

import json
import sys
import urllib.request
import urllib.error

API_BASE = "https://hf-mirror.com/api/models"
RAW_BASE = "https://hf-mirror.com"


def fetch_api(model_id):
    """Fetch full model metadata from HF API."""
    url = f"{API_BASE}/{model_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hermes-agent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  ⚠️  API fetch failed: {e}", file=sys.stderr)
        return None


def fetch_lfs_pointer(model_id, filename):
    """Fetch Git LFS pointer to get the real file size.

    NOTE: SHA256 oid is NOT extracted here. Use scripts/verify_sha256.py for that.
    LFS pointer format:
        version https://git-lfs.github.com/spec/v1
        oid sha256:<hex>
        size <bytes>
    """
    url = f"{RAW_BASE}/{model_id}/raw/main/{filename}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hermes-agent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("size "):
                    return int(line.split()[1])
    except Exception:
        pass
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    meta_path = sys.argv[1]
    file_pattern = sys.argv[2].lower() if len(sys.argv) > 2 else None

    # Load local repo_metadata.json
    with open(meta_path) as f:
        meta = json.load(f)

    model_id = meta.get("id", "?")
    total_gguf = meta.get("gguf", {}).get("total", 0)
    total_file_size = meta.get("gguf", {}).get("totalFileSize", 0)
    pipeline = meta.get("pipeline_tag", "unknown")
    architecture = meta.get("gguf", {}).get("architecture", "unknown")
    context_length = meta.get("gguf", {}).get("context_length", "unknown")

    # --- Print repo summary ---
    print(f"📦 Model: {model_id}")
    print(f"   Architecture:    {architecture}")
    print(f"   Pipeline:        {pipeline}")
    print(f"   Context length:  {context_length:,}")
    print(f"   totalFileSize:   {total_file_size / 1024**3:.2f} GiB (storage total)")
    print(f"   gguf.total:      {total_gguf / 1024**3:.2f} GiB (sum of ALL GGUF — not per-file!)")
    if "image-text-to-text" in pipeline:
        print(f"   ⚠️  MULTIMODAL → needs --mmproj for llama.cpp")
    print()

    # --- Fetch API for per-file data ---
    api_data = fetch_api(model_id)
    if api_data:
        siblings = api_data.get("siblings", [])
        print(f"📋 Files in repo ({len(siblings)} total):")
        print(f"   {'File':<65} {'Size':>12}  {'Source'}")
        print(f"   {'-'*65} {'-'*12}  {'-'*10}")

        matched = 0
        for sib in siblings:
            rfn = sib.get("rfilename", "")
            if file_pattern and file_pattern not in rfn.lower():
                continue
            matched += 1
            size = sib.get("size", 0)
            source = "API"
            if size == 0:
                lfs_size = fetch_lfs_pointer(model_id, rfn)
                if lfs_size:
                    size = lfs_size
                    source = "LFS ptr"
            size_str = f"{size / 1024**3:.2f} GiB" if size else "?"
            print(f"   {rfn:<65} {size_str:>12}  ({source})")

        if file_pattern and matched == 0:
            print(f"   (no files matching '{file_pattern}')")
    else:
        # Fallback: show local siblings (no sizes)
        siblings = meta.get("siblings", [])
        print(f"📋 Files in repo ({len(siblings)} total, sizes unavailable):")
        for sib in siblings:
            rfn = sib.get("rfilename", "")
            if file_pattern and file_pattern not in rfn.lower():
                continue
            print(f"   {rfn:<65}")
    print()
    if file_pattern:
        print(f'🔍 Filter: matching "{file_pattern}"')
    else:
        print("🔍 Filter: all files")


if __name__ == "__main__":
    main()
