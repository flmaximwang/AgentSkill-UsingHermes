# Power Query M error → root cause → fix

Real debugging transcript from collecting UID columns across 3 Excel stock tables
(ProteinStocks, PlasmidStocks, BacterialStocks) with duplicate detection + text sort.

## Error table
| Error (Chinese shown; English equivalent) | Root cause | Fix |
|---|---|---|
| `导入 ProteinStocks 没有匹配的导出。是否缺少模块引用?` (no matching export / module reference) | Bare-name reference to a table that is NOT loaded as a Power Query query (it's just an Excel Table; other tables happened to be loaded so their bare names worked) | `Excel.CurrentWorkbook(){[Name="ProteinStocks"]}[Content]`, or load the table as a query (Data → From Table/Range) |
| `找不到记录的字段 "Data"` (Field 'Data' not found) | `[Data]` is the field of `Excel.Workbook()` (external file); `Excel.CurrentWorkbook()` uses `[Content]` | Swap to `[Content]` |
| `联接操作不能导致生成具有重复列名("UID")的表` (join would produce duplicate column names) | `Table.Join` merges ALL columns from both tables; both sides had a "UID" column | Rename one side before join: `Table.RenameColumns(Counts, {{"UID","UID_Key"}})`, join on the new key, drop temp column at end |
| `无法将运算符 < 应用于类型 List 和 List` (cannot apply < to List and List) | `Table.FromList(list, Splitter.SplitByNothing(), {"A","B"})` is a single-column splitter — the WHOLE `{A,B}` pair lands in column A as a List, so `Table.Sort` compares List values | Use `Table.FromRows(list, {"A","B"})` for multi-column rows |
| Sorting looks wrong (`0826HQ01` before `0826FP31`) | `Table.Join` reorders left-table rows; the sort itself was correct (verified in isolation) | Eliminate join (Table.ToRecords + AddColumn lookup) or AddIndexColumn → join → Sort by index |

## Key API facts
- `Excel.CurrentWorkbook()` rows have fields: Name, Item, Kind, Hidden, Content. Table data lives in `[Content]`.
- `Excel.Workbook(File.Contents("path"))` sheet/table data lives in `[Data]`.
- `Table.FromList(list, Splitter.SplitByNothing(), cols)` = single column only; `Table.FromRows(list, cols)` = multi-column from list-of-lists.
- `Table.Join` output order is NOT guaranteed — never rely on left-table order after a join.
- Text sort is lexicographic (culture-independent): `F < H` so `0826FP*` all precede `0826HQ*`; also `"10" < "2"`.

## Diagnostic snippets (run in a scratch query)
- List every available table/defined-name:
  ```m
  let X = Excel.CurrentWorkbook() in X
  ```
- Inspect the record fields of one name (confirms Content vs Data):
  ```m
  let R = Excel.CurrentWorkbook(){[Name="ProteinStocks"]}, F = Record.FieldNames(R) in F
  ```
- Hidden-character probe (codepoints + length; Len > 8 ⇒ leading/trailing space, first codepoint 32 = space):
  ```m
  let
      T = Table.FromList({"0826FP31","0826HQ01"}, Splitter.SplitByNothing(), {"UID"}),
      Codes = Table.AddColumn(T, "CharCodes", each List.Transform(Text.ToList(Text.From([UID])), (c) => Character.ToNumber(c))),
      Final = Table.AddColumn(Codes, "Len", each Text.Length(Text.From([UID])), Int64.Type)
  in Final
  ```
- Source-tagged merge across tables (mirrors the production query's full data flow):
  ```m
  All = List.Combine({
      List.Zip({UIDsA, List.Repeat({"TableA"}, List.Count(UIDsA))}),
      List.Zip({UIDsB, List.Repeat({"TableB"}, List.Count(UIDsB))})
  }),
  Tbl = Table.FromRows(All, {"UID","Source"})
  ```
