---
name: pymol-visualization
title: PyMOL Visualization
description: Generate PyMOL .pse files programmatically using biorazer (biotite) for PDB I/O and scipy for transformations.
trigger: User asks to visualize a protein structure, create a PyMOL session, or show structural biology concepts.
references:
  - references/biorazer-pymol-workflow.md
required_environment_variables: [PYMOL_ROOT, BIORAZER_ENV_ROOT]
---

# PyMOL Visualization

## Workflow

### 1. PDB I/O — always use biorazer (biotite)

```python
from biorazer.structure.io.protein import PDB2STRUCT, STRUCT2PDB

# Read
full = PDB2STRUCT('input.pdb', '/dev/null').read()

# Extract chain
monomer = full[full.chain_id == 'A'].copy()

# Write
STRUCT2PDB('output.pdb', 'output.pdb').write(arr)
```

Always use `AtomArray` directly — never extract coordinates into raw numpy arrays and then reconstruct PDB lines manually. biorazer handles all annotation fields automatically.

### 2. Transformations — always use scipy

```python
from scipy.spatial.transform import Rotation

# Rotate around arbitrary axis
r = Rotation.from_rotvec(axis * np.radians(angle_deg))
arr.coord = r.apply(arr.coord - origin) + origin

# Euler angles (XYZ order for Rosetta-style DOFs)
r = Rotation.from_euler('xyz', [x, y, z], degrees=True)
arr.coord = r.apply(arr.coord)
```

Never write your own Rodrigues function — scipy's implementation is numerically robust.

### 3. Translation and radius scaling

```python
# Scale distance from axis in perpendicular plane
v = arr.coord - origin
para = np.outer(np.dot(v, axis), axis)
arr.coord = origin + para + (v - para) * factor

# Simple translate
arr.coord = arr.coord + offset
```

### 4. Building multi-chain assemblies

```python
# Concatenate AtomArrays (uses + operator)
assembly = chain1.copy()
for chain in [chain2, chain3]:
    assembly += chain  # works in this biotite version

# Set chain IDs after concatenation
nA = len(monomer)
for ci, ch_id in enumerate(['Z', 'A', 'B', 'C', 'D']):
    assembly.chain_id[ci * nA:(ci + 1) * nA] = ch_id
```

### 5. PyMOL session setup

```python
import pymol
from pymol import cmd

pymol.finish_launching(['pymol', '-cq'])

cmd.load('file.pdb', 'object_name')
cmd.hide('everything', 'object_name')
cmd.show('cartoon', 'object_name')
cmd.color('color_name', 'object_name')
cmd.set('cartoon_tube_radius', 0.15, 'object_name')
cmd.set('transparency', 0.55, 'object_name')
```

### 6. Grouping objects

Group related objects in the PSE for organized display:

```python
cmd.group('group_name', 'obj1 obj2 obj3')
```

**But never group objects the user needs to switch individually** (one object per ligand site, per chain,
per variant): a disabled group suppresses its children, so `disable all` + `enable <child>` shows nothing —
see Pitfall 5. Keep those flat and give the "show everything" escape hatch on the command line
(`show sticks, (obj and resn HEM)` — the atoms still live in the parent object).

### 7. View settings

```python
cmd.set('antialias', 2)
cmd.set('depth_cue', 0)
cmd.set('ambient', 0.4)
cmd.set('direct', 0.6)
cmd.set('reflect', 0.3)
cmd.center('reference_object')
cmd.zoom('reference_object', 3.5)
```

## User Preferences

| Preference | Rule |
|---|---|
| Background color | NEVER change bg_color. Keep default black unless user explicitly asks. |
| Primary representation | Cartoon. Don't use surface/ribbon/lines unless requested. |
| Object organization | Group by category for display — but **never** group objects the user is meant to toggle one-by-one; a group gates its children (see Pitfall 5). |
| Coloring | Red for active/main subunit; softer colors for symmetric partners. |

## Symmetric Assembly Visualization

### Symmetry axis
```python
for z_off in np.linspace(-axis_len/2, axis_len/2, 40):
    pos = center + axis_vec * z_off
    cmd.pseudoatom('ax', pos=list(pos))
cmd.group('symmetry_axis', 'ax_*')
cmd.show('spheres', 'symmetry_axis')
cmd.color('grey60', 'symmetry_axis')
```

### VRT coordinate axes
Use BioRazer-PyMOL's `arrow_between` for axes:
```python
from biorazer_pymol.mark.arrow import arrow_between
arrow_between(x1, y1, z1, x2, y2, z2, name='axis', r_color=1.0, g_color=0.3, b_color=0.3)
```

### Origin axes
```python
from biorazer_pymol.widget.axes import axes_in_place
axes_in_place()
cmd.group('origin_axes', 'X_axis Y_axis Z_axis')
```

## Pitfalls

0. **视图矩阵的行含义**: `get_view()/set_view()` 前 9 个数是**相机轴在世界里的方向**(3 行),
   **第 3 行 = 视线方向**。所以: 沿轴看 = 把轴放第 3 行; 侧视 = 把轴放**第 1 行**、第 3 行放一个
   与轴垂直的方向。放错行会得到沿轴视图 —— 本库一份脚本就把“侧视”写成了沿轴视图(4 张图全错,
   与 `view_along_axis` 几乎同一份代码)。第 10-12 个数 = 平移, 最后 6 个 (`v[12:18]`) = scale/origin,
   改视角时要原样带回去:

   ```python
   v = cmd.get_view()
   z = axis / np.linalg.norm(axis)
   hint = np.array([0., 0., 1.]) if abs(z[2]) < 0.9 else np.array([1., 0., 0.])
   view_dir = hint - z * (hint @ z); view_dir /= np.linalg.norm(view_dir)
   sx, sy = z, np.cross(view_dir, z)          # 轴当屏幕横向; det = +1
   R = np.stack([sx, sy, view_dir]); t = -R @ center
   cmd.set_view((*R[0], *R[1], *R[2], *t, *v[12:18]))
   ```

