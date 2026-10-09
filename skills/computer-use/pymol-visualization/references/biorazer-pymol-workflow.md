# BioRazer + PyMOL PSE Generation Workflow

## Environment

- **biorazer**: `$BIORAZER_ENV_ROOT/bin/python`
  - Provides `biorazer.structure.io.protein.PDB2STRUCT` and `STRUCT2PDB` (wraps biotite)
  - Also provides `biorazer_pymol` from `~/Repositories/BioRazer-PyMOL`
- **PyMOL**: `$PYMOL_ROOT/Contents/MacOS/python`
  - Must use `PYTHONPATH=""` to avoid Hermes venv numpy conflicts
  - Import `biorazer_pymol` modules by adding repo to sys.path

## Two-Phase Architecture

Always split the workflow into two scripts:

### Phase 1: Data generation (biorazer env)

Generate PDB files from source data. Run with:
```bash
"$BIORAZER_ENV_ROOT/bin/python" phase1_script.py
```

### Phase 2: PSE creation (PyMOL env)

Load PDBs into PyMOL, set styles, group objects, save .pse. Run with:
```bash
PYTHONPATH="" "$PYMOL_ROOT/Contents/MacOS/python" phase2_script.py
```

## Key Technical Patterns

### C5 Symmetry Axis from Chain Centroids
```python
coms = np.array([full[full.chain_id == ch].coord.mean(axis=0) for ch in 'ABCDE'])
center = coms.mean(axis=0)
cov = np.cov(coms.T)
_, eig_vecs = np.linalg.eigh(cov)
axis = eig_vecs[:, 0]
if axis[2] < 0: axis = -axis
```

### Recenter (Rosetta-style)
```python
res1 = monomer[monomer.res_id == 1]
ca1 = res1[res1.atom_name == 'CA']
translation = ca1.coord[0].copy()
monomer.coord = monomer.coord - translation
```

### Slide into Contact Detection
```python
from scipy.spatial.distance import cdist
z_coords = assembly[assembly.chain_id == 'Z'].coord
min_d = float('inf')
for ch in ['A', 'B', 'C', 'D']:
    d = np.min(cdist(z_coords, assembly[assembly.chain_id == ch].coord))
    if d < min_d: min_d = d
```

### VRT X-Axes from SDF (start -1,0,0 + rot Rz N)
```python
vrt_x_axes = []
for i in range(5):
    angle = i * 72
    r = Rotation.from_euler('z', angle, degrees=True)
    x_dir = r.apply(np.array([-1.0, 0.0, 0.0]))
    vrt_x_axes.append(x_dir)
```

### Rosetta SymDock Algorithm Flow (for visualization)
1. Read monomer PDB → recenter (residue 1 CA at origin)
2. Read SDF → generate VRT coordinate frames (rot Rz N)
3. Randomize BASEJUMP (angle_x/y/z from 0:360, XYZ order)
4. Set initial radius (x(50))
5. Slide-into-contact: binary search (2.0→1.0→0.5→0.25→...→0.2Å steps)
6. Low-res MC: centroid, 10 outer × 50 inner cycles, Gaussian steps (3Å, 8°), adaptive
7. High-res MCM: full-atom, rigid-body perturbation + repacking + minimization
