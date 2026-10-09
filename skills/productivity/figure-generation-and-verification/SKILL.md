---
name: figure-generation-and-verification
description: "Use when delivering a labeled diagram or chart image."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [svg, diagram, ocr, cjk, verification, feishu]
    related_skills: [ocr-on-mac, trip-map-builder]
---

# Figure Generation and Verification

When the deliverable is an **image** (explanatory diagram, annotated cross-section,
comparison chart), you cannot see your own output. Text can silently drop to tofu
boxes, collide with a heading, or run off the panel — and the file still looks fine
by every non-visual check (byte size, dimensions, non-zero ink).

Never send an unverified figure. Pipeline: **author SVG → rasterize with headless
Chrome → OCR-verify → deliver**.

## 1. Author the figure as SVG

Write one self-contained SVG with `write_file`. Absolute coordinates only — no
layout engine, so what you write is what renders.

CJK font stack (put it on the root `<svg>` element):

```
font-family="PingFang SC, Heiti SC, Hiragino Sans GB, sans-serif"
```

SVG is not HTML: `<b>` / `<i>` / `<br>` inside `<text>` are inert — the tags render
literally or are dropped, silently, and neither the renderer nor the OCR check flags it.
Weight and emphasis go through `<tspan font-weight="700">…</tspan>`; a line break is a
second `<text>` element at a new `y`.

### Layout discipline

These rules exist because violating them produces garbled text that only OCR reveals:

- Keep **≥ 15 px between baselines of stacked text**, and **≥ 20 px between a
  heading baseline and any annotation baseline**. Two labels at y=102 and y=106
  render as one illegible smear.
- A centered heading (`text-anchor="middle"`) claims a wide horizontal band.
  Do not place side callouts at nearly the same y. Either drop the callouts below
  the heading band, or number them in-figure (`①②③`) and put a single legend
  caption line under the panel.
- Reserve an empty band inside each panel for its labels; never let text sit on
  top of dense artwork.
- Budget width before rendering: at `font-size: 13`, a CJK glyph is ≈ 13 px wide,
  so `x_end ≈ x_start + 13 × n_chars`. Check every string against its panel edge.
- Budget height the same way: the last baseline plus its descender must sit ≥ 10 px
  inside the root `height`. A footer 6 px under the final table row is a collision,
  not a margin.
- Give every panel an explicit `<rect>` background so overlapping art stays visible.
- Prefer hand-authored SVG over matplotlib for annotation-heavy figures: no
  dependency, and absolute coordinates make overflow predictable.

## 2. Rasterize with headless Chrome — not rsvg-convert

`rsvg-convert` works, but fontconfig on macOS frequently has no PingFang SC
registered, so Pango falls back to a Japanese font (Hiragino) — simplified-only
glyphs can come out wrong. Chrome uses the real system font stack.

```python
import base64, urllib.parse, os
svg = "/abs/path/figure.svg"
new_tab("file://" + urllib.parse.quote(svg))   # percent-encode: paths contain CJK
wait_for_load()
cdp('Emulation.setDeviceMetricsOverride',
    width=1260, height=740, deviceScaleFactor=2, mobile=False)
res = cdp('Page.captureScreenshot', format='png', captureBeyondViewport=True)
open("/abs/path/figure.png", "wb").write(base64.b64decode(res["data"]))
```

- Set the viewport to the SVG's intrinsic `width`/`height`, or the capture clips.
- `deviceScaleFactor=2` yields a 2× PNG (crisp when rendered inline in chat).
- Percent-encode the file URL; a raw `file://` URL breaks on CJK paths.
- After editing the SVG, append a cache-buster (`?v=2`) to the URL — Chrome will
  otherwise re-serve the stale file and you will "verify" the old render.

## 3. Verify by OCR — required, not optional

Run macOS Vision OCR over the PNG and read the text back. You are looking for
three failure modes:

| Symptom in OCR output | Actual problem |
|---|---|
| a whole line missing | glyphs unavailable (tofu) |
| two of your labels merged into one garbled string | **layout collision** — not an OCR error |
| a string truncated mid-way | text overflowed its panel |

```bash
S=~/.hermes/profiles/<profile>/skills/productivity/ocr-on-mac
source $S/.env/bin/activate && python3 $S/scripts/ocr.py /abs/path/figure.png --lang zh-Hans --plain
```

Compare the OCR lines against the strings you authored. Do not chase punctuation
or math symbols (`x²=kt` comes back mangled) — only structural failures.
Fix the SVG and re-render until every intended string returns cleanly.

### Glyph-availability probe (no OCR needed)

Render a tiny SVG containing only the CJK sample text, and the same SVG with a
deliberately nonexistent `font-family`. Compare ink coverage — equal non-zero
coverage means the glyphs resolved through the fallback chain:

```bash
magick t.png -colorspace gray -threshold 80% -negate -format "%[fx:mean]" info:
```

## 4. Deliver

- Send the **PNG** (`MEDIA:/absolute/path.png`) — chat platforms render PNG inline,
  SVG usually as a download.
- Save the `.svg` (editable source) beside the `.png`.
- If the figure belongs to a project or vault, save it in that project's folder and
  add a one-line pointer to it in the accompanying note.

## Pitfalls

- **Never deliver an unverified figure.** A tofu/overlapping figure reads as a broken
  answer and you cannot see it to notice.
- Do not use `magick`/`rsvg-convert` as the primary rasterizer for CJK figures — they
  depend on fontconfig, which is not the font set the user actually sees.
- Do not stack two text baselines closer than ~15 px even when the font sizes look
  small enough to fit; descenders and accents overlap first.
- When OCR merges two labels into one string, fix the **layout**, not the OCR call.
- Re-render with a cache-buster after every SVG edit, or you will verify a stale PNG.

## Resources

- `templates/figure.svg` — known-good scaffold: title band, two panels, numbered
  in-figure markers, one legend line per panel, a rect-per-row comparison table, source
  footer, correct spacing conventions, and the `<tspan>` emphasis idiom. Copy and modify.
- `ocr-on-mac` skill — the OCR engine and CLI used in step 3.
