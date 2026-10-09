# Normalisation pass — mechanics, traps, known spec drift

Depth for SKILL.md §4. Read this when applying a tier-1/tier-2 change to one vault project, not when
deriving a spec.

## Tier 1 changes and what applies each

| Change | How | Why it is tier 1 |
|---|---|---|
| Ignore rules | patch in-repo `.gitignore`, then `git rm --cached <path>` for anything already tracked | the file stays on disk; only tracking stops |
| Misfiled assets | `mkdir -p <record>/assets` then `git mv` | `![[file.ext]]` embeds resolve by basename, so no note edit needed |
| Missing required frontmatter keys | `patch` the note's frontmatter | additive metadata, not a rewrite of the record body; generate a fresh uuid4 for a missing `UID` |
| Broken `adv-uri` vault names | `patch` `vault=<old>` → `vault=<current dir name>` | the uid half is already right |
| Junk directories | `rm -rf` inside a record (`__pycache__`, `.vscode`) | regenerable, already ignored |
| Permission modes | `find . -type f -perm 600 -not -path './.git/*' -print0 \| xargs -0 chmod 644` | changes no content and no mtime |
| Stale template README | rewrite the directory table from `ls` | the README is the only place claiming directories that exist nowhere |

## Rename / move mechanics (Obsidian vault, git-managed)

- `git mv` does **not** create the destination's parent directory — `mkdir -p <parent>` first or it
  fails with `No such file or directory` and leaves a half-applied batch.
- A parent and its child cannot both be moved in one chained script using the old paths: after
  `git mv <old-dir> <new-dir>`, the child must be addressed under `<new-dir>`. Moving the child first
  and the parent second avoids the ordering trap entirely.
- Verify a rename batch by `find`-ing the destination tree, not by counting `git mv` successes — a
  chained `&&` script reports a total that includes paths it never touched.
- Keep the basename when the move was not explicitly requested: wiki links and embeds resolve by
  basename across the vault, so moving `<note>.md` into a differently-named folder breaks nothing,
  while renaming it breaks every inlink until they are updated in the same pass.
- Count inlinks with a regex over every `.md` and `.base` and diff against the set of existing note
  basenames; a `[[...]]` inside a backtick code span is a false positive in a raw text scan.
- **`git ls-files` C-quotes non-ASCII paths** (`"Records/…"`), so a set comparison against
  `os.walk` output (`comm`, a Python set diff) reports tracked files as untracked and invents a
  finding. Compare counts instead, use `git ls-files -z`, and take the verdict from
  `git status --porcelain`.
- **Renaming a template file is a move inside the app's configured template folder.** Read
  `.obsidian/plugins/templater-obsidian/data.json` → `templates_folder` (and core `templates.json`)
  before touching `Templates/`: the basename may change, the directory may not, or the template picker
  goes empty for the next session. Keep the template's `tags` aligned with what its own embeds filter
  on — add the new family tag while a `.base` still filters the old one.
- SnapGene lock files are literally named `.sglock` (literal pattern correct), while backup files are
  `<note>.md.bak` (literal `.bak` matches nothing — `*.bak` is the rule).
- A self-check that reads `note = <dir>/<dir>.md` must compare the *basename*, not the returned path,
  or every record reports `note != folder` and the whole matrix is wrong.
- **Retiring a tag root is a two-file-class edit, not a tag rename.** The token lives in (a) the notes
  carrying it and (b) the `.base` filter that groups rows by it (`file.tags.contains("<Root>/<X>")`);
  filter expressions elsewhere match fields or UUIDs and need nothing. Rewrite both, then re-grep for
  zero hits. Old spellings of one concept are separate tokens (`<Root>/<Domain>/<ID>` and a bare
  `<Root>/<Domain>-<ID>` both existed) — map each explicitly rather than a regex that assumes a shape.
- **A tag-driven collection view needs an explicit discriminator after a merge.** Once the merged
  entity note sits under the same tag root as its records — and loses a `_` filename prefix that used
  to exclude it from `!file.name.startsWith("_")` — the view lists it as an empty row. Add the
  records' own family tag (`file.tags.contains("Logs")`) beside the identity tag.
- **A path-qualified link is the only link a move breaks.** `[[Root/Purpose/Note]]` stops resolving
  when `Purpose/` is dropped; rewrite it to `[[Note]]` in the same pass and grep `'\[\[Root/'`
  vault-wide afterwards. Links inside tables and inside a frontmatter `protocol:`/`protocols:` field
  are usually already basename-only, so scan before assuming they need edits.

