# lammps-skill

An AI-agent skill, verified Python toolkit, clean-room teaching engine (`mdlite`) and undergraduate
course for molecular dynamics with LAMMPS (latest stable release primary; `develop` watched).
Version 0.1.0 — foundation; see `CHANGELOG.md`.

## What it does

- **`lammpskill`** detects and drives every way LAMMPS can be installed — WSL apt, a CMake source
  build, conda-forge, the PyPI wheel, the Windows installer (Docker and a remote cluster are designed
  and pinned) — through one `Installation` contract, and measures what each route gives
  (`references/platforms.md`). It builds input scripts from a Python `Spec`, checks them for the
  mistakes the manual warns about (14 rules, each citing its manual page), runs LAMMPS through a
  hidden subprocess or in-process through the official python module with the same `Result`, and reads
  and writes data, dump, log, restart-header and EAM potential files with its own code — validated
  against files LAMMPS wrote. Analysis (block averages, RDF, MSD/diffusion, VACF, S(k), energy drift,
  elastic constants) and benchmark comparison are independent of the binary; ASE, pymatgen, MDAnalysis
  and OVITO are optional bridges, never required.
- **`mdlite`** is a numpy molecular-dynamics engine written from the textbooks: cell and Verlet lists,
  Lennard-Jones, harmonic bonds, EAM from setfl/funcfl tables, velocity Verlet with Berendsen,
  Langevin and Nosé–Hoover-chain thermostats, steepest descent and FIRE. It is cross-checked against
  LAMMPS at measured precision and against NIST reference data (`references/benchmarks.md`).
- **`SKILL.md`** holds the agent workflows; **`references/`** what the agent must know;
  **`docs/USER_MANUAL.md`** the manual; **`AGENTS.md`** every flag. Chapters and the course arrive in
  plan 1b.

## Install

```powershell
scripts\install_env_windows.ps1        # conda env `lammps` + Jupyter kernel (or scripts/install_env.sh)
```

LAMMPS itself (GPL-2.0, not included) — any route, see `references/install-routes.md`:

| route | command |
|---|---|
| WSL apt (Ubuntu archive) | `wsl -d Ubuntu -u root -- bash /mnt/c/<path>/scripts/install_lammps_wsl.sh` |
| WSL source build (chosen tag + package preset) | `… install_lammps_wsl.sh --source --deps-only` (root), then `… --source --preset core` (user) |
| conda-forge | `conda create -n lammps-cf -c conda-forge lammps` |
| PyPI wheel (in-process only; Windows needs MS-MPI) | `pip install lammps` |
| Windows installer | https://rpm.lammps.org/windows/ |

`pip install -e .` (or `pip install lammps-skill` once on PyPI) gives the `lammpskill` command;
extras `[ase]`, `[pymatgen]`, `[mdanalysis]`, `[lammps]`, `[all]`.

## Quick start

```bash
python scripts/verify_lammps.py --probe                 # routes detected + probed, the platform table
lammpskill new --preset lj_melt --out case --steps 1000 # an input script from a preset
lammpskill check case/in.lammps                         # the checker (exit 1 on an error-level finding)
lammpskill run case --mpi 2                             # run it (hidden, time-limited, MPI only if the build has it)
lammpskill log case/log.lammps --csv thermo.csv         # the thermo block as CSV
lammpskill rdf case/d.dump --out g.png                  # g(r) from a dump
python scripts/run_benchmarks.py --potential <Cu_u3.eam from your installation>   # regenerate the records
```

## What is verified

- The suite (`python -m pytest tests -q`, 228 tests, pyflakes clean, conformance FAIL=0) runs everywhere; the tests that
  need LAMMPS run against every detected route and skip otherwise. On the reference machine they ran
  against the Ubuntu 26.04 apt build (10 Dec 2025): data-file round trip through LAMMPS, dumps and
  restarts written by LAMMPS, a synthetic EAM file accepted by `pair_style eam/alloy`, SPC/E water with
  PPPM and SHAKE, `mpirun -np 2`.
- Records (`data/records/`, tolerances read by the tests from the records themselves): LJ forces
  mdlite vs LAMMPS agree to 3e-13; fcc Cu on `Cu_u3.eam` — lattice constant and cohesive energy agree
  to 3e-5; mdlite NVT at T* = 0.85, ρ* = 0.776 agrees with the NIST SRSW Monte Carlo reference within
  3σ of the combined errors.
- Every route module is exercised with fakes; the two pinned routes (Docker, remote) are contracts the
  runner refuses with a message.

## Layout

```
lammpskill/   install/ (seven routes)  io/ (box, log, data, dump, restart, potential, backends)  script.py  run.py  post.py  cli.py
mdlite/       box  neighbors  pair  eam  integrate  thermostats  minimize  measure
scripts/      verify_lammps.py  install_env.sh  install_env_windows.ps1  install_lammps_wsl.sh  run_benchmarks.py
references/   install-routes  platforms  input-script  file-formats  packages  backends  benchmarks  analysis  pitfalls  ecosystem
data/         benchmarks/ (NIST LJ, EAM Cu — with provenance)  records/ (measured cross-checks)
docs/         USER_MANUAL.md  build_manual.py  DESIGN.md        tests/  (fixtures written by LAMMPS on this machine)
```

## Licence

Apache-2.0 — see `LICENSE` and `NOTICE`. LAMMPS itself is GPL-2.0 and is **not** included: install it
yourself (`scripts/install_lammps_wsl.sh` on WSL, or any other route in `references/install-routes.md`)
and this toolkit drives it. The optional `lammps` python module, ASE, pymatgen, MDAnalysis and OVITO
backends are separate packages under their own licences; they are never required. No LAMMPS source,
example input, potential file or manual text is part of this repository.

### Disclaimer

This software is provided "as is", without warranties or conditions of any kind, express or implied,
including, without limitation, any warranties of merchantability, fitness for a particular purpose,
title or non-infringement. In no event shall the authors or copyright holders be liable for any
damages of any character (direct, indirect, incidental, special, consequential or otherwise) arising
from, out of or in connection with the software or its use, even if advised of the possibility of
such damages. A simulation result is only as good as its force field, its sampling and its user:
verify every number before it leaves your desk.

This project is independent and not affiliated with or endorsed by Sandia National Laboratories,
National Technology & Engineering Solutions of Sandia, LLC (NTESS), Temple University or the LAMMPS
developers.
