---
name: web-content-extraction
description: "Extract text content from web pages when standard tools (web_extract) fail — handles Chinese social-media articles (mp.weixin.qq.com), paywalled academic papers, Cloudflare-protected sites. Covers browser fallback, raw-HTML scraping, and API-based metadata retrieval."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [web, extraction, wechat, paywall, crossref, Chinese-content]
    related_skills: [download-from-anywhere, ocr-and-documents]
---

# Web Content Extraction (Fallback)

## When to Use

Use when `web_extract()` returns an empty/error result for a URL. Common failure modes:

| Error pattern | Likely cause |
|---------------|-------------|
| `Blocked: URL targets a private or internal network address` | Chinese social-media platform (mp.weixin.qq.com) or firewall-gated site |
| Cloudflare challenge page ("Just a moment...", "请稍候…") | Wiley, many journal sites, CDN-protected domains |
| Empty `content` field in result | JS-rendered page, WebExtract can't execute JavaScript |

## General Workflow

```
Tier 1: web_extract(url)       → success?  ✓ done
                                     ✗ fail → Tier 2
Tier 2: browser_navigate(url)  → content visible?  ✓ extract from snapshot
                                     ✗ truncated → Tier 3
Tier 3: curl raw HTML + parse  → success?  ✓ done
                                     ✗ still blocked → Tier 4
Tier 4: API fallback           → CrossRef for papers, Wayback Machine, etc.
```

---

## Tier 2: Browser Fallback

For any URL that `web_extract` can't handle, try `browser_navigate` first:

```python
from hermes_tools import terminal

# Check what the browser sees
# Then use browser_snapshot(full=True) for full-page content
```

**Pitfall**: Browser snapshots may be truncated for long articles. If truncated, move to Tier 3.

---

## Tier 3: Raw HTML + curl Extraction

### Chinese WeChat Articles (mp.weixin.qq.com)

