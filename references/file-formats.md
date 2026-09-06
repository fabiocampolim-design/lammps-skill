# File formats — what `lammpskill.io` reads and writes

Every reader here was written from the manual's description of the format and validated against files
LAMMPS (10 Dec 2025, wsl-apt) wrote on this machine; nothing was transcribed from the LAMMPS source.

## Data files (`io.data`) — `read_data` / `write_data`

- Line 1 is a free comment (LAMMPS writes "LAMMPS data file via write_data, version …").
- Header: `N atoms`, `N atom types`, optional `N bonds/angles/dihedrals/impropers` and their `types`,
  the box as `xlo xhi`, `ylo yhi`, `zlo zhi` lines and an optional `xy xz yz` tilt line.
- Sections start with a keyword line (`Masses`, `Pair Coeffs # lj/cut`, `Atoms # atomic`, `Velocities`,
  `Bonds`, `Angles`, `Dihedrals`, `Impropers`, the `* Coeffs` families) followed by a blank line.
- `Atoms # style` names the atom style; without the comment `read_data(path, atom_style=…)` must be
  told. Column layouts implemented (`ATOM_STYLE_COLUMNS`): atomic `id type x y z`; charge `id type q x y z`;
  bond / angle / molecular `id mol type x y z`; full `id mol type q x y z`; sphere `id type diameter
  density x y z`. Three trailing integers are image flags (`ix iy iz`) and are kept.
- Coefficient sections are kept as raw lines (`DataFile.coeffs["Pair Coeffs"]`) and written back unchanged.
- The writer produces the canonical layout (header, box, Masses, coeffs, Atoms, Velocities, topology);
  `test_round_trip_through_lammps_itself` writes a file, has LAMMPS read and re-write it, and compares.

## Dump files (`io.dump`) — `dump atom` / `dump custom`, text

`ITEM: TIMESTEP` / `ITEM: NUMBER OF ATOMS` / `ITEM: BOX BOUNDS pp pp pp` (three `lo hi` lines; with
`xy xz yz` in the header the three lines carry the tilt and the bounds include it — the manual's
*Howto_triclinic* relation `xlo_bound = xlo + min(0, xy, xz, xy+xz)` etc. is inverted by the reader) /
`ITEM: ATOMS <columns>` and one row per atom. Frames are returned sorted by id. `positions` picks
`x y z`, else `xu yu zu`, else `xs ys zs` (scaled → cartesian through the box). `.gz` files are read
transparently. The writer emits the same blocks; the default float format of LAMMPS's own dump is
**6 significant digits** — use `dump_modify <id> format float %20.15g` when the numbers matter
(`scripts/run_benchmarks.py`).

## Log files (`io.log`) — thermo output

- `one` style: a header line whose first token is `Step`, then numeric rows with the same number of
  columns; a run ends at `Loop time of T on P procs for N steps with M atoms`, which also gives
  `nprocs`, `nsteps`, `natoms`. Several runs per log are kept in order (`LogFile.runs`, `.thermo` = last).
- `yaml` style (`thermo_modify line yaml` / `thermo_style yaml`): a block from `---` with
  `keywords: [...]` and `data:` rows `- [...]` to `...`.
- `WARNING:` and `ERROR:` / `ERROR on proc` lines are collected; the version from `LAMMPS (…)`;
  `Created N atoms` sets `natoms` before any run.
- **Pitfall** (found 2026-09-06): with `units lj` LAMMPS normalises thermo energies per atom by default
  (`thermo_modify norm yes`); `pe` is then the energy per atom, not the total. Say `thermo_modify norm no`
  when you mean the total.

## Restart files (`io.restart`)

Binary; the manual says the format is neither portable nor documented, so only the header is read:
the magic string `LammpS RestartT` (observed as a 16-byte NUL-terminated string), the endianness word,
a revision integer, then the first record (`flag 0`, length, the version string, e.g. "10 Dec 2025").
Everything else — atoms, box, styles — is obtained through LAMMPS itself: `read_restart` then
`write_data`, run through `lammpskill.run`.

## EAM potential files (`io.potential`)

- **setfl** (`pair_style eam/alloy`, `eam/fs`): three comment lines; `Nelements el1 el2 …`;
  `Nrho drho Nr dr cutoff`; per element `Z mass a0 lattice`, then Nrho values of F(ρ), then Nr values
  of ρ(r); then one block of Nr values of r·φ(r) per element pair in the order (0,0), (1,0), (1,1),
  (2,0), (2,1), (2,2) … (`EAMSetfl.pair_index`). The writer reproduces this layout; LAMMPS accepted a
  synthetic file we generated (`test_synthetic_potential_is_accepted_by_lammps`).
- **funcfl** (`pair_style eam`, single element): comment; `Z mass a0 lattice`; `Nrho drho Nr dr cutoff`;
  F(ρ), then Z(r) (effective charge), then ρ(r); converted to setfl with r·φ = Z² · 27.2 · 0.529
  (Hartree·Bohr → eV·Å, the manual's convention). `Cu_u3.eam` read this way gives a0 and Ecoh that
  agree with LAMMPS to 3e-5 (`data/records/eam_cu_lattice.json`).
- Potential files are found by LAMMPS in the case directory or under `LAMMPS_POTENTIALS`; the apt
  route installs them under `/usr/share/lammps/potentials`. None is redistributed by lammps-skill.
