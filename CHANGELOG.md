# Changelog

All notable changes to lammps-skill. Format: Keep a Changelog; versions: SemVer.

## 0.1.6 — 2026-09-07

The weekly upstream watch (playbook S8 / rule 23).

- New `scripts/watch_upstream.py`: `--snapshot` records a baseline, `--weekly [--pull]` writes
  `docs/watch/YYYY-WW.md` with what moved on GitHub (head, releases, open issues and PRs), which
  upstream pages changed, new matsci.org topics and new PyPI versions. Every source is wrapped --
  an unreachable one is reported, never raised, because a watch that dies when a forum is down is
  not a watch. Idempotent within a week, and a second run never empties the week's report.
- New `scripts/register_watch_task.ps1`: registers it as a **hidden** weekly Scheduled Task that
  logs to a file (KEEP rules/12), with `-DryRun` and `-Remove`.
- Two defects the first live run exposed, both fixed and tested:
  `www.lammps.org/download.html` is a 252-byte meta-refresh stub, so that sensor hashed to **one
  word** and could never have fired -- the URL is the canonical `/download/` now, and any watched
  page under `MIN_PAGE_WORDS` visible words is reported as a warning. And GitHub's `/tags` is not
  date-ordered (the live call returned `stable_31Mar2017` first), so a new tag can fall outside the
  window: the release signal is `/releases`, which is ordered and covers every tag LAMMPS tags.

## 0.1.5 — 2026-09-07

Two misclassifications the first full `examples/` sweep made, both found by reading its output
rather than its exit status.

- **N-24:** upstream's examples link their potentials *relatively* --
  `examples/snap/Ta06A.snap -> ../../potentials/Ta06A.snap`. `cp -r` copied the link, whose target
  does not exist under the scratch root, so 12 snap/mliap cases failed with "Cannot open input
  script Ta06A.snap" while `ls` showed the name sitting right there. The copy is `cp -rL` now, and
  those cases report what is actually true of the build: `missing-package: ML-SNAP`.
- **N-23:** not every case opens a thermo block. `examples/voronoi` checks itself with `print`,
  runs no dynamics, finishes in 6 s -- and was scored `no-run`, which reads as a failure. A log that
  reached LAMMPS's `Total wall time:` line with no error is now `ok-no-thermo`.

## 0.1.4 — 2026-09-06

Fixes the `$LAMMPS_POTENTIALS` prefix 0.1.3 introduced, and adds the guard that would have caught it.

- **N-22:** the prefix was a bare `LAMMPS_POTENTIALS=... lmp`, but `build_command` runs the
  executable under `timeout`, which execs its argument directly -- so the assignment became the
  program name ("timeout: failed to execute process") and 191 consecutive cases were scored
  `no-run` before anyone looked. It is `env LAMMPS_POTENTIALS=... lmp` now. Verified on the four
  `vashishta` cases, which failed with "cannot open vashishta potential file" before and pass now.
- New `early_abort_reason`: a sweep whose first five cases are *all* `no-run` stops with an
  explanation and exit code 3, instead of writing hundreds of rows of nothing.

## 0.1.3 — 2026-09-06

- `scripts/run_examples.py` exports **`$LAMMPS_POTENTIALS`** into the run (new `--potentials`,
  default `<root>/potentials`). Without it, 20+ cases of the first full sweep came back as
  `error: cannot open sw potential file Si.sw` -- which reads like a broken example but was a
  missing environment variable (finding N-20). The variable is prefixed to the executable, because
  a Windows `env=` never crosses the `wsl.exe` boundary; the `mpirun` prefix now takes the same path.
- `classify` distinguishes **`timeout-after-start`** from `timeout`: a case that wrote thermo rows
  before the sweep's cap does run on that route, it is only longer than a sweep allows.
- `references/platforms.md` and `docs/USER_MANUAL.md` corrected: the reference machine has **16 GB**
  of host RAM (15.9 usable), of which the WSL2 VM is given 7.7 GB -- earlier notes reported the VM's
  share as the host's. The manual now also lists `multi` among the thermo styles `read_log` parses.

## 0.1.2 — 2026-09-06

LAMMPS's own `bench/` cases now run here on both live routes and are compared against the reference
logs upstream ships with them: `lj`, `chain` and `eam` reproduce every printed digit on both routes
at 1 and 4 processes, and `rhodo` agrees to 4e-9 (one unit in the last printed digit of `TotEng`);
`chute` is the one case the `core` source build cannot run, for want of GRANULAR. Recorded in
`docs/04-examples-run-log.md` (study side).

- New `scripts/run_examples.py`: sweeps `bench/` or `examples/` on one route, copying each case out
  of the installed tree (upstream inputs are never redistributed by this project) and recording the
  outcome as `ok` / `missing-package` (naming the package) / `error` / `timeout` / `no-run`, plus a
  column-by-column comparison against upstream's reference log where one exists. Timing columns are
  recorded but never drive the verdict -- they measure the machine that wrote the reference.
- `lammpskill.io.log.parse_log` understands **`thermo_style multi`** (finding N-18): `bench/in.rhodo`
  uses it, ran for 42 s, and was scored "no thermo output" by a parser that knew only `one` and `yaml`.
- Four defects fixed test-first while building the sweep: it scores on the log because both builds
  here exit 0 after a fatal input error (N-15); discovery runs in the shell that owns the tree, since
  Windows Python cannot see an ext4 path (N-16); the scratch root is resolved to an absolute path,
  because `build_command` single-quotes the working directory and `cd '$HOME/...'` never expands
  (N-17); and discovery is one `find` instead of one `wsl.exe` launch per directory (N-19).

## 0.1.1 — 2026-09-06

The `wsl-source` route is live: `stable_22Jul2025_update6` built with the `core` preset on WSL2
Ubuntu 26.04 (11 packages, MPI, OpenMP, shared library, python module), measured at 1.38 s on the
LJ-melt probe and recorded in `references/platforms.md`. Getting there found four defects in our
installer and detection, each fixed with a failing test first, and one upstream candidate (P-1).

- `scripts/install_lammps_wsl.sh` (source route): install RPATH so the installed `lmp_<preset>` finds
  `liblammps_<preset>.so` (N-11); the python module goes into `~/.local/venv-lammps-<preset>` through
  upstream's `python/install.py` with the venv activated and run from the build directory, because
  `--target install-python` is refused by PEP 668 distributions (N-10, P-1); the verify step loads the
  module with `name=<preset>` (N-12). New step name `python-module` in the status list.
- `lammpskill.install`: `detect_in_wsl` takes an optional `python_query` (the source route's module
  lives in a venv, not in the system python3); it derives the machine name from `lmp_<machine>`,
  probes the module by **constructing** `lammps.lammps(name=<machine>)` instead of importing, records
  it as `Installation.extra["machine"]`, and asks only for that route's own library so an apt row is
  not shadowed by a source build (N-12, N-13). `wsl_source.cmake_command` emits the RPATH flags.
- References: `install-routes.md` §2 documents the three deviations from the manual's build page;
  `platforms.md` gains the measured `wsl-source` row; `pitfalls.md` gains four entries.

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
