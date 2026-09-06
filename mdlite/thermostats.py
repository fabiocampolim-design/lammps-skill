# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Thermostats for velocity Verlet: each exposes apply(state, dt, half) and is called before the first half kick
(half=0) and after the second (half=1)."""

import numpy as np

from .measure import kinetic_energy, kinetic_temperature


class Berendsen:
    """Weak coupling (Berendsen et al. 1984): rescale v at the end of the step. Not canonical — the chapters say so."""

    def __init__(self, T0, tau):
        self.T0, self.tau = float(T0), float(tau)

    def apply(self, state, dt, half):
        if half != 1:
            return
        T = kinetic_temperature(state.vel, state.mass)
        lam = np.sqrt(1.0 + dt / self.tau * (self.T0 / T - 1.0)) if T > 0 else 1.0
        state.vel *= lam


class Langevin:
    """Stochastic thermostat, O-step of BAOAB (Leimkuhler & Matthews 2013): v <- c1 v + c2 sqrt(T0/m) xi."""

    def __init__(self, T0, gamma, seed=None):
        self.T0, self.gamma, self.rng = float(T0), float(gamma), np.random.default_rng(seed)

    def apply(self, state, dt, half):
        if half != 1:
            return
        c1 = np.exp(-self.gamma * dt)
        c2 = np.sqrt((1.0 - c1 * c1) * self.T0)
        m = state.mass_array[:, None]
        state.vel = c1 * state.vel + c2 * self.rng.normal(size=state.vel.shape) / np.sqrt(m)


class NoseHooverChain:
    """Martyna–Tuckerman–Klein chain (Martyna, Klein & Tuckerman 1992), half-step propagation before and after the
    velocity-Verlet step (Tuckerman 2010 §4.10). `history` stores the conserved-quantity contribution after each apply(half=1)."""

    def __init__(self, T0, tau, nchain=3):
        self.T0, self.tau, self.nchain = float(T0), float(tau), int(nchain)
        self.xi = np.zeros(nchain)      # thermostat "positions"
        self.vxi = np.zeros(nchain)     # thermostat velocities
        self.Q = None
        self.dof = None
        self.history = []

    def _init(self, state):
        n = len(state.pos)
        self.dof = 3 * n - 3
        omega2 = (2 * np.pi / self.tau) ** 2
        self.Q = np.full(self.nchain, self.T0 / omega2)
        self.Q[0] *= self.dof

    def apply(self, state, dt, half):
        if self.Q is None:
            self._init(state)
        h = 0.5 * dt
        K2 = 2.0 * kinetic_energy(state.vel, state.mass)
        M = self.nchain
        G = np.zeros(M)
        G[0] = (K2 - self.dof * self.T0) / self.Q[0]
        for k in range(1, M):
            G[k] = (self.Q[k - 1] * self.vxi[k - 1] ** 2 - self.T0) / self.Q[k]
        # half-step update of the chain, last to first
        self.vxi[M - 1] += 0.5 * h * G[M - 1]
        for k in range(M - 2, -1, -1):
            e = np.exp(-0.25 * h * self.vxi[k + 1])
            self.vxi[k] = e * (e * self.vxi[k] + 0.5 * h * G[k])
        scale = np.exp(-h * self.vxi[0])
        state.vel *= scale
        K2 *= scale * scale
        self.xi += h * self.vxi
        G[0] = (K2 - self.dof * self.T0) / self.Q[0]
        for k in range(M - 1):
            e = np.exp(-0.25 * h * self.vxi[k + 1])
            self.vxi[k] = e * (e * self.vxi[k] + 0.5 * h * G[k])
            G[k + 1] = (self.Q[k] * self.vxi[k] ** 2 - self.T0) / self.Q[k + 1]
        self.vxi[M - 1] += 0.5 * h * G[M - 1]
        if half == 1:
            extra = 0.5 * (self.Q * self.vxi ** 2).sum() + self.dof * self.T0 * self.xi[0] + self.T0 * self.xi[1:].sum()
            self.history.append(float(extra))
