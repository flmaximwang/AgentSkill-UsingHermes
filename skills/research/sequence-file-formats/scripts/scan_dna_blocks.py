#!/usr/bin/env python3
"""Independent SnapGene .dna block scanner + optional write-path round-trip probe.

    python3 scan_dna_blocks.py FILE...                 # read-only header scan (fast, safe)
    python3 scan_dna_blocks.py --tree DIR              # recursive: aggregate block inventory
    python3 scan_dna_blocks.py --roundtrip FILE -o OUT # needs sgffp; run with that venv's python

WHY AN INDEPENDENT SCANNER: a library's own block accounting cannot audit the same library's
writer -- it reports what it decoded, not what was in the file. This walks the container
directly (19 header bytes, then repeating 1-byte type + 4-byte big-endian length) and seek()s
over payloads, so scanning a whole vault costs seconds.

SAFETY: scan/--tree open files read-only. --roundtrip refuses to write over its input and only
ever writes to the path given with -o.
"""
import argparse
import collections
import hashlib
import os
import struct
import sys

HEADER = 19
TYPE_OF_SEQUENCE = {1: "DNA", 2: "protein", 7: "RNA"}

# Block ids the reader/writer actually consults. Prefer the installed library; fall back to a
# literal snapshot of sgffp 0.22.x so this script also runs without sgffp installed.
try:
    import sgffp
    from sgffp import parsers as _p

    SCHEME = set(_p.SCHEME)
    LEGACY_CACHE_BLOCKS = set(_p.LEGACY_CACHE_BLOCKS)
    MODERN_VERSION = _p.MODERN_EXPORT_VERSION
    KNOWN_SOURCE = f"sgffp {getattr(sgffp, '__version__', '?')} parser tables"
except Exception:  # noqa: BLE001 - scanner must work standalone
    SCHEME = {0, 1, 5, 6, 7, 8, 10, 11, 14, 16, 17, 18, 20, 21, 23, 27, 28, 29, 30, 32, 34}
    LEGACY_CACHE_BLOCKS = {2, 3, 13}
    MODERN_VERSION = 15
    KNOWN_SOURCE = "literal snapshot of sgffp 0.22.x (library not importable)"

# Vendor caches that `sff check -l` marks [*] known but that are absent from the reader/writer
# tables -- i.e. marked safe and then dropped on write. Verify, do not trust the marker.
CHECK_MARKED_BUT_DROPPED = {35}


def read_cookie(fh):
    """Validate the 19-byte header and return its fields."""
    if fh.read(1) != b"\t":
        raise ValueError("wrong magic byte (not a SnapGene file)")
    if struct.unpack(">I", fh.read(4))[0] != 14 or fh.read(8) != b"SnapGene":
        raise ValueError("wrong header")
    ts = struct.unpack(">H", fh.read(2))[0]
    export_version = struct.unpack(">H", fh.read(2))[0]
    import_version = struct.unpack(">H", fh.read(2))[0]
    return {
        "type_of_sequence": TYPE_OF_SEQUENCE.get(ts, f"type{ts}"),
        "export_version": export_version,
        "import_version": import_version,
    }


def scan(path):
    """Return (cookie, [(block_type, length, offset)], trailing_byte_count)."""
    blocks = []
    with open(path, "rb") as fh:
        cookie = read_cookie(fh)
        off = HEADER
        while True:
            head = fh.read(5)
            if len(head) < 5:
                break
            block_type, length = struct.unpack(">BI", head)
            blocks.append((block_type, length, off))
            off += 5 + length
            fh.seek(length, 1)  # skip the payload: this is what keeps the scan cheap
    return cookie, blocks, off - os.path.getsize(path)


def classify(block_type):
    if block_type in SCHEME:
        return "decoded"
    if block_type in LEGACY_CACHE_BLOCKS:
        return "cache-kept"
    if block_type in CHECK_MARKED_BUT_DROPPED:
        return "CHECK-SAYS-KNOWN-BUT-WRITE-DROPS"
    return "UNKNOWN-DROPPED"


def report(path, verbose=True):
    cookie, blocks, trailing = scan(path)
    kinds = collections.Counter(classify(bt) for bt, _, _ in blocks)
    risky = [(bt, ln) for bt, ln, _ in blocks if classify(bt).startswith(("UNKNOWN", "CHECK"))]
    if verbose:
        print(f"{path}")
        print(f"  {cookie['type_of_sequence']} export_version={cookie['export_version']} "
              f"blocks={len(blocks)} trailing={trailing}B")
        print(f"  kinds: {dict(kinds)}")
        if risky:
            print(f"  WRITE-BACK WOULD LOSE: {[(bt, classify(bt)) for bt, _ in risky]}")
    return cookie, blocks, risky


