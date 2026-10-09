---
name: run-and-verify-bundled-scripts
description: Use when running a skill's or suite's bundled scripts/CLIs.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [cli, scripts, skill-scripts, deliverables, verification, tooling]
    related_skills: [install-macos-gui-app-from-source, terminal-tool-usage-answers]
---

# Running a package's bundled scripts and CLIs

A skill or tool suite ships entry points: `scripts/*.py`, `scripts/*.sh`, native `bin/` binaries. Driving them is easy;
the failure mode is a run that exits 0, prints nothing, and wrote nothing — or one that wrote perfectly good numbers from
the wrong input variant. This is the checklist that closes both.

## When to Use

- A task means executing `scripts/*.py`, `scripts/*.sh`, or a `bin/` binary that ships with an installed skill or tool
  suite, and the result has to be trusted enough to report or hand to the user.
- You are about to batch-run such an entry point over many items (samples, models, files) and want the run to be
  resumable and its numbers verifiable.
- A bundled script / CLI returned without complaint but the expected output is missing, stale, or computed from an
  unexpected input variant.

Not this skill: installing the package (`install-macos-gui-app-from-source`), or answering questions about a terminal
program's usage (`terminal-tool-usage-answers`).

## Procedure

1. **Read the entry point before the first real run.** `--help`, or the `main()`/argparse block when the help is thin.
   Extract exactly two things: the SHAPE of each positional argument (file vs directory vs glob) and the DEFAULT output
   location.
2. **Run ONE item end to end before fanning out.** One sample, one model, one item exposes a wrong path or a wrong input
   variant in a minute instead of after a long batch. Inspect what it actually wrote before starting the rest.
3. **Fan out with a small fixed pool and one log per item.** A driver that calls the entry point per item with
   `ThreadPoolExecutor(max_workers=3)` and redirects each item's stdout+stderr to `<results>/_logs/<item>.log` gives
   resumable, greppable evidence. More workers does not help a single-threaded compute-heavy tool.
4. **Assert artifacts after every call — exit 0 is not success.** Check the expected file exists and is fresh (mtime),
   then parse one known key out of the tool's own record (JSON / tables / log) and print it. A script that takes `<dir>`
   and looks for `<dir>/<expected-file>` silently `continue`s its loop when handed a file path instead of the directory:
   exit 0, no stdout, nothing written.
   **Parseability is not integrity either.** A download cut short still carries a valid header, so any format that is
   header-plus-payload (`.safetensors`, archives, sqlite dumps) parses cleanly while the payload is missing — the file
   is structurally plausible and useless. Compare the byte count against the producer's own declared size
   (`content-length` from the source, a `sizeKB`/`bytes` metadata field, a published hash) before anything consumes it;
   an artifact that was never fully written is the expensive kind of wrong.
5. **Run every step the package's own delivery list names.** "One command" often covers only the compute step; the
   human-readable README/summary usually has its own generator (frequently a separate script that takes the *directory*,
   not the JSON). After it runs, re-read the file and confirm it carries *this* run's numbers, not the previous one's.
6. **Keep superseded outputs until the user decides.** Move the old tree aside (`_prev_<date>/`), do not delete. A copy
   that landed in an unexpected location may be the only remaining record of an earlier run's numbers — and the evidence
   for whatever you are about to claim changed.

## Rules

- **State numbers from a fresh read of the output file, and name the variant they came from.** When the package documents
  a preferred input variant (a filtered/consensus model, a specific run tag) but the code builds its candidate list
  programmatically, read which variant was actually used out of the output's provenance fields (`model`, `reused`, `tag`)
  before quoting any score. A `sorted()`/`set()` wrapped around a concatenated list of globs silently destroys the
  precedence the docs describe; report the mismatch, do not quietly work around it.
- **Do not trust a documented default output directory over the package's stated delivery location.** Docs say where
  deliverables belong and often warn why the obvious location is wrong (per-item dirs regenerated or wiped by another
  process); pass the output path explicitly. Convergence between script default and doc is not something to assume —
  check both, and treat a mismatch as a finding. When the consumer is a GUI app rather than a file reader, settle the
  location with that app's own listing endpoint — what the app enumerates is what the user can see, and a
  plausible-looking sibling directory is a silent miss: the artifact is on disk, the run succeeded, and the user
  reports it missing.
