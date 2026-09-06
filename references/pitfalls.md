# Pitfalls — what LAMMPS says, why, and the fix

Two lists: the input-script mistakes the checker catches (`lammpskill check FILE`, codes C01–C14, each
with its manual page) and the operational pitfalls met while building this product, each dated.

## Checker codes

- **C01** no `units`: LAMMPS silently uses `lj`; every coefficient you typed in real or metal units is
  then wrong by orders of magnitude. Fix: `units …` as the first command.
- **C02** long-range pair style without `kspace_style`: "Pair style requires a KSpace style". Fix:
  `kspace_style pppm 1.0e-4` (or `ewald`) after the pair style.
- **C03** `kspace_style` without a long-range pair style: "KSpace style is incompatible with Pair
  style". Fix: use `*/coul/long` or drop the kspace.
- **C04** timestep above the usual limit (lj 0.01, real 2.0 fs, metal 0.005 ps): atoms overshoot, the
  energy drifts or LAMMPS reports lost atoms. Fix: smaller step, or SHAKE/rigid for the fast bonds.
- **C05** `run`/`minimize` before any `pair_style`: "Pair style must be defined". Fix: order.
- **C06** `pair_coeff` before `pair_style`: "Pair_coeff command before pair_style is defined". Fix: order.
- **C07** duplicate fix ID: "Replacing a fix, but new style != old style" or a silent replacement.
  Fix: distinct IDs or `unfix` first.
- **C08** bonded atom style with no data file or molecule: nothing can define the bonds. Fix:
  `read_data`, `read_restart` or `molecule` + `create_atoms`.
- **C09** `thermo N` larger than the run: no thermo rows at all, the log parser finds no run. Fix: smaller `thermo`.
- **C10** dump interval larger than the run: an empty dump file. Fix: smaller interval.
- **C11** `velocity … create` before every mass is set: "All masses are not set". Fix: `mass` for every
  type (or `mass * …`) before `velocity`.
- **C12** no `timestep`: the units' default applies (lj 0.005, real 1.0, metal 0.001) — fine when you know it.
- **C13** nothing written at the end: the run leaves no structure behind. Fix: `write_data`, `write_restart` or a dump.
- **C14** `read_data` file missing from the working directory: "Cannot open file". Fix: path.

## Operational pitfalls (dated)

- **2026-09-06 — `thermo_modify norm` defaults to *yes* in `units lj`.** `pe` in the thermo output is
  the energy *per atom*; comparing it with a total energy gave −6.04 vs −1545.7 in the first LJ
  cross-check. Fix: `thermo_modify norm no` (the preset in `run_benchmarks.py` does this).
- **2026-09-06 — dump floats have 6 significant digits by default.** Forces read back from a dump
  disagreed with mdlite at 5e-5; `dump_modify <id> format float %20.15g` brought it to 3e-13.
- **2026-09-06 — `pair_modify` / `dump_modify` must follow the command they modify.** A `Spec` has no
  field for them; insert them into the rendered text after the `pair_coeff` / `dump` line.
- **2026-09-06 — the apt build is the 10 Dec 2025 feature release**, not the yearly stable; its `-h`
  lists 52 packages without EXTRA-FIX / EXTRA-MOLECULE / EXTRA-DUMP / REAXFF / ML-*. Check
  `Installation.packages` before choosing styles; build from source for the rest.
- **2026-09-06 — the PyPI `lammps` wheel on Windows needs MS-MPI.** `liblammps.dll` imports
  `msmpi.dll`; `import lammps` fails with "Could not find module … (or one of its dependencies)" until
  the Microsoft MPI runtime is installed (finding N-2). The wheel also installs an `lmp.exe` with the
  same dependency.
- **2026-09-06 — restart files start with a 16-byte NUL-terminated magic string** (`LammpS RestartT\0`),
  then the endianness word, a revision integer and the version record; the rest is undocumented —
  read it through LAMMPS (`read_restart` + `write_data`).
- **2026-09-06 — `lmp -h` prints each style list after a blank line**; a parser that stops at the first
  blank line after `* Atom styles:` sees nothing. The `Installed packages:` block has the same shape.
- **2026-09-06 — every WSL or LAMMPS process must start hidden.** From Python: `CREATE_NO_WINDOW`,
  `stdin=DEVNULL`, output captured; never `DETACHED_PROCESS` for `wsl.exe` (it opens its own console).
- **2026-09-06 — `timeout` inside the WSL command line**, not only on the Windows side: killing
  `wsl.exe` does not kill `lmp` inside WSL; `run_command` wraps the executable with GNU `timeout`.
- **2026-09-06 — a fixed-step steepest descent explodes on a Lennard-Jones wall** (fmax 2.6e14 after
  200 steps at α = 0.01). Cap the displacement (`dmax`) or use FIRE; that is the point of chapter 01.
