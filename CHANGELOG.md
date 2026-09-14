# Changelog

All notable changes to lammps-skill. Format: Keep a Changelog; versions: SemVer.

## 0.1.15 — 2026-09-14

Atom visuals, Phase 1 of the roadmap in
`docs/superpowers/specs/2026-09-14-lammps-skill-atom-visuals-design.md`: `lammpskill/viz.py`
(headless atom snapshots and animated GIFs, ASE + matplotlib, no new dependency; OVITO stays
pinned) and the course pipeline's extension to carry GIF figures with the same provenance/caption
discipline as PNGs. Chapter 01 gets a real snapshot and a real animation of its own LJ melt (a
200-atom, 10-frame subsample of the real 4000-atom run -- kept small the way chapter 6 already
learned to, not the full trajectory), rendered as argon-like spheres since reduced LJ units carry
no real element. Folded into course lecture L1 as a new slide (56 slides now, was 55).
`tests/test_chapters.py`'s caption guard now recognises `display(Image(filename=...))` (a GIF
embed) alongside `plt.show()`. Fixed three more hardcoded `.png` lookups the new GIF figure
exposed, beyond the one built for it: `build_deck.py`'s `render_handout()` and `render_notes()`,
and two tests in `test_course.py` -- all four now resolve the real extension. The other five
roadmap items (a Cu vacancy in chapter 05, new chapters for water and a polymer chain, four more
chapter retrofits, two new course lectures) remain future work, each its own brainstorm-and-spec
pass.

## 0.1.14 — 2026-09-14

Course content (rule 22, Plan B of
`docs/superpowers/plans/2026-09-13-lammps-skill-course-content-plan-b.md`): every lecture now runs
its full intro → core → math depth. The deck grows from twelve slides (one per lecture, Plan A)
to fifty-five, sized to what each chapter's own material supports — L0 (Orientation) gets six,
L10 (Scaling and Limits) gets four, most lectures get five. No new figures: L2 (Forces and
Integration), L5 (Potentials: EAM) and L7 (Minimisation) — the three lectures whose chapters plot
nothing — use `eq`/`code`/`table` layouts for their depth instead (owner's decision, 2026-09-13),
matching the content's actual shape rather than manufacturing a plot to satisfy the rule. Every
equation (central-difference forces, velocity Verlet, the Berendsen thermostat and barostat, the
Nosé–Hoover chain's conserved quantity, the EAM energy form, the steepest-descent displacement
cap) was checked against the actual `mdlite` implementation before being written into a slide, not
taken from a textbook in the abstract. `tests/test_course.py`'s level-ordering guard is tightened:
every lecture stack must now end in a `math`-level slide unconditionally (Plan A's single-slide
escape hatch is gone). 55 slides, 65 PDF pages (55 + 10 dividers).

## 0.1.13 — 2026-09-13

Course infrastructure (rule 22, plan A of
`docs/superpowers/plans/2026-09-13-lammps-skill-course-infra.md`): `course/` now has a working
reveal.js deck, A4 handout, lecturer notes and a committed PDF fallback, built the same way as
pythtb-skill's course (`content.en.js` → `build_deck.py` → `index.html`/handout/notes;
`extract_figures.py` → `deck/figs/*.png` + `provenance.json`). New: a `caption()` retrofit on
the four chapters that already plot a figure (01, 03, 04, 06 — 00/02/05/07/08/09/10 still have
none), figures named by chapter key (`ch01-f1`) rather than a numbered section since chapters
are self-contained; `course/shared/` (vendored reveal.js 5.2.0, MIT) and
`course/tools/{extract_figures,build_deck,make_slides_pdf,make_handout,verify_deck,build_pptx}.py`.
Eleven lectures locked 1:1 with the eleven chapters; Plan A ships one real slide per lecture
(twelve total — L6 gets a second, since it has three figures, not one — four of them showing
the four captured figures) — the intro → core → math depth per lecture is Plan B, not yet
started. `tests/test_course.py` guards the whole contract (content is strict JSON, every figure
has provenance and a real caption, generated outputs are fresh, the PDF page count matches the
deck, the vendored MIT licence is intact and named in NOTICE).

## 0.1.12 — 2026-09-08

Chapters 07 and 10 -- minimisation and scaling. **Plan 1b's chapter set is now complete: all
eleven chapters, 00 through 10.**

- `build/chapter07_minimisation.py` → `chapters/LAMMPS_07_Minimisation.ipynb`: N-7 reproduced on
  purpose (two atoms at r=0.3 sigma, `dmax` effectively disabled -- `fmax` explodes, matching the
  original bug), then the fix (the default `dmax=0.05` cap) on the same geometry; steepest descent
  vs FIRE on a perturbed FCC lattice. Runs with no LAMMPS installed.
