---
name: skill-package-management
description: "Use when installing Python packages for a skill. Checks venv viability, creates if missing, installs with uv."
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, skills, python, venv, uv, package-management]
    related_skills: [hermes-agent, ocr-on-mac, mamba-python-install]
---

# Skill Package Management

## When to Use

When you need to install a Python package inside a skill's directory — for example, setting up a new skill's dependencies, or adding a package to an existing skill's virtual environment.

## Overview — Two Workflows

| Scenario | Workflow |
|----------|----------|
| Setting up a NEW skill (first time) | pyproject.toml + config.yaml + ask user for venv path |
| Adding a package to an EXISTING skill | Read venv from config.yaml then pip install |

The config.yaml approach makes the venv path explicit, user-configurable, and self-documenting. Use it for every new skill.

---

## Preferred Workflow: pyproject.toml + config.yaml (new skills)

### Step 0: Create pyproject.toml (uv-based, no setuptools)

Define dependencies in a `pyproject.toml` at the skill root. With uv, no `[build-system]` section is needed — uv reads `[project].dependencies` directly:

```toml
[project]
name = "skill-name"
version = "0.1.0"
description = "..."
requires-python = ">=3.10"
dependencies = [
    "Pillow>=10.0.0",
]
```

Do NOT add a `[build-system]` section with setuptools. The user explicitly prefers uv-native pyproject.toml files. uv handles both venv creation and dependency installation without setuptools.

### Step 1: Create config.yaml at skill root

```yaml
# Skill configuration
# venv_path: path to Python virtual environment
venv_path: ""
```

### Step 2: Ask user for venv path

Use the `clarify` tool to ask where they want the venv. Common answers:
- Inside the skill dir: `~/.hermes/skills/<category>/<name>/.env`
- Elsewhere: whatever path they specify

### Step 3: Write venv path to config.yaml

```bash
sed -i '' "s|venv_path: \"\"|venv_path: \"/path/user/specified\"|" path/to/config.yaml
```

### Step 4: Create venv at configured path

Use `uv venv` (it detects Homebrew Python automatically):

```bash
VENV_PATH=$(grep '^venv_path: ' path/to/config.yaml | sed 's/^venv_path: *//')
uv venv "$VENV_PATH"
```

If the directory already exists (from a previous attempt), clear and recreate:

```bash
uv venv --clear "$VENV_PATH"
```

### Step 5: Install dependencies

Activate the configured venv and install:

```bash
VENV_PATH=$(grep '^venv_path: ' path/to/config.yaml | sed 's/^venv_path: *//')
source "$VENV_PATH/bin/activate" && uv pip install Pillow
```

Or from pyproject.toml (editable install):

```bash
source "$VENV_PATH/bin/activate" && uv pip install -e path/to/skill_root
```

### Step 6: Verify

```bash
VENV_PATH=$(grep '^venv_path: ' path/to/config.yaml | sed 's/^venv_path: *//')
source "$VENV_PATH/bin/activate" && python3 -c "import PIL; print('OK')"
```

### Why this workflow?

- **Configurable** — user chooses where venv lives; skill is reusable across machines
- **Self-documenting** — config.yaml tells the agent where to look
- **Clean** — pyproject.toml declares all deps in one place, not scattered across install commands

---

## Quick Workflow: Read config to Probe then Install (existing skills)

Use this when adding a package to an already-set-up skill where config.yaml already exists.

### Read venv path from config.yaml

Always check config.yaml first:

```bash
SKILL_DIR=~/.hermes/skills/<category>/<name>
VENV_PATH=$(grep '^venv_path: ' "$SKILL_DIR/config.yaml" 2>/dev/null | sed 's/^venv_path: *//')
if [ -z "$VENV_PATH" ]; then
  VENV_PATH="$SKILL_DIR/.env"
fi
```

### Probe the environment

The environment may be a **Python venv** or a **mamba/conda environment**. Always detect the type first:

```bash
# Step 1: detect environment type
if [ -d "$VENV_PATH/conda-meta" ]; then
  ENV_TYPE=conda
elif [ -f "$VENV_PATH/bin/activate" ]; then
  ENV_TYPE=venv
else
  ENV_TYPE=unknown
fi
```

Then probe accordingly:

```bash
# Step 2: probe based on type
if [ "$ENV_TYPE" = "venv" ]; then
  source "$VENV_PATH/bin/activate" 2>/dev/null && \
    python3 -c "import sys; print(f'venv OK: Python {sys.version_info.major}.{sys.version_info.minor} at {sys.executable}')"
elif [ "$ENV_TYPE" = "conda" ]; then
  "$VENV_PATH/bin/python3" -c "import sys; print(f'conda env OK: Python {sys.version_info.major}.{sys.version_info.minor} at {sys.executable}')"
else
  # fallback: try direct python3 path (works for both if paths are set up)
  "$VENV_PATH/bin/python3" -c "import sys; print(f'direct: Python {sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null
fi
```

