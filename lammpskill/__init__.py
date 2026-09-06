# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""lammpskill — our own LAMMPS toolkit: install routes, file I/O, input scripts, runner, analysis."""

import os

_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_VERSION_FILE = os.path.join(_ROOT, "VERSION")
if os.path.exists(_VERSION_FILE):          # a checkout: the VERSION file next to the packages
    with open(_VERSION_FILE, encoding="utf-8") as _f:
        __version__ = _f.read().strip()
else:                                      # an installed wheel: the metadata written from VERSION at build time
    from importlib.metadata import version as _md_version
    __version__ = _md_version("lammps-skill")
