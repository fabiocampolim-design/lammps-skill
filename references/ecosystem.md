# Ecosystem — neighbours, honestly

One row per project that overlaps with lammps-skill, what it does, its licence, its activity as seen
on the date checked, what we take from it (nothing but the comparison) and how we differ. Names were
collision-checked on 2026-09-06 before `lammps-skill` was chosen (free on PyPI and GitHub).

| project | what it is | licence | activity (checked) | how we differ |
|---|---|---|---|---|
| `lammps` python module (upstream `python/`) | the official ctypes wrapper of `liblammps`; `PyLammps` / `IPyLammps` conveniences | GPL-2.0 | part of every release | we drive it (`run.LibraryBackend`) and add the subprocess route, parsers, checker, analysis, mdlite; we do not replace it |
| `lammps` PyPI wheel (njzjz/lammps-wheel) | third-party binary wheels of the module for Windows/Linux/macOS | GPL-2.0 | 2025.7.22.4.0 (2026-09-06) | a route we detect; Windows needs MS-MPI (N-2) |
| ASE (`ase.calculators.lammpsrun`, `lammpslib`, `ase.io.lammpsdata`) | general atomistic toolkit with LAMMPS calculators and data-file I/O | LGPL-2.1 | 3.29.0 (2026-09-06) | optional bridge only; our data/dump/log readers are independent and tested against LAMMPS output |
| pymatgen (`pymatgen.io.lammps`) | materials toolkit with LAMMPS data/input writers | MIT | 2026.8.30 (2026-09-06) | optional bridge |
| MDAnalysis | trajectory analysis with DATA/DUMP readers | GPL-2.0 | on PyPI | optional bridge; `lammpskill.post` has its own RDF/MSD/VACF so nothing GPL is required |
| OVITO python | visualisation and modifiers, LAMMPS importer | GPL-3.0 / MIT modules | 3.16.0 on conda-forge (2026-09-06) | optional bridge; course walkthroughs use the GUI |
| pylammpsmpi | run the python module on MPI ranks | BSD-3 (conda-forge 0.5.0) | on conda-forge (2026-09-06) | not used; the remote/cluster route is pinned |
| pymatgen-lammps, lammpsio, lammpskit (PyPI + `simantalahkar/lammpskit`), pylammps (PyPI) | smaller I/O and workflow helpers; the last two took the names we could not use | various | on PyPI (2026-09-06) | read in plan 1b for `docs/11-ecosystem.md`; nothing taken |
| `Chenghao-Wu/skill_lammps`, `chatmaterials/lammps-workflows`, `SciMate-AI/HPC-Skills` | agent-skill and workflow repositories around LAMMPS | see each repo | found by the GitHub name search (2026-09-06) | ours ships verified code (tests against real LAMMPS output, measured records), a teaching engine and a course; read in full in plan 1b |

What the comparison means for the product: the one thing nobody in this list does is *verify* —
parsers tested against files the binary wrote, install routes measured, mdlite cross-checked at
stated precision, a checker whose rules cite the manual. That is the product's reason to exist.