- **Being enumerated by the consumer is necessary but not sufficient — match the format it writes itself.** A GUI
  consumer can list your file through its own endpoint and still render nothing for it, because it accepts only the
  structure its exporter produces (a graph editor that lists every file in its folder as a card, but only for the
  editor-format documents it wrote; API/prompt-format siblings in the same folder show up in the listing and never
  become usable objects). Put your artifact beside one the app itself produced — same directory, known to work — and
  diff the two structures (top-level keys, per-item schema, slot/widget ordering) instead of inferring from the listing
  that it will display; where the app has an export path, round-trip through it and compare. Keep both formats when two
  consumers disagree (the UI wants the editor document, the submit endpoint wants the prompt document) and give the
  conversion one reversible, self-checking command.
- **Reading the consumer's source proves a path exists, never that your file takes it.** Finding the loader in the
  app's bundle (`isApiJson` → `loadApiJson`) settles that the branch is reachable; it says nothing about the visible
  result. Label such a claim as inferred, say what would verify it, and when the user reports the artifact missing
  treat the observation as authoritative and re-derive from it — do not argue your source reading against their screen.
- **Native CLIs shipped inside an app need the app's environment before they run.** Export the install-root variable the
  suite documents, and know that the licence/config file usually sits in that root. A tool exiting with "environment
  variable undefined / licence not found" is unconfigured, not broken.
- **Feed the tool a clean input file.** Files written by an upstream step often carry `#` comment header/footer blocks or a
  trailing metadata block — filter to the columns the tool parses. When scores will be compared between items, restrict
  every item to the same range first.
- **Run a bundle's script from the source clone, not from the installed copy.** Executing `scripts/*.py`
  inside an installed skill writes `__pycache__/` into the delivered tree; the package manager compares the tree
  it recorded, reads it as locally modified, and then **skips that bundle's updates** until a forced re-install.
  When the delivered copy genuinely has to be exercised as evidence, run it there, then delete the caches
  (`find <skill dir> -name __pycache__ -type d -exec rm -rf {} +`) and confirm with a re-check.
  The manager's status command is not a drift detector either: it answers from the metadata it recorded, so a copy
  that carries content the published revision does not have still reads *up to date* — compare the two trees
  byte-wise to find that direction. And it takes one package name per invocation: loop over the names instead of
  passing a list, or the whole call dies on an argument error with no per-package result.
- **A verifier that rewrites a tracked report has no verdict-only mode — import the check instead.** Gate scripts
  normally dump their result to a path they own inside the repo (`<suite>/report.json`), so running one merely to
  read a verdict leaves the tree dirty and can drag an unrelated diff into the next commit. When verdicts are all
  you want, call the underlying check directly: run the *app's* interpreter and put its install root on `sys.path`
  before importing the check module (`sys.path.insert(0, '<install root>')`, `<install root>/venv/bin/python3`),
  iterate the suite's items yourself, and print one line per item. Keep the writing form for the run whose report
  you mean to commit.
- **Changing a bundle's content invalidates the numbers the bundle claims about itself — re-run its gates and
  re-record them in the same commit.** A suite that publishes quality evidence (scanned-clean counts, verified-quote
  fragment totals, coverage or scope rows in its README index) is asserting those numbers about the *previous*
  revision: new prose that quotes a source moves the fragment total, and a new capability can leave an index row's
  stated scope incomplete — while every gate still exits 0. Re-run each recorded gate after the edit, put the new
  number in the same commit as the content, and treat any figure you did not just re-measure as a claim you must not
  repeat. Run them before publishing, too: a verdict you can compute locally is one you never discover from a failed
  install.
- **A gate's number is evidence about what that gate scans, nothing more — read its scope before repeating it as
  coverage.** Recorded credentials ("N/N fragments verified", "0 findings", "0 stale") are computed over one input
  shape and one corpus snapshot, and the excluded cases are silent: a quote checker that matches only block-quote lines
  returns `0 fragments` *and* a clean total for a file whose prose quotes the same source inline, and a corpus pinned to
  a doc snapshot can never reach a passage that lives in a comment page. Before repeating "everything was checked", open
  the gate and answer two questions — which shapes does it enumerate, and which snapshot does it compare against — then
  verify the excluded shapes by hand and say in the report that you did. When the fix is cheap, take it: put anything
  you claim is verbatim into the shape the gate does read.