- `build/chapter10_scaling_limits.py` → `chapters/LAMMPS_10_Scaling_And_Limits.ipynb`: MPI (1 vs 2
  ranks) and OpenMP (2 threads) speed-up on the chapter-01 LJ melt case, with the chapter stating
  upfront that the measurement itself is bounded by this session's KEEP compute-sharing claim (2
  cores) rather than the host's full core count; no GPU and no `-partition` methods, said plainly.
  **Record `lj_scaling_ch10`, run live** (wsl-apt): 2 MPI ranks 1.73x, 2 OpenMP threads 2.09x --
  sub-ideal MPI scaling on a small (4000-atom) case is the honest result, not a bug.
- `build/assemble.py`: `_SPEC` now lists all eleven chapters, 00-10.

343 tests green (335 -> 343), 5 skipped, pyflakes clean, all eleven notebooks executed on the
lammps-mc kernel and stay well under the rule-25 size cap, conformance PASS=23 FAIL=0.

## 0.1.11 — 2026-09-08

Chapter 04 -- ensembles and restarts, and the mdlite NPT sketch (plan 1b, task 4 complete: 00-06,
08, 09 all written; only 07 and 10 remain).

- New `mdlite/npt.py`: `BerendsenBarostat` + `velocity_verlet_npt`, an NPT *sketch* by weak coupling
  on temperature and pressure (Berendsen et al. 1984) -- explicitly not a fluctuating-cell method,
  documented as not sampling the isothermal-isobaric ensemble correctly. `tests/test_mdlite_npt.py`:
  a compressed system expands toward a lower target pressure and vice versa, particle count and
  output stay finite, and the barostat's `mu()` moves the right direction at both signs of `P0-P`.
- `lammpskill/script.py`: `Spec.units` accepts `None` to omit the whole initialization block (units,
  dimension, boundary, atom_style) -- found live while writing this chapter: LAMMPS refuses each of
  those once `read_restart` has already defined the box (`ERROR: Units command after simulation box
  is defined`, then the same for `dimension`). `tests/test_script.py` pins the new behaviour and
  that the checker's C01 ("no units") still fires, honestly, since it cannot know a restart supplied
  one.
- `build/chapter04_ensembles_restarts.py` → `chapters/LAMMPS_04_Ensembles_And_Restarts.ipynb`: the
  mdlite NPT sketch (with its limits stated in the chapter text) next to LAMMPS's own `fix npt`;
  restart continuation through a `Spec` with `read_restart` in `pre` and `units=None`. **Records
  `lj_npt_ch04` and `lj_restart_ch04`, both run live** (wsl-apt): `fix npt` expanded a compressed
  500-atom system from V=455 toward V=1067 (target P=1.0, reached P=1.20); the restart continued
  cleanly from step 300 (T=1.036) to step 600 (T=1.019).
- `build/assemble.py`: `_SPEC` now lists nine chapters (00-06, 08, 09) -- every chapter in the plan
  except 07 (minimisation) and 10 (scaling), both still open.

## 0.1.10 — 2026-09-08

Chapters 05 and 06 -- EAM and structure/analysis (plan 1b, task 4 partial: 04 still open, it needs
a new mdlite NPT sketch first).

- `build/chapter05_potentials_eam.py` → `chapters/LAMMPS_05_Potentials_EAM.ipynb`: why the
  potential file is fetched, never shipped (rule 7); `mdlite.eam.EAM` forces vs a numerical
  derivative and the cubic-fit-of-E(a) lattice-constant method, both on `synthetic_setfl` so the
  chapter runs with no real potential file present; the real-copper `eam_cu_lattice` record
  (da=3.46e-5, de=2.75e-5 against LAMMPS) read back to close the loop.
