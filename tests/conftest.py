# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Shared fixtures. Run from lammps-skill/:  python -m pytest tests"""

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for sub in ("", "scripts", "build", "docs"):
    p = os.path.join(ROOT, sub) if sub else ROOT
    if p not in sys.path:
        sys.path.insert(0, p)

FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def pytest_addoption(parser):
    parser.addoption("--run-notebooks", action="store_true", default=False,
                     help="re-execute every chapter notebook on the pinned kernel (slow)")
    parser.addoption("--with-lammps", action="store_true", default=False,
                     help="run the tests that drive a real LAMMPS installation (auto-detected otherwise)")


@pytest.fixture(scope="session")
def repo_root():
    return ROOT


@pytest.fixture(scope="session")
def fixtures():
    return FIXTURES


@pytest.fixture(scope="session")
def lammps_installations():
    """Every detected LAMMPS installation (list) or a pytest.skip."""
    from lammpskill.install import detect_all
    found = detect_all()
    if not found:
        pytest.skip("no LAMMPS installation reachable (WSL apt/source, conda, wheel, Windows)")
    return found


@pytest.fixture(scope="session")
def lammps_exe(lammps_installations):
    """The first installation that has an executable (subprocess route) or a pytest.skip."""
    for inst in lammps_installations:
        if inst.executable:
            return inst
    pytest.skip("no LAMMPS executable (only in-process routes found)")
