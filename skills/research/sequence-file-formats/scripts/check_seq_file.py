#!/usr/bin/env python
"""Validate sequence files before hand-off: parse, length consistency, round trip.

Run with a BioPython-capable interpreter:
    /Applications/BioRazer/bin/python check_seq_file.py pUC19.gb [more files...]

Per file it reports:
  * format + parsed length / topology / feature count
  * GenBank only: LOCUS-declared length vs actual ORIGIN length (the redundant
    field parsers only warn about)
  * features whose location falls outside 1..len(seq)
  * a write -> read round trip, comparing sequence length and the feature set
  * .dna: read via sgffp when it is installed

Exit status: 0 clean, 1 problems found, 2 no arguments.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import warnings

try:
    from Bio import SeqIO
except ImportError:  # pragma: no cover
    sys.exit(
        "BioPython is not importable with this interpreter. "
        "Use /Applications/BioRazer/bin/python (system python3 has no Bio module)."
    )

GENBANK_EXT = (".gb", ".gbk", ".genbank", ".gbff")
FASTA_EXT = (".fa", ".fasta", ".fna", ".ffn")


def infer_format(path: str, head: str) -> str:
    """Sniff the format from extension, falling back to the file header."""
    ext = os.path.splitext(path)[1].lower()
    if ext in GENBANK_EXT or re.match(r"^LOCUS\s", head):
        return "genbank"
    if ext in FASTA_EXT or head.lstrip().startswith(">"):
        return "fasta"
    if ext == ".dna":
        return "snapgene"
    return ""


def locus_declared_length(head: str):
    """bp count declared on the LOCUS line, or None if the line is unparseable."""
    match = re.search(r"^LOCUS\s+\S+\s+(\d+)\s+bp", head, re.M)
    return int(match.group(1)) if match else None


def check_snapgene(path: str) -> list:
    problems = []
    try:
        from sgffp import SgffReader
    except ImportError:
        problems.append(
            ".dna needs an explicit reader: uv pip install --python <venv>/bin/python sgffp "
            "(read-only: snapgene_reader, bio-parsers' snapgeneToJson)"
        )
        return problems
    obj = SgffReader.from_file(path)
    print(
        f"  snapgene: {len(obj.sequence.value)} bp, {obj.sequence.topology}, "
        f"features={len(obj.features)}, primers={len(obj.primers)}"
    )
    return problems


def check(path: str) -> list:
    problems: list = []
    with open(path, "r", errors="replace") as handle:
        head = handle.read(4096)
    fmt = infer_format(path, head)

    if fmt == "snapgene":
        return check_snapgene(path)
    if not fmt:
        return ["unrecognised format (no LOCUS line, no '>' header, unknown extension)"]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        records = list(SeqIO.parse(path, fmt))
    for warning in caught:
        problems.append(f"parser warning: {warning.message}")
    if not records:
        return problems + ["no records parsed"]

    for index, record in enumerate(records):
        tag = f"record {index} ({record.id})"
        print(
            f"  {tag}: {len(record.seq)} bp, "
            f"{record.annotations.get('topology', '?')}, features={len(record.features)}"
        )
        for feature in record.features:
            if int(feature.location.start) < 0 or int(feature.location.end) > len(record.seq):
                problems.append(
                    f"{tag}: feature {feature.type} {feature.location} "
                    f"outside 1..{len(record.seq)}"
                )

    if fmt == "genbank":
        declared = locus_declared_length(head)
        actual = sum(len(r.seq) for r in records)
        if declared is not None and declared != actual:
            problems.append(
                f"LOCUS declares {declared} bp but ORIGIN holds {actual} bp — the redundant "
                "length field is not cross-checked by parsers, so re-write the record to fix it"
            )
        if len(records) == 1:
            with tempfile.TemporaryDirectory() as tmp:
                out = os.path.join(tmp, "roundtrip.gb")
                SeqIO.write(records[0], out, "genbank")
                back = SeqIO.read(out, "genbank")
                before = sorted(str(f.location) + f.type for f in records[0].features)
                after = sorted(str(f.location) + f.type for f in back.features)
                print(f"  round trip: {len(back.seq)} bp, features {len(before)} -> {len(after)}")
                if len(back.seq) != len(records[0].seq):
                    problems.append("round trip changed the sequence length")
                if before != after:
                    problems.append(f"round trip changed features: {set(after) ^ set(before)}")
    return problems


def main(argv: list) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    found = 0
    for path in argv[1:]:
        print(path)
        try:
            problems = check(path)
        except Exception as exc:  # a parse failure is exactly what this tool reports
            print(f"  UNREADABLE: {type(exc).__name__}: {exc}")
            found += 1
            continue
        for problem in problems:
            print(f"  ! {problem}")
        found += len(problems)
        print("  ok" if not problems else "  ^ review the items above")
    print()
    print("verdict:", "PROBLEMS FOUND" if found else "clean")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
