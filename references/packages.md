# Packages — what a build contains and what each plan needs

LAMMPS is a core plus optional packages; a binary has the packages it was compiled with, and every
route lists them under `Installed packages:` in `lmp -h` (`Installation.packages`). Before writing a
script, check that its styles are in the build: a missing package produces "Unrecognized pair style"
or "Unknown fix style" at run time.

## Plan 1 (LJ / EAM / molecular core) — what the chapters use

| need | commands / styles | package |
|---|---|---|
| Lennard-Jones fluids, NVE/NVT/NPT, thermo, dumps | `pair_style lj/cut`, `fix nve/nvt/npt/langevin`, `compute msd/rdf` | core (always present) |
| EAM metals, elastic constants, `fix box/relax` | `pair_style eam`, `eam/alloy`, `fix box/relax` | MANYBODY (eam styles are core; MANYBODY adds Tersoff/SW/…) |
| molecules with bonds and angles, SHAKE | `atom_style full`, `bond_style harmonic`, `angle_style harmonic`, `fix shake` | MOLECULE, RIGID (shake) |
| long-range electrostatics | `pair_style lj/cut/coul/long`, `kspace_style pppm` / `ewald` | KSPACE |
| OpenMP threads | `-sf omp -pk omp N` | OPENMP |
| in-process Python | `fix python/invoke`, `python` command, the module | PYTHON |

The wsl-apt build (10 Dec 2025, 52 packages) has all of these. The `core` preset of the source route
adds EXTRA-COMPUTE, EXTRA-DUMP, EXTRA-FIX, EXTRA-MOLECULE, EXTRA-PAIR so the "extra" fixes and
computes the manual lists (e.g. `fix ave/correlate/long`, `compute stress/mop`) are available too.

## Later plans

| plan | packages |
|---|---|
| 2 reactive / many-body | REAXFF, QEQ, MANYBODY (Tersoff, SW, MEAM via MEAM) |
| 3 machine-learning potentials | ML-SNAP, ML-PACE, ML-IAP (and their library dependencies) |
| 4 free energy / enhanced sampling, rigid, CG | FEP, REPLICA, COLVARS, PLUMED, RIGID, CG-SPICA |
| 5 DPD / granular / SPH / accelerators | DPD-BASIC, GRANULAR, SPH, OPENMP, KOKKOS (OpenMP here; CUDA studied only), GPU (studied only) |

## Source-route presets (`install_lammps_wsl.sh --preset`)

`core`, `molecular` (+ MC MISC QEQ SHOCK), `metals` (+ MEAM PHONON REPLICA), `reactive` (+ QEQ REAXFF),
`ml` (+ ML-SNAP ML-PACE ML-IAP), `all-cpu` (the manual's `most.cmake`). The exact package lists are in
`lammpskill.install.wsl_source.PRESET_PACKAGES`; the configure line is printed by `--dry-run`.
