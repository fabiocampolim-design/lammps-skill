# Install routes — every way LAMMPS can be present, one contract

LAMMPS is GPL-2.0 and is **not** part of lammps-skill. The toolkit detects and drives whatever
installation you have; `lammpskill.install` has one module per route, each with the same contract:
`NAME`, `describe()`, `detect(env=None, run=None) -> Installation | None`. `detect_all()` walks the
routes in the order below and returns every installation found; `verify_lammps.py --probe` runs the
same LJ melt on each and prints the platform table (`references/platforms.md` keeps the measured rows).

An `Installation` records: `route`, `host` (windows / wsl / linux / docker / remote), `executable`
(None for in-process routes), `version` (the `-h` first line after the dash), `packages` (sorted,
upper case), `mpi`, `omp`, `library`, `python_module`, `launch` (the hidden command prefix),
`distro`, `python`, `extra` (`pinned`, `potentials`, …).

## 1. `wsl-apt`

Ubuntu archive packages (lammps, lammps-data, lammps-examples, liblammps-dev, python3-lammps) inside WSL2; installed by scripts/install_lammps_wsl.sh as root; executable /usr/bin/lmp (MPI build), potentials under /usr/share/lammps/potentials. Fast to install, package set and version fixed by the distribution.

- Install: `wsl -d Ubuntu -u root -- bash /mnt/c/<path>/lammps-skill/scripts/install_lammps_wsl.sh`
  (`--dry-run` prints the steps; the script refuses to run unprivileged and prints the command).
- Detection: `wsl.exe -d <distro> -e bash -lc "command -v lmp"`, then `lmp -h`, then
  `python3 -c "import lammps"`. Distro from `LAMMPSKILL_WSL_DISTRO` (default `Ubuntu`).
- Gives: `lmp` (Open MPI build), `liblammps.so`, `python3-lammps` for the WSL python, the
  `lammps-data` potentials, `lammps-examples`. Ubuntu 26.04 ships the **10 Dec 2025 feature release**,
  not the yearly stable; the package list is fixed by Debian's build (52 packages here: no EXTRA-FIX,
  EXTRA-MOLECULE, EXTRA-DUMP, REAXFF, ML-*).

## 2. `wsl-source`

CMake build of a chosen tag (default the latest stable) in $HOME/src/lammps-<tag> on WSL ext4, with the package preset you choose (core, molecular, metals, reactive, ml, all-cpu), shared library and python module, installed to $HOME/.local as lmp_<preset>. Slowest to set up, full control of packages and flags.

