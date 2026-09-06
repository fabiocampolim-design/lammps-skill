# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
import numpy as np
import pytest

from mdlite.box import Box
from mdlite.integrate import State, velocity_verlet
from mdlite.measure import kinetic_temperature
from mdlite.neighbors import CellList, VerletList
from mdlite.pair import HarmonicBond, LennardJones


def fcc(n, rho):
    a = (4.0 / rho) ** (1.0 / 3.0)
    base = np.array([[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]) * a
    cells = np.array([[i, j, k] for i in range(n) for j in range(n) for k in range(n)]) * a
    return (cells[:, None, :] + base[None, :, :]).reshape(-1, 3), Box([n * a] * 3)


def test_cell_list_finds_every_pair_within_cutoff():
    pos, box = fcc(3, 0.8442)
    cl = CellList(box, 2.5)
    cl.build(pos)
    i, j = cl.pairs()
    d = box.minimum_image(pos[i] - pos[j])
    r = np.sqrt((d * d).sum(1))
    D = pos[:, None, :] - pos[None, :, :]
    D = box.minimum_image(D.reshape(-1, 3)).reshape(D.shape)
    R = np.sqrt((D * D).sum(-1))
    iu = np.triu_indices(len(pos), 1)
    brute = (R[iu] < 2.5).sum()
    assert (r < 2.5).sum() == brute and np.all(i < j)


def test_verlet_list_rebuilds_only_after_displacement():
    pos, box = fcc(3, 0.8442)
    vl = VerletList(box, 2.5, skin=0.3)
    assert vl.update(pos) is True and vl.update(pos + 0.05) is False and vl.update(pos + 0.2) is True


def test_lj_forces_match_numerical_derivative():
    pos, box = fcc(2, 0.8442)
    rng = np.random.default_rng(0)
    pos = pos + rng.normal(0, 0.05, pos.shape)
    lj = LennardJones()
    vl = VerletList(box, 2.5)
    vl.update(pos)
    E, F, _ = lj.energy_forces(pos, box, vl.pairs)
    h = 1e-6
    for (k, c) in ((0, 0), (5, 2), (11, 1)):
        p = pos.copy()
        p[k, c] += h
        Ep = lj.energy_forces(p, box, vl.pairs)[0]
        p[k, c] -= 2 * h
        Em = lj.energy_forces(p, box, vl.pairs)[0]
        assert F[k, c] == pytest.approx(-(Ep - Em) / (2 * h), rel=1e-5, abs=1e-6)


def test_lj_lattice_energy_matches_the_analytic_shifted_sum():
    pos, box = fcc(3, 0.8442)
    lj = LennardJones(shift=True)
    vl = VerletList(box, 2.5)
    vl.update(pos)
    E, F, vir = lj.energy_forces(pos, box, vl.pairs)
    d = box.minimum_image(pos[vl.pairs[0]] - pos[vl.pairs[1]])
    r = np.sqrt((d * d).sum(1))
    r = r[r < 2.5]
    ref = (4 * (r ** -12 - r ** -6) - 4 * (2.5 ** -12 - 2.5 ** -6)).sum()
    assert E == pytest.approx(ref, rel=1e-12) and np.abs(F).max() < 1e-10


def test_harmonic_bond():
    pos = np.array([[0, 0, 0], [1.5, 0, 0]], float)
    E, F, _ = HarmonicBond(k=10.0, r0=1.0).energy_forces(pos, Box([10, 10, 10]), np.array([[0, 1]]))
    assert E == pytest.approx(10.0 * 0.25) and F[0, 0] == pytest.approx(10.0) and F[1, 0] == pytest.approx(-10.0)


def test_nve_conserves_energy_and_temperature_is_sane():
    pos, box = fcc(3, 0.8442)
    rng = np.random.default_rng(1)
    vel = rng.normal(0, np.sqrt(1.0), pos.shape)
    vel -= vel.mean(0)
    st = State(pos=pos, vel=vel, mass=1.0, box=box)
    rec = velocity_verlet(st, [LennardJones()], dt=0.005, nsteps=200, nlist=VerletList(box, 2.5), every=10)
    E = np.array([r["E_tot"] for r in rec])
    assert len(rec) == 21 and abs(E[-1] - E[0]) / abs(E[0]) < 2e-3
    assert 0.3 < rec[-1]["T"] < 1.5 and np.isfinite(rec[-1]["P"])
    assert kinetic_temperature(st.vel, 1.0) == pytest.approx(rec[-1]["T"])