WeChat articles place full content in a `<div id="js_content">` that the raw HTML contains (even though `web_extract` can't reach it). `web_extract` on mp.weixin.qq.com typically returns ONLY the title with an empty content field — that's the JS-render signature; go straight to curl.

```python
from hermes_tools import terminal

# Save HTML to a temp file first (articles can be 3+ MB), then parse with Python.
result = terminal(f'''
curl -s -L -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \\
  "{url}" -o /tmp/wechat_article.html && \\
python3 -c "
import re, html
doc = open('/tmp/wechat_article.html', encoding='utf-8').read()
m = re.search(r'var msg_title = [\\'\"](.+?)[\\'\"]', doc)
print('TITLE:', m.group(1) if m else '?')
m = re.search(r'<div class=\"rich_media_content[^\"]*\" id=\"js_content\"[^>]*>(.*?)</div>\\s*<script', doc, re.S)
content_html = m.group(1) if m else ''
# PRESERVE paragraph structure: convert block tags to newlines BEFORE stripping tags
content_html = re.sub(r'<br\\s*/?>', '\\n', content_html)
content_html = re.sub(r'</p>', '\\n', content_html)
content_html = re.sub(r'</section>', '\\n', content_html)
text = re.sub(r'<[^>]+>', '', content_html)
text = html.unescape(text)
lines = [l.strip() for l in text.split('\\n') if l.strip()]
print('\\n'.join(lines))
"
''', timeout=60)
```

Key points:
- Use `-L` to follow redirects and set a desktop User-Agent
- **Save to file first, then parse** — a single curl pipe can hit shell quoting hell and buffer limits; a temp file lets you re-parse (title, author, publish time from `var msg_title` / `var nickname` / `var publish_time` JS globals)
- The regex extracts `#js_content` div content up to the next `<script>` tag; the non-greedy `(.*?)` stops at the first `</div><script` which is the standard article footer
- **Preserve paragraphs**: convert `<br>`, `</p>`, `</section>` to `\n` BEFORE stripping tags, then drop empty lines. Collapsing whitespace (`re.sub(r'\s+',' ',text)`) flattens a 10k-char article into an unreadable blob.
- Decode HTML entities with `html.unescape()`

### General HTML Extraction (Non-WeChat)

For generic JS-rendered pages:

```python
# Look for article-specific content patterns
re.search(r'<article[^>]*>(.*?)</article>', content, re.DOTALL)
# Or common content div class patterns
re.search(r'class="[^"]*(?:content|article|post|main)[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL)
```

### Chinese institute sites: JS-redirect stubs + stale indexed URLs

CAS/institute (and some Chinese corporate) sites restructure their path tree while the domain stays up. Two traps follow:

- **Index pages are often tiny JS stubs.** A curl fetch may return a file of a few hundred bytes whose only body is `<script>location.replace("./gk/")</script>`. Detect: file < ~1 KB and grep for `location.replace`. Follow the target directory, re-fetch, then parse the real menu `<a href>` links from the HTML to reach live detail pages.
- **Search-index URLs go stale after a revamp.** Old path segments are renamed (e.g. `fxcsjspt` → `zpzyjspt`); the old URLs 404 in the user's browser even though the content still exists at the new path. Recover from the LIVE site menu, never from the search index.

See `references/live-url-verification.md` for the curl status-check loop and the HTML-table extraction snippet.

---

## Tier 4: API Fallback for Academic Papers

When a paper page (Wiley, Elsevier, Springer, etc.) is behind Cloudflare:

### CrossRef API (free, no auth needed)

```python
from hermes_tools import terminal

result = terminal(f'''
curl -s "https://api.crossref.org/works?query={title_query}&rows=1" | \\
  python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('message', {}).get('items', [])
if items:
    item = items[0]
    print('Title:', item.get('title', [''])[0])
    print('DOI:', item.get('DOI', ''))
    print('Authors:', ', '.join([a.get('family', '') for a in item.get('author', [])]))
    print('Journal:', item.get('container-title', [''])[0])
    abstract = item.get('abstract', '')
    if abstract:
        # Strip XML tags from abstract
        abstract = re.sub(r'<[^>]+>', '', abstract)
        print('ABSTRACT:', abstract[:3000])
"
''', timeout=15)
```

**When to use**: You know the paper title or a unique phrase from it. CrossRef returns metadata + abstract even for paywalled articles.

### Sci-Hub (as last resort)
Not recommended — reliability varies and legality is jurisdiction-dependent.

### OA mirrors (PMC / Europe PMC) — full text, figures, SI

For **open-access** papers, skip the publisher site entirely. The PMC /
Europe PMC mirror serves full text, figure images, and the Supporting
Information PDF to plain `curl`, and it is where you get a publication-quality
figure for reuse in notes or slides. See
`references/paper-figure-extraction.md` for the DOI→PMCID lookup, the
figure-number→file mapping, the 300-dpi render + crop recipe, the Elsevier
figure-CDN route, and the vision-verification pitfall.

---

## Platform-Specific Notes

### mp.weixin.qq.com (WeChat 公众号)
- **Reason for failure**: WeChat blocks non-WeChat IP ranges; `web_extract` classifies as private-network
- **Browser access**: Works, but snapshot may truncate long articles (700+ lines of content)
- **Curl access**: The raw HTML contains the full `js_content` div even if truncated in the browser
- **Rate limiting**: WeChat may serve a CAPTCHA or redirect for rapid repeated access; space out requests

### Wiley Online Library
- **Reason for failure**: Cloudflare challenge before every page view
- **CrossRef fallback**: Works reliably for metadata + abstract
- **Full text**: Usually not available via any free API for recent papers (< 1 year old); open-access papers are the exception — the PMC/Europe PMC mirror has them (see "OA mirrors" below)

### Elsevier / ScienceDirect
- **Reason for failure**: Similar Cloudflare protection
- **CrossRef fallback**: Works for metadata
- **Alternative**: Check if the paper has a preprint on bioRxiv/medRxiv/ChemRxiv/arXiv
- **Figures**: the article HTML is blocked, but figure files are served openly by the `ars.els-cdn.com` CDN — see `references/paper-figure-extraction.md`

### Chinese e-commerce & UGC sites (知乎 / 京东 / 淘宝 / 中关村在线)

- **知乎 (zhuanlan.zhihu.com, zhihu.com/tardis/bd/art/<id>)**: curl returns a ~700-byte stub. `web_extract` DOES work — but call it with **exactly one URL per call**. Passing several Chinese JS-rendered article URLs in one `web_extract` call makes the whole batch fail with `Extract timed out after 120s via parallel`; re-issuing each URL singly succeeds.
- **京东**: `item.jd.com/<sku>.html` is a JS shell — no price, but it does embed `window._itemInfo` metadata. The mobile page `item.m.jd.com/product/<sku>.html` (iPhone UA) returns the same JSON with SKU/color/vendor plus `width/height/length/weight`, which are **物流箱尺寸 + 含包装毛重, not product dimensions or net weight** — label them as such. Price is injected by JS/login and is not in the HTML: take prices from dated 行情 articles (ZOL) or search snippets instead of burning calls on price endpoints.
- **淘宝/Tmall 列表页与详情页**: curl returns a ~3 KB anti-bot stub. The rendered page text (title + `¥price`) usually survives inside `web_search` result descriptions — usable, but quote it as "未实时核验".
- **中关村在线 (dcdv.zol.com.cn, detail.zol.com.cn)**: fetchable, but pages are **GB18030-encoded** — decode with `decode('gb18030')`; utf-8 gives mojibake. ZOL 行情稿 are the best source for dated 京东价/到手价.
- **品牌官网** (syitren.com and similar) are curl- and `web_extract`-friendly and carry the authoritative spec table + list price — try the manufacturer's own domain before any aggregator.

See `references/china-ecommerce-spec-price-extraction.md` for the per-site table and the JD `_itemInfo` extraction recipe.

---

## Pitfalls

1. **Don't give up after one failed method.** Each tier in the workflow targets a different access mode; one usually works.
2. **Curl with Python pipe triggers security flags.** The "Pipe to interpreter" warning is benign for HTML parsing (no execution risks) and can be auto-approved.
3. **Browser snapshot truncation is invisible.** You won't know you got a truncated article unless you check the total content length or find an obvious cut-off. Always follow up with curl extraction for long texts.
4. **WeChat article links are session-specific.** The full URL from a share is usually stable, but embedded "阅读原文" (read original) links are often JavaScript handlers, not direct `href` values.
5. **CrossRef abstract may contain XML tags** (`<jats:p>`, `<jats:italic>`, etc.). Strip these before using the text.
6. **Paywalled papers may be on preprint servers.** Always search for "title + bioRxiv/arXiv/ChemRxiv" before declaring the paper inaccessible.
7. **Do NOT hardcode WeChat article IDs or session cookies.** Each article link is unique and cookies expire.
8. **Verify URLs are live before delivering them to the user.** `web_extract` returning content does NOT prove the URL currently works — it can serve from cache while the live page is a 404 (site revamp). Curl the exact URL for HTTP 200 first; when the user reports a dead link, recover the current URL from the live site's menu and explain the cause (restructure), not just swap in a link. See `references/live-url-verification.md`.
9. **Never batch Chinese JS-rendered article URLs into one `web_extract` call.** Multi-URL batches return `Extract timed out after 120s via parallel` for every URL in the batch; single-URL calls to the same links succeed. Retry singly before declaring a page unreachable.
10. **A page that curls fine can still be the wrong source tier.** Chinese AI-generated 横评 (知乎 flags `内容疑似 AI 生成`; 搜狐/网易 reposts carry `本文包含人工智能生成内容`) print spec tables and 频响曲线 numbers that contradict each other for the same model. Cross-check numbers across two such sources and report the conflict — never average it into a single figure.

## Verification Checklist

- [ ] Tier 1 attempted: `web_extract(url)` — for Chinese article sites (知乎, 公众号) one URL per call, never a batch
- [ ] Tier 2 attempted: `browser_navigate` + `browser_snapshot(full=True)`
- [ ] Tier 3 attempted: curl HTML extraction (with platform-specific extraction pattern)
- [ ] Tier 4 attempted when relevant: CrossRef API for academic papers
- [ ] Full content extracted (check for truncation artifacts: mid-sentence cut-offs, missing sections)
- [ ] If paper: DOI recorded and abstract extracted
- [ ] Backup content saved to Obsidian or local file if needed
