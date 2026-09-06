# Changelog

All notable changes to lammps-skill. Format: Keep a Changelog; versions: SemVer.

## 0.1.0 — 2026-09-06 (foundation)

- Product skeleton: Apache-2.0 licence, NOTICE, non-affiliation (Sandia, NTESS, Temple, the LAMMPS
  developers), held-material guard, vendored conformance checker 1.6.4, 3-OS CI with pyflakes first.
- Installers (rule 24): conda env `lammps` + kernel (`install_env.sh`, `install_env_windows.ps1`),
  LAMMPS from the Ubuntu archive or from source with package presets on WSL
  (`install_lammps_wsl.sh`, dry run, root refusal, tested failure path). The apt route was installed
  here (10 Dec 2025 build) and produced the test fixtures (`-h` listing, LJ-melt log, data file).
- `lammpskill.install`: seven routes (wsl-apt, wsl-source, conda, wheel, windows; docker and remote
  pinned as fake-tested contracts) under one `Installation` dataclass; hidden `run_command` with a
  `timeout` inside WSL; the LJ-melt `probe`; `scripts/verify_lammps.py` with the platform table.
- `lammpskill.io`: `Box`; log parser (`one` + `yaml` thermo, warnings, errors, loop lines, several
  runs); data files (7 atom styles, image flags, coefficient sections, topology, a round trip through
  LAMMPS); dumps (scaled/unwrapped/triclinic, gzip, writer); restart header (observed 16-byte magic);
  EAM setfl/funcfl reader/writer with a synthetic potential accepted by LAMMPS; optional
  ASE/pymatgen/MDAnalysis/OVITO bridges.
- `lammpskill.script`: `Spec` → input script in the manual's order; presets `lj_melt`, `eam_fcc`,
  `spce_water` (our own water-box builder, runs in LAMMPS with PPPM + SHAKE); 14-rule checker citing
  manual pages.
- `lammpskill.run`: subprocess backend (MPI/OMP only when the build has them, MPI verified with
  `mpirun -np 2`), library backend over the `lammps` python module, `run()`, `run_or_load()` (S11).
- `lammpskill.post`: block averages, RDF, MSD/diffusion, VACF, S(k), energy drift, elastic constants;
  `data/benchmarks/` with the NIST SRSW Lennard-Jones MC + MD tables (copied 2026-09-06) and the EAM
  Cu fitting targets, each with provenance.
- `mdlite`: box, cell + Verlet lists, Lennard-Jones, harmonic bonds, EAM from splines, velocity
  Verlet, Berendsen/Langevin/Nosé–Hoover-chain thermostats, steepest descent (capped) + FIRE.
  Records (`data/records/`, tolerances read by the tests): forces vs LAMMPS 3e-13; Cu a0/Ecoh vs
  LAMMPS 3e-5; NVT vs NIST within 3σ.
- `lammpskill` CLI (detect/verify/new/check/run/log/dump/rdf, audit log), `pyproject.toml` with
  optional extras; the wheel builds and `__version__` falls back to the package metadata.
- References (10), SKILL.md workflows, AGENTS.md, user manual + `build_manual.py`, README product
  page, DESIGN.md, docs guard. Suite: 228 tests (3 skip without an in-process module / MDAnalysis),
  run twice, pyflakes clean, conformance 1.6.4 FAIL=0, the wheel builds and imports.
- Findings recorded in the study repository: `thermo_modify norm` per-atom default in lj units, dump
  float precision, the PyPI wheel's MS-MPI dependency on Windows (N-2), the apt build being a feature
  release (N-3).
