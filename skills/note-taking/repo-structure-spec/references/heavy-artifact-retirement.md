# Retiring a heavy archive from a vault repo

Depth for §5. The recurring artifact is a snapshot of an inventory tree — `Backup/Inventories-<NN>.zip`
and its siblings: 0.5–1 GB uncompressed, mostly SnapGene `.dna`, protein `.prot`, EM density `.map`,
AlphaFold output `.json`, with a handful of `.xlsx`/`.csv` ledger tables and `.md` notes on top.
Sometimes one is already committed, and then it dominates `.git`.

## 1. Census — before asking anything

```bash
# is it tracked, how big is the blob, what did it do to the repo
git ls-files Backup
git cat-file -s HEAD:Backup/Inventories-10.zip
du -sh .git
# the norm across sibling projects of the same root
for v in <root>/<project>*/; do [ -d "$v/.git" ] && printf '%s tracked=%s git=%s\n' \
  "$(basename $v)" "$(git -C $v ls-files | grep -c '^Backup/')" "$(du -sh $v/.git | cut -f1)"; done
```

```python
# extension × count × uncompressed bytes, and the biggest entries
import collections, os, zipfile
z = zipfile.ZipFile(ZIP)
ext, size = collections.Counter(), collections.Counter()
for i in z.infolist():
    e = os.path.splitext(i.filename)[1].lower() or "(dir/none)"
    ext[e] += 1; size[e] += i.file_size
print("uncompressed total", sum(i.file_size for i in z.infolist()))
for i in sorted(z.infolist(), key=lambda i: -i.file_size)[:10]:
    print(i.file_size, i.filename)
```

- **Census in Python, not `unzip -l`**: `unzip` mojibakes non-UTF8 entry names (`�?�� pASKK1`)
  while `zipfile` decodes them correctly. Same reason for extracting in Python.
- Report the census as a table with the module count and the byte breakdown; a single 226 MB `.map`
  explaining a quarter of the archive is the kind of fact that decides the output scope.

## 2. Output-scope decision (goes into the clarify)

| option | size for ~2,100 entries | use when |
|---|---|---|
| path + size + mtime + sha256 manifest, no content | ~0.3–0.5 MB | the content stays reachable elsewhere (archive share, a DB) |
| the ledger tables only (xlsx/csv → JSON) | ~0.2 MB | the point is a diffable ledger history |
| text inlined (md/txt/csv/xlsx content; binaries hashed) | ~130 MB | the wording of notes matters, the binaries do not |
| everything inlined base64 | ~1.3 GB of undiffable text | effectively never — it is the archive again, worse |

Plus the second question that decides whether this is even useful: **where do the extracted files go**
(in place under the gitignored dir, outside the vault, or a temp dir deleted after conversion).
And the third: **delete the working-tree archive only, or rewrite history now** — see §7.

## 3. The provenance JSON shape

```jsonc
{
  "source_archive": "Backup/Inventories-10.zip",
  "source_path_in_archive": "Inventories/Plasmids/## Archive/Plasmids.xlsx",
  "source_sha256": "23df2b1d…",          // bytes of the source file, so losslessness is checkable
  "source_bytes": 20473,
  "format": "xlsx",                       // or "csv" (+ "encoding")
  "converted_on": "YYYY-MM-DD",
  "sheets": [{
    "sheet": "Sheet1",                   // csv tables get "(csv)"
    "columns": ["ID", "LOT. NO.", null],  // header, i.e. the column order
    "rows": [["pCT007-scFv_m903", null]], // positional: list-of-lists, aligned to columns
    "row_count": 48, "col_count": 6,
    "trimmed_empty_rows": 0, "trimmed_empty_cols": 0,
    "duplicate_headers": []
  }]
}
```

- **Positional rows, not objects keyed by header.** Ledger sheets carry blank and repeated headers;
  keying by header silently collapses those cells. Positional rows also give one text line per record,
  which is what makes the JSON diffable at all.
