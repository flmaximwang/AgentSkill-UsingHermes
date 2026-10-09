---
name: zotero-mcp
description: Configure, extend, or troubleshoot the Zotero MCP server — local-only mode, connector API, write workarounds, and routine operations.
---

# Zotero MCP

> Use this skill whenever Zotero MCP tools (`zotero_add_by_*`, `zotero_search_*`, etc.) are invoked, when a write to Zotero fails in local-only mode, or when asked to set up or debug the Zotero MCP connection.

## Setup

The server is configured in `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  zotero-mcp:
    command: /Applications/ZoteroMCP/.env/bin/zotero-mcp
    env:
      ZOTERO_LOCAL: 'true'
    enabled: true
```

Zotero desktop **must be running** for the connector API to respond. Check with:

```bash
pgrep -il "zotero"
```

Multiple `zotero-mcp` server instances can accumulate — this is normal; each Hermes session spawns its own.

## Local-Only Mode: Write Operations

When `ZOTERO_LOCAL: 'true'` (no `ZOTERO_API_KEY` configured), the standard MCP write tools (`zotero_add_by_doi`, `zotero_add_by_bibtex`, `zotero_add_from_file`, `zotero_create_collection`, etc.) **all fail** with:

> Cannot perform write operations in local-only mode. Add ZOTERO_API_KEY and ZOTERO_LIBRARY_ID to enable hybrid mode.

**Workaround**: POST directly to Zotero desktop's local connector API (`http://127.0.0.1:23119/connector/saveItems`). This bypasses the MCP layer and writes to the local SQLite database via the running Zotero desktop.

### Adding an Item by DOI

```bash
curl -X POST "http://127.0.0.1:23119/connector/saveItems" \
  -H "Content-Type: application/json" \
  -H "Zotero-Connector-API-Version: 3" \
  -d '{
    "items": [
      {
        "itemType": "journalArticle",
        "title": "Fabrication of Electronically Conductive Protein-Heme Nanowires for Power Harvesting",
        "creators": [
          {"firstName": "Lorenzo", "lastName": "Travaglini", "creatorType": "author"}
        ],
        "date": "2024",
        "DOI": "10.1002/smll.202311661",
        "publicationTitle": "Small",
        "volume": "20",
        "pages": "2311661",
        "url": "https://onlinelibrary.wiley.com/doi/10.1002/smll.202311661"
      }
    ]
  }'
```

Returns **201 Created** on success. The response body is empty.

### Item JSON Fields

| Item Type | Required Fields |
|-----------|----------------|
| `journalArticle` | title, creators[], date, DOI (or publicationTitle + volume + pages) |
| `book` | title, creators[], date, ISBN, publisher |
| `webpage` | title, url, date |
| `preprint` | title, creators[], date, DOI, repository |

`creators[]` entries need `firstName`, `lastName`, and `creatorType` (e.g. `"author"`, `"editor"`, `"translator"`).

## Post-Add Workflow

1. Verify the item landed:
   `zotero_search_items(query='Author Year')` or `zotero_search_by_citation_key(citekey='...')`

2. Update the semantic search database so the new item is findable:
   `zotero_update_search_database()`

3. Optionally file into a collection:
   `zotero_manage_collections(item_keys=['...'], add_to=['COLLECTION_KEY'])`

## Read Operations (work in local mode)

All `zotero_search_*`, `zotero_get_*`, and `zotero_list_*` tools work fine in local-only mode — only writes are blocked at the MCP level.

## Literature Methodology Tracing

For tracing the evolution of a research group's methodology across multiple publications (e.g., "how did Baker Lab's symmetric design approach develop?"), see `references/literature-methodology-tracing.md`. Key pattern: use Zotero search + web_search to distinguish related but distinct techniques at different layers (backbone generation vs. docking vs. sequence design), and expect user corrections on scope boundaries.

## Search Query Strategy

Zotero's `zotero_search_items` uses **substring matching** on metadata (title, creators, year). Each extra word NARROWS the match, so long multi-word queries often return zero results even when the paper is in the library.

**Correct approach — keep queries SHORT:**
- `'Author Year'` → `'Fallas 2017'` ✓
- `'Author keyword'` → `'Andre docking'` ✓
- Avoid full titles or long topic phrases — they over-constrain the substring search.

When the user says "all of them are there" after you failed to find papers, the query was too long/narrow. Trim to surname + year or surname + distinctive keyword and retry.

For topic discovery (not known papers), use `zotero_semantic_search` instead — it uses embeddings and handles natural-language queries.

## SVG Timeline Paper Extraction

When a presentation project (Beamer) uses SVG timeline diagrams, paper references are embedded as `<text>` elements in readable SVG XML. **Do NOT set up OCR** — grep or `read_file` the SVG directly and extract `<text>` content. Works for Inkscape-created timeline SVGs. Example patterns to search for:
- `inkscape:label="Author Year"` — box label annotations
- `<text ...>Author et al. (Year)</text>` — the actual citation text

## Pitfalls

- Zotero desktop **and** the MCP server must both be running. The connector API (`:23119`) is served by Zotero desktop itself, not by the MCP server.
- The endpoint is `/connector/saveItems` — **case-sensitive**. `saveitems` or `SaveItems` returns 404.
- The header `Zotero-Connector-API-Version: 3` is required. Without it the request may silently fail or return 404.
- Only one item array entry per call is safest — batch submissions may partially fail with no error feedback.
- The connector API does **not** auto-resolve DOIs to rich metadata like `zotero_add_by_doi` does. You must supply all fields (title, creators, journal, etc.) yourself, or fetch them from CrossRef first.
- After adding many items, run `zotero_update_search_database()` to rebuild the semantic index.
- If `curl` fails with "Connection refused", Zotero desktop is not running — launch it first.