def wipe_sig(sgff):
    """Semantic signature: equality here means the write path preserved the content."""
    feats = []
    for f in sgff.features:
        try:
            quals = tuple(sorted((k, str(v)) for k, v in dict(f.qualifiers).items()))
        except Exception:  # noqa: BLE001
            quals = ()
        feats.append((f.name, f.type, getattr(f, "start", None), getattr(f, "end", None),
                      getattr(f, "strand", getattr(f, "direction", None)), quals))
    primers = sorted(str(getattr(p, "name", "")) + str(getattr(p, "sequence", ""))
                     for p in sgff.primers)
    hist = 0
    try:
        hist = len(sgff.history.nodes or [])
    except Exception:  # noqa: BLE001
        pass
    return {"seq": sgff.sequence.value, "topology": sgff.sequence.topology,
            "features": sorted(feats, key=str), "primers": primers, "history_nodes": hist}


def roundtrip(path, out):
    if os.path.abspath(path) == os.path.abspath(out):
        sys.exit("refusing to overwrite the source file; pass a different -o path")
    from sgffp import SgffReader, SgffWriter

    with open(path, "rb") as fh:
        before_bytes = hashlib.sha256(fh.read()).hexdigest()
    before = SgffReader.from_file(path)
    SgffWriter.to_file(before, out, preserve=True)
    after = SgffReader.from_file(out)
    with open(out, "rb") as fh:
        after_bytes = hashlib.sha256(fh.read()).hexdigest()

    in_types = {bt for bt, _, _ in scan(path)[1]}
    out_types = {bt for bt, _, _ in scan(out)[1]}
    sig_in, sig_out = wipe_sig(before), wipe_sig(after)

    print(f"{path}\n  -> {out}")
    print(f"  byte-identical: {before_bytes == after_bytes}  (expect False: XML is re-serialised)")
    print(f"  LOST BLOCK TYPES: {sorted(in_types - out_types) or 'none'}")
    print(f"  content seq/topology/features/primers/history identical: "
          f"{sig_in == sig_out}")
    if sig_in != sig_out:
        for key in sig_in:
            if sig_in[key] != sig_out[key]:
                print(f"    DIFFERS: {key}")
                print(f"      in : {str(sig_in[key])[:200]}")
                print(f"      out: {str(sig_out[key])[:200]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="file(s) to scan")
    ap.add_argument("--tree", metavar="DIR", help="recursively scan every *.dna under DIR")
    ap.add_argument("--roundtrip", metavar="FILE", help="read -> write -> compare (needs sgffp)")
    ap.add_argument("-o", "--out", metavar="OUT.dna", help="output path for --roundtrip")
    args = ap.parse_args()

    print(f"known-block tables: {KNOWN_SOURCE}")
    if args.roundtrip:
        if not args.out:
            sys.exit("--roundtrip needs -o OUT.dna")
        roundtrip(args.roundtrip, args.out)
        return

    targets = list(args.paths)
    if args.tree:
        for root, _, names in os.walk(args.tree):
            targets += [os.path.join(root, n) for n in names if n.lower().endswith(".dna")]
    if not targets:
        sys.exit("nothing to scan: pass files or --tree DIR")

    agg = collections.Counter()
    versions = collections.Counter()
    risky_files, bad = [], []
    for t in targets:
        try:
            cookie, _, risky = report(t, verbose=not args.tree)
        except Exception as exc:  # noqa: BLE001 - report, never abort the sweep
            bad.append((t, f"{type(exc).__name__}: {exc}"))
            continue
        versions[cookie["export_version"]] += 1
        for bt, _ in risky:
            agg[bt] += 1
        if risky:
            risky_files.append(t)

    if args.tree:
        print(f"scanned {len(targets) - len(bad)} files | export_version: {dict(sorted(versions.items()))}")
        print(f"block types that would be LOST on write-back: {dict(sorted(agg.items()))}")
        print(f"files carrying them: {len(risky_files)}")
        for t in risky_files[:12]:
            print(f"   {t}")
    for t, why in bad[:8]:
        print(f"   unreadable: {t}  ({why})")


if __name__ == "__main__":
    main()