- **Normalise whitespace on both sides before concluding a passage is absent from a corpus.** Source prose is
  hard-wrapped, so a line-based search — `search_files`, or any grep-style matcher in a pipeline — misses a phrase
  whenever the wrap falls inside it, and that miss is indistinguishable from "this quote is fabricated". Reuse the
  verifier's own normaliser (import its module and call
  its corpus/normalise helpers) instead of hand-building the comparison: a corpus side assembled without normalisation
  reports false MISSes on real quotes, which is how a correct verdict gets overturned.
- **Never locate a bundle's entry point with `find … -path '*<script>' | head -1`.** The same script ships as several
  byte-identical copies (the one inside the installed profile skill and the agent's own bundled `optional-skills/`
  copy), so which one a `| head -1` hands you depends on directory-traversal order and can differ between runs —
  any command built that way is unreproducible evidence. Name a preferred path explicitly, fall back through a short
  ordered list, and exit with a clear message when none exists. (The rule above still decides which copy may be
  *executed* against a delivered tree.)
- **Check for other writers.** The same machine often runs another session against the same results tree: look at
  mtimes/hashes before assuming a file is yours, and never delete a tree you did not create in this session.
- **Removing your own duplicate artifacts: prove byte-identical first, then delete by explicit path.** `cmp -s` every
  candidate against the copy you are keeping and print the list before anything goes; an artifact with no duplicate
  (your own comparison montage, a summary you generated) gets moved somewhere the user can see, not deleted along with
  the directory. Delete with per-path `rm <absolute path>` plus per-path **non-recursive** `rmdir <absolute path>` —
  `rmdir -p`, `find . -delete`, and any delete string carrying `.`/`..` are refused outright by the terminal guard,
  which matches the *shape* "recursive delete of the current tree" whatever the target, so building a command that
  way just burns a round trip.
- **Report a metric that improved while the geometry got worse.** Packages expose several scores; a composite judgement
  needs all of them. A number that got better because the input got worse must be quoted together with the number that
  got worse, plus the selection/parameters it was measured with.
- **A marker-bracketed generator silently skips every file that lacks its marker pair.** Structure/README/inventory
  generators of this shape fill the block *between* two markers and report per file `skipped (no markers)` — exit 0,
  nothing written, and a brand-new file stays unpopulated however often you re-run it; the skip is only visible in the
  companion verifier's output ("no generated section: … fewer than two markers"). Fix: paste the section heading plus the
  two markers into the new file, re-run the generator, and never hand-write the block the generator owns.
- **A large generated block absorbs other writers' uncommitted work as a wrong number.** The block is recomputed from the
  working tree, so a line count or entry count rendered while someone else's edit is in flight lands in *your* commit while
  the file itself stays at the old size — the pushed repo contradicts itself and the `--check` mode of the generator is what
  finds it. Check `git status --short <the directory being recounted>` first; if it is dirty, defer the regenerate.
- **Syntax-check a shell script without naming its path.** `bash -n <path>` can be refused before it runs when the
  referenced file's text contains a gateway-lifecycle command (`hermes gateway restart` / `stop` / `uninstall`) — the guard
  reads referenced scripts statically and will not let anything inside a gateway process touch that lifecycle. Feed the same
  bytes on stdin instead (`bash -n < <path>`), which has no referenced path to inspect.

## References

- `references/atsas-cli-entrypoints.md` — ATSAS 4.x: install-root env var and licence, the home-symlink the wrapping
  libraries search for, which binary reports what, and the CRYSOL fit recipe with the log lines to read.
- `references/envelope-vs-model-size-check.md` — deciding whether an ab initio envelope is oversized for a
  high-resolution model: bead volume vs mass, apparent density, metric cross-checks.

## Related

- Installing the app or CLI in the first place: `install-macos-gui-app-from-source`.
- Answering "how does this tool work" (usage, keys, prompts): `terminal-tool-usage-answers`.
