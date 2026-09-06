# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Route windows: the official Windows installer (rpm.lammps.org/windows/): lmp.exe on PATH, liblammps.dll, LAMMPS_POTENTIALS."""

import os
import shutil
import subprocess
import sys

from .base import CREATE_NO_WINDOW, Installation, parse_help

NAME = "windows"


def describe():
    return ("The LAMMPS Windows installer packages (serial or MS-MPI; optional GUI / bundled Python variants) from "
            "rpm.lammps.org/windows/: lmp.exe and liblammps.dll on PATH, potentials via the LAMMPS_POTENTIALS variable, "
            "examples and manual included. Native, no WSL; the package set excludes libraries that need external builds.")


def detect(env=None, run=None):
    env = os.environ if env is None else env
    exe = env.get("LAMMPSKILL_WINDOWS_LMP") or shutil.which("lmp", path=env.get("PATH")) or shutil.which("lmp.exe", path=env.get("PATH"))
    if not exe:
        return None
    try:
        if run is not None:
            h = run([exe, "-h"])
        else:
            kw = dict(stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
            if sys.platform == "win32":
                kw["creationflags"] = CREATE_NO_WINDOW
            h = subprocess.run([exe, "-h"], **kw)
    except (OSError, subprocess.TimeoutExpired):
        return None
    info = parse_help(h.stdout if h.returncode == 0 else "")
    if not info["version"]:
        return None
    lib = os.path.join(os.path.dirname(exe), "liblammps.dll")
    return Installation(route=NAME, host="windows", executable=exe, version=info["version"], packages=info["packages"],
                        mpi=info["mpi"], omp=info["omp"], library=lib if os.path.isfile(lib) else None,
                        python_module=False, launch=(), distro=None, python=None,
                        extra={"potentials": env.get("LAMMPS_POTENTIALS", "")})
