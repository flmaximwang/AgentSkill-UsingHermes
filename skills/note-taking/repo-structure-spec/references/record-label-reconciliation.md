# Reconciling record ids against the sample ledger

The task arrives as part of a project pass: 整理 <project> 仓库 / 把记录里提到的所有样品与产物追进 stock.
The records are the historical fact, the ledger holds the authoritative keys — unlike a plain rename,
here the two sides disagree on **identifiers**, and both sides get edited.

## Classify before touching anything

| class | looks like | action |
|---|---|---|
| in ledger | exact `stock_uid` hit (typo or not) | none |
| should be in ledger | prefix typo (`PL`↔`PR`, `PP`/`PT`→`PR`), legacy date-code spelling (design code + backbone + batch + custodian), a design code used where a uid belongs | add as alias + correct the record + trace block |
| different batch | record says `-02`, ledger holds only `-01` | **give it its own row** (position unknown); record id unchanged |
| unresolvable | bare construct code, no batch/suffix | mark position-unknown, no alias, record it in the generator |
| not a ledger id | design codes, purification batch numbers, data-archive numbers, placeholder codes, another project's ids | leave alone |

Report the classes (and one fact per row: which record, which line). "Not in the library" must not be
reported as one flat gap list.

## Steps

1. **Extract** — one pass per record is fine for a handful; for a whole project fan out subagents, one
   batch of records each, each writing a JSON file (`{batch, records[], ids[{id, kind, mentioned_in[],
   in_stock, stock_row|note}]}`). The parent merges and de-duplicates, and **re-tests every negative
   finding in the library** (`WHERE stock_uid LIKE '…%'`) before using it — a subagent's summary is a
   self-report and a fabricated "not in stock" sends you off to rewrite good records.
2. **Converge on the ledger side by changing the generator, never by hand-editing the library** —
   `ALIASES = {correct uid: [historical spellings…]}` plus `ALIAS_UNRESOLVED`; an `aliases` column on the
   stock tables (and on entity tables — a construct code belongs there, not on a tube); a reverse-lookup
   view (uid → aliases, one row per uid) so the mapping is inspectable; re-run the whole `build.sql`
   (self-dropping) and commit.
   **Check the batch number before writing each alias**: `-02` inside `-01`'s alias list is the bug this
   whole rule exists to prevent. Merging two spellings is allowed only for the same entity **and** the
   same batch, with the evidence named.
3. **A position column, not a position guess** — give the unified stock view
   `location_status = IF(box IS NULL, '存储位置未知', <box_row_col>)` and count it in `checks`. In a project
   with no box data at all this equals the tube count: that is a *stated convention*, not a data error.
4. **Rewrite the records** — body id → the correct key; append the trace block
   `> [!note] 台账校正留痕（YYYY-MM-DD）` naming the old spelling, the target key and the reason
   (typo / design code / batch). A record whose batch the ledger lacks keeps its own id and says
   position-unknown. Nothing is edited silently.
5. **Acceptance, per old spelling** (paste the real output, not "done"):

```bash
dolt --host 127.0.0.1 --port <P> --no-tls sql -q \
  "USE <db>; SELECT stock_uid, stock_kind FROM v_stock_all WHERE aliases LIKE '%<old spelling>%';"
```

expected: every old spelling lands on its target uid, no cross-batch entry remains, the alias view's
row count equals the expected number of aliases, and a content search over the records
(`search_files` for the old spelling) hits the trace block only.

## Where the evidence lives

- **A project whose ledger was never in a spreadsheet still has a source**: its Feishu export
  `Backup/飞书多维表格/常规实验管理-<NN>.base` is a `gzipSnapshot` — decompress the trailing block → JSON
  (`tables` at the top level, one entry per table in the observed instance). The purification / protein
  inventory / plate-memo / transformation tables carry the `purification-id`, `material`, `product` and
  batch fields that the records' frontmatter mirrors; only matching those row by row justifies calling a
  tube's origin known.
- **Ids → entities**: design code → plasmid name → construct; the construct catalogues' binary files
  carry construct codes in their filenames, but only for the ones that exist as files. **Do not derive a
  construct name from a letter-group rule for the rest** — in the observed case the derivation disagreed
  with the code the record used, and the correct outcome was to leave that id unresolved rather than
  mint a name.
- **Batch judgement**: the trailing `-NN-<custodian>` segment; a `@2`-style suffix belongs to the design
  code, not to the batch.
