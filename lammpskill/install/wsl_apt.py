# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Route wsl-apt: the Ubuntu archive's `lammps` packages inside WSL2 (lmp on PATH, python3-lammps, lammps-data)."""

import os
import subprocess
import sys

from .base import CREATE_NO_WINDOW, Installation, parse_help

NAME = "wsl-apt"


def describe():
    return ("Ubuntu archive packages (lammps, lammps-data, lammps-examples, liblammps-dev, python3-lammps) inside WSL2; "
            "installed by scripts/install_lammps_wsl.sh as root; executable /usr/bin/lmp (MPI build), potentials under "
            "/usr/share/lammps/potentials. Fast to install, package set and version fixed by the distribution.")


def _run(run, cmd):
    if run is not None:
        return run(cmd)
    kw = dict(stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    if sys.platform == "win32":
        kw["creationflags"] = CREATE_NO_WINDOW
    return subprocess.run(cmd, **kw)


def wsl_prefix(distro):
    return ("wsl.exe", "-d", distro, "-e", "bash", "-lc")


def detect_in_wsl(exe_query, route, env=None, run=None, python_query=None):
    """Shared by wsl-apt and wsl-source: find an executable by a shell query, read -h, test the module.

    python_query, when given, is a shell command printing the interpreter that owns this route's module
    (the source build uses a venv); without it the module is tested with python3.
    """
    env = os.environ if env is None else env
    distro = env.get("LAMMPSKILL_WSL_DISTRO", "Ubuntu")
    prefix = list(wsl_prefix(distro))
    try:
        p = _run(run, prefix + [exe_query])
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0 or not p.stdout.strip():
        return None
    exe = p.stdout.replace("\x00", "").strip().splitlines()[0].strip()
    h = _run(run, prefix + ["%s -h" % exe])
    info = parse_help(h.stdout.replace("\x00", "") if h.returncode == 0 else "")
    if not info["version"]:
        return None
    python = "python3"
    if python_query:
        pq = _run(run, prefix + [python_query])
        found = pq.stdout.replace("\x00", "").strip() if pq.returncode == 0 else ""
        if found:
            python = found.splitlines()[0].strip()
    # A build made with LAMMPS_MACHINE=<m> ships liblammps_<m>.so; lammps.lammps() with no name then
    # falls through to the system loader and binds whatever liblammps.so it finds -- here the apt one,
    # version mismatch and all (finding N-12). So derive the machine from lmp_<m> and probe by
    # constructing: a module that imports but cannot start LAMMPS is not a working module.
    base = exe.replace("\\", "/").rsplit("/", 1)[-1]
    machine = base[4:] if base.startswith("lmp_") else ""
    probe = ('import lammps; l = lammps.lammps(name="%s", cmdargs=["-log","none","-screen","none","-nocite"]); '
             'print("ok", l.version()); l.close()' % machine)
    py = _run(run, prefix + ["%s -c '%s'" % (python, probe)])
    module = py.returncode == 0 and "ok" in py.stdout
    # Each route asks only for its own library: with both an apt and a source build present, one
    # combined `ls` sorted $HOME before /usr and gave the apt row the source library (N-13).
    if machine:
        lib_query = ("ls -1 $HOME/.local/lib/liblammps_%s.so* $HOME/src/lammps-*/build/liblammps_%s.so"
                     " 2>/dev/null | head -1" % (machine, machine))
    else:
        lib_query = "ls -1 /usr/lib/x86_64-linux-gnu/liblammps.so* /usr/lib/liblammps.so* 2>/dev/null | head -1"
    lib = _run(run, prefix + [lib_query])
    libpath = lib.stdout.replace("\x00", "").strip() if lib.returncode == 0 else ""
    return Installation(route=route, host="wsl", executable=exe, version=info["version"], packages=info["packages"],
                        mpi=info["mpi"], omp=info["omp"], library=libpath or None,
                        python_module=module, launch=tuple(prefix), distro=distro, python=python,
                        extra={"os": info["os"], "compiler": info["compiler"], "machine": machine})


def detect(env=None, run=None):
    return detect_in_wsl("command -v lmp", NAME, env=env, run=run)
