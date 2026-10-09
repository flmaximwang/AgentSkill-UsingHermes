# Extracting publication-quality figures from papers

Goal: pull a clean, high-resolution figure out of a paper for reuse in notes
or slides — without OCR, and without fighting Cloudflare.

## Prefer OA mirrors over publisher sites

Publisher sites (Wiley, RSC, Elsevier, Springer) and ResearchGate sit behind
Cloudflare and return a "Just a moment…" HTML interstitial to `curl`. Do not
loop on them. Open-access mirrors serve the same figures and answer plain curl:

- PMC article HTML: `https://pmc.ncbi.nlm.nih.gov/articles/PMC<id>/`
- Europe PMC JATS XML (lists figure filenames): `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC<id>/fullTextXML`
- Europe PMC supplementary ZIP (SI PDF + figure images): `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC<id>/supplementaryFiles`

DOI → PMCID:
`https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:<doi>&format=json`
→ `resultList.result[].pmcid`.

## Elsevier / ScienceDirect: figures via the ARS CDN

ScienceDirect and Elsevier-hosted journals (incl. JBC on jbc.org) block `curl`
with the Cloudflare interstitial, but their **figure files** come from an open
CDN with no challenge. Build the URL from the article PII (the `1-s2.0-<PII>`
token in the ScienceDirect URL) plus the figure number:

```bash
# from https://www.sciencedirect.com/science/article/pii/S0021925818899070
curl -sL -H "Referer: https://www.sciencedirect.com/" \
  "https://ars.els-cdn.com/content/image/1-s2.0-<PII>-gr1_lrg.jpg" -o fig1.jpg
```

- `gr<N>` = Figure N. The paper's figure-caption list comes back as text from
  `web_extract` even when the images don't load — use it to confirm which
  `gr<N>` you want.
- Try `_lrg` FIRST: it is the high-resolution original (`...-gr1_lrg.jpg`,
  e.g. 1800×1666) versus the small bare name (`...-gr1.jpg`, 678×628).
- `-hires`, `_hires`, `-i600/-i900/-i1500` all 404 here — do not loop on them.

## Pick the right figure, not just any figure

A figure from a mechanism-focused paper covers only the sub-range that paper
cares about (an experiment starting at 380 nm yields a spectrum starting at
380 nm). When the user needs the *characteristic* or full-range figure for an
entity, go to its **original characterization paper** — the report that first
defined the entity — not to the newest paper that happens to plot it.

## Map figure number → file by the alt attribute, not the filename

Filenames are arbitrary (`g001` is not Figure 1). Read the `<img alt="Figure N">`
attribute in the PMC article HTML, and confirm against the figure's
`<figcaption>` text.

## Main-text blobs are often thumbnails — go to the SI PDF

PMC main-text figure blobs are frequently low resolution (e.g. 319×144). The
`?format=900w`, `-i1500`, `-hires` variants 404 — stop trying them. The
Supporting Information PDF usually holds the figure as a vector or a large
bitmap. `pdftotext` the SI to confirm which figure is on which page.

```bash
curl -sL "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC<id>/supplementaryFiles" -o si.zip
unzip -o si.zip -d si/
pdfimages -list si/*-s001.pdf          # embedded bitmaps: page, width, height, encoder
pdfimages -png  si/*-s001.pdf si/img   # extract bitmaps (skips VECTOR figures)
pdftoppm -r 300 -png -f 3 -l 3 si/*-s001.pdf page   # render page 3 for vector figures
magick page-3.png -crop 2390x1035+50+880 +repage fig.png
```

Iterate the crop on a small preview: `sips -Z 1000 fig.png --out view.png`.

## Verify the crop covers what was asked

After cropping, check the axis/coverage against the request, not just that the
image is legible. Cropping a panel that starts where the plot starts is not a
success if the user asked for the full range.

## Verify the figure — and don't be fooled by vision

- The vision tool fails to decode very large images and then answers with
  generic, *invented* boilerplate ("typically, heme proteins show a Soret
  band…"). Treat any boilerplate-sounding vision answer as a decode failure,
  not a reading of the figure.
- Downscale before asking vision about a crop: `sips -Z 1000 big.png --out view.png`.
- The authoritative identity check lives in the source: the `<img alt="Figure N">`
  plus the `<figcaption>` text. Confirm from those.

## Embedding

Obsidian: drop the file in a sibling `<note>_assets/` folder and embed with
`![[name.png]]` — see the obsidian skill's `references/memos-and-snippets.md`.
