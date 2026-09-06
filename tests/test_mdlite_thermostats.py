# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
import numpy as np
import pytest

from mdlite.integrate import State, velocity_verlet
from mdlite.neighbors import VerletList
from mdlite.pair import LennardJones
from mdlite.thermostats import Berendsen, Langevin, NoseHooverChain
from test_mdlite_core import fcc


@pytest.mark.parametrize("make", [lambda: Berendsen(1.0, 0.1), lambda: Langevin(1.0, 1.0, seed=0), lambda: NoseHooverChain(1.0, 0.5)])
def test_thermostats_bring_T_to_target(make):
    pos, box = fcc(3, 0.8442)
    rng = np.random.default_rng(4)
    vel = rng.normal(0, np.sqrt(2.0), pos.shape)
    vel -= vel.mean(0)
    st = State(pos, vel, 1.0, box)
    rec = velocity_verlet(st, [LennardJones()], dt=0.005, nsteps=1500, nlist=VerletList(box, 2.5), thermostat=make(), every=10)
    T = np.array([r["T"] for r in rec[-50:]])
    assert abs(T.mean() - 1.0) < 0.08, T.mean()


def test_nose_hoover_conserves_the_extended_energy():
    pos, box = fcc(3, 0.8442)
    rng = np.random.default_rng(5)
    vel = rng.normal(0, 1.0, pos.shape)
    vel -= vel.mean(0)
    st = State(pos, vel, 1.0, box)
    nh = NoseHooverChain(1.0, 0.5)
    rec = velocity_verlet(st, [LennardJones()], dt=0.002, nsteps=1000, nlist=VerletList(box, 2.5), thermostat=nh, every=10)
    H = np.array([r["E_tot"] + r["H_extra"] for r in rec[1:]])
    assert abs(H[-1] - H[0]) / abs(H[0]) < 5e-3
