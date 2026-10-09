---
name: software-development
description: Check this skill before coding.
---

# Software Development Skills

## Rules
- Use skill `karpathy-guidelines` before coding.
- Use skill `mamba-python-install` when you want to configure a Python environment.

## Debugging
- Use skill `systematic-debugging` when you want to debug code systematically.
- Use skill `python-debugpy` when you want to debug Python code.
- Use skill `node-inspect-debugger` when you want to debug Node.js code.

## Improvement
- Use skill `code-review` when you want to review code.
- Use skill `simplify-code` when you want to simplify code.

## Techniques
- `references/stdlib-http-cli.md` — Writing portable CLI tools that make HTTP
  calls using only Python stdlib (`urllib.request` + `json`), avoiding the
  `requests`/`urllib3` dependency problem on Python ≥3.14.  Includes the full
  pattern: POST/GET/download functions, retry wrapper, and when to use (or not
  use) stdlib-only.

## Scripts
- `scripts/colabfold_msa.py` — Standalone MSA generator for protein structure
  prediction. Calls the ColabFold MMseqs2 public API, produces A3M files
  compatible with OpenDDE. Deployed to `~/.local/bin/colabfold_msa`.
  Demonstrates the stdlib-only HTTP pattern in a real bioinformatics tool.

## References
- `references/git-archeology.md` — Tracing API/parameter renames through git
  history (`git log -S`, `git show ^:file`, semantic-vs-rename detection,
  silent dataclass fallback traps).
- `references/git-case-sensitivity-macos.md` — Git case-sensitivity
  pitfalls on macOS APFS: file collisions, residual "deleted" files after
  remote renames, and the debugging workflow (`git ls-files` →
  `git ls-tree HEAD` → `ls` → `git checkout HEAD --`).
- `references/matplotlib-axes-sizing.md` — Guaranteeing consistent Axes
  data-area dimensions across figures (explicit positioning instead of
  `tight_layout`).  Useful when legend width or label length varies between
  plots.
- `references/dataclass-field-documentation.md` — IDE-visible field docs (`#:` + `Annotated`) + `@dataclass(slots=True)` to prevent silent stray attributes.
- `references/matplotlib-ticks.md` — Setting major and minor X-axis ticks
  through ContDescAnno (ticklabel_space_major / ticklabel_space_minor /
  ticks_minor).  Covers the normalized-coordinate calculation and the
  `None`-guard pattern for minor ticks.
