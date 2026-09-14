# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""scripts/run_benchmarks.py: the parts that need neither LAMMPS nor a real Cu potential file --
_fit_a0_ecoh and _vacancy_formation_energy_mdlite, exercised on synthetic_setfl() (rule 7: no
real potential file is ever required to exist, matching chapter 05's own convention). The parts
that DO need a real Cu file and a LAMMPS installation (eam_cu, eam_cu_vacancy themselves) are
exercised manually by the project owner, the same as eam_cu already was before this file existed.

The fit grid here (a in 2.6..3.6) and supercell size (n=4) are deliberately NOT the ones chapter
05's own synthetic-potential demo uses (a in 1.0..1.6, cutoff 5.0 default) -- that combination
puts the box side well under twice the cutoff, violating the minimum-image convention (confirmed
by direct measurement: it gives a POSITIVE "cohesive" energy, i.e. an unbound crystal, which is
not a physically sensible result to build an absolute-scale test on). This file's own grid keeps
the box comfortably larger than 2x the cutoff at every sampled lattice constant, so the physical
sanity checks below (a bound crystal, a positive vacancy formation energy under the cohesive
energy in magnitude) are checking something real, not an artifact of an undersized box."""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from lammpskill.io.potential import synthetic_setfl  # noqa: E402
from mdlite.eam import EAM  # noqa: E402

import run_benchmarks as rb  # noqa: E402

A_LO, A_HI, N_CELLS = 2.6, 3.6, 4   # min-image-safe for synthetic_setfl()'s default cutoff=5.0
                                     # at every point in this range (measured: L/2 > cutoff throughout)


@pytest.fixture(scope="module")
def eam():
    return EAM(synthetic_setfl(), {1: 0})


@pytest.fixture(scope="module")
def a0_ecoh(eam):
    return rb._fit_a0_ecoh(eam, a_lo=A_LO, a_hi=A_HI, n_grid=12, n_cells=N_CELLS)


@pytest.fixture(scope="module")
def vac(eam, a0_ecoh):
    a0, _ = a0_ecoh
    return rb._vacancy_formation_energy_mdlite(eam, a0, n=N_CELLS)


def test_fit_a0_ecoh_is_self_consistent(eam, a0_ecoh):
    """The fit's own derivative at the fitted minimum should be ~0 (chapter 05 runs the same
    self-consistency check inline for the identical cubic-fit method), and -- checkable here
    because the box is min-image-safe, unlike chapter 05's synthetic demo -- a bound crystal
    really does have negative cohesive energy."""
    a0, ecoh = a0_ecoh
    assert A_LO < a0 < A_HI
    assert ecoh < 0, "a bound (cohesive) configuration has negative energy per atom"
    a_grid = np.linspace(a0 - 0.01, a0 + 0.01, 5)
    from mdlite.box import Box
    from mdlite.neighbors import VerletList
    energies = []
    for a in a_grid:
        pos, L = rb._fcc(N_CELLS, 4.0 / a ** 3)
        box = Box([L, L, L])
        vl = VerletList(box, eam.s.cutoff)
        vl.update(pos)
        E, _, _ = eam.energy_forces(pos, box, vl.pairs, np.ones(len(pos), int))
        energies.append(E / len(pos))
    slope = np.polyfit(a_grid, energies, 1)[0]
    # measured directly: a 12-point cubic fit over a 1.0-wide grid lands the minimum to within a
    # local slope of ~0.3 for this potential -- looser than chapter 05's own 1e-6 (a much finer,
    # purpose-tuned grid over a 0.6-wide range around a known-good synthetic potential minimum);
    # the point of this check is "near the minimum", not matching that unrelated precision
    assert abs(slope) < 0.5, "the fitted a0 should sit near the local minimum of E(a)"


def test_vacancy_formation_energy_mdlite_relaxes_and_returns_real_positions(vac):
    assert vac["natoms_perfect"] == 4 * N_CELLS ** 3
    assert len(vac["positions_after"]) == vac["natoms_perfect"] - 1
    assert len(vac["positions_before"]) == vac["natoms_perfect"]
    assert vac["fmax_after"] < 1e-4, "FIRE should relax the vacancy configuration to low residual force"
    L = vac["cell"][0]
    assert all(0 <= c <= L for c in vac["removed_position"]), "the removed site must be a real position inside the box"


def test_vacancy_formation_energy_is_reasonable_relative_to_cohesive_energy(a0_ecoh, vac):
    """No literature number to check a synthetic potential against -- the physically meaningful
    self-check is that removing an atom and relaxing costs energy (a bound crystal does not get
    more stable with a hole in it) and that the cost stays under the cohesive energy magnitude,
    not many multiples of it, which would indicate the relaxation or the reference is wrong."""
    _, ecoh = a0_ecoh
    assert 0 < vac["e_formation"] < abs(ecoh), (
        "vacancy formation energy (%.4f) should be positive and under the cohesive energy "
        "magnitude (%.4f) for a physically reasonable, bound potential" % (vac["e_formation"], abs(ecoh)))