- Exit 0 + OK message: environment is usable, skip to install
- Exit != 0: environment is broken or missing, recreate

Do NOT just check for the directory existence — a stale or broken environment (wrong Python version, incomplete installation) will fail at install time. Always probe by running Python.

### Create the venv (if missing or broken)

Use `uv venv` directly — it detects Homebrew Python and creates the venv faster:

```bash
uv venv "$VENV_PATH"
```

If the path already exists (e.g. from a previous broken install), clear it first:

```bash
uv venv --clear "$VENV_PATH"
```

Fallback (if uv is unavailable):

```bash
/opt/homebrew/bin/python3.12 -m venv "$VENV_PATH"
```

After creation, verify by re-running the probe.

### Install packages

Activate the configured environment and install. The method depends on environment type:

**For venv (standard):**
```bash
source "$VENV_PATH/bin/activate" && uv pip install <package1> <package2>
```

**For conda/mamba environments (no `bin/activate`):**
```bash
"$VENV_PATH/bin/pip" install <package1> <package2>
```

**Universal fallback (detect-and-install):**
```bash
if [ -d "$VENV_PATH/conda-meta" ]; then
  "$VENV_PATH/bin/pip" install <package>
else
  source "$VENV_PATH/bin/activate" && uv pip install <package>
fi
```

#### Multiple packages in one command

```bash
if [ -d "$VENV_PATH/conda-meta" ]; then
  "$VENV_PATH/bin/pip" install pyobjc-framework-Vision pyobjc-framework-Cocoa
else
  source "$VENV_PATH/bin/activate" && uv pip install pyobjc-framework-Vision pyobjc-framework-Cocoa
fi
```

#### From a requirements file

```bash
if [ -d "$VENV_PATH/conda-meta" ]; then
  "$VENV_PATH/bin/pip" install -r "$SKILL_DIR/requirements.txt"
else
  source "$VENV_PATH/bin/activate" && uv pip install -r "$SKILL_DIR/requirements.txt"
fi
```

---

## Common Pitfalls

1. **Forgetting config.yaml** — always create config.yaml with venv_path when setting up a new skill. The old pattern of hardcoding .env in the skill dir is deprecated for new skills.
2. **Checking directory existence instead of probing** — `test -d .env` passes for stale/broken venvs. Always probe by activating.
3. **Python version mismatch** — if the venv was created with Python 3.14 but pyobjc doesn't support it, probing catches it (activation succeeds but import fails later). Recreate with 3.12.
4. **source not persisting** — each terminal() call is a new shell. Combine source + install in a single command string.
5. **uv not installed** — if `uv` is missing, fall back to the venv's own pip: `source "$VENV_PATH/bin/activate" && pip install <package>`.
6. **`uv venv` fails with "directory already exists"** — when the target path already has a non-venv directory (or a stale venv), `uv venv` errors out. Fix: use `uv venv --clear <path>` to replace it.
7. **Conda/mamba environment assumed to be a venv** — `source .../bin/activate` fails silently on conda environments (that file doesn't exist). Always probe with `[ -d "$VENV_PATH/conda-meta" ]` and use direct `"$VENV_PATH/bin/pip"` / `"$VENV_PATH/bin/python3"` paths instead. The probe section above handles this automatically.
8. **Long model downloads (>100MB) must use cron, not background process** — downloading model files (e.g. surya's 1.35GB layout model) can take minutes. Do NOT use `terminal(background=true)`. Use `cronjob(action='create', schedule='1m', ...)` instead. The cron job runs independently with proper timeout handling and auto-delivers the result.

## When NOT to use this skill

For installing standalone Python CLI apps (not skill dependencies), use the companion `mamba-python-install` skill instead. Mamba environments live under `/Applications/<APP>/.env` or `~/Applications/<APP>/.env` when sudo is not available.

The mamba route is preferred when:
- The package is a CLI tool the user invokes directly (e.g. bypy, yt-dlp)
- The app needs a dedicated environment outside the Hermes skills tree
- The user wants to migrate it to /Applications/ later

## Verification Checklist

- [ ] pyproject.toml created with dependency list
- [ ] config.yaml created with venv_path filled
- [ ] Venv probe succeeded or new venv was created at configured path
- [ ] `uv pip install` completed with exit code 0
- [ ] Package import test passes (use direct path for conda, source activate for venv)
