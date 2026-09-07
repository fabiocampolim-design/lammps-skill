---
name: lammps
description: Install, detect, drive and analyse LAMMPS molecular-dynamics simulations through every install route (WSL apt, source build, conda-forge, PyPI wheel, Windows installer; Docker and remote designed) with a verified Python toolkit (lammpskill), and teach molecular dynamics with the mdlite engine (LJ, EAM, velocity Verlet, thermostats, validated against NIST and cross-checked against LAMMPS). Use this skill whenever the user mentions LAMMPS, molecular dynamics, an input script, pair_style, fix nvt/npt/nve, EAM, Lennard-Jones, a data file, a dump file, thermo output, RDF, MSD, diffusion, a force field, or running an MD simulation — even without naming LAMMPS.
license: Apache-2.0
---

# lammps-skill 0.1.2

LAMMPS toolkit written from the manual and from files LAMMPS writes: install routes
(`references/install-routes.md`, `references/platforms.md`), input scripts and the checker
(`references/input-script.md`), file formats (`references/file-formats.md`), the runner, analysis
(`references/analysis.md`), benchmarks (`references/benchmarks.md`), packages
(`references/packages.md`) and a clean-room teaching engine (`mdlite`). Read
`references/pitfalls.md` before touching a script. Run everything from the product root with the
`lammps` conda env and `PYTHONIOENCODING=utf-8`; every flag is in `AGENTS.md`. LAMMPS is GPL-2.0 and
is **not included**: the user installs it (any route) and the toolkit drives it. Never assume a
package, a route or a number: detect, probe, measure, and say what was not verified.

## 1. Set up and verify
```bash
scripts/install_env_windows.ps1            # or scripts/install_env.sh — conda env lammps + kernel; both accept a dry run
python scripts/verify_lammps.py --probe    # every route detected and probed; the platform table
lammpskill detect                          # the same, one line per installation
```
Nothing found? `references/install-routes.md` → pick a route → `scripts/install_lammps_wsl.sh` (apt,
or `--source --preset core`), the Windows installer, `conda install -c conda-forge lammps`, or
`pip install lammps` (in-process only; on Windows it needs MS-MPI).

## 2. Choose or compare install routes
`lammpskill detect --json` gives packages, MPI, OMP, module per route; `references/platforms.md` gives
the measured wall times. Rule: the route that has the packages the script needs wins
(`references/packages.md`); ties go to the fastest measured; the in-process module when the user wants
per-step Python access. Docker and remote are pinned: designed, refused by the runner, documented.

## 3. Build an input script from a spec; check it
```python
from lammpskill.script import Spec, Stage, render, check, lj_melt, eam_fcc, spce_water
text = render(lj_melt(steps=1000))
for f in check(text, workdir="case"): print(f.level, f.code, f.message, f.manual)
```
`lammpskill new --preset spce_water --out case` writes the data file too. Every checker code is
explained in `references/pitfalls.md`; `Spec` has no field for `pair_modify`/`dump_modify` — insert
them after the command they modify.

## 4. Run: subprocess or in-process, MPI/OpenMP, time limit
```python
from lammpskill.run import run
res = run(text, "case", mpi=4, time_limit=600)   # auto: first executable route; in-process when only the module exists
res.ok, res.thermo.last, res.warnings, res.errors
```
`lammpskill run case --route wsl-apt --mpi 4 --omp 2 --time-limit 600`. MPI/OMP are applied only when
the build has them (a warning otherwise). Everything starts hidden and with a `timeout` inside WSL.

## 5. Read what LAMMPS wrote
`lammpskill.io`: `read_log`, `read_data` / `write_data`, `read_dump` / `write_dump`,
`read_restart_header`, `read_eam_setfl` / `read_eam_funcfl`. Hand-offs: `io.backends.to_ase`,
`to_pymatgen`, `mdanalysis_universe`, `ovito_pipeline` — optional, each with its licence in
`references/backends.md`. `lammpskill log FILE --csv out.csv`, `lammpskill dump FILE --info`.

## 6. Analyse and compare with a benchmark
`lammpskill.post`: `block_average`, `rdf`, `msd` + `diffusion_coefficient`, `vacf`,
`structure_factor`, `energy_drift`, `elastic_from_stress`; `load_benchmark("nist_lj")` +
`compare(value, entry)`. `lammpskill rdf traj.dump --out g.png`. A number is reported with its block
error and against a reference or not at all.

## 7. Set up a force field correctly
Units ↔ styles ↔ coefficients ↔ potential files: `references/input-script.md` (presets, where every
parameter comes from) and `references/file-formats.md` (EAM setfl/funcfl, where LAMMPS looks for
potential files). The checker catches long-range pair styles without `kspace_style`,
coefficient-before-style, unset masses, timestep vs units. Potential files stay in the user's
installation; none is copied into a repository.

## 8. Teach with mdlite
`mdlite`: `Box`, `VerletList`, `LennardJones`, `HarmonicBond`, `eam.EAM`, `velocity_verlet` with
`thermostats.Berendsen` / `Langevin` / `NoseHooverChain`, `minimize.steepest_descent` / `fire`. What
each validation shows and the measured residue against LAMMPS and NIST: `references/benchmarks.md`,
`data/records/` (regenerate with `scripts/run_benchmarks.py`).

## 9. In-process LAMMPS (the python module)
```python
from lammpskill.run import LibraryBackend
with LibraryBackend().session("case") as L:
    L.commands_string(text); L.extract_compute("thermo_pe", 0, 0)
```
Only where a route reports `python module: yes` for the python you are running
(`references/platforms.md`).

## 10. Visualise
Headless: `io.backends.ovito_pipeline(dump)` when OVITO is installed; matplotlib for everything else
(`lammpskill rdf … --out png`). GUI walkthroughs: the course (plan 1b).

## 11. Report a bug upstream
Reproduce minimal (a `Spec`, the smallest `n`), run on two routes, check the GitHub tracker, the
MatSci forum and `develop`'s history first, grade PROVEN (observed on a real run, output captured) or
CODE (read, not reproduced), and write the draft into the study repository's drafts folder — the owner
sends. Never open an issue or post from an agent.

## 12. Pitfalls
`references/pitfalls.md`. A stable temperature is not a converged result: check the energy drift, the
block error, and the finite-size trend before believing a number; `thermo_modify norm` is per-atom by
default in `units lj`.
