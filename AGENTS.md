# AGENTS.md — lammps-skill for AI agents

Product root: this directory. Run everything from here with the `lammps` conda env
(`%USERPROFILE%\miniconda3\envs\lammps\python.exe` on Windows, `conda run -n lammps python`
elsewhere; Jupyter kernel `lammps-mc`) and `PYTHONIOENCODING=utf-8` (Windows consoles are cp1252).

| Task | Command |
|---|---|
| Health check + platform table | `python scripts/verify_lammps.py --probe` |
| Fast suite | `python -m pytest tests -q` (LAMMPS-dependent tests auto-skip) |
| Static check (CI runs it first) | `python -m pyflakes lammpskill mdlite scripts tests docs` |
| Cross-check records | `python scripts/run_benchmarks.py --potential <Cu EAM file>` |
| Manual as HTML | `python docs/build_manual.py --no-pdf` |
| The command | `lammpskill <detect|verify|new|check|run|log|dump|rdf>` |

The docs guard (`tests/test_docs_guard.py`) fails when a flag below is missing from this file or
from `docs/USER_MANUAL.md`.

## Rules an agent must keep

- **LAMMPS is not included.** Detect it (`lammpskill detect`); never assume a route, a package or a
  version — read `Installation.packages` and `references/platforms.md`. Docker and remote are pinned.
- **Every process hidden.** `run_command` starts `wsl.exe` / `lmp` with no window and a `timeout`; do
  not launch LAMMPS any other way from Python.
- **Nothing from LAMMPS enters the repository**: no source, no shipped example, no potential file, no
  manual text. Program output captured as a fixture is fine.
- **Numbers carry provenance.** A benchmark has a source; a record has the measured residue and the
  route/version/date; a test reads its tolerance from the record.
- **Never assume — ask.** A gap (a licence, a platform, whether a system-wide install may run) is a
  question for the owner, never a default.

## `scripts/verify_lammps.py`

| flag | meaning |
|---|---|
| `--no-lammps` | skip route detection and probe (CI without LAMMPS) |
| `--require-lammps` | fail when no installation is detected |
| `--route {wsl-apt,wsl-source,conda,wheel,windows,docker,remote}` | detect only this route and print why it fails |
| `--probe` | run the LJ-melt probe on every detected route |
| `--steps N` | probe length in steps (default 250) |
| `--outdir DIR` | where the probe runs are written (default out/probe) |
| `--table-out FILE` | append the platform-table rows (Markdown) to this file |
| `--log-dir DIR` | audit-log directory (default: no file) |
| `-q`, `--quiet` | one summary line |
| `--version` | print `lammps-skill <VERSION>` and exit |

Exit codes: 0 all checks passed or skipped, 1 a check failed.

## `scripts/run_benchmarks.py`

| flag | meaning |
|---|---|
| `--which a,b` | benchmarks to run: `lj-vs-lammps`, `lj-nvt`, `eam-cu` (default all three) |
| `--outdir DIR` | where the record JSON files go (default data/records) |
| `--workdir DIR` | scratch directory for the LAMMPS runs (default out/benchmarks) |
| `--potential PATH` | a Cu EAM file you obtained (funcfl `.eam` or setfl `.eam.alloy`) — required for `eam-cu` |
| `--steps N` | production steps for `lj-nvt` (default 20000) |
| `--state-point KEY` | NIST key prefix for `lj-nvt`, e.g. `T0.85_rho0.776` (default: the first MC entry) |
| `--log-dir DIR` | append a one-line log per invocation |
| `--version` | print the version and exit |

Exit codes: 0 every requested benchmark wrote its record, 1 one failed, 2 unknown benchmark name.

## `scripts/run_examples.py`

Runs LAMMPS's **own** `bench/` and `examples/` cases on one route and records the outcome. The
inputs are the LAMMPS developers' (GPL-2.0) and are never copied into this repository: each case is
copied out of the installed tree into a scratch directory on the host that runs it, and only the
outcome is written here. Scores on the **log**, never on the return code — both builds on the
reference machine exit 0 after a fatal input error (finding N-15).

| flag | meaning |
|---|---|
| `--route NAME` | install route to run on, e.g. `wsl-apt`, `wsl-source` (required) |
| `--set bench\|examples` | which tree to sweep (default `bench`) |
| `--root DIR` | the installed LAMMPS tree holding `bench/` and `examples/` |
| `--procs N` | repeatable; process counts to run (default 1). `N > 1` is skipped on a build without MPI |
| `--time-limit S` | seconds per case, enforced by `timeout` inside WSL (default 120) |
| `--only TEXT` | substring filter on the case name |
| `--outdir DIR` | where the JSON record and the markdown table are written (default `out/examples`) |
| `--run-root DIR` | scratch directory for the copies (default `~/runs/examples`) |
| `--potentials DIR` | directory exported as `$LAMMPS_POTENTIALS` (default `<root>/potentials`) |

Outcomes: `ok`, `ok-no-thermo` (finished, but the case never opened a thermo block — several are
self-checking with `print`), `missing-package` (names the package the build lacks — a fact about the
build, not a broken case), `error`, `timeout-after-start` (ran, then hit the cap), `timeout`, `no-run`. When upstream ships a reference log for the case at that
process count (`log.<date>.<case>.g++.<n>`), the final thermo row is compared with it and the worst
relative difference is recorded.

## `docs/build_manual.py`

| flag | meaning |
|---|---|
| `--outdir DIR` | where `USER_MANUAL.html` / `.pdf` go (default docs/) |
| `--no-pdf` | write the HTML only |
| `-v`, `--verbose` | print the converter used and the commands |

Uses pandoc when present, a built-in Markdown→HTML fallback otherwise.

## `lammpskill` (the CLI, `lammpskill.cli`)

Global: `--log-dir DIR` (append an audit record per command to `lammpskill-audit.jsonl`), `--version`.

| subcommand | flags |
|---|---|
| `detect` | `--route ROUTE` (only this route), `--json` (machine-readable) |
| `verify` | `--probe` (also run the LJ-melt probe) |
| `new` | `--preset {eam_fcc,lj_melt,spce_water}` (required), `--out DIR` (required), `--steps N`, `--n N` (lattice repetitions per side; molecules per side for spce_water) |
| `check FILE` | `--workdir DIR` (for the read_data check; default the file's directory) — exit 1 on an error-level finding |
| `run DIR` | `--in NAME` (input script inside DIR, default in.lammps), `--route ROUTE`, `--backend {auto,subprocess,library}`, `--mpi N`, `--omp N`, `--time-limit S` (default 3600) |
| `log FILE` | `--csv OUT` (last thermo block as CSV), `--last` (last row as JSON) |
| `dump FILE` | `--info` (frames, atoms, columns, box), `--frames` (one line per frame) |
| `rdf FILE` | `--nbins N` (default 100), `--rmax R` (default half the smallest box length), `--out FILE` (.csv or .png; default print) |

Exit codes: 0 success, 1 failure (no installation, an error-level finding, a failed run, no thermo output).

## Python entry points

`lammpskill.install.detect_all()`, `lammpskill.install.base.run_command / probe`,
`lammpskill.script.Spec / render / check / lj_melt / eam_fcc / spce_water`,
`lammpskill.run.run / SubprocessBackend / LibraryBackend / run_or_load`,
`lammpskill.io.{log,data,dump,restart,potential,backends}`, `lammpskill.post.*`,
`mdlite.{box,neighbors,pair,eam,integrate,thermostats,minimize,measure}`.
