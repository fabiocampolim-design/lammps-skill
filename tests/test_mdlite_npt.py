# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
import numpy as np

from mdlite.integrate import State
from mdlite.neighbors import VerletList
from mdlite.npt import BerendsenBarostat, velocity_verlet_npt
from mdlite.pair import LennardJones
from mdlite.thermostats import Berendsen
from test_mdlite_core import fcc


def _run(rho, T0, P0, nsteps=800, dt=0.005, seed=2):
    pos, box = fcc(3, rho)
    rng = np.random.default_rng(seed)
    vel = rng.normal(0, np.sqrt(T0), pos.shape)
    vel -= vel.mean(0)
    st = State(pos, vel, 1.0, box)
    vl = VerletList(box, 2.5)
    rec = velocity_verlet_npt(st, [LennardJones()], dt, nsteps, vl, Berendsen(T0, 0.5),
                               BerendsenBarostat(P0, 2.0), every=20)
    return rec


def test_compressed_system_expands_toward_a_lower_target_pressure():
    rec = _run(rho=1.1, T0=2.0, P0=1.0)
    V = np.array([r["V"] for r in rec])
    assert np.all(np.isfinite(V))
    assert V[-1] > V[0], "a system started denser than its target should expand toward it"


def test_expanded_system_compresses_toward_a_higher_target_pressure():
    rec = _run(rho=0.4, T0=2.0, P0=3.0)
    V = np.array([r["V"] for r in rec])
    assert np.all(np.isfinite(V))
    assert V[-1] < V[0], "a system started more dilute than its target should compress toward it"


def test_particle_count_and_output_are_conserved_and_finite():
    rec = _run(rho=0.8442, T0=1.5, P0=1.0, nsteps=100)
    assert len(rec) > 1
    assert all(np.isfinite(r["P"]) and np.isfinite(r["V"]) and np.isfinite(r["T"]) for r in rec)


def test_barostat_mu_moves_the_right_direction():
    # Berendsen et al. 1984: mu^3 = 1 - dt/tau * beta * (P0 - P). P above target -> mu > 1 (the
    # box expands, relieving the excess pressure); P below target -> mu < 1 (it shrinks, raising
    # the density and so the pressure, back toward P0).
    b = BerendsenBarostat(P0=1.0, tau=2.0)
    assert b.mu(dt=0.01, P=1.5) > 1.0, "pressure above target: mu > 1, the box should grow"
    assert b.mu(dt=0.01, P=0.5) < 1.0, "pressure below target: mu < 1, the box should shrink"
    assert b.mu(dt=0.01, P=1.0) == 1.0, "pressure at target: no rescaling"
