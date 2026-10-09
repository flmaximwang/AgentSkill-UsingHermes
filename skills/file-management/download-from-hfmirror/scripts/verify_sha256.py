#!/usr/bin/env python3
"""Verify a downloaded model file's SHA256 against the hf-mirror LFS pointer.

Usage:
    python3 verify_sha256.py <repo_metadata.json> <file_pattern>

    - repo_metadata.json: path to .hfd/repo_metadata.json (from hfd.sh)
    - file_pattern: substring to match the file in repo siblings

    The script reads the Git LFS pointer from hf-mirror.com, extracts the
    expected SHA256, computes the local SHA256, and prints a verdict.

Examples:
    python3 verify_sha256.py /Library/Models/Qwen-3.6/.hfd/repo_metadata.json Q4_K_XL
    python3 verify_sha256.py /Library/Models/Qwen-3.6/.hfd/repo_metadata.json mmproj
"""

import json
import sys
import hashlib
import os
import urllib.request
import urllib.error

RAW_BASE = "https://hf-mirror.com"


def fetch_lfs_sha256(model_id, filename):
    """Fetch the Git LFS pointer and extract the SHA256 oid."""
    url = f"{RAW_BASE}/{model_id}/raw/main/{filename}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hermes-agent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("oid sha256:"):
                    return line.split(":")[1]
    except Exception as e:
        print(f"  ❌ Failed to fetch LFS pointer: {e}", file=sys.stderr)
        return None
    return None


def compute_local_sha256(filepath):
    """Compute SHA256 of a local file."""
    try:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        print(f"  ❌ File not found: {filepath}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ❌ Error reading file: {e}", file=sys.stderr)
        return None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    meta_path = sys.argv[1]
    file_pattern = sys.argv[2].lower()

    # Load repo_metadata.json to find model_id and target file
    with open(meta_path) as f:
        meta = json.load(f)

    model_id = meta.get("id", "")
    if not model_id:
        print("❌ No model ID in repo_metadata.json")
        sys.exit(1)

    # Determine target directory from meta_path
    target_dir = os.path.dirname(os.path.dirname(meta_path))

    # Find matching file in siblings
    siblings = meta.get("siblings", [])
    matching = [s for s in siblings if file_pattern in s.get("rfilename", "").lower()]

    if not matching:
        print(f"❌ No file matching '{file_pattern}' found in repo")
        sys.exit(1)

    if len(matching) > 1:
        print(f"⚠️  Multiple files match '{file_pattern}':")
        for sib in matching:
            print(f"   {sib['rfilename']}")
        print("--- Using first match ---")

    target_file = matching[0]["rfilename"]
    local_path = os.path.join(target_dir, target_file)

    print(f"📦 Model:   {model_id}")
    print(f"📄 File:    {target_file}")
    print(f"🔗 Source:  {RAW_BASE}/{model_id}/raw/main/{target_file}")
    print(f"💾 Local:   {local_path}")
    print()

    # Fetch expected SHA256
    print("📡 Fetching expected SHA256 from LFS pointer...")
    expected = fetch_lfs_sha256(model_id, target_file)
    if not expected:
        print("❌ Could not get expected SHA256")
        sys.exit(1)
    print(f"   Expected: {expected}")
    print()

    # Compute local SHA256
    print("💻 Computing local SHA256...")
    local_hash = compute_local_sha256(local_path)
    if not local_hash:
        sys.exit(1)
    print(f"   Local:    {local_hash}")
    print()

    # Compare
    if expected == local_hash:
        print("✅ SHA256 MATCH — file is intact")
        return 0
    else:
        print("❌ SHA256 MISMATCH — file is CORRUPTED")
        print("   Do NOT use this file. Re-download it.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
