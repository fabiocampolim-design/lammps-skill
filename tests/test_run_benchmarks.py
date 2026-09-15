# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""scripts/run_benchmarks.py: the parts that need neither LAMMPS nor a real Cu potential file --
_fit_a0_ecoh and _vacancy_formation_energy_mdlite, exercised on synthetic_setfl() (rule 7: no
real potential file is ever required to exist, matching chapter 05's own convention); and
_polymer_energy_forces_mdlite, which needs neither LAMMPS nor any external file at all (the
bead-spring chain has no real-element dependency). The parts that DO need LAMMPS (eam_cu,
eam_cu_vacancy, polymer_vs_lammps themselves) are exercised manually by the project owner, the
same as eam_cu already was before this file existed.

The fit grid here (a in 2.8..3.3, n=4) is the same min-image-safe grid chapter 05's own synthetic-
potential cells use (build/chapter05_potentials_eam.py) -- deliberately NOT chapter 05's original
grid (a in 1.0..1.6, n=3, cutoff 5.0 default), which puts the box side well under twice the
cutoff, violating the minimum-image convention (confirmed by direct measurement: it gives a
POSITIVE "cohesive" energy, i.e. an unbound crystal). Measured margins for this grid: at a=2.8,
box side L=11.2 A vs 2*cutoff=10.0 A (12% margin) and vs 2*(cutoff+VerletList's default 0.3 A
skin)=10.6 A (6% margin) -- both comfortably positive throughout the sampled range, so the
physical sanity checks below (a bound crystal, a positive vacancy formation energy under the
cohesive energy in magnitude) are checking something real, not an artifact of an undersized box."""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from lammpskill.io.potential import synthetic_setfl  # noqa: E402
from lammpskill.script import bead_spring_chain  # noqa: E402
from mdlite.box import Box  # noqa: E402
from mdlite.eam import EAM  # noqa: E402

import run_benchmarks as rb  # noqa: E402

A_LO, A_HI, N_CELLS = 2.8, 3.3, 4   # the same grid build/chapter05_potentials_eam.py's own EAM
                                     # fit cell uses -- min-image-safe for synthetic_setfl()'s
                                     # default cutoff=5.0 throughout (see module docstring)


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
    # measured directly: a 12-point cubic fit over this 0.5-wide grid lands the minimum to within
    # a local numerical slope of ~0.005 for this potential -- much tighter than the old 1.0-wide
    # grid's ~0.3 (a coarser grid fits the cubic worse near its own minimum). 0.05 leaves a real
    # 10x margin above the measured value while still catching a wrong root, a grid endpoint, or a
    # broken fit (all of which push the local slope past several units, not fractions of one).
    assert abs(slope) < 0.05, "the fitted a0 should sit near the local minimum of E(a)"


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


def test_polymer_energy_forces_mdlite_matches_a_numerical_derivative():
    """_polymer_energy_forces_mdlite needs neither LAMMPS nor any potential file -- the same
    central-difference check every other force calculation in this project (mdlite and chapter
    cells alike) is held to."""
    _, df = bead_spring_chain(n_beads=10)
    box = Box(df.box.lengths, lo=df.box.lo)
    pos = df.positions
    bonds0 = df.bonds[:, 2:4] - 1
    E0, F = rb._polymer_energy_forces_mdlite(pos, box, bonds0)

    h = 1e-6
    worst = 0.0
    for k, c in ((0, 0), (3, 1), (9, 2), (5, 0)):
        p = pos.copy()
        p[k, c] += h
        Ep, _ = rb._polymer_energy_forces_mdlite(p, box, bonds0)
        p[k, c] -= 2 * h
        Em, _ = rb._polymer_energy_forces_mdlite(p, box, bonds0)
        numeric = -(Ep - Em) / (2 * h)
        worst = max(worst, abs(F[k, c] - numeric))
    assert worst < 1e-5
    assert E0 != 0.0
