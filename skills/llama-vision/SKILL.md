---
name: llama-vision
description: "Vision workflow using local llama-server (Qwen3.6-35B-A3B): start server, compress image, analyze, stop server."
version: 1.0.0
author: User workflow
tags: [vision, llama-server, llama.cpp, qwen, multimodal, image]
platforms: [macos]
---

# Llama Vision: Local Vision Model Workflow

## Trigger

Use when:
1. You need `vision_analyze` with a local image **and** the active model doesn't have native vision — start the server, feed it the image, clean up afterward.
2. `vision_analyze` gives **inconsistent or unreliable results** on a complex/scientific image — use this as a cross-validation second opinion (see `vision-grounding` skill).

## Steps

### 1. Start llama-server

```bash
launchctl start com.user.llama-server
```

Then **wait for health check** (model loading takes 30–60s):

```bash
for i in $(seq 1 60); do
  if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/health | grep -q 200; then
    echo "Ready after ${i}s"
    break
  fi
  sleep 2
done
```

Retry logic: if the server doesn't come up within 120s, `kill $(pgrep -f llama-server)` and `launchctl start com.user.llama-server` again.

### 2. Compress the image (optional but recommended)

Reduces latency by feeding a smaller image to the model. The script preserves the aspect ratio and only shrinks if the longest side exceeds the limit.

```bash
cd ~/.hermes/skills/llama-vision
COMPRESSED=$(.env/bin/python3 scripts/compress_image.py "$IMAGE_PATH" --max-size 1280)
```

The script prints the compressed path to stdout and a dimension/size summary to stderr.

### 3. Call vision_analyze

Use `vision_analyze(image_url="$COMPRESSED", question="...")` with the compressed path.

**If vision_analyze already has the image path** (user sent an image and the system shows its cached path), skip steps 1-2 and just pre-validate that llama-server is running first.

### 4. Stop llama-server (cleanup)

Free ~20GB RAM and GPU resources:

```bash
# Option A — graceful stop
PID=$(pgrep -f "llama-server.*--model.*Qwen") && kill $PID

# Option B — wait for llama-server to finish pending requests, then kill
sleep 2 && kill $(pgrep -f "llama-server.*--model.*Qwen")
```

Verify it stopped:
```bash
pgrep -q -f "llama-server.*--model.*Qwen" || echo "✅ Stopped"
```

## Scripts

### `scripts/compress_image.py`

Compresses an image so the longest side ≤ 1280px (configurable via `--max-size`), preserving aspect ratio with LANCZOS resampling. Saves to a temporary file and prints the path to stdout.

**Usage:**
```bash
cd ~/.hermes/skills/llama-vision
.env/bin/python3 scripts/compress_image.py /path/to/image.jpg [--max-size 1280]
```

**Environment:** Uses the isolated `.env` virtual environment with Pillow installed. No system Python packages are modified.

## Configuration

- **Server port:** 8080 (hardcoded in LaunchAgent)
- **Model:** `/Library/Models/Qwen-3.6/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf` + mmproj
- **LaunchAgent:** `com.user.llama-server` (OnDemand, does NOT auto-start)
- **Hermes auxiliary vision config** (in `~/.hermes/config.yaml`):
  ```yaml
  auxiliary:
    vision:
      provider: custom
      model: qwen3.6-35b-a3b
      base_url: http://127.0.0.1:8080/v1
      api_key: not-needed
      timeout: 120
  ```

  You can also set each key via CLI instead of editing YAML directly:
  ```bash
  hermes config set auxiliary.vision.provider custom
  hermes config set auxiliary.vision.model qwen3.6-35b-a3b
  hermes config set auxiliary.vision.base_url http://127.0.0.1:8080/v1
  hermes config set auxiliary.vision.api_key not-needed
  hermes config set auxiliary.vision.timeout 120
  ```

## Pitfalls

| Issue | Fix |
|---|---|
| **Server not responding after 2 minutes** | Kill it and restart: `kill $(pgrep -f llama-server) && launchctl start com.user.llama-server` |
| **Memory still high after stop** | Wait a few seconds — macOS reclaims memory gradually. Check with `memory_pressure \| head -5` |
| **LaunchAgent not registered** | `launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.user.llama-server.plist` |
| **Vision API returns 503** | Model is still loading. Wait longer and retry. |
| **Max token errors on long images** | Reduce `--max-size` to 800 or lower for very large/detailed images. |
| **Server start interrupted mid-wait** | User sends new message while waiting → command returns 130. DON'T restart immediately — first check `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/health`; the server probably started in the background and is ready. |