## Inspecting workbooks and binaries

- Read `.xlsx` through `terminal` with the system `python3` (it has `openpyxl`); the `execute_code`
  interpreter does not. Dump `wb.sheetnames`, the first row of each sheet, and `ws.max_row - 1`:
  sheet names and sheet headers are the vocabulary that tells generations apart.
- Guard the header read — a worksheet with no rows raises `StopIteration` on `next(iter_rows())`;
  wrap it and keep going.
- Moving a `.xlsx` breaks every `=INDEX([2]Table!…)` cross-workbook link, which is why Excel lock
  files (`~$*`) are gitignored.

## File metadata vs the write tools

- `chmod` changes no mtime and no content, but it invalidates a write tool's cached read: after any
  out-of-band touch of a file, re-read it before `write_file`, or prefer targeted `patch` edits.

## Measuring an older-generation project (script blind spots)

- `scripts/audit-project.py` walks `Logs/` only. On a project whose records live in
  `Records/<bucket>/(<YYYY-MM-DD>) <Title>/` it prints `record folders: 0` and an empty per-record
  table — nothing is wrong with the project, the walk is looking in the wrong organ. Derive the numbers
  yourself: a record note is `Records/<bucket>/<folder>/<folder>.md`, one level below a bucket.
- Count folders **one level below a bucket**, not by walking the whole tree:
  `<folder>_assets/<timestamp>/<timestamp>.md` and `Workspace/data/**/README.md` auto-exports also
  satisfy "a note named after its folder" (measured 93 vs the true 34). The same trap hits a
  frontmatter-coverage scan — 155 `.md` in the project, 34 of them record notes.
- A back-fill is safest as a scripted insert, verified with `git diff --stat` before committing: a
  fresh uuid4 `UID` goes as the **first** line inside the frontmatter block; missing
  `highlight: []` / `keywords: []` go before the first canonical-order key present
  (`keywords` / `protocol(s)` / `archive-id` / `contributors`), otherwise at the end of the block.
  Expect few hits — the generation may already carry them.
- Count embeds of files that do not exist rather than assuming them: `grep -c '!\[\[.*\.base\]\]'`
  per note, then check the named view exists in the project. A project that never carried the view
  renders every embed empty, and the view usually survives in a *sibling* project under a different
  directory — a copy-in is a content decision for the user, not a fix.

## Snapshotting the pass

- `Migration/<YYYY.MM.DD>.<NNN>/` is where a pass is recorded: `do_migration.py` (idempotent;
  `--dry-run` the default, `--apply` writes) plus a `README.md` carrying the per-commit counts, the
  evidence behind each, and the items deliberately left undecided.
- Verify the snapshot by running it: a clean pass reports zero pending work — that is the check that
  the script and the tree agree.
- **Run the exact command your README documents before committing the script.** A documented
  `--dry-run` that argparse never defined fails on the next session's first attempt.
- **Do not rename or move paths while a path-level comparison against an external manifest is
  pending.** That comparison joins on paths, so a rename silently invalidates it; when the same
  request also asks a data-safety question, answer that first from live evidence, land the no-rename
  fixes, and hold the moves.

## Records → Logs migration (older bucket layout → current record layout)

One project, one commit: every record leaves `Records/<bucket>/(<YYYY-MM-DD>) <Title>/` for
`Logs/<YYYY>/<MM>/<DD>/<Type>-<NNN>/`, and the note is renamed to match its folder.
`git show --name-status HEAD | grep -c '^R'` is the batch evidence (34 records → 433 renames, because
each record drags its `_assets/` and `Workspace/` along).

1. **Classify every record into the closed `<Type>` set and show the mapping table before moving it:**
   `样品准备…` / `Preparation of…` → `Purification`; `样品分析…` / `Analysis of…` →
   `Characterization`, or `TEM` when the title names a TEM run; a crystal-preparation record →
   `Characterization` (the vocabulary has no Crystallization type).
2. **A record the vocabulary cannot name keeps its own title, un-numbered** —
   `Logs/2026/06/05/数据归档-TEM002-20260526/` (strip the leading `(<date>) `, turn `. ` into `-`). This
   user's explicit answer was 保留原标题、不编 Type: do not invent a type and do not extend the closed set.
