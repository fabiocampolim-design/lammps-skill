# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Pair potentials for mdlite. Each returns (energy, forces, virial) for a pair list; forces from -dU/dr (Frenkel & Smit 2002, ch. 3)."""

import numpy as np


def _accumulate(n, i, j, fvec):
    F = np.zeros((n, 3))
    np.add.at(F, i, fvec)
    np.add.at(F, j, -fvec)
    return F


class LennardJones:
    def __init__(self, epsilon=1.0, sigma=1.0, rcut=2.5, shift=True):
        self.epsilon, self.sigma, self.rcut, self.shift = float(epsilon), float(sigma), float(rcut), bool(shift)
        self.u_shift = self.pair_energy(np.array([self.rcut]), shifted=False)[0] if shift else 0.0

    def pair_energy(self, r, shifted=True):
        s6 = (self.sigma / r) ** 6
        u = 4 * self.epsilon * (s6 * s6 - s6)
        return u - (self.u_shift if shifted else 0.0)

    def pair_force(self, r):
        s6 = (self.sigma / r) ** 6
        return 24 * self.epsilon * (2 * s6 * s6 - s6) / r

    def energy_forces(self, pos, box, pairs):
        i, j = pairs
        d = box.minimum_image(pos[i] - pos[j])
        r2 = (d * d).sum(1)
        m = r2 < self.rcut ** 2
        i, j, d, r = i[m], j[m], d[m], np.sqrt(r2[m])
        E = float(self.pair_energy(r).sum())
        f = self.pair_force(r)
        fvec = (f / r)[:, None] * d
        virial = float((fvec * d).sum())
        return E, _accumulate(len(pos), i, j, fvec), virial


class HarmonicBond:
    def __init__(self, k, r0, bonds=None):
        self.k, self.r0 = float(k), float(r0)
        self.bonds = None if bonds is None else np.asarray(bonds, int)

    def energy_forces(self, pos, box, bonds=None):
        bonds = self.bonds if bonds is None else np.asarray(bonds, int)
        i, j = bonds[:, 0], bonds[:, 1]
        d = box.minimum_image(pos[i] - pos[j])
        r = np.sqrt((d * d).sum(1))
        E = float((self.k * (r - self.r0) ** 2).sum())
        f = -2 * self.k * (r - self.r0)
        fvec = (f / r)[:, None] * d
        return E, _accumulate(len(pos), i, j, fvec), float((fvec * d).sum())
