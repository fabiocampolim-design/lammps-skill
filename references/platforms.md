# Platforms — the measured table

Machine (2026-09-06): Windows 10 host, 8 cores, **16 GB RAM** (15.9 GB usable; the WSL2 VM is given
7.7 GB of it — an earlier version of this line reported the VM's share as the host's), **no GPU**;
WSL2 Ubuntu 26.04 (`resolute`,
kernel 6.18 microsoft-standard), GNU C++ 15.2, Open MPI 5.0.10, Python 3.14; conda env `lammps`
(Python 3.12, numpy 2.5.2, scipy 1.18.0, matplotlib 3.11.1) on the Windows side. GPU, KOKKOS-CUDA and
the GPU package are studied from the manual and the source, never run here.

"LJ melt" = the probe of `verify_lammps.py --probe`: 4000 LJ atoms (fcc 0.8442, T* = 3.0, rc = 2.5),
250 steps, one process, case directory on the Windows side (`/mnt/c` from WSL). Wall time includes
process start-up. Every number below was produced by the command named; a row with "—" was not run.

| route | host | version | executable | library | python module | MPI | OMP | packages | LJ melt (s) | verified | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| wsl-apt | wsl | 10 Dec 2025 | `/usr/bin/lmp` | `/usr/lib/x86_64-linux-gnu/liblammps.so` | yes (python3-lammps, WSL python 3.14) | yes (Open MPI 5.0.10) | yes | 52 | 1.45 (probe); 3.07 wall for the first run incl. `write_data` | 2026-09-06 | Ubuntu package `20251210+dfsg-1build1`; feature release, not the stable; MPI verified with `mpirun -np 2` (`tests/test_run.py`) |
| wsl-source | wsl | 22 Jul 2025 - Update 6 (`stable_22Jul2025_update6`) | `~/.local/bin/lmp_core` | `~/.local/lib/liblammps_core.so` | yes, in its own venv `~/.local/venv-lammps-core` (Python 3.14) — **not** the system `python3` | yes (Open MPI 5.0.10) | yes | 11 (the `core` preset exactly) | 1.38 (probe) | 2026-09-06 | built with `install_lammps_wsl.sh --source --preset core --jobs 4`; this is the **stable** release, unlike the apt route's feature release; source tree 735 MB, venv 38 MB, `liblammps_core.so.0` 24 MB; see N-10 … N-13 |
| conda | linux / macOS | 2025.07.22 available | — | — | — | — | — | — | — | 2026-09-06 (availability only) | **conda-forge has no win-64 `lammps` build**; linux-64 (2382 builds), osx-64 (1520), osx-arm64 (785), linux-aarch64 (180), newest 2025.07.22 everywhere. `cpu_*` and `cuda*` variants, `nompi` / `mpi_openmpi` / `mpi_mpich`. On a Windows host the route means conda inside WSL |
| wheel | windows | 2025.7.22.4.0 (pip) | `Scripts/lmp.exe` (ships with the wheel) | `site-packages/lammps/liblammps.dll` | installs, **does not load**: needs `msmpi.dll` (MS-MPI runtime) | (MS-MPI) | ? | ? | — | 2026-09-06 | finding N-2; route reports "not detected" until MS-MPI is installed (owner's decision) |
| windows | windows | — | — | — | — | — | — | — | — | — | installer not run (system-wide; owner's decision) |
| docker | docker | — | — | — | — | — | — | — | — | — | PINNED (no Docker Desktop) |
| remote | remote | — | — | — | — | — | — | — | — | — | PINNED (no machine) |

## Per-route facts worth knowing

- **wsl-apt package list (52)**: ASPHERE BOCS BODY CG-DNA CG-SPICA CLASS2 COLLOID COMPRESS CORESHELL
  DIELECTRIC DIFFRACTION DIPOLE DPD-BASIC DRUDE EFF ELECTRODE EXTRA-COMPUTE EXTRA-PAIR FEP GRANULAR
  H5MD KIM KSPACE LATBOLTZ MANIFOLD MANYBODY MC MEAM MGPT MISC MOFFF MOLECULE MOLFILE NETCDF OPENMP
  OPT ORIENT PERI PHONON PYTHON QEQ QTB REPLICA RIGID SHOCK SMTBQ SPH SRD TALLY UEF VORONOI VTK
  (from `tests/fixtures/lmp_help_wsl_apt.txt`). Missing for the plan-1 chapters: nothing; missing for
  later plans: REAXFF, ML-SNAP/ML-PACE/ML-IAP, EXTRA-FIX, EXTRA-MOLECULE, EXTRA-DUMP, COLVARS, PLUMED.
- **Potentials**: `lammps-data` installs 257 files under `/usr/share/lammps/potentials`
  (`Cu_u3.eam`, `Cu_mishin1.eam.alloy`, …). They stay there; the toolkit reads them in place and never
  copies one into this repository.
- **I/O location**: the probe and every test run from the Windows side through `/mnt/c`. The ext4
  (`~/runs`) vs `/mnt/c` timing difference has **not** been measured yet; when a chapter needs it, the
  number goes here with its command.
- **Windows console**: every WSL/LAMMPS process is started hidden (`CREATE_NO_WINDOW`, stdin closed);
  nothing appears on screen.
