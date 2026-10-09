---
name: sds-page-gel-cropper
description: "Crop specific lanes from SDS-PAGE gel images using vision model + Pillow. Input images should already have background/borders removed (gel-only)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [bio, gel, sds-page, image-processing, cropping, lab]
    related_skills: [skill-package-management]
---

# SDS-PAGE Gel Cropper

Crop specific lanes from SDS-PAGE gel images. The agent uses its vision model to identify lane positions, then Pillow precisely crops the requested lanes.

**Dependencies:** Pillow, numpy (auto-installed in the skill's venv)

**Config:** `~/.hermes/skills/life-science-research/sds-page-gel-cropper/config.yaml` — contains `venv_path` pointing to the venv.

## When to Use

Use this skill when the user says:
- "Crop lane 2 and 4 from this gel"
- "Extract lanes 1-3 from the gel image"
- "Save lane 5 as a separate image"
- Any request to isolate individual lanes from an SDS-PAGE gel photo

**Input requirements:**
- Image should be **already background-cropped** (gel area only, no white borders or labels)
- Any standard image format (JPEG, PNG, TIFF)
- Lanes are **vertical** and numbered left to right (1 = leftmost)

## Workflow

### Step 1: Inspect the gel with vision

Call `vision_analyze()` on the gel image with this prompt:

```
这是一张 SDS-PAGE 胶图。请告诉我：
1. 有多少条垂直泳道？从左到右编号 1~N。
2. 每条泳道的左右边界位置，用归一化坐标 [0,1] 表示
   (0=左边缘, 1=右边缘)。
   格式如：Lane 1: 0.05-0.25, Lane 2: 0.30-0.50
3. 泳道间距是否均匀？
图片宽度为 <图片实际宽度>px。
```

### Step 2: Extract coordinates from vision output

Parse the vision model's response to extract lane boundaries. The response will state something like:

```
- Lane 1: 左边界≈0.05，右边界≈0.25
- Lane 2: 左边界≈0.30，右边界≈0.50
```

Convert to the `--vision-coords` format:
```
1:0.05:0.25 2:0.30:0.50 3:0.55:0.75 4:0.80:0.95
```

### Step 3: Parse the user's lane spec

The user may specify lanes in various formats:
- `"lane 2"` → crop lane 2 only
- `"lane 1-3"` → crop lanes 1, 2, 3
- `"lane 1,3-5"` → crop lanes 1, 3, 4, 5
- `"泳道 2 和 4"` → Chinese query also supported

Use `parse_lane_spec.py` to validate the spec before proceeding.

### Step 4: Crop the lanes

```bash
source <venv_path>/bin/activate && python <scripts_dir>/gel_crop.py \
  <image_path> \
  "<lane_spec>" \
  --vision-coords <coord1> <coord2> ... \
  --output-dir <output_directory>
```

**Example:**
```bash
source /Applications/GelCropper/.env/bin/activate && \
python ~/.hermes/skills/life-science-research/sds-page-gel-cropper/scripts/gel_crop.py \
  /path/to/gel.jpeg \
  "2,4" \
  --vision-coords 1:0.05:0.25 2:0.30:0.50 3:0.55:0.75 4:0.80:0.95
```

### Step 5: Verify quality (optional but recommended)

Call `vision_analyze()` on each cropped lane output to check:
- No bands cut off on left or right edges
- Margins are reasonable (not excessive white space)
- Lane is complete

If margins are too generous, tighten the coordinates and re-crop.

## Alternative: Auto-detect lanes

If the gel has **high contrast and clearly visible gaps between lanes**, the auto-detection fallback can be used:

```bash
source <venv>/bin/activate && python <scripts>/gel_crop.py \
  <image_path> "<lane_spec>" --auto-lanes <N>
```

Where `<N>` is the number of lanes (from vision model).

**⚠️ Limitation:** Auto-detection performs poorly on gels with uneven background staining or faint bands. The vision-model approach is preferred.

## Alternative: Refine boundaries

If vision model coordinates leave too much margin, use the gradient-based refinement:

```bash
source <venv>/bin/activate && python <scripts>/refine_boundaries.py \
  <image_path> '<estimates_json>' --output-json /tmp/boundaries.json

# Then use the refined boundaries:
python <scripts>/gel_crop.py \
  <image_path> "<lane_spec>" \
  --lane-boundaries /tmp/boundaries.json
```

## File Structure

```
life-science-research/sds-page-gel-cropper/
├── SKILL.md           # This file
├── pyproject.toml     # Project config (Pillow, numpy)
├── config.yaml        # venv_path setting
└── scripts/
    ├── gel_crop.py           # Main entry: crop lanes from gel
    ├── parse_lane_spec.py    # Parse "1,3-5" → [1,3,4,5]
    ├── detect_lanes.py       # Auto-detect via intensity projection (fallback)
    └── refine_boundaries.py  # Gradient-based boundary refinement
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Left bands cut off | Vision model's left coordinate too far right | Shift that lane's left boundary 0.02-0.03 leftward |
| Too much right white space | Vision model's right coordinate too far right | Tighten that lane's right boundary 0.02-0.03 leftward |
| "No module named 'numpy'" | numpy not installed | Run: `source <venv>/bin/activate && uv pip install numpy` |
| Auto-detection gives uneven lane widths | Low contrast or uneven staining | Switch to --vision-coords mode |
| Lane boundary file parse error | JSON format mismatch | Ensure file uses `"left"`/`"right"` keys (not `"left_px"`) |

## Pipeline Example

Full agent workflow:

```python
# 1. Load this skill
skill_view(name='sds-page-gel-cropper')

# 2. Inspect gel
vision_analyze(
    image_url='/path/to/gel.jpeg',
    question='--- Step 1 prompt ---'
)

# 3. Parse vision response (agent reads coordinates)

# 4. Crop
terminal(command='source /Applications/GelCropper/.env/bin/activate && '
         'python .../gel_crop.py /path/to/gel.jpeg "2,4" '
         '--vision-coords 1:0.05:0.25 2:0.30:0.50')

# 5. Verify
vision_analyze(image_url='/path/to/cropped/lane2.png', question='Check quality')
```
