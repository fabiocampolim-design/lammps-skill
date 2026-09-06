# Backends — optional bridges, never required

`lammpskill.io.backends` exposes the ecosystem behind one interface; every import is local to the
function, `available()` says what is installed, and a missing package raises `BackendUnavailable`
with the install hint and the licence. The rest of lammpskill never imports any of them.

| package | licence | version seen (2026-09-06) | what we bridge | what we do not |
|---|---|---|---|---|
| `lammps` (the official python module) | GPL-2.0 | 20251210 (python3-lammps in WSL); wheel 2025.7.22.4.0 (third party, njzjz/lammps-wheel) | `run.LibraryBackend`: in-process runs, `session()` for `extract_compute` / `fix python`; `install.wheel` detection | nothing else — the module is the upstream's own API |
| `ase` | LGPL-2.1 | 3.29.0 | `to_ase(DataFile | Frame)` → `ase.Atoms` (cell, pbc, tags = LAMMPS types, masses), `from_ase(atoms)` → `DataFile` | ASE's own LAMMPS calculators (`LAMMPSrun`, `LAMMPSlib`) — they drive LAMMPS their way; we keep ours |
| `pymatgen` | MIT | 2026.8.30 | `to_pymatgen(obj)` → `Structure` | `pymatgen.io.lammps` writers |
| `MDAnalysis` | GPL-2.0 | not installed here yet | `mdanalysis_universe(data, dump)` → `Universe` (DATA topology, LAMMPSDUMP trajectory) | analysis in MDAnalysis — `lammpskill.post` has its own RDF/MSD/VACF so the chapters work without it |
| `ovito` | GPL-3.0 (+ MIT modules) | 3.16.0 on conda-forge, not installed here yet | `ovito_pipeline(path)` → `import_file` pipeline for headless rendering and modifiers | the GUI (course walkthroughs only) |

Neighbours that are **not** bridged (recorded for `references/ecosystem.md`): `pylammpsmpi` (MPI
parallel python driver), `pymatgen-lammps` (conda-forge), `lammpsio`, `lammpskit` (PyPI + GitHub,
name taken), `pylammps` (PyPI, name taken).

## Rules

- Symbol from mass: `to_ase` / `to_pymatgen` guess the element from the nearest ASE atomic mass; a
  LAMMPS data file carries no element names. Set `Atoms.set_chemical_symbols` yourself when it matters.
- Nothing from these packages is vendored; the tests that need one skip when it is absent
  (`tests/test_io_backends.py`).
- The third-party wheel is GPL-2.0 like LAMMPS; it bundles `liblammps.dll` which on Windows needs the
  MS-MPI runtime (`references/install-routes.md`, finding N-2).
