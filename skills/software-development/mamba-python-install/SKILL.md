---
name: mamba-python-install
description: "Install Python CLI apps/applications using mamba environments. Preferred over Homebrew venvs for system-level Python tools."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mamba, python, venv, installation, conda]
    related_skills: [skill-package-management]
---

# Mamba Python Install

## When to Use

When the user asks to install a Python CLI app or package, and the user's preferred workflow is via mamba environments (not Homebrew Python venvs).

## Workflow

### Step 1: Create the environment

```bash
# If target is /Applications (requires sudo):
sudo mamba create -p /Applications/<APP>/.env python=<VERSION> -y
sudo chmod -R 775 /Applications/<APP>

# If target is ~/Applications (no sudo needed):
mamba create -p ~/Applications/<APP>/.env python=<VERSION> -y
chmod -R 775 ~/Applications/<APP>
```

Choose Python version appropriate for the package. Python 3.12 is a safe default.

### Step 2: Install the package

**Important — `uv` vs `pip` distinction:**

- `mamba activate <ENV>` then `uv pip install` — **works fine**. `mamba activate` properly sets PATH so `uv` sees the correct Python.
- `mamba run -p <ENV> uv pip install` — **FAILS**. `mamba run -p` does NOT set PATH the same way; `uv` scans cwd and picks up whatever `.env/` it finds (e.g. `hermes-agent/.env`).

Use one of these safe patterns:

```bash
# Option A: activate then pip install (works with both pip and uv)
mamba activate ~/Applications/<APP>/.env && pip install <PACKAGE>

# Option B: mamba run with pip (safe, env's own pip is always correct)
mamba run -p ~/Applications/<APP>/.env pip install <PACKAGE>

# Option C: mamba run with explicit bash -c
mamba run -p ~/Applications/<APP>/.env bash -c "pip install <PACKAGE>"
```

The user's preferred workflow (per direct instruction):
```bash
mamba create -p /Applications/<APP>/.env python=<VERSION>
chmod -R 775 /Applications/<APP>
mamba activate /Applications/<APP>/.env
uv pip install <PACKAGE>     # works because activate sets PATH correctly
```

### Step 3: Verify

```bash
mamba run -p ~/Applications/<APP>/.env python3 -c "import <PACKAGE>; print(<PACKAGE>.__file__)"
mamba run -p ~/Applications/<APP>/.env <APP> --version
```

### Step 4: Migration to /Applications

To relocate a mamba env from `~/Applications/<APP>/.env` to `/Applications/<APP>/.env`:

```bash
# Copy the entire env directory
sudo cp -a ~/Applications/<APP>/.env /Applications/<APP>/.env
sudo chmod -R 775 /Applications/<APP>

# Update prefixes (conda environments store hardcoded paths)
sudo mamba run -p /Applications/<APP>/.env bash -c "\$CONDA_PREFIX/bin/python3 -m site"  # verify it works
# Mamba envs are relocatable - just need the right paths
```

Or simply recreate:
```bash
sudo mamba create -p /Applications/<APP>/.env --clone ~/Applications/<APP>/.env
sudo chmod -R 775 /Applications/<APP>
```

## Common Pitfalls

1. **`mamba activate` needs shell hook in `terminal()`** — Each `terminal()` call is a fresh shell. `mamba activate <ENV>` alone will fail with "Run 'mamba init' to setup shell hook". Always combine in one command: `eval "$(mamba shell hook --shell bash)" && mamba activate <ENV> && uv pip install <PACKAGE>`. Or use `mamba run -p <ENV> pip install <PACKAGE>` for simple installs.
2. **`uv` + `mamba run`** — `mamba run -p` combined with `uv pip install` picks up the wrong venv from the cwd. Always use the env's own `pip` instead.
3. **sudo required for /Applications** — creating dirs under /Applications needs sudo; ~/Applications/ avoids this.
4. **Permissions** — after sudo-created envs, run `chmod -R 775` so the user can install packages without sudo.
5. **Python version** — if a package needs a specific Python version, specify it at create time.
