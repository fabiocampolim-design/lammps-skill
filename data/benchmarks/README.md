# data/benchmarks — reference tables with provenance

A value enters a file here only with its source. Every file has a `provenance` block (`source`,
`url`, `retrieved` date, `licence`, `note`) and an `entries` map of `{key: {value, error, units,
meaning}}`. `lammpskill.post.load_benchmark(name)` refuses a file without both blocks;
`lammpskill.post.compare(value, entry)` judges a result against an entry (default tolerance 2 sigma of
the stated uncertainty).

| File | What | Origin | Licence |
|---|---|---|---|
| `nist_lj.json` | Lennard-Jones fluid reference data: reduced pressure and energy at fixed (T*, rho*) state points | NIST Standard Reference Simulation Website (SRSW) | US Government work, public domain |
| `eam_cu.json` | fcc Cu lattice constant and cohesive energy: fitting targets of the u3 EAM potential and the experimental values | Foiles, Baskes & Daw 1986 (doi:10.1103/PhysRevB.33.7983); Kittel | facts, cited |

The measured cross-checks (mdlite vs LAMMPS, mdlite vs NIST) are **records**, not benchmarks: they
live in `data/records/` and carry the residue at the precision it was measured plus the route,
version and date that produced them (playbook S4).

No potential file, example input or manual text from LAMMPS is stored here or anywhere in this
repository.
