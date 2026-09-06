# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
import numpy as np
import pytest

from lammpskill.io import backends
from lammpskill.io.box import Box
from lammpskill.io.data import DataFile


def _df():
    return DataFile.from_arrays(box=Box(0, 5, 0, 5, 0, 5), types=np.array([1, 2]), positions=np.array([[0, 0, 0], [1, 1, 1]], float),
                                masses={1: 1.0, 2: 12.011}, atom_style="atomic")


def test_available_reports_every_backend():
    av = backends.available()
    assert set(av) == {"lammps", "ase", "pymatgen", "MDAnalysis", "ovito"}
    assert all(v is None or isinstance(v, str) for v in av.values())


def test_missing_backend_raises_with_a_hint(monkeypatch):
    def boom(name):
        raise ImportError(name)
    monkeypatch.setattr(backends, "_import", boom)
    with pytest.raises(backends.BackendUnavailable, match="pip install ase"):
        backends.to_ase(_df())


@pytest.mark.skipif(backends.available()["ase"] is None, reason="ase not installed")
def test_ase_round_trip():
    atoms = backends.to_ase(_df())
    assert len(atoms) == 2 and atoms.pbc.all() and atoms.get_masses()[1] == pytest.approx(12.011)
    back = backends.from_ase(atoms)
    np.testing.assert_allclose(back.positions, [[0, 0, 0], [1, 1, 1]])


@pytest.mark.skipif(backends.available()["pymatgen"] is None, reason="pymatgen not installed")
def test_pymatgen_structure():
    s = backends.to_pymatgen(_df())
    assert len(s) == 2 and abs(s.volume - 125.0) < 1e-9
