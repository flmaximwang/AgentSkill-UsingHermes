# NCBI E-utilities via curl (Fallback Pattern)

For use with the `ncbi-entrez-skill` sub-skill. When `web_search` is unavailable (SSL errors, timeout, or proxy issues), use `curl` directly against the NCBI E-utilities API. This is faster than the browser and works well through the 127.0.0.1:7890 proxy.

## Proxy setup

```bash
PROXY="-x http://127.0.0.1:7890"
```

## ESearch — find PMIDs

```bash
curl -s --connect-timeout 10 $PROXY \
  "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=ZIP14+Slc39a14+iron+uptake&retmax=20&retmode=json"
```

Key params: `db`, `term`, `retmax`, `retmode=json`

## EFetch — get abstracts

```bash
curl -s --connect-timeout 10 $PROXY \
  "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=16950869,21653899,18270315&rettype=abstract&retmode=xml"
```

Quick extraction from XML:
```bash
... | grep -E '(ArticleTitle|AbstractText)' | head -80
```

## Pitfalls

- **Complex queries yield 0 results** — MeSH auto-expansion chokes on deep nesting. Keep queries flat: `ZIP14+AND+Slc39a14+AND+iron+uptake`.
- **Timeout on large sets** — keep `retmax` ≤ 20.
- **Drug/compound names** — try `SupplementaryConcept` field if `[All Fields]` fails: `"ferric+ammonium+citrate"[Supplementary Concept]`

## When to use this vs the ncbi_entrez.py script

| Situation | Tool |
|-----------|------|
| Quick lookup, 1-3 queries | curl (this ref) |
| Complex pipeline, saving output | `scripts/ncbi_entrez.py` |
| web_search is down (SSL/proxy) | **curl** (proven fallback) |

## Session trace

This approach worked in a session where `web_search` failed with `SSL: UNEXPECTED_EOF_WHILE_READING`. PubMed via proxy succeeded. Used to answer a mechanism question about ZIP14-mediated Fe³⁺-citrate transport — cross-referenced Liuzzi 2006, Pinilla-Tenas 2011, Girijashanker 2008.
