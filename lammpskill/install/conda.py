# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Route conda: the conda-forge `lammps` package in the current env or in LAMMPSKILL_CONDA_ENV."""

import os
import shutil
import subprocess
import sys

from .base import CREATE_NO_WINDOW, Installation, parse_help

NAME = "conda"


def describe():
    return ("conda-forge `lammps` package (Linux/macOS builds; whether a win-64 build exists is recorded in "
            "references/platforms.md from a real `conda search`, never assumed) in the current env or in the env named "
            "by LAMMPSKILL_CONDA_ENV. Executable lmp on the env's PATH; the python module ships with it.")


def _run(run, cmd):
    if run is not None:
        return run(cmd)
    kw = dict(stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    if sys.platform == "win32":
        kw["creationflags"] = CREATE_NO_WINDOW
    return subprocess.run(cmd, **kw)


def detect(env=None, run=None):
    env = os.environ if env is None else env
    envname = env.get("LAMMPSKILL_CONDA_ENV")
    if envname:
        conda = env.get("CONDA_EXE") or shutil.which("conda")
        if not conda:
            return None
        prefix = os.path.join(os.path.dirname(os.path.dirname(conda)), "envs", envname)
    else:
        prefix = env.get("CONDA_PREFIX")
        if not prefix:
            return None
    candidates = [os.path.join(prefix, "bin", "lmp"), os.path.join(prefix, "Library", "bin", "lmp.exe"),
                  os.path.join(prefix, "bin", "lmp_mpi"), os.path.join(prefix, "bin", "lmp_serial")]
    exe = next((c for c in candidates if os.path.isfile(c)), None)
    if exe is None:
        return None
    try:
        h = _run(run, [exe, "-h"])
    except (OSError, subprocess.TimeoutExpired):
        return None
    info = parse_help(h.stdout if h.returncode == 0 else "")
    if not info["version"]:
        return None
    py = os.path.join(prefix, "python.exe" if sys.platform == "win32" else os.path.join("bin", "python"))
    mod = _run(run, [py, "-c", "import lammps; print('ok')"]) if os.path.isfile(py) else None
    return Installation(route=NAME, host="windows" if sys.platform == "win32" else "linux", executable=exe,
                        version=info["version"], packages=info["packages"], mpi=info["mpi"], omp=info["omp"], library=None,
                        python_module=bool(mod and mod.returncode == 0 and "ok" in mod.stdout), launch=(), distro=None,
                        python=py if os.path.isfile(py) else None, extra={"prefix": prefix})