3. **Number per day *and* per type** — counters keyed `(Y, M, D, Type)`, 3 digits from `001`. Two
   same-type records on one day take consecutive numbers; different types on the same day never
   collide. Read the date from the **folder name**: two same-day, same-type records can carry almost
   the same title, and the frontmatter usually has no date at all.
4. **Rename the note to the folder name** (`<Type>-<NNN>.md`) after moving the folder. Record basenames
   were referenced 0 times in the project measured here, so the rename was free; a project that links
   its records (including a dangling `[[<title>]]` from a task note) needs those rewritten in the same
   pass.
5. **Two frontmatter edits, and they are not symmetric.** Add the record family tag `Logs` (the view
   filters on it), but **keep** the old `Records` tag whenever a `.base` in the project filters
   `file.tags.contains("Records")` — dropping it silently empties that view. Repoint
   `parents: [[Records]]` → `[[Logs]]` so the field follows the new organ. Leave `archive-id` exactly
   as found: filled = archived, empty = in-progress.
6. **Handle the inline tags form.** `tags: [Records]` on one line is invisible to a regex expecting the
   block form, so that note is silently skipped and the view misses it. After the batch, re-scan every
   record for the tag, report the straggler count, and convert the line to the block form.
7. **Copy `Logs.base` from a current-generation sibling** — its `进行中` view filter is
   `note["archive-id"].isEmpty()`, on top of `file.tags.contains("Logs")` and
   `!file.basename.startsWith("_ ")`-style exclusions. A migrated `Logs/` with no `.base` has no
   in-progress view at all.
8. **Count the result at the exact depth, and count values rather than keys.** A record note is
   `Logs/<YYYY>/<MM>/<DD>/<folder>/<folder>.md`. `archive-id:` present with an empty value still means
   in-progress, so a regex requiring a list item under the key under-reports it (33 keys, 25 values →
   9 in-progress, one of them with no key at all).
9. **Delete the emptied buckets** and say so in the commit body — `Records/` disappearing is part of
   the migration, not an accident. The remaining decisions (the generation's record template, a
   view whose file exists nowhere) go in the report as undecided, not as silent edits.

- `du -ch` driven by `find … -exec du -ch {} +` prints one total **per invocation**, so `tail -1` is
  the last batch, not the tree (measured: 22 G reported for a 38 G copy). Sum `os.path.getsize` in
  Python, or take a single `du -sh`, when a size is going into a report.
- **Probe the copy without the source**: `unzip -t` every archive (CRC), magic bytes for large
  binaries (HDF5 = `894844460d0a1a0a`), `sips -g pixelWidth` for images — a same-count comparison
  proves nothing about readability.

## Protocols: one folder per protocol, and where `Series<N>.v<M>` comes from

`Protocols/` is tiled flat — one folder per protocol, **no purpose layer**, versions in the filename:
`Protocols/<协议>/<标题> - Series<N>.v<M>.md`. The folder carries the title *without* the version
suffix (a `.base` view filtering `file.name == this.file.name` needs the two names to differ). A
container folder named after the project ("05 四螺旋束纤维的可设计性") holding every protocol at once
is that purpose layer, and goes once the protocols have their own folders.

1. **Derive `Series`/`v` from citations, never from taste.** The evidence lives in the records that
   used the protocol: each citation carries the doc id (`docx/<id>`), often an `edition_id`, and
   sometimes a release number (`… (release-002)`). Build a doc-id → (title as cited, edition, release,
   citation dates) table before renaming anything.
   - Same doc id, retitled, cited later → a later revision of one protocol: `6×His-MBP-…` cited as
     `release-001` → `10×His-MBP-…` = `- Series1.v2`.
   - An unnumbered `edition_id` first, a `release-002` later → the exported file is the newest edition
     cited, so it is `v2`, not `v1`.
   - One edition, no release number anywhere → `Series1.v1`; no evidence of a second generation means
     every file stays `Series1`.
   - **Never fabricate the versions you lack.** Earlier editions that provably existed but were never
     exported stay gaps: name them in a `版本沿革` table (doc id, citation evidence, resulting number)
     in the protocol folder's index, and do not create placeholder files.
2. **Strip the legacy purpose prefix** (`蛋白纯化_…`) when the folder already names the purpose; keep
   the export's `_` where the original title had `/` (a filename cannot carry a slash).
3. **Per-sample task sheets keep their sample code.** Several docs sharing one title but differing by
   sample (`…-2025.10.10`, `….001`, `….002` for A2/A5/B2) are parallel applications, not generations:
   numbering them `Series1..3` erases the sample identity from the filename. Put them in one folder per
   title, leave the names alone, and state the choice in the report.
