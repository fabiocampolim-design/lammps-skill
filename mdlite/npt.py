# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""An NPT *sketch*: Berendsen weak coupling (Berendsen et al. 1984) applied to the box as well as
the thermostat that already exists. This is not a fluctuating-cell method (no Parrinello-Rahman or
Martyna-Tuckerman-Klein cell mass) and does not sample the isothermal-isobaric ensemble correctly --
like mdlite.thermostats.Berendsen, it is a relaxation method: it moves the box toward a target
pressure and holds it there. That is enough to teach what NPT is *for*, not a claim to be a
research-grade barostat; the chapter that uses this says so."""

from .integrate import forces
from .measure import kinetic_temperature, pressure


class BerendsenBarostat:
    """Isotropic box rescaling toward a target pressure P0, weak-coupling time constant tau."""

    def __init__(self, P0, tau, compressibility=1.0):
        self.P0, self.tau, self.compressibility = float(P0), float(tau), float(compressibility)

    def mu(self, dt, P):
        return (1.0 - dt / self.tau * self.compressibility * (self.P0 - P)) ** (1.0 / 3.0)


def velocity_verlet_npt(state, potentials, dt, nsteps, nlist, thermostat, barostat, every=1):
    """Velocity Verlet with a temperature thermostat and a Berendsen barostat, the latter applied
    once per full step after the second half-kick. Records step, T, the energy terms, P and V."""
    nlist.update(state.pos)
    m = state.mass_array[:, None]
    E, F, vir = forces(state, potentials, nlist)
    records = []

    def record():
        T = kinetic_temperature(state.vel, state.mass)
        K = 0.5 * float((m[:, 0] * (state.vel * state.vel).sum(1)).sum())
        records.append({"step": state.step, "T": T, "E_pot": E, "E_kin": K, "E_tot": E + K,
                         "P": pressure(state, vir, T), "V": state.box.volume})

    record()
    for _ in range(nsteps):
        if thermostat is not None:
            thermostat.apply(state, dt, half=0)
        state.vel += 0.5 * dt * F / m
        state.pos += dt * state.vel
        state.pos = state.box.wrap(state.pos)
        nlist.update(state.pos)
        E, F, vir = forces(state, potentials, nlist)
        state.vel += 0.5 * dt * F / m
        if thermostat is not None:
            thermostat.apply(state, dt, half=1)

        T = kinetic_temperature(state.vel, state.mass)
        P = pressure(state, vir, T)
        mu = barostat.mu(dt, P)
        state.box.lengths *= mu
        state.pos = state.box.lo + (state.pos - state.box.lo) * mu
        nlist.update(state.pos)
        E, F, vir = forces(state, potentials, nlist)   # forces at the rescaled positions, for the next step

        state.step += 1
        state.time += dt
        if state.step % every == 0:
            record()
    return records
