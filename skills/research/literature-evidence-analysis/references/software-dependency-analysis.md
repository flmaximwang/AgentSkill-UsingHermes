# Analyzing Scientific Software Dependency Claims

When a paper or README says a software package "uses" or "depends on" a library (e.g. PyRosetta), the packaging metadata and actual code may tell different stories. This reference documents the verification workflow and common patterns.

## Verification Workflow

1. **Check `setup.py` / `pyproject.toml`**:
   - `install_requires` = packages installed automatically (truly required)
   - `extras_require` = optional packages, installed only with `pip install pkg[name]`
   - If the target is in `extras_require`, the metadata says it's optional.

2. **Check the actual Python code**:
   - **Top-level imports** (`from pyrosetta import ...` at module level, no `try/except`) = **functionally required** regardless of packaging metadata. The module cannot be imported without it.
   - **Deferred imports** (inside functions, or `try: import foo \nexcept ImportError: foo = None`) = genuinely optional, with an explicit fallback.

## Common Pattern: License-Restricted Dependencies

Many scientific packages depend on license-restricted software that cannot be distributed on PyPI:

- **PyRosetta** (Rosetta Commons, free non-profit license)
- **Schrödinger** (commercial license)
- **Gaussian** (commercial)
- **CCDC GOLD / CSD** (commercial)

These are universally listed as `extras_require` in `setup.py`, even when the code performs **top-level hard imports** at module load time. The packaging metadata reflects distribution constraints, not functional optionality.

### Case Study: RPXDock + PyRosetta

| Source | What it says | Interpretation |
|---|---|---|
| `setup.py` | `EXTRAS = {'pyrosetta': 'pyrosetta'}` | Metadata says optional |
| `rpxdock/body/body.py` line 7 | `from pyrosetta import rosetta as ros` — top-level | Functionally required |
| `rpxdock/rosetta/triggers_init.py` line 2 | `from pyrosetta import Pose, pose_from_file, ...` — top-level | Functionally required |
| `triggers_init.py` line 18 | `init(get_init_string())` — module-level call | Runs PyRosetta init at import time |

**Conclusion**: `pip install rpxdock` without PyRosetta → `ImportError` on first import. The `[pyrosetta]` extra is a distribution convenience marker, not a toggleable feature.

## How to Express This in Answers

```
The paper states RPXDock "uses PyRosetta" to load .pdb files.
setup.py lists it as an extras_require (due to PyRosetta's
non-PyPI license), but the code does a top-level
`from pyrosetta import rosetta as ros` in body.py,
making it functionally required at runtime.
```

## Common Pitfalls

- **"Optional dependency" ≠ "optional feature"**: A package may list a dependency as optional in setup.py but crash without it at runtime. Always check the import location (top-level vs deferred).
- **The `extras_require` license dodge**: Some packages use `extras_require` as a workaround for non-PyPI-compatible licenses, not because the feature is truly optional. The keys are often named after the dep (`'pyrosetta': 'pyrosetta'`) rather than the feature (`'docking': '...'`), which is a tell.
- **Environment.yml vs setup.py**: RPXDock's `environment.yml` includes PyRosetta (because conda can install it from Rosetta's channel), while `setup.py` lists it as extras (because pip cannot). The `environment.yml` is the honest dependency list; the `setup.py` reflects distribution reality.
