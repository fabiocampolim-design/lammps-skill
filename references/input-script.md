# Input scripts — what `lammpskill.script` writes and checks

Written from the manual's *Commands_structure* / *Commands_parse* pages and from what LAMMPS accepted
on this machine; no example script is copied.

## How LAMMPS reads a line (as observed)

One command per line; the first word is the command, the rest are its arguments; `#` starts a
comment; `&` at the end continues a line; `${name}` / `$x` substitute variables; blank lines are
ignored. Commands act in order: a `pair_coeff` before its `pair_style` is an error, `pair_modify` and
`dump_modify` must follow the `pair_style` / `dump` they modify, masses must be set before
`velocity … create`, and everything about the system (box, atoms) must exist before settings that
refer to it.

## The four sections `render()` writes

1. **initialization** — `units`, `dimension`, `boundary`, `atom_style` (`Spec.pre` lines go before).
2. **system definition** — `lattice`, `region`, `create_box`, `create_atoms` *or* `read_data`; `mass`.
3. **settings** — `pair_style` + `pair_coeff`, bond/angle/dihedral styles and coefficients,
   `kspace_style`, `special_bonds`, `neighbor`, `neigh_modify`, `timestep`, `group`, `velocity`,
   `compute`, `fix`, `dump`, `thermo`, `thermo_style`, `thermo_modify`.
4. **run** — the `stages` (`run N` / `minimize …` in order), `write_data`, then `Spec.post` lines.

Anything `Spec` has no field for (`pair_modify`, `dump_modify`, `variable`, `region` beyond the box,
`fix_modify`, `restart`, `read_restart`) goes in `pre` / `post`, or is inserted into the rendered text
right after the command it modifies (`scripts/run_benchmarks.py` does exactly that for `pair_modify
shift yes` and `dump_modify … format float %20.15g`).

## Presets (parameters cited in `references/benchmarks.md`)

| preset | system | force field | what it is for |
|---|---|---|---|
| `lj_melt(n, rho, T, steps, rc)` | fcc lattice of LJ atoms, reduced units, `fix nve` | `lj/cut` | the probe, the first run, chapters 01–03 |
| `eam_fcc(element, a, n, potential, T, steps, minimize)` | fcc metal, `units metal`, `fix box/relax` minimisation and optional NVT | `eam` (funcfl) or `eam/alloy` (setfl) by extension | chapter 05, the EAM cross-check |
| `spce_water(n_side, spacing, T, steps, workdir)` | rigid SPC/E water on a cubic lattice with random orientations, written as a `full`-style data file | `lj/cut/coul/long` + `pppm`, `fix shake`, `fix nvt` | chapter 06 (ran in LAMMPS 10 Dec 2025: 8 molecules, 20 steps, no errors) |

SPC/E geometry and charges: O–H 1.0 Å, H–O–H 109.47°, q_O = −0.8476, q_H = +0.4238,
ε_OO = 0.1553 kcal/mol, σ_OO = 3.166 Å (Berendsen, Grigera & Straatsma, J. Phys. Chem. 91, 6269 (1987)).

## The checker (`check(text, workdir=None)`)

Each finding is `Finding(level, code, message, line, manual)`; the manual page is the one to read.
`lammpskill check FILE` exits 1 on any `error`.

| code | level | manual page | what it catches |
|---|---|---|---|
| C01 | warning | units | no `units` (the silent default is `lj`) |
| C02 | error | kspace_style | a long-range pair style (`*/coul/long`, `*/long`, `coul/msm`, `coul/dsf`) without `kspace_style` |
| C03 | error | kspace_style | `kspace_style` without a long-range pair style |
| C04 | warning | timestep | timestep above the usual limit for the units (lj 0.01, real 2.0, metal 0.005) |
| C05 | error | run | `run`/`minimize` before any `pair_style` |
| C06 | error | pair_coeff | `pair_coeff` before `pair_style` |
| C07 | error | fix | a fix ID reused without `unfix` |
| C08 | warning | atom_style | bonded atom style without `read_data` / `read_restart` / `molecule` |
| C09 | warning | thermo | `thermo N` larger than the following `run M` |
| C10 | warning | dump | dump interval larger than the whole run |
| C11 | error | velocity | `velocity … create` before every type has a mass |
| C12 | info | timestep | no `timestep` (the units' default applies) |
| C13 | info | write_data | nothing written at the end |
| C14 | error | read_data | the `read_data` file is not in the working directory |

What it does **not** check yet (plan 1b candidates, from the manual's *Errors_messages* page): group
names that do not exist, `pair_coeff` type ranges beyond `create_box`, `fix shake` on non-bonded
styles, `kspace_style` with non-periodic boundaries, `boundary` vs `region` mismatch.