0b. **用 B-factor 给每个原子一个半径, 画大小不同的球** (孔道球串、通道包络):
   PDB 里把半径写进 B-factor 列(61-66), 再 `cmd.alter(obj, "vdw=b")` → `show spheres`,
   `sphere_quality 2`; `cmd.spectrum("b", "blue_white_red", obj)` 让大小与颜色挂钩;
   看内部结构时 `set cartoon_transparency, 0.55`。保存/校验: `cmd.save(x.pse)` 后用
   `cmd.load(x.pse)` + `count_atoms` + `iterate("vdw")` 读回来核。⚠ 注意 PyMOL 读 CIF
   **保留 altloc**(原子数比分析用的 `altloc="first"` 多), 两边原子数不一致是正常的。

0c. **CGO 在 headless 渲染里可能完全不出现** (实测: PyMOL 2.x, `finish_launching(['pymol','-qc'])`
   + `cmd.png(...,ray=1)`): `load_cgo` + `SAUSAGE`(圆台) 画通道圆柱 → 画面里什么都没有,
   而 `get_names("objects")` 里有该对象。判定法: `show cgo`/`hide cgo` × `ray=1`/`ray=0` 四张 PNG
   若**逐字节相同**, 就不是参数写错, 是这条渲染路径不画 CGO。替代方案(已验证):
   沿路径加密成**球链**(0.5 Å 一个球, 半径按弧长插值, 见 0b 的 B-factor 半径做法) —— 球心足够密时
   外轮廓就是光滑的管; `show surface` 合球面也行但会被半透明 cartoon 遮暗、看着更差。
0d. **手写 PDB 行的列位** 必须严格: 名字 13-16, altLoc 17, resName 18-20, chainID 22, resSeq 23-26,
   x/y/z **31-38/39-46/47-54**, occupancy 55-60, B-factor **61-66**。差一列(最常见: 名字字段多一个空格)
   → x/y/z 整体右移 → PyMOL 把 B-factor 读成 0 → 用 `alter vdw=b` 画的球**半径全丢**
   (实测 414 个球只有 1 个可见)。写完后一定读回校验:
   `cmd.iterate(obj, "vals.append(round(b,2))")` → 看唯一值个数/范围是否与写入一致。

1. **Symmetric assembly**: All subunits share ONE random orientation cloned to all VRTs. Never apply different rotations to different symmetric copies.
2. **Rotation order**: Rosetta's `set_dof angle_x/y/z` uses XYZ Euler order, not ZYZ.
3. **Rotation center**: Rotation is around the anchor residue's CA (or COM), not around the symmetry axis.
4. **Arrow_pass vs arrow_between**: `arrow_pass(point, direction)` is centered at the point, extending ±length in both directions; `arrow_between(start, end)` draws from start to end with arrowhead at end.

5. **组会"门控"子对象: 组被 disable 后, 子对象即使 `enabled=True` 也画不出来。**
   `cmd.group("hemes", "hem28 hem38 hem81")` 后 `cmd.disable("hemes")`: `get_names("objects", enabled_only=1)`
   里三个子对象**仍在**, 但渲染图里没有; 再 `cmd.enable("hem28")` 也不恢复 (与只关组那张图**逐字节相同**)。
   所以**要给用户逐个开关的对象一律不进组** (平铺), "全看"的出口用命令行
   `show sticks, (obj and resn HEM)` 或几个对象一起开。判据不能只看 `get_names` —— 要比**渲染出来的图**
   (同参数两次渲染 md5 相同 = 开关没生效)。

6. **`within` 是原子级选择, `byres` 不按链区分同号残基。**
   `resn HEM within 2.4 of (resid 28 and name NE2)` 只圈到 Fe 那 1 个原子 (对象里有 10 个 Fe, 但对整个
   配体而言棒状原子全丢) → 要整残基得套 `byres`; 但**当所有配体的残基号相同** (全是 900) 时, `byres`
   一次圈进全部 30 个 (各 1290 原子) —— 它认不出不同链上的同号残基。
   **根因修在产出侧**: 让上游把身份写进残基号 (HEM 的 `res_id = 900 + 位点号`), 可视化直接
   `resn HEM and resid 928` 取, 不在显示层用几何猜归属。配一条自检: **各子对象原子数之和必须等于该类
   原子的总数** (漏选与重复归属都会当场暴露), 在脚本末尾打印一行核对。

7. **`.pse` 与光线追踪 PNG 不逐字节稳定, 别用 `cmp` 核它们。**
   同一套脚本连跑两次: `.pse` **字节数相同、字节不同** (对象名 / 原子数 / Fe 数完全一致), `ray=1` 的
   PNG 差几十字节 —— 会话内部状态 + 多线程渲染的非确定性。核对方式是**对象结构**: `get_names("objects")`
   + 每个对象的 `count_atoms` (见 `scripts/inspect_pse.py`)。"逐字节可复现"的断言只能覆盖表 / JSON /
   定长 PDB / matplotlib PNG, 不要让它覆盖这两类。

## Scripts

- `scripts/inspect_pse.py` — 打印一个或多个 `.pse` 的对象清单、每个对象的原子数与 Fe 数; 给两个文件时
  逐对象比对 (对象名集合 + 原子数), 不一致退出码 1 —— 可直接当验收命令用。
  `"$PYMOL_ROOT/Contents/bin/python3.10" scripts/inspect_pse.py a.pse [b.pse]`