4. **Move the index to the top** (`Protocols/README.md`) and rewrite it to the folder ↔ file mapping
   plus the `版本沿革` table — it must stop pointing at the `手册/` sub-paths the files no longer have.
5. Verify with `find Protocols -type f` (folders flat, one file family each), `git show --name-status
   HEAD | grep -c '^R'`, and a re-grep for the retired prefix and the old basenames (expect 0 hits).

## Removing a deprecated organ

"`Inventory` 已经弃用，删除相关引用" means delete the directory **and** its references, not one of them.

- `grep -rn` the organ's name over `*.md` and `*.base` first, and check whether the only reference
  points *inside* the directory being deleted (`![[Inventory.base]]` lived in `Inventory/Inventory.md`)
  — then `git rm -r` removes folder and reference in one act, and no dangling embed is left behind.
- Re-grep afterwards: the expected residue is prose that documents the removal (project README,
  migration snapshot), not links. Report that distinction rather than claiming "0 hits".
- Say where the authority moved to (here: the ledger lives in Dolt, not in the vault) so the next
  session does not rebuild the page; a directory deletion may also close an outstanding gap — name the
  item it closed.
- A *sibling* class the user did not name (`Lookup-05.xlsx`, sheets holding headers only) gets flagged
  with the same reasoning and left in place — one line, their call.

## Known spec-vs-library drift (re-check before enforcing)

Recorded because a spec written from a survey outlives the projects it described. Format: spec says →
library actually does.

- **Lookup workbook sheets.** Spec: `Entities` / `Stocks` / `Boxes` (`Table`/`Layout`/`Helper`).
  Library (14 workbooks): `<Type> Entities`, `<Type> Stocks`, `Box Table`, `Box Layout`, `Helper`,
  plus a `UID Summary`. The bare names survive only in superseded per-type split workbooks.
- **Protocol back-reference field.** The record template and current records use `protocols:` (a list
  holding the protocol's uuid and optionally `"[[protocol name]]"`); older records use `protocol:`.
  Both view files match either form — one filter tests `list(protocols).contains(this.file)`, another
  `list(protocols).contains(note["UID"])` — so a uuid-only entry still resolves and the missing
  wiki-link half is not a defect worth "fixing".
- **`Records/` means two different things by generation.** Older projects:
  `Records/<start>-<end>-<7-digit bucket>/(<YYYY-MM-DD>) <Title>/`. Newer projects: flat project-level
  notes at the `Records/` root (task / records templates), with individual archived entries staying in
  `Logs/` and carrying `archive-id`. Determine the generation before restructuring anything — and note
  that the library is **mid-transition**: some siblings put records directly in `Logs/<YYYY>/<MM>/<DD>/`
  as `<Type>-<NNN>/`, others still two levels up as `Logs/<YYYY>/<MM>/(<date>) <type> <title>/`. Count
  `<Type>-<NNN>` usage before calling either shape canonical, and copy the target shape (record
  frontmatter, `Logs.base`) from whichever sibling already has the newer form.
- **Ignore-rule literals.** A literal `.bak` line matches nothing; `<note>.md.bak` files in the
  library are tracked because of it. `*.bak` is the rule.

## Domain conventions worth not re-deriving

- **Archiving is a frontmatter act, not a move.** Filling
  `archive-id: <7-digit bucket>/<box-range>/<YYYY.MM.DD>` is what removes an entry from the
  in-progress view (that view's filter is `note["archive-id"].isEmpty()`); the note stays where it is.
  State this in the project README.
- `archive-id: null//<YYYY.MM.DD>` is meaningful, not a missing value: the entry was never written
  into the physical lab notebook. Keep it and document the meaning rather than "fixing" it to a
  bucket number.
- Attachment dumps and day folders holding Chinese-typed names are deliberately **not** converted —
  say so in the report instead of normalising them. A project's `Records/<bucket>/(<YYYY-MM-DD>)
  <Title>/` record set is a different case: this user orders it **converted** into the
  current-generation `Logs/` layout ("先迁移 Records"), so do not pre-emptively declare it out of
  scope — recipe below.
- A README copied from a project template lists directories that exist in no project; keep the
  rewrite to a real directory table plus the record conventions, and take the one-line project
  overview only from what the vault's own notes state.
