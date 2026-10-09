#!/usr/bin/env python3
"""Extract the structural skeleton of a book chapter from pdftotext -layout output.

Feeds the coverage matrix when generating study exercises: every section heading,
equation, text box, thought experiment, and figure in the chapter becomes a
knowledge block that must map to an exercise.

Usage:
    pdftotext -f 25 -l 47 -layout book.pdf /tmp/ch.txt
    python extract_chapter_structure.py /tmp/ch.txt

Output is line-numbered so each item can be re-read in context.
"""
import re
import sys
from collections import Counter


def main(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    text = "".join(lines)

    print("=== SECTION HEADINGS (candidate, line: text) ===")
    # Headings: short lines, title-ish, not headers/footers. Heuristic, so
    # eyeball the list; cross-check with the PDF's own ToC if present.
    footer = re.compile(r"(Downloaded from|Wiley Online Library|Terms and Conditions|Creative Commons License|John Wiley|^\s*$)")
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if footer.search(s) or len(s) < 12 or len(s) > 110:
            continue
        # headings usually end without sentence punctuation and start capitalized
        if not s[0].isupper() or s.endswith((".", ";", ",")):
            continue
        # skip pure page-number/bar lines
        if re.fullmatch(r"[\d\s|]+", s):
            continue
        print(f"  {i:5d}: {s}")

    print("\n=== EQUATIONS (Eq n) ===")
    eqs = sorted(set(int(x) for x in re.findall(r"Equation\s+(\d+)", text)))
    print(eqs)

    print("\n=== TEXT BOXES (Text Box n.n) ===")
    boxes = sorted(set(re.findall(r"Text Box\s+([\d.]+)", text)), key=lambda s: tuple(map(int, s.split("."))))
    print(boxes)

    print("\n=== THOUGHT EXPERIMENTS ===")
    print(sorted(set(int(x) for x in re.findall(r"Thought Experiment\s+(\d+)", text))))

    print("\n=== FIGURES (Fig n.n) ===")
    figs = sorted(set(re.findall(r"Figure\s+(\d+\.\d+)", text)), key=lambda s: tuple(map(int, s.split("."))))
    print(figs)

    print("\n=== KEY TERM FREQUENCY ===")
    terms = ["molar ratio", "stoichiometr", "affinity", "specificity", "cooperativ",
             "mass action", "Langmuir", "Adair", "saturation", "breakpoint",
             "equivalence point", "isotherm", "rectangular hyperbola", "conservation of mass",
             "monomer", "dimer", "titration", "ΔG", "Kd", "Ka"]
    for t in terms:
        n = text.count(t)
        if n:
            print(f"  {t:24s} {n}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