- `build/chapter06_structure_analysis.py` → `chapters/LAMMPS_06_Structure_And_Analysis.ipynb`:
  g(r), S(k) computed from it, MSD and the diffusion coefficient, VACF, and a block-averaged
  temperature, all from one dumped trajectory. **Record `lj_structure_ch06`, run live** (wsl-apt,
  864 atoms, 101 frames) -- redesigned mid-task after the first version stored the raw trajectory
  (8.8 MB of committed JSON for no benefit a plot doesn't already give); the analysis now runs
  inside `compute()` and only the reduced arrays (12.8 KB) leave it.
- `build/assemble.py`: `_SPEC` now lists eight chapters (00, 01, 02, 03, 05, 06, 08, 09); 04 is the
  one gap in the 00-10 range until the NPT sketch lands.

## 0.1.9 — 2026-09-08

Chapters 01, 02, 03 — the core physics, with live records (plan 1b, task 3 complete).

- `build/chapter01_first_simulation.py` → `chapters/LAMMPS_01_First_Simulation.ipynb`: an LJ melt
  end to end -- `Spec` → `render` → `check` → `run_or_load` → plot. All 14 checker rules are each
  triggered by their own minimal, deliberately-broken snippet before the clean preset (which draws
  only its two documented `info` findings) is run for real. **Record `lj_melt_ch01`, run live**
  (wsl-apt, 10 Dec 2025, 4000 atoms, 250 steps, 0.68 s) -- the same case `tests/fixtures/log_lj_melt.lammps`
  already carries.
- `build/chapter02_forces_integration.py` → `chapters/LAMMPS_02_Forces_And_Integration.ipynb`:
  `mdlite` forces vs a numerical derivative, energy-drift scaling with the timestep, then the
  existing `lj_energy_vs_lammps` record (dF=3.16e-13) read through the same `run_or_load` path.
- `build/chapter03_thermostats.py` → `chapters/LAMMPS_03_Thermostats.ipynb`: Berendsen, Langevin
  and Nosé–Hoover side by side (what each conserves, what each distorts), the Nosé–Hoover
  extended-energy check, the `lj_nvt_nist` record read back, and LAMMPS's own `fix nvt`.
  **Record `lj_nvt_ch03`, run live** (wsl-apt, 864 atoms, 1000 steps: <T> over the last quarter
  1.008 against a target of 1.0).
- `build/assemble.py`: `_SPEC` now lists six chapters (00, 01, 02, 03, 08, 09).
- Compute claimed under KEEP rules/13 (2 cores, 4 GB) for the two live LAMMPS runs this task made.

## 0.1.8 — 2026-09-08

Chapters 08 and 09 — the rest of the no-LAMMPS chapters (plan 1b, task 2 complete).

- `build/chapter08_reading.py` → `chapters/LAMMPS_08_Reading_What_LAMMPS_Writes.ipynb`: data, dump,
  log (`one`/`multi`/`yaml`) and restart-header formats, each demonstrated from a fixture already in
  the test suite, plus the four pitfalls that cost this project time -- N-4 (`thermo_modify norm`
  defaults to per-atom in `units lj`), N-5 (the dump's default 6-digit float format capped a force
  cross-check at 5e-5; `dump_modify ... format float %20.15g` took it to 3e-13), N-6 (the restart
  magic string's on-disk field is one byte longer than the string itself -- a NUL terminator that
  has to be consumed even though it isn't compared), N-18 (`parse_log` learned the `multi` thermo
  style block). Runs with no LAMMPS installed.
- `build/chapter09_choosing_build.py` → `chapters/LAMMPS_09_Choosing_A_Build.ipynb`: the 314-case
  `docs/04` examples sweep, as data the chapter and its tally both read -- both builds match
  upstream's own reference logs; **package list beats package count** (ten cases run on the
  11-package source build that the 52-package apt build cannot); the POEMS package removed upstream
  the same day as the `stable_22Jul2025` tag, so the same style is `missing-package` on one route and
  `no longer available` on the other. Runs with no LAMMPS installed.
- `build/assemble.py`: `_SPEC` now lists three chapters (00, 08, 09).

## 0.1.7 — 2026-09-07

The chapter build system and the first chapter (plan 1b, task 1-2).

- `build/nbbuild.py`, `build/assemble.py`, `build/execute.py`: chapters are **generated** from
  `build/chapterNN_*.py` -- a correction is made once, in Python, and re-assembled. Each notebook
  gets a contents header, a Setup cell, and a **generated tally cell that asserts what the chapter
  claimed**, so a chapter that stops being true fails when executed rather than quietly misleading.
- `chapters/LAMMPS_00_Orientation.ipynb`: the two release lines and why the update number is part
  of the version; **package list, never package count** -- demonstrated live on this machine, where
  the 52-package Ubuntu build lacks EXTRA-FIX and the 11-package source build has it; what the
  toolkit adds; and **how `mdlite` differs from pylj**, which `docs/09` identified as its closest
  neighbour. Runs with no LAMMPS installed.
- `tests/test_chapters.py` guards the generator: chapter shape, the pinned `lammps-mc` kernel, the
  rule-25 size cap, no committed outputs from `assemble`, every `##` section listed in the contents,
  and that a chapter marked "runs anywhere" never reaches for the runner.

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
