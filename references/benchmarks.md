# Benchmarks and records — what is verified, at what precision

Two kinds of numbers live under `data/`:

- **benchmarks** (`data/benchmarks/*.json`): published reference values with their source, retrieval
  date and licence — `lammpskill.post.load_benchmark(name)`, `compare(value, entry)`.
- **records** (`data/records/*.json`): our own cross-checks, written by `scripts/run_benchmarks.py`
  with the residue *as measured* and a tolerance one decade above it (or 3σ of the combined
  statistical error when that is larger), plus the route, LAMMPS version and date that produced them.
  `tests/test_crosscheck.py` reads the tolerance from the record, never from a literal (playbook S4).

## NIST SRSW Lennard-Jones fluid (`nist_lj.json`)

Source: NIST Standard Reference Simulation Website (SRD 173), pages `mc.htm` (NVT Monte Carlo,
N = 500, rc = 3σ + standard long-range corrections, 5.0E7 equilibration and 2.5E8 production trials)
and `md.htm` (NVE MD, velocity Verlet, dt = 0.005, N = 500, same truncation, > 50 t* equilibration,
100 t* production). Copied by hand on 2026-09-06; US Government work, public domain. Entries carry
NIST's stated uncertainty (`+/-` columns, or the parenthesised last digit for the MD table); the MD
rows also carry the measured T* and the diffusion coefficient D*.

Tail corrections we add when comparing a truncated simulation to these numbers
(Allen & Tildesley 2017, eqs. 2.144–2.145 in reduced units):
U_tail/N = (8/3) π ρ [ (1/3) rc⁻⁹ − rc⁻³ ], P_tail = (16/3) π ρ² [ (2/3) rc⁻⁹ − rc⁻³ ].

## EAM copper (`eam_cu.json`)

Fitting targets of the "universal 3" Cu potential (Foiles, Baskes & Daw, PRB 33, 7983 (1986)):
a0 = 3.615 Å, Ecoh = −3.54 eV/atom; experimental a0 = 3.615 Å, Ecoh = −3.49 eV (Kittel). The
potential file itself (`Cu_u3.eam`, shipped with LAMMPS) is read from your installation and never
stored here. The vacancy formation energy is also among this potential's fitting targets (its
literature value, 1.29 ± 0.02 eV, is positron-annihilation data: Triftshäuser & McGervey, *Applied
Physics* 6, 177 (1975), doi:10.1007/BF00883748) — `eam_cu_vacancy.json` below agrees with it
closely because the potential was fit to reproduce it, not as an independent check.

## Records produced on this machine (wsl-apt, LAMMPS 10 Dec 2025, 2026-09-06)

| record | what | measured residue | tolerance |
|---|---|---|---|
| `lj_energy_vs_lammps.json` | 256 perturbed-fcc LJ atoms, one configuration: `mdlite.pair.LennardJones` (shifted, rc 2.5) vs LAMMPS `run 0` with `pair_modify shift yes`, forces dumped with `%20.15g` | forces max diff 3.2e-13; energy diff 3.6e-5 (the thermo print precision, ~8 significant digits) | 1e-12 / 1e-4 |
| `eam_cu_lattice.json` | fcc Cu on `Cu_u3.eam`: mdlite cubic fit of E(a) (12 points, cubic splines on the funcfl tables) vs LAMMPS `fix box/relax` minimisation | a0 3.5e-5 Å; Ecoh 2.8e-5 eV | 1e-4 / 1e-4 |
| `lj_nvt_nist.json` | mdlite Nosé–Hoover NVT, 500 atoms, T* = 0.85, ρ* = 0.776, 20 000 steps, rc 3σ + the tail formulas above, vs the NIST NVT MC entry | U* −5.5147 ± 0.0012 vs −5.5121 ± 0.0005 (diff 0.0026); P* −0.010 ± 0.008 vs 0.0068 ± 0.0018 (diff 0.017) — both within 3σ of the combined errors | 0.01 / 0.1 (3σ combined) |
| `eam_cu_vacancy.json` | fcc Cu vacancy formation energy on the same `Cu_u3.eam`, same fitted a0: mdlite FIRE-relaxed (N-1)-atom supercell (fixed volume) vs LAMMPS `region`/`group`/`delete_atoms` + `minimize`, each engine against its own perfect-lattice reference; `thermo_modify format float %.15g` (LAMMPS's default ~8-digit thermo print is coarser than the ~1e-9 eV FIRE convergence, and an earlier version of this record without the format override agreed suspiciously exactly — a print-rounding artefact, not real precision) | formation energy 1.2e-8 eV | 1e-7 |

Lessons recorded while measuring (all in `references/pitfalls.md`): `thermo_modify norm` defaults to
per-atom energies in `units lj`; the dump's default float format is 6 digits; `pair_modify` /
`dump_modify` must follow the command they modify.

## Adding a benchmark

1. Put the numbers in a new `data/benchmarks/<name>.json` with `provenance` (source, url, retrieved,
   licence, note) and `entries` (`value`, `error`, `units`, `meaning`).
2. Add a row above and, when the comparison is ours, a benchmark function in
   `scripts/run_benchmarks.py` that writes a record with `measured`, tolerances and `provenance.why`.
3. `tests/test_crosscheck.py` gets a test that reads that record.
