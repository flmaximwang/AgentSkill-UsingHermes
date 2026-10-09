# Recovering live URLs after a site restructure (Chinese institute sites)

Use when: a user reports that a URL you gave them 404s, or before handing any URL sourced from search results/cache to a user, to confirm it is actually live.

## Rule of thumb

`web_extract` succeeding on a URL does **not** mean the URL is currently live — the extractor can serve a cached/indexed copy while the live page returns 404. Only a curl status check against the exact URL proves it. Verify before delivering; re-verify against the LIVE site (not the search index) when a user reports a dead link.

## 1. Status-check loop

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
for u in "http://host/path" "https://host/path" "http://host/" ; do
  curl -s -o /dev/null -w "%{http_code}\n" -L -A "$UA" --max-time 25 "$u"
done
```

- `-L` follows redirects; always send a desktop UA (many CN sites reject default curl UA).
- `000` = connection failed / HTTPS not supported (these sites are often HTTP-only — do not treat as "site down" when the http:// variant returns 200).
- `404` on a detail page while the domain's `/` returns 200 ⇒ the site was restructured, not the page deleted.

## 2. Detect JS-redirect stubs

An index page may be a few-hundred-byte stub:

```html
<script>location.replace("./gk/");</script>
```

Fetch it to a file, check size (< ~1 KB) and grep for `location.replace`, then fetch the target directory.

## 3. Parse the real menu links

Save the HTML to a temp file first (avoids the curl|python pipe flag and lets you re-parse), then extract nav links:

```python
import re
html = open('/tmp/page.html', encoding='utf-8', errors='replace').read()
for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
    href, txt = m.group(1), ' '.join(re.sub(r'<[^>]+>', '', m.group(2)).split())
    if txt: print(txt, '=>', href)
```

Relative links (`../zpzyjspt/`) resolve against the current URL. Revamps rename path segments (e.g. `fxcsjspt` → `zpzyjspt`) — the detail pages survive at new paths; re-verify each with the status loop (expect 200).

## 4. Re-extract content from the LIVE page

Admin/contact tables survive a revamp as-is. Regex table extraction keeps cell structure that generic tag-stripping flattens:

```python
import re
html = open('/tmp/page.html', encoding='utf-8', errors='replace').read()
tbl = re.search(r'<table.*?</table>', html, re.S).group(0)
for r in re.findall(r'<tr[^>]*>(.*?)</tr>', tbl, re.S):
    cells = [' '.join(re.sub(r'<[^>]+>', ' ', c).split())
             for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)]
    print(' || '.join(cells))
```

## 5. Report

Give the corrected live URLs AND the cause (site revamp renamed the section path) — the user needs to know the old link was legitimately removed, not that you guessed wrong.

## Pitfall: don't re-search

When a delivered URL 404s, re-navigating the live site's menu finds the new path deterministically; a fresh web search returns the same stale index entries and the same dead links.
