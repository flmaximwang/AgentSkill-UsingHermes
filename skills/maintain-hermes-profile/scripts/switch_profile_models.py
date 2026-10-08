#!/usr/bin/env python3
"""Point every profile's default model (and a named custom provider) at one target.

Rewrites ONLY the top-level `model:` block body of each config.yaml, and adds the
`providers.<provider>:` entry (copied from the main home's config.yaml) where the profile
does not define it. Profiles do NOT inherit the main config's providers.

Guards, each one earned by a real failure:
  * the `model:` header line is preserved in place -- appending a replacement block that
    carries its own `model:` line creates a DUPLICATE top-level key;
  * duplicate top-level keys are rejected before the write: PyYAML's safe_load accepts them
    silently while Hermes' strict loader refuses the file and falls back to last-good, which
    shows up only as `hermes profile list` printing `--` in the Model column;
  * a pre-edit backup of every written file lands under <home>/backups/<label>/config.yaml.

Usage:
  python3 switch_profile_models.py --model deepseek-v4-1-flash \
      --provider volcengine-agent-plan --base-url https://ark.cn-beijing.volces.com/api/plan/v3 [--dry-run]
  python3 switch_profile_models.py ... --profiles artist,game-research   # default: every profile
"""
from __future__ import annotations

import argparse
import datetime
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml

TOP_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")


def top_keys(lines):
    return [m.group(1) for l in lines if (m := TOP_KEY.match(l))]


def model_block_end(lines):
    for i in range(1, len(lines)):
        if lines[i].strip() and TOP_KEY.match(lines[i]):
            return i
    raise SystemExit("no end of model block found")


def provider_block(main_lines, provider):
    """The `providers.<provider>` subtree from the main config, as its own `providers:` block."""
    start = next((i for i, l in enumerate(main_lines) if l.rstrip() == "providers:"), None)
    if start is None:
        raise SystemExit("main config has no top-level `providers:` section")
    key = "  %s:" % provider
    sub = next((i for i in range(start + 1, len(main_lines)) if main_lines[i].rstrip() == key), None)
    if sub is None:
        raise SystemExit(f"main config has no providers.{provider} entry to copy")
    end = len(main_lines)
    for i in range(sub + 1, len(main_lines)):
        l = main_lines[i]
        if l.strip() and not l.startswith("    "):  # dedent back to providers level or above
            end = i
            break
    return ["providers:\n"] + main_lines[sub:end]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default="~/.hermes")
    ap.add_argument("--model", required=True)
    ap.add_argument("--provider", required=True, help="provider name, without any `custom:` prefix")
    ap.add_argument("--base-url", default="")
    ap.add_argument("--api-mode", default="chat_completions")
    ap.add_argument("--profiles", default="all", help="`all` or comma-separated names (`default` = main home)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    home = Path(a.home).expanduser()
    main_cfg = home / "config.yaml"
    main_lines = main_cfg.read_text(encoding="utf-8").splitlines(keepends=True)
    pb = provider_block(main_lines, a.provider)

    if a.profiles == "all":
        configs = [main_cfg] + sorted((home / "profiles").glob("*/config.yaml"))
    else:
        wanted = [w.strip() for w in a.profiles.split(",") if w.strip()]
        configs = [(main_cfg if w == "default" else home / "profiles" / w / "config.yaml") for w in wanted]

    body = ["  default: %s\n" % a.model, "  provider: %s\n" % a.provider]
    if a.base_url:
        body.append("  base_url: %s\n" % a.base_url)
    if a.api_mode:
        body.append("  api_mode: %s\n" % a.api_mode)

    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup = home / "backups" / f"model-switch-{ts}"
    changed, already, failed = [], [], []

    for path in configs:
        label = "default" if path.parent == home else path.parent.name
        if not path.exists():
            failed.append((label, "no such config"))
            continue
        raw = path.read_text(encoding="utf-8")
        lines = raw.splitlines(keepends=True)
        dups = [k for k, n in Counter(top_keys(lines)).items() if n > 1]
        if not lines or lines[0].rstrip() != "model:" or dups:
            failed.append((label, f"unexpected top-level shape (dups={dups})"))
            continue

        end = model_block_end(lines)
        try:
            cur = yaml.safe_load("".join(lines[1:end])) or {}
        except Exception:  # noqa: BLE001
            cur = {}
        cur = cur if isinstance(cur, dict) else {}
        if (cur.get("default") == a.model
                and str(cur.get("provider") or "").replace("custom:", "").strip() == a.provider):
            already.append(label)
            continue

        new = lines[:1] + body + (pb if "%s:" % a.provider not in raw else []) + lines[end:]
        text = "".join(new)
        if Counter(top_keys(new)).most_common(1)[0][1] != 1:
            failed.append((label, "duplicate top-level key after edit"))
            continue
        parsed = yaml.safe_load(text)
        m = parsed.get("model") or {}
        if not (isinstance(m, dict) and m.get("default") == a.model and m.get("provider") == a.provider):
            failed.append((label, f"parsed model block unexpected: {m}"))
            continue
        if a.provider not in (parsed.get("providers") or {}):
            failed.append((label, "providers entry missing after edit"))
            continue

        changed.append((label, (pb if "%s:" % a.provider not in raw else []) != []))
        if a.dry_run:
            continue
        (backup / label).mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup / label / "config.yaml")
        path.write_text(text, encoding="utf-8")

    tag = " [dry-run, nothing written]" if a.dry_run else ""
    print(f"backup dir: {backup}{tag}")
    print("changed (%d): %s" % (len(changed), ", ".join(f"{l}{' +providers' if p else ''}" for l, p in changed)))
    print("already on target (%d): %s" % (len(already), ", ".join(already)))
    if failed:
        for label, why in failed:
            print(f"  ! {label}: {why}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
