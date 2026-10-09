---
name: hermes-pycache-cleanup
description: "Fix ImportError after Hermes auto-updates by clearing stale Python __pycache__ bytecode."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [hermes, pycache, bytecode, import-error, troubleshooting, gateway]
    related_skills: [hermes-agent, systematic-debugging]
---

# Hermes `__pycache__` Cleanup

Fix `ImportError` in Hermes gateway/agent after an auto-update.

## When to use

A profile's gateway logs (`~/.hermes/profiles/<profile>/logs/gateway.log`) show:

```
ImportError: cannot import name '<function_name>' from 'agent.skill_utils'
```

Or any `ImportError` referencing a name that **exists** in the current source `.py` file.

## Why this happens

After a Hermes auto-update (`hermes-setup --update` → `git pull`):

1. Git replaces `.py` source files while keeping the original git‑commit timestamps
2. Python's `__pycache__`/`.pyc` files are **NOT** cleared
3. Python compares the `.pyc` mtime against the `.py` mtime — the old `.pyc` looks "newer", so it gets used
4. The stale `.pyc` is missing any recently added functions or changed imports → `ImportError`

See also: `skill_view(name="hermes-agent", file_path="references/stale-pyc-after-desktop-install.md")` for an older reproduction.

## Steps

### 1. Confirm the error

```bash
tail -50 /Users/maxim/.hermes/profiles/<profile>/logs/gateway.log
tail -50 /Users/maxim/.hermes/profiles/<profile>/logs/errors.log
```

Look for `ImportError: cannot import name ... from ...`.

### 2. Clear all `__pycache__` directories

```bash
find /Users/maxim/.hermes/hermes-agent -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
echo "OK"
```

### 3. Verify the import works

```bash
/Users/maxim/.hermes/hermes-agent/venv/bin/python3.11 -c "
import sys
sys.path.insert(0, '/Users/maxim/.hermes/hermes-agent')
from agent.skill_utils import skill_matches_platform_list
print('Import OK')
"
```

Replace `skill_matches_platform_list` with whatever name the error mentioned.

### 4. Restart the profile's gateway

Find the PID:

```bash
cat /Users/maxim/.hermes/profiles/<profile>/gateway.pid
```

Kill it — the Hermes desktop supervisor (or systemd) will auto-restart:

```bash
kill <pid>
```

Wait a few seconds, then verify:

```bash
sleep 5
ps aux | grep "<profile>" | grep -v grep
tail -10 /Users/maxim/.hermes/profiles/<profile>/logs/gateway.log
```

Look for `Starting Hermes Gateway...` and `Connected` in the latest entries.

### 5. Test

Send a message to the profile on its connected platform (e.g., Feishu). The `ImportError` should be gone.

## Pitfalls

- **Do NOT use `kill -9`** unless absolutely necessary — it can confuse the Hermes supervisor
- If the gateway exits with `"signal-initiated shutdown without restart request"`, the supervisor didn't trigger a restart. The desktop app will restart it on the next message or dashboard trigger.
- The `__pycache__` is **shared across all profiles** (under `hermes-agent/`), so clearing it once fixes the issue for every profile
- **This recurs with every Hermes update** that adds/removes functions or changes imports — there is no permanent fix without modifying the Hermes update script to clear `__pycache__` post-update. Expect to run this after every notable update.
