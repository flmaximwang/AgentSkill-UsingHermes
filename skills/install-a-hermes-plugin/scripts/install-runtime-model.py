#!/usr/bin/env python3
"""Install runtime data (a spaCy model) into one of Hermes' dependency environments.

Hermes' dependency manager builds a *whole new environment* whenever the dependency
set changes, so anything installed by hand lives inside one generation and is gone
after the next rebuild. Run this after installing or updating a plugin that needs
data the package index cannot carry, and again after any rebuild that drops it.

`python -m spacy download` shells out to uv, and uv refuses to guess which
environment to install into, so this script always passes VIRTUAL_ENV itself.

Usage:
  install-runtime-model.py --list
  install-runtime-model.py --model en_core_web_sm --check
  install-runtime-model.py --model en_core_web_sm --dry-run
  install-runtime-model.py --model en_core_web_sm
  install-runtime-model.py --model xx_ent_wiki_sm --venv <path to a venv>

Exit codes:
  0  installed, or already present (with --check: present)
  2  no candidate environment found, or the given --venv is unusable
  3  --check: the model is missing in the selected environment
  4  the install command failed
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL = "en_core_web_sm"
# Carried into the child process so a mirrored/proxied network keeps working;
# everything else is read one variable at a time through the accessor form.
PASS_THROUGH = (
    "PATH", "HOME", "TMPDIR", "LANG", "LC_ALL",
    "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
    "UV_DEFAULT_INDEX", "UV_INDEX_URL", "UV_CACHE_DIR",
)

OK, NO_ENV, MISSING, INSTALL_FAILED = 0, 2, 3, 4


def hermes_root(override: str | None) -> Path:
    if override:
        return Path(override).expanduser()
    home = os.environ.get("HERMES_HOME")
    return Path(home).expanduser() if home else Path.home() / ".hermes"


def venv_python(venv: Path) -> Path | None:
    for rel in ("bin/python", "Scripts/python.exe"):
        candidate = venv / rel
        if candidate.is_file():
            return candidate
    return None


def candidates(installs_dir: Path) -> list[Path]:
    """Every environment venv under <root>/installs/*/environments/*/venv, newest first."""
    found = [p for p in installs_dir.glob("*/environments/*/venv") if venv_python(p)]
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def stamp(path: Path) -> str:
    when = _dt.datetime.fromtimestamp(path.stat().st_mtime)
    return when.strftime("%Y-%m-%d %H:%M")


def module_of(model: str) -> str:
    return model.replace("-", "_")


def child_env(venv: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for name in PASS_THROUGH:
        value = os.environ.get(name)
        if value:
            env[name] = value
    env["VIRTUAL_ENV"] = str(venv)
    env["PATH"] = f"{venv / 'bin'}:{env.get('PATH', '')}"
    return env


def has_module(python: Path, module: str) -> bool:
    probe = (
        "import importlib, sys;"
        "importlib.import_module(sys.argv[1]);"
        "print('import ok')"
    )
    done = subprocess.run(
        [str(python), "-c", probe, module],
        capture_output=True, text=True, timeout=300,
    )
    return done.returncode == 0


def state_of(python: Path, model: str) -> str:
    """present / MISSING / no-spacy — a venv without spaCy is simply not the plugin's."""
    if not has_module(python, "spacy"):
        return "no spacy"
    return "present" if has_module(python, module_of(model)) else "MISSING"


def install_command(python: Path, model: str) -> list[str]:
    return [str(python), "-m", "spacy", "download", model]


def do_install(venv: Path, python: Path, model: str, dry_run: bool) -> int:
    command = install_command(python, model)
    print(f"venv:    {venv}   (built {stamp(venv)})")
    print(f"command: VIRTUAL_ENV={venv} {' '.join(command)}")
    if dry_run:
        print("status:  dry run — nothing executed")
        return OK
    done = subprocess.run(command, env=child_env(venv), timeout=1800)
    if done.returncode != 0:
        print(f"status:  install failed (exit {done.returncode})", file=sys.stderr)
        return INSTALL_FAILED
    if not has_module(python, model):
        print(f"status:  command succeeded but '{module_of(model)}' still does not import",
              file=sys.stderr)
        return INSTALL_FAILED
    print(f"status:  {model} installed and importable in {venv}")
    return OK


def select(cli_venv: str | None, installs_dir: Path) -> tuple[Path | None, int]:
    if cli_venv:
        venv = Path(cli_venv).expanduser()
        if not venv.is_dir() or venv_python(venv) is None:
            print(f"error: {venv} is not a Python environment (no bin/python)", file=sys.stderr)
            return None, NO_ENV
        return venv, OK
    found = candidates(installs_dir)
    if not found:
        print(f"error: no environment venv under {installs_dir}/*/environments/*/venv",
              file=sys.stderr)
        print("hint: install a plugin or run `hermes memory setup <provider>` first, "
              "or pass --venv explicitly", file=sys.stderr)
        return None, NO_ENV
    return found[0], OK


def list_environments(installs_dir: Path, model: str) -> int:
    found = candidates(installs_dir)
    if not found:
        print(f"no environment venv under {installs_dir}/*/environments/*/venv")
        return NO_ENV
    for venv in found:
        python = venv_python(venv)
        state = state_of(python, model) if python else "no python"
        print(f"{stamp(venv)}  {state:8s}  {venv}")
    return OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install runtime data (spaCy model) into a Hermes environment venv.")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"spaCy model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--venv", help="environment venv to use (default: newest one)")
    parser.add_argument("--hermes-root", help="HERMES_HOME (default: $HERMES_HOME or ~/.hermes)")
    parser.add_argument("--list", action="store_true",
                        help="list candidate environments and whether the model is present")
    parser.add_argument("--check", action="store_true",
                        help="only report; exit 3 when the model is missing")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the command without running it")
    args = parser.parse_args(argv)

    installs_dir = hermes_root(args.hermes_root) / "installs"
    if args.list:
        return list_environments(installs_dir, args.model)

    venv, code = select(args.venv, installs_dir)
    if venv is None:
        return code
    python = venv_python(venv)
    assert python is not None  # select() proved it

    state = state_of(python, args.model)
    if state == "no spacy":
        print(f"error: {venv} has no spaCy — it is not the environment a "
              f"spaCy-using plugin runs in", file=sys.stderr)
        print("hint: --list shows every candidate, --venv picks another one", file=sys.stderr)
        return NO_ENV
    if state == "present":
        print(f"venv:    {venv}   (built {stamp(venv)})")
        print(f"status:  {args.model} already present")
        return OK
    if args.check:
        print(f"venv:    {venv}   (built {stamp(venv)})")
        print(f"status:  MISSING {args.model}")
        return MISSING
    return do_install(venv, python, args.model, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
