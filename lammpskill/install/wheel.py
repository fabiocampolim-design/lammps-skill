# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Route wheel: `pip install lammps` (third-party wheel njzjz/lammps-wheel, GPL-2.0, bundles liblammps) — in-process only."""

import sys

from .base import Installation

NAME = "wheel"


def describe():
    return ("The PyPI `lammps` wheel (2025.7.22.4.0 on 2026-09-06; built by a third party, njzjz/lammps-wheel, GPL-2.0; "
            "win_amd64, manylinux, macOS) installed into the current python. No executable: LAMMPS runs in-process "
            "through lammpskill.run.LibraryBackend. Quickest route on Windows; package set fixed by the wheel builder.")


def detect(env=None, run=None):
    try:
        import lammps  # noqa: F401  (GPL-2.0; imported only here and in run.LibraryBackend)
    except Exception:
        return None
    try:
        L = lammps.lammps(cmdargs=["-log", "none", "-screen", "none", "-nocite"])
    except Exception:
        return None
    try:
        version = str(L.version())
        pkgs = tuple(sorted(str(p).upper() for p in getattr(L, "installed_packages", [])))
        try:
            mpi = bool(L.has_mpi_support)
        except Exception:
            mpi = False
    finally:
        try:
            L.close()
        except Exception:
            pass
    return Installation(route=NAME, host="windows" if sys.platform == "win32" else "linux", executable=None, version=version,
                        packages=pkgs, mpi=mpi, omp="OPENMP" in pkgs, library=getattr(lammps, "__file__", None),
                        python_module=True, launch=(), distro=None, python=sys.executable)
