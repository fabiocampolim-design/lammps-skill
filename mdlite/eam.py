# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Embedded-atom method (Daw & Baskes 1984) from a setfl table: E = sum_i F_i(rho_i) + 1/2 sum_ij phi_ij(r);
rho_i = sum_j rho_j(r_ij). Tables interpolated with cubic splines; phi from r*phi / r."""

import numpy as np


class EAM:
    def __init__(self, setfl, type_map):
        from scipy.interpolate import CubicSpline
        self.s, self.type_map = setfl, dict(type_map)
        self.rcut = setfl.cutoff
        r, rg = setfl.r, setfl.rhogrid
        self.F = [CubicSpline(rg, setfl.F[k]) for k in range(len(setfl.elements))]
        self.rho = [CubicSpline(r, setfl.rho[k]) for k in range(len(setfl.elements))]
        self.rphi = [CubicSpline(r, setfl.rphi[p]) for p in range(len(setfl.rphi))]
        self.types = None

    def energy_forces(self, pos, box, pairs, types=None):
        types = self.types if types is None else types
        if types is None:
            types = np.ones(len(pos), int)
        el = np.array([self.type_map[int(t)] for t in types])
        i, j = pairs
        d = box.minimum_image(pos[i] - pos[j])
        r2 = (d * d).sum(1)
        m = r2 < self.rcut ** 2
        i, j, d, r = i[m], j[m], d[m], np.sqrt(r2[m])
        ei, ej = el[i], el[j]
        n = len(pos)
        nel = len(self.s.elements)
        # densities: rho_i gets rho_{el_j}(r_ij), rho_j gets rho_{el_i}(r_ij)
        rho = np.zeros(n)
        rho_ji = np.zeros(len(r))
        rho_ij = np.zeros(len(r))
        drho_ji = np.zeros(len(r))
        drho_ij = np.zeros(len(r))
        for k in range(nel):
            mk = ej == k
            if mk.any():
                rho_ji[mk] = self.rho[k](r[mk])
                drho_ji[mk] = self.rho[k](r[mk], 1)
            mk = ei == k
            if mk.any():
                rho_ij[mk] = self.rho[k](r[mk])
                drho_ij[mk] = self.rho[k](r[mk], 1)
        np.add.at(rho, i, rho_ji)
        np.add.at(rho, j, rho_ij)
        Femb = np.zeros(n)
        dF = np.zeros(n)
        for k in range(nel):
            mk = el == k
            if mk.any():
                Femb[mk] = self.F[k](rho[mk])
                dF[mk] = self.F[k](rho[mk], 1)
        # pair part
        phi = np.zeros(len(r))
        dphi = np.zeros(len(r))
        pidx = np.array([self.s.pair_index(a, b) for a, b in zip(ei, ej)], int) if len(r) else np.zeros(0, int)
        for p in range(len(self.s.rphi)):
            mp = pidx == p
            if mp.any():
                rp = self.rphi[p](r[mp])
                drp = self.rphi[p](r[mp], 1)
                phi[mp] = rp / r[mp]
                dphi[mp] = (drp - rp / r[mp]) / r[mp]
        E = float(Femb.sum() + phi.sum())
        fmag = -(dphi + dF[i] * drho_ji + dF[j] * drho_ij)      # -dE/dr along r_ij
        fvec = (fmag / r)[:, None] * d
        F = np.zeros((n, 3))
        np.add.at(F, i, fvec)
        np.add.at(F, j, -fvec)
        return E, F, float((fvec * d).sum())
