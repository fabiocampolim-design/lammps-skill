# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Install routes: one module per way LAMMPS can be present, one contract (base.Installation)."""

import importlib

from . import base

__all__ = ["base", "ROUTES", "get_route", "detect_all"]

ROUTES = ("wsl-apt", "wsl-source", "conda", "wheel", "windows", "docker", "remote")
_MODULES = {"wsl-apt": "wsl_apt", "wsl-source": "wsl_source", "conda": "conda", "wheel": "wheel",
            "windows": "windows", "docker": "docker", "remote": "remote"}


def get_route(name):
    if name not in _MODULES:
        raise KeyError("unknown route %r; known: %s" % (name, ", ".join(ROUTES)))
    return importlib.import_module("lammpskill.install." + _MODULES[name])


def detect_all(routes=None, env=None, run=None):
    found = []
    for name in routes or ROUTES:
        try:
            inst = get_route(name).detect(env=env, run=run)
        except Exception:  # a broken route never hides the others; verify_lammps prints the reason with --route
            inst = None
        if inst is not None:
            found.append(inst)
    return found