- One output per source table named `<basename>.json`; when two sources share a basename (`summary.xlsx`
  under two pipeline dirs) prefix the parent directory. A `_manifest.json` lists every output with its
  source path, hashes, row/column counts and exclusions.
- Reads: xlsx with `load_workbook(..., data_only=True)` and **not** `read_only=True` (see §6); csv with
  `utf-8-sig`, then `utf-8`, then `gb18030`, cutting over only when the stripped first row differs from
  the second; cut the BOM out of the header cell.
- Shape: pad to a rectangle, then drop trailing all-empty rows, then trailing all-empty columns, and
  **record both counts in the output** — `dims`/`max_row` include phantom rows, and a table whose
  dimensions claim 205 rows can hold 3.
- Formulas become their **cached values** (`data_only=True`); say so in the note and in the report —
  the baseline is Excel's last computed value, not a recomputation.

## 4. Verification (two independent checks)

```bash
/usr/bin/python3 Toolbox/inventories_tables_to_json.py     # convert
/usr/bin/python3 <skill>/scripts/verify_archive_table_json.py --dir <vault>/Inventory/Inventories-10
```

The verifier re-reads each source out of the archive, re-derives its sha256, re-applies pad/trim and
compares header plus every cell (normalising `None`/`""`, and numeric floats that are integral).
It prints one line per table — `src_rows / json_rows / header / sha / diffs` — and a FAIL count.
A passing run reads `7/7 OK, 0 diffs`.

Archive integrity, when files are extracted:

```python
z.testzip()                      # None ⇒ every entry's CRC matches
sum(i.file_size for i in z.infolist())   # must equal the extracted bytes on disk
```

`du -sh` on the extracted tree reads lower than that sum (block rounding) — quote the Python-summed
bytes as the extraction proof and `du` as disk usage, not as a discrepancy.

## 5. Landing and the remainder

- Converter → somewhere disposable (the profile scratch area). Committing it into the vault's tracked
  tools directory (`Toolbox/`) is what this file used to prescribe; the user deleted that committed
  script one commit later, so do not count on it surviving. If you do commit it: argparse with defaults
  and units in the help text, no hand-copied parameter table in the docstring.
- Output → `<domain>/<Archive stem>/` (for an inventory snapshot: `Inventory/Inventories-<NN>/`), plus a
  `_<Name>.md` directory page (the `_` prefix keeps it out of `.base` queries) holding source, archive
  sha256, the table list with per-table row counts, the JSON structure, the regeneration command, the
  exclusions, the remainder's location, and any job left open. Write the regeneration command in a form
  that still runs once the converter is gone: `git show <commit>:<path> > /tmp/<name>.py`, then run it.
- Link the new page from the domain index note in the same pass.
- Heavy remainder → outside the vault tree and on a durable volume (never a home or system temp dir),
  with a `_source.txt` stub beside it; report files, dirs and bytes.
- Commit once, subject in the repo's own convention (`feat(<scope>): …` with a Chinese subject here).

## 6. Pitfalls

- **`read_only=True` does not resolve hyperlinks**: a cell whose display text comes from a hyperlink
  reads as `None`, silently, and drops out of the conversion. Read conversion workbooks with
  `load_workbook(path_or_buffer, data_only=True)`. (Same trap recorded in `spreadsheet-to-dolt-mirror`.)
- **Not every `.xlsx`/`.csv` in the archive is a ledger.** Pipeline `output.csv`, dimer score csvs and
  summary sheets are experiment output; enumerate them, convert the named subset, and list the
  exclusions in both the manifest and the directory page.
- **`git rm` + commit does not shrink `.git`** — the blob stays reachable from the older commit.
  Only a history rewrite (e.g. `git filter-repo`) removes it, and it changes every commit hash: a
  separate, explicitly agreed step (§7). Until it is run, say so plainly with before/after numbers.
  The keep-history-instead route is also valid and has been chosen before: delete the artifact going
  forward and document `git show <commit>:<path>` as the way to get the old version back.
