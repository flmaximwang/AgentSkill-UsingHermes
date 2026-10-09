---
name: power-query-m
description: Use when writing/debugging Power Query M (Excel) formulas.
---

# Power Query M (Excel)

Write and debug Power Query M formulas for collecting/merging/sorting/flagging data across Excel tables (e.g. lab stock tables: ProteinStocks, PlasmidStocks, BacterialStocks; collect all UID columns, detect duplicates, sort).

## Referencing tables
- A table only works as a bare name (`Table.Column(ProteinStocks, "UID")`) if it has been loaded as a Power Query **query** (visible in the left Queries pane). Plain Excel tables that were never loaded error with: `导入 X 没有匹配的导出 / no matching export`.
- Reference workbook tables by name instead:
  `Excel.CurrentWorkbook(){[Name="ProteinStocks"]}[Content]`
- ⚠️ FIELD NAMES: `Excel.CurrentWorkbook()` → `[Content]`. `[Data]` belongs to `Excel.Workbook(...)` (external files). Mixing them gives `找不到记录的字段 "Data" / Field 'Data' not found`.
- List available names first: run `Excel.CurrentWorkbook()` and read the `Name` column.

## Combining & sorting
- Concatenate column lists then convert: `All = A & B & C`, `Table.FromList(All, Splitter.SplitByNothing(), {"UID"})`.
- `Table.FromList` + `Splitter.SplitByNothing()` is **single-column only**. For multi-column rows use `Table.FromRows(list_of_pairs, {"UID","Source"})` — otherwise the whole row list lands in one cell and sorting later fails with `无法将运算符 < 应用于类型 List 和 List`.
- Text sort is lexicographic: `0826FP` < `0826HQ` (F<H ✓) but also `10` < `2`. Expected behavior, not a bug.

## Duplicate detection WITHOUT reordering
- `Table.Join` does **NOT** preserve the left table's row order. Symptom: output looks unsorted even though you sorted first.
- Don't join for lookups — grouped count + record lookup keeps row order 100%:
  ```m
  Counts = Table.Group(Sorted, {"UID"}, {{"Count", each Table.RowCount(_), Int64.Type}}),
  Lookup = Table.ToRecords(Counts),
  Result = Table.AddColumn(Sorted, "Duplicate?",
               each let myU = [UID] in
                    if (List.First(List.Where(Lookup, (r) => r[UID] = myU)))[Count] > 1
                    then "YES" else "", type text)
  ```
- If you MUST join: `Table.AddIndexColumn` → join → `Table.Sort` back by index → drop the index.
- `Table.Join` errors `联接操作不能导致生成具有重复列名的表` when both sides share a column name → rename one side first (`Table.RenameColumns(Counts, {{"UID","UID_Key"}})`) and drop the temp column at the end.
- Nested `each` shadow `_`: bind the outer row's field to a variable (`let myU = [UID]`) before an inner `each` / `List.Where`, or use an explicit `(r) =>` lambda.

## Empty tables / nulls
- Empty table (0 rows, column present) flows through cleanly end-to-end: `Table.Column` returns `{}`, concatenation skips it, group/join/sort handle it. Errors only if the COLUMN is missing, or the upstream QUERY itself failed (that's an error value, not an empty table).
- Blank cells → `null` in M (sorts first, groups as one bucket). Empty string `""` is a real text value. Filter with `Table.SelectRows(T, each [UID] <> null and [UID] <> "")`.

## Debugging "wrong sort order"
1. Replicate the FULL data flow of the production query (ALL source tables, same concat order) — never diagnose on a one-source subset; cross-table bugs won't reproduce.
2. Test sort in isolation (no join). If correct, the join is reordering rows.
3. Check hidden characters: `Len = Text.Length(...)` (> expected ⇒ leading/trailing space) and `List.Transform(Text.ToList(...), Character.ToNumber)` for codepoints (leading 32 = space).
4. Tag rows with source: `List.Zip({Values, List.Repeat({"SourceName"}, List.Count(Values))})` then `List.Combine`.

## References
- references/debugging-m-errors.md — error message → root cause → fix table plus diagnostic snippets from a real session.
