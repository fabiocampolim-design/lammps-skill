# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Route wsl-source: our own CMake build of a LAMMPS tag inside WSL ext4 (scripts/install_lammps_wsl.sh --source)."""

import os

from .wsl_apt import detect_in_wsl

NAME = "wsl-source"
PRESETS = ("core", "molecular", "metals", "reactive", "ml", "all-cpu")
PRESET_PACKAGES = {
    "core": "MOLECULE KSPACE MANYBODY RIGID OPENMP PYTHON EXTRA-COMPUTE EXTRA-DUMP EXTRA-FIX EXTRA-MOLECULE EXTRA-PAIR",
    "molecular": "MOLECULE KSPACE MANYBODY RIGID OPENMP PYTHON EXTRA-COMPUTE EXTRA-DUMP EXTRA-FIX EXTRA-MOLECULE EXTRA-PAIR MC MISC QEQ SHOCK",
    "metals": "MOLECULE KSPACE MANYBODY RIGID OPENMP PYTHON EXTRA-COMPUTE EXTRA-DUMP EXTRA-FIX EXTRA-PAIR MEAM PHONON REPLICA",
    "reactive": "MOLECULE KSPACE MANYBODY RIGID OPENMP PYTHON EXTRA-COMPUTE EXTRA-DUMP EXTRA-FIX EXTRA-PAIR QEQ REAXFF",
    "ml": "MOLECULE KSPACE MANYBODY RIGID OPENMP PYTHON EXTRA-COMPUTE EXTRA-DUMP EXTRA-FIX EXTRA-PAIR ML-SNAP ML-PACE ML-IAP",
}


def describe():
    return ("CMake build of a chosen tag (default the latest stable) in $HOME/src/lammps-<tag> on WSL ext4, with the "
            "package preset you choose (core, molecular, metals, reactive, ml, all-cpu), shared library and python "
            "module, installed to $HOME/.local as lmp_<preset>. Slowest to set up, full control of packages and flags.")


def cmake_command(preset="core", tag="stable_22Jul2025_update6", prefix="$HOME/.local", jobs=4):
    """The configure line the installer runs (kept here so the reference doc and the tests read one source)."""
    if preset == "all-cpu":
        flags = "-C ../cmake/presets/most.cmake -D PKG_PYTHON=yes"
    else:
        flags = " ".join("-D PKG_%s=yes" % p for p in PRESET_PACKAGES[preset].split())
    # CMAKE_INSTALL_RPATH: $PREFIX/lib is not on the loader path, so without it the installed
    # lmp_<preset> cannot find liblammps_<preset>.so (finding N-11, PROVEN 2026-09-06).
    return ("cmake -D CMAKE_BUILD_TYPE=Release -D CMAKE_INSTALL_PREFIX=%s -D CMAKE_INSTALL_RPATH=%s/lib "
            "-D CMAKE_INSTALL_RPATH_USE_LINK_PATH=yes -D BUILD_MPI=yes -D BUILD_OMP=yes "
            "-D BUILD_SHARED_LIBS=yes -D LAMMPS_MACHINE=%s %s ../cmake" % (prefix, prefix, preset, flags))


def detect(env=None, run=None):
    env = os.environ if env is None else env
    override = env.get("LAMMPSKILL_WSL_LMP")
    if override:
        query = "test -x %s && echo %s" % (override, override)
    else:
        query = "ls -1 $HOME/.local/bin/lmp_* $HOME/src/lammps-*/build/lmp_* 2>/dev/null | head -1"
    # The source build's python module lives in its own venv (PEP 668 forbids the system install, and
    # an apt python3-lammps would answer for it); ask that interpreter, not python3 (finding N-10).
    return detect_in_wsl(query, NAME, env=env, run=run,
                         python_query="ls -1 $HOME/.local/venv-lammps-*/bin/python 2>/dev/null | head -1")