- **Delivering the conversion without the cell-by-cell diff** turns a result into a claim; the user
  reads the numbers, so produce them.

## 7. Removing the blob from history (agreed, then executed)

`git filter-repo` on a **non-bare** repo does not only rewrite refs: its `cleanup()` ends with
`git reset --hard`, `git reflog expire --expire=now --all` and `git gc --prune=now`. Read `cleanup()`
and the call site in the installed script (`grep -n 'reset --hard' $(which git-filter-repo)`) before
trusting any summary, this one included. Consequences: the artifact just removed from history is
**deleted from the working tree**, the reflog is emptied (no undo), and whatever the user had
uncommitted is reverted. It also refuses to run on a repo that is not a fresh clone — a repo with no
remote counts as not-fresh — unless `--force` is passed.

### Pre-flight

```bash
git remote -v                       # expect empty: nothing to force-push afterwards
git status --short                  # note what the user has pending; you will restore it
git ls-files | wc -l                # baseline for the "only the artifact went" check
git rev-parse HEAD:<path>           # blob id, to prove it unreachable afterwards
du -sh .git
git clone --mirror --local . <durable>/<project>-pre-filterrepo.git   # hardlinked, instant
git -C <durable>/<project>-pre-filterrepo.git cat-file -s <blob>      # prove the mirror holds it
```

The mirror insures the rewrite itself. Being hardlinked it is nearly free at creation, but it costs
the full blob once the original's objects are pruned — budget that, and delete it after the checks
pass unless the user wants a pre-rewrite snapshot. Put it on a durable volume: a mirror written into
`/Users/<user>/Temp` was gone before it was needed.

### Run

```bash
mv <path> <outside-the-worktree>     # same volume ⇒ instant; protects it from reset --hard
git filter-repo --force --invert-paths --path <path>
mv <outside-the-worktree> <path>     # untracked now; put it back if it should stay
```

### Post-checks — `scripts/verify_blob_purge.sh <path>` runs these; quote the numbers

| check | expected |
|---|---|
| `du -sh .git` | drops by roughly the blob size |
| `git log --all --oneline -- <path>` | empty |
| `git rev-list --objects --all \| grep -c <basename>` | `0` |
| `git cat-file -s <old blob id>` | `fatal: … could not get object info` |
| `git rev-list --count HEAD` | old count + the commits added since |
| `git ls-files \| wc -l` | baseline − one per removed path |
| `git fsck --no-progress` | silent |
| tracked-file counts per key directory | unchanged apart from the artifact |
| the artifact on disk | present, sha256 equal to the manifest's recorded value |
| `git reflog` | 0 lines — state it out loud, it is the removed undo |

No single one of these proves the intent; the report carries all of them, before and after.

### Repair what the rewrite invalidated

1. **Every commit hash quoted in the repo's own documents now dangles.** Grep the tree for them (short
   hex and `git show <hash>:` forms, ignoring frontmatter UUIDs and archive ids), map each to its new
   hash, and rewrite the reference in the same pass. Verify the replacement resolves *and* is the right
   object: `git show <new>:<path> | wc -c` plus `file` on the extracted bytes. A README instructing a
   future session to `git show <old hash>:<file>` against a rewritten repo is worse than silence.
2. **Restore the user's pending state.** The `reset --hard` reverted their uncommitted deletion or
   edit; re-apply exactly that and leave it uncommitted. Never commit their work-in-progress as part
   of your housekeeping commit.
3. **Add the heavy directory to `.gitignore` in the same pass** (a vault had `Data` but not `Backup`).
   An ignore rule cannot untrack an existing file, but it stops the next one.
4. **Commit the doc and ignore-rule repairs separately**, and record the rewrite in the directory page
   with the old→new hash mapping and the measured `.git` delta, so the next session does not read the
   missing hashes as corruption.
