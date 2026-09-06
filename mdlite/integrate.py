# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Velocity Verlet (Swope et al. 1982; Frenkel & Smit 2002 §4.3) with an optional thermostat hook applied at both half steps."""

import numpy as np

from .measure import kinetic_energy, kinetic_temperature, pressure


class State:
    def __init__(self, pos, vel, mass, box, step=0, time=0.0, types=None):
        self.pos, self.vel = np.array(pos, float), np.array(vel, float)
        self.mass, self.box, self.step, self.time = mass, box, step, time
        self.types = None if types is None else np.asarray(types, int)

    @property
    def mass_array(self):
        m = np.asarray(self.mass, float)
        return np.broadcast_to(m, (len(self.pos),)) if m.ndim == 0 else m


def forces(state, potentials, nlist=None):
    E, F, vir = 0.0, np.zeros_like(state.pos), 0.0
    for p in potentials:
        if getattr(p, "bonds", None) is not None:
            e, f, v = p.energy_forces(state.pos, state.box, p.bonds)
        elif hasattr(p, "type_map"):
            e, f, v = p.energy_forces(state.pos, state.box, nlist.pairs, state.types)
        else:
            e, f, v = p.energy_forces(state.pos, state.box, nlist.pairs)
        E += e
        F += f
        vir += v
    return E, F, vir


def velocity_verlet(state, potentials, dt, nsteps, nlist=None, thermostat=None, every=1, callback=None):
    if nlist is not None:
        nlist.update(state.pos)
    m = state.mass_array[:, None]
    E, F, vir = forces(state, potentials, nlist)
    records = []

    def record():
        T = kinetic_temperature(state.vel, state.mass)
        K = kinetic_energy(state.vel, state.mass)
        rec = {"step": state.step, "time": state.time, "T": T, "E_pot": E, "E_kin": K, "E_tot": E + K,
               "P": pressure(state, vir, T)}
        hist = getattr(thermostat, "history", None)
        if hist:
            rec["H_extra"] = hist[-1]
        records.append(rec)
        if callback:
            callback(state, rec)

    record()
    for _ in range(nsteps):
        if thermostat is not None:
            thermostat.apply(state, dt, half=0)
        state.vel += 0.5 * dt * F / m
        state.pos += dt * state.vel
        state.pos = state.box.wrap(state.pos)
        if nlist is not None:
            nlist.update(state.pos)
        E, F, vir = forces(state, potentials, nlist)
        state.vel += 0.5 * dt * F / m
        if thermostat is not None:
            thermostat.apply(state, dt, half=1)
        state.step += 1
        state.time += dt
        if state.step % every == 0:
            record()
    return records
