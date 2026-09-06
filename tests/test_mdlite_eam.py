# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
import numpy as np
import pytest

from lammpskill.io.potential import synthetic_setfl
from mdlite.eam import EAM
from mdlite.integrate import State
from mdlite.minimize import fire, steepest_descent
from mdlite.neighbors import VerletList
from mdlite.pair import LennardJones
from test_mdlite_core import fcc


def test_eam_forces_match_numerical_derivative():
    s = synthetic_setfl()
    pos, box = fcc(2, 0.25)          # a = 2.52: neighbours inside the 5.0 cutoff
    rng = np.random.default_rng(0)
    pos = pos + rng.normal(0, 0.03, pos.shape)
    eam = EAM(s, {1: 0})
    types = np.ones(len(pos), int)
    vl = VerletList(box, s.cutoff)
    vl.update(pos)
    E, F, _ = eam.energy_forces(pos, box, vl.pairs, types)
    h = 1e-5
    for (k, c) in ((0, 0), (7, 1), (20, 2)):
        p = pos.copy()
        p[k, c] += h
        Ep = eam.energy_forces(p, box, vl.pairs, types)[0]
        p[k, c] -= 2 * h
        Em = eam.energy_forces(p, box, vl.pairs, types)[0]
        assert F[k, c] == pytest.approx(-(Ep - Em) / (2 * h), rel=2e-4, abs=1e-6)


def test_minimisers_reduce_forces_on_a_perturbed_lattice():
    pos, box = fcc(3, 0.8442)
    rng = np.random.default_rng(1)
    st = State(pos + rng.normal(0, 0.05, pos.shape), np.zeros_like(pos), 1.0, box)
    vl = VerletList(box, 2.5)
    r1 = steepest_descent(st, [LennardJones()], vl, steps=200)
    assert r1["fmax"] < 1.0
    r2 = fire(st, [LennardJones()], vl, steps=2000, ftol=1e-5)
    assert r2["fmax"] < 1e-4 and r2["E"] <= r1["E"]
