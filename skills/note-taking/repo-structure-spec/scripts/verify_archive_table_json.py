#!/usr/bin/env python3
"""Verify provenance JSON generated from an archive table against its source in the archive.

Re-reads every source table (`source_path_in_archive`) out of the archive, re-derives its sha256,
re-applies the pad/trim convention, and compares the header and every cell with `rows` in the JSON.
Prints one line per table — `src_rows / json_rows / header / sha / diffs` — and a FAIL count.

Usage:  /usr/bin/python3 verify_archive_table_json.py --dir <output dir> [--zip PATH] [--manifest FILE]
NOTE: needs openpyxl; reads the manifest produced by the converter (_manifest.json).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import zipfile

import openpyxl


def norm(v):
    """Compare-ready string form: None and "" are the same; integral floats print as ints."""
    if v is None or v == "":
        return None
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def empty(c) -> bool:
    return c is None or c == ""


def trim(rows: list[list]) -> list[list]:
    """Same convention as the converter: pad to a rectangle, drop trailing empty rows, then columns."""
    while rows and all(empty(c) for c in rows[-1]):
        rows.pop()
    w = max((len(r) for r in rows), default=0)
    rows = [list(r) + [None] * (w - len(r)) for r in rows]
    while w > 0 and all(empty(r[w - 1]) for r in rows):
        w -= 1
    return [r[:w] for r in rows]


def raw_table(z: zipfile.ZipFile, src: str) -> list[list]:
    blob = z.read(src)
    if src.lower().endswith(".xlsx"):
        wb = openpyxl.load_workbook(io.BytesIO(blob), data_only=True, read_only=True)
        try:
            return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
        finally:
            wb.close()
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = blob.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f"cannot decode {src}")
    return [list(r) for r in csv.reader(io.StringIO(text, newline=""))]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify archive-table JSON against its source tables.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--dir", required=True, help="directory holding the converter's outputs, containing _manifest.json")
    ap.add_argument("--zip", default=None, help="archive path; default = _manifest.json's source_archive relative to the vault root (i.e. the parent of --dir)")
    ap.add_argument("--manifest", default="_manifest.json", help="manifest file name inside --dir")
    args = ap.parse_args()

    manifest = json.load(open(os.path.join(args.dir, args.manifest), encoding="utf-8"))
    zip_path = args.zip or os.path.join(os.path.dirname(os.path.abspath(args.dir)), manifest["source_archive"])
    z = zipfile.ZipFile(zip_path)

    bad = 0
    for t in manifest["tables"]:
        obj = json.load(open(os.path.join(args.dir, t["file"]), encoding="utf-8"))
        src = t["source_path_in_archive"]
        sha = hashlib.sha256(z.read(src)).hexdigest()
        raw = trim(raw_table(z, src))
        s = obj["sheets"][0]
        hdr_ok = [norm(a) for a in raw[0]] == [norm(b) for b in s["columns"]]
        n = min(len(raw) - 1, len(s["rows"]))
        diff = [(i, j, a, b)
                for i in range(1, n + 1)
                for j, (a, b) in enumerate(zip(raw[i], s["rows"][i - 1]))
                if norm(a) != norm(b)]
        ok = hdr_ok and not diff and len(raw) - 1 == len(s["rows"]) and sha == t["source_sha256"]
        if not ok:
            bad += 1
        print(f"{'OK ' if ok else 'FAIL'} {t['file']:50s} src_rows={len(raw) - 1:>3} json_rows={len(s['rows']):>3} "
              f"cols={len(s['columns']):>2} header={'ok' if hdr_ok else 'MISMATCH'} "
              f"sha={'ok' if sha == t['source_sha256'] else 'MISMATCH'} diffs={len(diff)}")
        for d in diff[:3]:
            print("      row", d[0], "col", d[1], repr(d[2]), "!=", repr(d[3]))
    print(f"\nFAIL count: {bad}  (of {len(manifest['tables'])} tables)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
