# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Energy minimisers: steepest descent (teaching) and FIRE (Bitzek et al., PRL 97, 170201 (2006))."""

import numpy as np

from .integrate import forces


def _fmax(F):
    return float(np.sqrt((F * F).sum(1)).max())


def steepest_descent(state, potentials, nlist, steps=100, alpha=0.01, ftol=1e-6, dmax=0.05):
    """x <- x + alpha F, with every displacement capped at dmax so a steep repulsive wall cannot launch an atom
    (the teaching point of the chapter: a fixed step is not a line search)."""
    nlist.update(state.pos)
    E, F, _ = forces(state, potentials, nlist)
    k = 0
    for k in range(steps):
        fmax = _fmax(F)
        if fmax < ftol:
            break
        step = alpha * F
        if alpha * fmax > dmax:
            step *= dmax / (alpha * fmax)
        state.pos = state.box.wrap(state.pos + step)
        nlist.update(state.pos)
        E, F, _ = forces(state, potentials, nlist)
    return {"E": E, "fmax": _fmax(F), "steps": k + 1}


def fire(state, potentials, nlist, steps=1000, dt=0.005, ftol=1e-6, alpha0=0.1, finc=1.1, fdec=0.5, falpha=0.99, nmin=5, dtmax=0.05):
    nlist.update(state.pos)
    E, F, _ = forces(state, potentials, nlist)
    v = np.zeros_like(state.pos)
    alpha, npos = alpha0, 0
    m = state.mass_array[:, None]
    k = 0
    for k in range(steps):
        if _fmax(F) < ftol:
            break
        P = (F * v).sum()
        vn, fn = np.linalg.norm(v), np.linalg.norm(F)
        v = (1 - alpha) * v + alpha * (F / fn if fn else 0) * vn
        if P > 0:
            npos += 1
            if npos > nmin:
                dt = min(dt * finc, dtmax)
                alpha *= falpha
        else:
            npos = 0
            v[:] = 0
            dt *= fdec
            alpha = alpha0
        v += dt * F / m
        state.pos = state.box.wrap(state.pos + dt * v)
        nlist.update(state.pos)
        E, F, _ = forces(state, potentials, nlist)
    return {"E": E, "fmax": _fmax(F), "steps": k + 1}
