# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""lammpskill — our own LAMMPS toolkit: install routes, file I/O, input scripts, runner, analysis."""

import os

_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
with open(os.path.join(_ROOT, "VERSION"), encoding="utf-8") as _f:
    __version__ = _f.read().strip()