- Install: once as root `install_lammps_wsl.sh --source --deps-only`, then as the user
  `install_lammps_wsl.sh --source --tag stable_22Jul2025_update6 --preset core` (the configure line is
  `lammpskill.install.wsl_source.cmake_command(preset, tag)`: `BUILD_MPI`, `BUILD_OMP`,
  `BUILD_SHARED_LIBS`, `LAMMPS_MACHINE=<preset>`, one `-D PKG_<name>=yes` per package; `all-cpu` uses
  the manual's `most.cmake` preset).
- Detection: `LAMMPSKILL_WSL_LMP=/path/to/lmp_core` or the first of `~/.local/bin/lmp_*`,
  `~/src/lammps-*/build/lmp_*`.
- Gives: exactly the packages you asked for, the shared library, and `import lammps` for a **venv**
  interpreter at `~/.local/venv-lammps-<preset>/bin/python`.

Three things this route does differently from the manual's build page, each because a run here proved
it necessary (2026-09-06, `stable_22Jul2025_update6` on Ubuntu 26.04):

1. **An install RPATH.** `$HOME/.local/lib` is not on the loader path, so the installed `lmp_<preset>`
   could not find `liblammps_<preset>.so` and printed nothing. `cmake_command()` therefore passes
   `-D CMAKE_INSTALL_RPATH=<prefix>/lib -D CMAKE_INSTALL_RPATH_USE_LINK_PATH=yes` (finding N-11).
2. **The python module goes into a venv, not system site-packages.** `cmake --build . --target
   install-python` pip-installs system-wide, which a PEP 668 distribution refuses
   ("This environment is externally managed"), and it would collide with an apt `python3-lammps`
   anyway. The installer creates `~/.local/venv-lammps-<preset>` and runs upstream's
   `python/install.py` with that venv **activated** — `install.py` chooses its target from the
   `VIRTUAL_ENV` environment variable, not from `sys.prefix`, so passing the venv interpreter alone
   is not enough — from the build directory, because it resolves the wheel it just built relative to
   the current directory (findings N-10, P-1).
3. **`lammps.lammps(name="<preset>")`.** The build is `LAMMPS_MACHINE=<preset>`, so the module must be
   told to load `liblammps_<preset>.so`; with no name it falls through to the system loader and binds
   whatever `liblammps.so` it finds — here the apt one, which fails with "LAMMPS Python module
   installed for LAMMPS version 20250722, but shared library is version 20251210" (finding N-12).
   `detect()` therefore probes the module by *constructing* it with the machine name, not by importing.

## 3. `conda`

conda-forge `lammps` package (Linux/macOS builds; whether a win-64 build exists is recorded in references/platforms.md from a real `conda search`, never assumed) in the current env or in the env named by LAMMPSKILL_CONDA_ENV. Executable lmp on the env's PATH; the python module ships with it.

- Install: `conda create -n lammps-cf -c conda-forge lammps`.
- Detection: `CONDA_PREFIX` (current env) or `LAMMPSKILL_CONDA_ENV=<name>`; looks for `bin/lmp`,
  `bin/lmp_mpi`, `bin/lmp_serial`, `Library/bin/lmp.exe`.

## 4. `wheel`

The PyPI `lammps` wheel (2025.7.22.4.0 on 2026-09-06; built by a third party, njzjz/lammps-wheel, GPL-2.0; win_amd64, manylinux, macOS) installed into the current python. No executable: LAMMPS runs in-process through lammpskill.run.LibraryBackend. Quickest route on Windows; package set fixed by the wheel builder.

- Install: `pip install lammps`.
- Detection: `import lammps` and `lammps.lammps(...)` in the current python; the version comes from
  `L.version()`, the packages from `installed_packages`.
- **Windows finding (2026-09-06, N-2):** the wheel's `liblammps.dll` imports `msmpi.dll`; without the
  Microsoft MPI runtime the import fails with "Could not find module … liblammps.dll (or one of its
  dependencies)". The wheel also drops an `lmp.exe` in `Scripts/`, which needs the same DLL. Installing
  MS-MPI is a system-wide step the owner decides; until then the route reports "not detected" here.

## 5. `windows`

The LAMMPS Windows installer packages (serial or MS-MPI; optional GUI / bundled Python variants) from rpm.lammps.org/windows/: lmp.exe and liblammps.dll on PATH, potentials via the LAMMPS_POTENTIALS variable, examples and manual included. Native, no WSL; the package set excludes libraries that need external builds.

- Install: download from `https://rpm.lammps.org/windows/` (the page `packages.lammps.org/windows.html`
  explains the variants; MS-MPI needed for the parallel one). System-wide: the owner's call.
- Detection: `lmp`/`lmp.exe` on `PATH` or `LAMMPSKILL_WINDOWS_LMP`; `LAMMPS_POTENTIALS` recorded.

## 6. `docker` — PINNED

A LAMMPS container image run with `docker run --rm -v <case>:/work -w /work <image> lmp -in in.x`. PINNED until the owner installs Docker Desktop: the route detects only when LAMMPSKILL_DOCKER_IMAGE names an image the local docker CLI lists; which public images exist is recorded in docs/10 from a real check.

The runner refuses a pinned route with `NotImplementedError` naming the pin.

## 7. `remote` — PINNED

LAMMPS on a remote host reached over SSH, later through a Slurm queue: LAMMPSKILL_REMOTE=user@host:/path/to/lmp. PINNED (owner: implement when the machine exists). The runner interface is fixed here so chapters and the CLI need no change when it lands: submit / poll / fetch, with the case directory synced under ~/runs.

## How to choose

| You want | Route |
|---|---|
| a working LAMMPS in minutes on this Windows machine | `wsl-apt` |
| a package the apt build lacks (REAXFF, ML-*, EXTRA-FIX), a specific tag, a patched build | `wsl-source` |
| per-step Python access (`fix python`, `extract_compute`) | any route whose row says `python module: yes`; on Windows the `wheel` once MS-MPI is present |
| no WSL at all | `windows` (installer) |
| the same binary on a laptop and a cluster | `docker` / `remote` when unpinned |
