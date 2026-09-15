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
- **2026-09-06 — a CMake install to `$HOME/.local` needs an install RPATH.** `~/.local/lib` is not on
  the loader path: `lmp_core` printed nothing and exited 0 until the build passed
  `-D CMAKE_INSTALL_RPATH=$HOME/.local/lib` (finding N-11). Check with `ldd $(which lmp_core)`.
- **2026-09-06 — `cmake --build . --target install-python` fails on PEP 668 distributions.** It
  pip-installs into system site-packages; Ubuntu 26.04 answers "This environment is externally
  managed" and the build target fails after the wheel is built. Install into a venv instead — and
  *activate* it: upstream's `python/install.py` decides where to install from the `VIRTUAL_ENV`
  environment variable, not from `sys.prefix`, so running it with the venv interpreter alone still
  targets the system (findings N-10, P-1). It also resolves the wheel relative to the current
  directory, so run it from the build directory.
- **2026-09-06 — a build made with `LAMMPS_MACHINE=<m>` needs `lammps.lammps(name="<m>")`.** The
  library is `liblammps_<m>.so`; with no name the module falls back to the system `liblammps.so` and
  silently binds a different LAMMPS — here the apt build, which raised "LAMMPS Python module installed
  for LAMMPS version 20250722, but shared library is version 20251210" (finding N-12). A module that
  imports is not a module that works: probe it by constructing.
- **2026-09-06 — with two builds installed, ask each route for its own library.** One `ls` over
  `/usr/lib/...` and `$HOME/.local/lib/...` sorts `$HOME` first, so the apt row reported the
  source-built library (finding N-13).
- **2026-09-06 — LAMMPS exits 0 after a fatal input error.** `nonsense_command 1 2 3` prints
  `ERROR: Unknown command` and returns status **0** on both builds here (22 Jul 2025 update 6 and
  10 Dec 2025). Never gate anything on `lmp`'s return code: parse the log (`LogFile.errors`,
  `LogFile.runs`), which is what `Result.ok` and `run_examples.classify` do (finding N-15). The
  return code is still meaningful for one thing: `124` from `timeout`.
- **2026-09-06 — `thermo_style multi` is a different format entirely.** Not columns but
  `------------ Step N ----- CPU = t ----` followed by `Name = value` pairs; `bench/in.rhodo` uses
  it. A parser written for `one`/`yaml` silently reports "no thermo output" for a run that worked
  (finding N-18).
- **2026-09-06 — an example is its whole directory.** Inputs read data files and potentials sitting
  next to them; copying only `in.<name>` gives `ERROR: Cannot open file data.<name>`, which reads
  like a broken example. Copy the directory.
- **2026-09-06 — "missing package" is a fact about the build, not a broken case.** `ERROR:
  Unrecognized pair style 'reaxff' is part of the REAXFF package which is not enabled in this LAMMPS
  binary.` Record it as its own outcome, with the package named, or a route comparison turns into a
  list of false failures.
- **2026-09-06 — `timeout N VAR=value prog` does not work.** `timeout` execs its argument directly
  instead of going through a shell, so the assignment becomes the program name: `timeout: failed to
  execute process: No such file or directory`. Use `timeout N env VAR=value prog`. This is how an
  examples sweep scored 191 consecutive cases as "no thermo output" (finding N-22) — and note that
  the failure is silent in the usual way, because the exit status was still 0 (N-15).
- **2026-09-15 — `special_bonds` defaults to excluding directly-bonded pairs from LAMMPS's
  nonbonded sum, silently.** `special_bonds lj 0 0 0` (LAMMPS's own default) means the 1-2, 1-3 and
  1-4 neighbours along a bond topology get zero weight in the pairwise LJ energy — invisible unless
  you know to look for it, and exactly wrong for cross-checking against `mdlite`'s
  `LennardJones`/`HarmonicBond`, which sum independently over all pairs and all bonds with no
  exclusion concept at all. `lammpskill.script.bead_spring_chain()` sets `special_bonds lj 1.0 1.0
  1.0` explicitly so both engines describe the same system; any bonded `Spec` compared against
  mdlite needs the same check, the same way `thermo_modify norm no` is checked for every `units lj`
  case (N-4 above).
