# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Observables in reduced units (k_B = 1)."""

import numpy as np


def _mass_array(vel, mass):
    m = np.asarray(mass, float)
    return np.broadcast_to(m, (len(vel),)) if m.ndim == 0 else m


def kinetic_energy(vel, mass):
    m = _mass_array(vel, mass)
    return float(0.5 * (m[:, None] * vel * vel).sum())


def kinetic_temperature(vel, mass, dof=None):
    n = len(vel)
    dof = 3 * n - 3 if dof is None else dof
    return 2.0 * kinetic_energy(vel, mass) / dof


def pressure(state, virial, T):
    n = len(state.pos)
    V = state.box.volume
    return n * T / V + virial / (3.0 * V)
