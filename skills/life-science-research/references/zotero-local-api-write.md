# Zotero Local API: Adding Items Without API Key

When `zotero-mcp` is configured in **local-only mode** (`ZOTERO_LOCAL: 'true'` in config), the `zotero_add_by_*` MCP tools (doi, url, bibtex, csl_json, from_file) fail with:
> "Cannot perform write operations in local-only mode. Add ZOTERO_API_KEY and ZOTERO_LIBRARY_ID to enable hybrid mode."

The Zotero desktop app (when running) exposes a **connector API** on `http://127.0.0.1:23119` that accepts write operations directly.

## Workaround: POST to `/connector/saveItems`

```bash
curl -X POST "http://127.0.0.1:23119/connector/saveItems" \
  -H "Content-Type: application/json" \
  -H "Zotero-Connector-API-Version: 3" \
  -d '{
    "items": [
      {
        "itemType": "journalArticle",
        "title": "...",
        "creators": [
          {"firstName": "First", "lastName": "Author", "creatorType": "author"}
        ],
        "date": "2024",
        "DOI": "10.1002/example.12345",
        "publicationTitle": "Journal Name",
        "volume": "20",
        "pages": "123-145",
        "url": "https://..."
      }
    ]
  }'
```

Returns `201 Created` with empty body on success.

## Verification

After adding, search Zotero to confirm:
```python
# Via MCP tool
zotero_search_items(query='Author Year topic')
```

Then run `zotero_update_search_database()` to make the new item searchable semantically.

## Notes

- The connector API endpoint `/connector/saveItems` is NOT the same as Zotero's full REST API (`/api/items/` etc.) — that endpoint is not served locally
- Item JSON format matches the Zotero connector translation-server format
- Only basic fields (title, creators, DOI, date, publicationTitle, volume, pages, url) are accepted in this format — tags and collections aren't passed via this simple payload
- Zotero desktop must be running (`Zotero.app`) for port 23119 to be active
- The `X-Zotero-Connector-API-Version: 3` header is required
- `itemType` values follow Zotero's vocabulary (e.g. `journalArticle`, `book`, `preprint`, `webpage`)

## Dead End: pyzotero Local Client

Python's `zotero_mcp.client.get_local_zotero_client()` returns a `pyzotero.Zotero` instance, but **write operations fail** with 404 errors:

```python
from zotero_mcp.client import get_local_zotero_client
client = get_local_zotero_client()
template = client.item_template('journalArticle')
# → httpx.HTTPStatusError: 404 for http://localhost:23119/api/items/new?itemType=...
```

**Why**: The local connector at `localhost:23119` only serves `/connector/` endpoints. The full Zotero REST API (`/api/items/...`, `/api/items/new`, `/api/items?itemKey=...`) is a web-only API that the local connector does not implement. pyzotero assumes the full REST API exists, so it fails immediately on any write-related or template-request call.

Use the `/connector/saveItems` curl approach above instead, or configure `ZOTERO_API_KEY` + `ZOTERO_LIBRARY_ID` in the MCP config for hybrid mode.
