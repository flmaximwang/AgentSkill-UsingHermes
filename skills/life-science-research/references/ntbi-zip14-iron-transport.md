# Mammalian NTBI Transport: ZIP14 & Fe³⁺-Citrate (FAC) Uptake Mechanism

Condensed domain knowledge from literature review (Liuzzi 2006, Pinilla-Tenas 2011, Girijashanker 2008, Trinder 1998, Knutson 2019, Kosman 2020).

## Key Finding: Fe³⁺ Must Be Reduced to Fe²⁺ Before Transport

**No known mammalian transporter carries Fe³⁺ directly across the plasma membrane.** The consensus is that all NTBI uptake requires prior reduction.

Fe³⁺-citrate (the form of iron in ferric ammonium citrate, FAC) → membrane-bound ferrireductase → Fe²⁺ → ZIP14/ZIP8/DMT1 transport.

## Ferrireductases (Fe³⁺ → Fe²⁺)
- **STEAP2** (broad tissue, incl. neurons)
- **STEAP3** (erythroid cells, endosomal)
- **DCYTB/Cybrd1** (duodenal enterocytes)
- **PrP^C** (prion protein, neurons/liver — Tripathi 2015)

## ZIP14 (SLC39A14) — Primary NTBI Transporter
| Property | Detail |
|----------|--------|
| Substrate | Fe²⁺ (NOT Fe³⁺) |
| Mechanism | Metal/HCO₃⁻ symporter |
| Km for Fe²⁺ | ≈ 2 µM |
| pH-sensitive | Yes |
| Ca²⁺-dependent | Yes |
| Also transports | Zn²⁺, Mn²⁺, Cd²⁺ |
| Expression | Liver > duodenum > kidney > brain |

## Citrate Fate: Left Behind
Dual-label experiments (⁵⁹Fe + [¹⁴C]citrate, Trinder & Morgan 1998, PMID 9688655) show iron accumulates continuously while citrate uptake plateaus — **citrate is NOT co-transported with Fe**.

## Key Papers

| PMID | Authors | Year | Title | Key Evidence |
|------|---------|------|-------|-------------|
| 16950869 | Liuzzi et al. | 2006 | Zip14 mediates NTBI uptake into cells | BPS (Fe²⁺ chelator) blocks ZIP14 Fe uptake from ferric citrate |
| 21653899 | Pinilla-Tenas et al. | 2011 | Zip14 functional properties | **ZIP14 transports Fe²⁺ only** (ascorbate-dependent, NTA-inactive) |
| 18270315 | Girijashanker et al. | 2008 | Slc39a14 encodes ZIP14, metal/bicarbonate symporter | HCO₃⁻ dependence, splice variants ZIP14A/B |
| 9688655 | Trinder & Morgan | 1998 | Ferric citrate uptake by hepatoma cells | Fe reduced to Fe²⁺ before transport; citrate stays out |
| 25862412 | Tripathi et al. | 2015 | PrP^C as ferrireductase partner for ZIP14/DMT1 | PrP^C knockout mice have reduced NTBI liver uptake |
| 30316781 | Knutson | 2019 | NTBI transporters (review) | All known NTBI transporters carry Fe²⁺ |
| 32766655 | Kosman | 2020 | Holistic view of mammalian Fe uptake | PMET + ZIP pathway for NTBI |

## Search Strategy for PubMed (curl via proxy)
When web_search fails (SSL errors):
```bash
PROXY="-x http://127.0.0.1:7890"
# Search: keep terms flat (MeSH expansion chokes on deep nesting)
curl -s --connect-timeout 10 $PROXY \
  "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=ZIP14+Slc39a14+iron+uptake&retmax=20&retmode=json"
# Fetch abstracts
curl -s --connect-timeout 10 $PROXY \
  "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=16950869,21653899&rettype=abstract&retmode=xml"
```

## Common Pitfalls when Searching This Topic
- "Fe³⁺-citrate transport" yields mostly bacterial literature (FecA in E. coli)
- "NTBI" + "ZIP14" yields mammalian hepatocyte/cardiac papers
- FAC (ferric ammonium citrate) is widely used as a lab reagent to model iron overload but its cellular uptake mechanism is the same as Fe³⁺-citrate
