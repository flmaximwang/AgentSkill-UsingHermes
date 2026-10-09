# ATSAS CLI entry points

## Wiring (every shell, before anything else)

```bash
export ATSAS=/Applications/ATSAS-<version>      # e.g. 4.1.4-1
export PATH="$ATSAS/bin:$PATH"
```

`atsas.lic` lives in that install root next to `bin/` and `lib/`; the binaries find it through `$ATSAS`. Without the
export, every binary exits with "ATSAS environment variable undefined, 'atsas.lic' not found" even though the app itself
runs and even though another copy of the licence sits in `~/Downloads`. Check the install root's licence file before
assuming the registration failed.

Wrapping libraries search for the install directory themselves and may only look in the user's home. BioXTAS RAW's
`findATSASDirectory()` scans a fixed list that includes `$HOME` for a directory named `ATSAS-*`; the documented fix is a
home symlink to the install dir:

```bash
ln -s /Applications/ATSAS-<version> ~/ATSAS-<version>
```

Prove it with the library's own detector, not `which`:

```python
from bioxtasraw.SASUtils import findATSASDirectory   # -> '<root>/bin'
```

The RAW Python API then wants the **bin** directory, not the root: `settings.set('ATSASDir', '<root>/bin')`.

## Which binary answers which question

- `gnom` — indirect Fourier transform / P(r) from a curve; takes an explicit Dmax (the `datgnom` wrapper does not expose
  that option, which is why the API route is preferred).
- `dammif` — ab initio bead model; `-mode Fast|Slow`, `--symmetry <Pn>`. Its log prints the fitted "Radius of gyration"
  and the "Dummy atom radius" — that radius is what converts a bead count into a volume (see the other reference).
- `damaver` — ensemble averaging and clustering. Writes per-cluster and `-global-` variants, each as `-damstart` /
  `-damaver` / `-damfilt`; the filtered average is the "most probable" model, and the summary plus pairwise distance
  files sit next to the models.
- `cifsup` — superposition and NSD, the SUPCOMB successor (ATSAS >= 4). `--method=NSD --selection=REGRID`. The score is
  written into the OUTPUT file's header, not to stdout (PDB wrapper: `REMARK 265`). The same pair of models scores an
  order of magnitude apart across ALL / BACKBONE / REGRID / SHELL — always quote the selection with the score.
- `datmw` / `datclass` — mass from the data / shape class assignment.
- `crysol` — computes a curve from a model and fits it to an experimental curve.

## CRYSOL recipe

```bash
awk '!/^#/ && NF>=3 {print $1,$2,$3}' <subtracted.dat> > cols.dat
awk '$1>=<qmin>' cols.dat > clean.dat      # same q range for every item you intend to compare
crysol model.pdb clean.dat
```

- Pipeline exporters append `#` comment header/footer blocks; CRYSOL wants plain columns, so filter first.
- Outputs: `<model>.log`, `<model>_<stem>.log`, `<model>_<stem>.fit` (curves), `.alm`.
- Read from the log: `Chi-square of fit`, `Probability of fit`, `Rg from the slope of net intensity` (the model's Rg as
  the fit sees it), `Scaling of the excluded volume`, `Solvent density`.
- The default fits the scale and the solvent contrast. Interpret chi-square next to the model's size and the data's low-q
  quality: chi-square climbing with concentration across a dilution series is reporting the concentrated curves' low-q
  region, not the model.
