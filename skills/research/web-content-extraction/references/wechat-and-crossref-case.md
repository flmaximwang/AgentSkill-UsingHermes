# Session Reference: WeChat Article + Paywalled Paper Extraction

> Extracted from session 2026-07-11: reading an Angew. Chem. VIP paper promoted on WeChat.

## Target URLs

| URL | Type | Access result |
|-----|------|--------------|
| `https://mp.weixin.qq.com/s/X9LMrJdJvumW63VUFJo-9w` | WeChat 公众号 (遇见生物合成) | web_extract blocked (private/internal), browser OK but truncated, curl + HTML parsing succeeded |
| `https://onlinelibrary.wiley.com/doi/10.1002/anie.202521406` | Angew. Chem. Int. Ed. (VIP) | Cloudflare blocked all tools |
| `https://doi.org/10.1002/ange.1402106` | German edition (same paper) | Same Cloudflare block |

## Paper Details (from CrossRef)

- **Title**: Machine-Learning-Enabled Rapid Evolution of Photoenzymes for the Asymmetric Synthesis of *gem*-Difluorophosphonates
- **Authors**: Hongkui Wang, Jiafan Xu, Jiahai Zhou (周佳海), Yang Gu (古阳)
- **Journal**: Angew. Chem. Int. Ed. (VIP), published 2026-07-07
- **DOI**: 10.1002/anie.202521406 (Int. Ed.) / 10.1002/ange.1402106 (German ed.)
- **CrossRef query used**: `Machine-Learning-Enabled+Rapid+Evolution+of+Photoenzymes+gem-Difluorophosphonates`

## WeChat Article Extraction Code (reusable snippet)

```python
from hermes_tools import terminal

result = terminal("""
curl -s -L \\
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \\
  "https://mp.weixin.qq.com/s/X9LMrJdJvumW63VUFJo-9w" | \\
  python3 -c "
import sys, re, html
content = sys.stdin.read()
match = re.search(r'id=\"js_content\"[^>]*>(.*?)</div>\\s*<script', content, re.DOTALL)
if match:
    text = match.group(1)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\\s+', ' ', text)
    print(text[:15000])
"
""", timeout=30)
```

## CrossRef Query Code (reusable snippet)

```python
from hermes_tools import terminal

result = terminal("""
curl -s "https://api.crossref.org/works?query=Machine-Learning-Enabled+Rapid+Evolution+of+Photoenzymes+gem-Difluorophosphonates&rows=1" | \\
  python3 -c "
import sys, json, re
data = json.load(sys.stdin)
items = data.get('message', {}).get('items', [])
if items:
    item = items[0]
    print('Title:', item.get('title', [''])[0])
    print('DOI:', item.get('DOI', ''))
    print('Authors:', ', '.join([a.get('family', '') + ' ' + (a.get('given', '') or '') for a in item.get('author', [])]))
    print('Journal:', item.get('container-title', [''])[0])
    print('Published:', item.get('published-print', {}).get('date-parts', item.get('published-online', {}).get('date-parts', [])))
    abstract = item.get('abstract', '')
    if abstract:
        abstract_clean = re.sub(r'<[^>]+>', '', abstract)
        print('ABSTRACT:', abstract_clean[:3000])
"
""", timeout=15)
```

## Key Takeaway for Future Sessions

This pattern (WeChat science article → linked paper) is common for Chinese-language science dissemination. The full workflow:

1. Extract WeChat article via curl HTML parsing (detailed enough for most summary needs)
2. Get paper title/authors from WeChat article
3. Query CrossRef for DOI + abstract
4. Compose Obsidian note from both sources combined
