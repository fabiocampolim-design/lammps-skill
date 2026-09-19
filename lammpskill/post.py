# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Analysis independent of the binary: statistics, RDF, MSD/diffusion, VACF, S(k), energy drift, elastic constants,
and comparison against licence-cleared reference tables in data/benchmarks/ (each with its provenance)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import numpy as np

_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BENCHMARKS = os.path.join(_ROOT, "data", "benchmarks")


def block_average(x, nblocks=10):
    x = np.asarray(x, float)
    n = len(x) // nblocks
    if n < 1:
        raise ValueError("need at least %d samples for %d blocks" % (nblocks, nblocks))
    blocks = x[: n * nblocks].reshape(nblocks, n).mean(axis=1)
    return float(blocks.mean()), float(blocks.std(ddof=1) / np.sqrt(nblocks))


def rdf(positions, box, nbins=100, rmax=None, types=None, pair=None, chunk=2000):
    pos = np.asarray(positions, float)
    if rmax is None:
        rmax = 0.5 * float(box.lengths.min())
    if pair is not None and types is not None:
        types = np.asarray(types)
        a = pos[types == pair[0]]
        b = pos[types == pair[1]]
        same = pair[0] == pair[1]
    else:
        a, b, same = pos, pos, True
    edges = np.linspace(0.0, rmax, nbins + 1)
    counts = np.zeros(nbins)
    for start in range(0, len(a), chunk):
        d = a[start:start + chunk, None, :] - b[None, :, :]
        d = box.minimum_image(d.reshape(-1, 3)).reshape(d.shape)
        r = np.sqrt((d * d).sum(axis=-1))
        if same:
            idx = np.arange(start, min(start + chunk, len(a)))
            r[np.arange(len(idx)), idx] = np.inf
        counts += np.histogram(r[r < rmax], bins=edges)[0]
    shell = 4.0 / 3.0 * np.pi * (edges[1:] ** 3 - edges[:-1] ** 3)
    rho_b = len(b) / box.volume
    norm = len(a) * rho_b * shell
    g = counts / norm
    return 0.5 * (edges[1:] + edges[:-1]), g


def rdf_trajectory(traj, **kw):
    r, acc = None, None
    for fr in traj.frames:
        r, g = rdf(fr.positions, fr.box, types=fr.types if kw.get("pair") else None, **kw)
        acc = g if acc is None else acc + g
    return r, acc / len(traj.frames)


def unwrap_positions(traj):
    """Positions unwrapped by the minimum-image displacement between consecutive frames (needs dt small vs box crossing)."""
    P = traj.positions.copy()
    for k in range(1, len(P)):
        d = traj.frames[k].box.minimum_image(P[k] - P[k - 1])
        P[k] = P[k - 1] + d
    return P


def msd(traj, dt=1.0, unwrap=True):
    """Mean-squared displacement. `dt` is the real time **per LAMMPS step** (e.g. the input
    script's `timestep` command) -- it multiplies each frame's own `f.timestep` (already the
    actual step count LAMMPS wrote, e.g. 0, 20, 40, ... for a dump every 20 steps), which already
    encodes the dump interval. Passing `dt * dump_every` double-counts it and silently produces a
    diffusion coefficient wrong by a factor of `dump_every` (found live, chapter 06, 2026-09-19).
    This is a different convention from `vacf()` below, whose `dt` multiplies a plain lag index,
    not a real step count -- the two are not interchangeable."""
    P = unwrap_positions(traj) if unwrap else traj.positions
    d = P - P[0]
    m = (d * d).sum(axis=-1).mean(axis=1)
    t = np.array([f.timestep for f in traj.frames], float) * dt
    t = t - t[0] if np.all(np.diff(t) > 0) else np.arange(len(m)) * dt
    return t, m


def diffusion_coefficient(t, m, fit_from=0.5, dim=3):
    i0 = int(len(t) * fit_from)
    A = np.column_stack([t[i0:], np.ones(len(t) - i0)])
    sol, res, _, _ = np.linalg.lstsq(A, m[i0:], rcond=None)
    slope = sol[0]
    dof = max(len(t) - i0 - 2, 1)
    s2 = (res[0] / dof) if len(res) else 0.0
    cov = s2 * np.linalg.inv(A.T @ A)
    return float(slope / (2 * dim)), float(np.sqrt(cov[0, 0]) / (2 * dim))


def vacf(velocities, dt=1.0, max_lag=None):
    v = np.asarray(velocities, float)
    nf = len(v)
    max_lag = nf - 1 if max_lag is None else min(max_lag, nf - 1)
    c = np.zeros(max_lag + 1)
    for lag in range(max_lag + 1):
        c[lag] = (v[: nf - lag] * v[lag:]).sum(axis=-1).mean()
    return np.arange(max_lag + 1) * dt, c / c[0]


def structure_factor(r, g, rho, kmax=15.0, nk=150):
    r, g = np.asarray(r, float), np.asarray(g, float)
    k = np.linspace(kmax / nk, kmax, nk)
    kr = np.outer(k, r)
    integrand = r ** 2 * (g - 1.0) * np.sin(kr) / kr
    S = 1.0 + 4.0 * np.pi * rho * np.trapezoid(integrand, r, axis=1)
    return k, S


def energy_drift(thermo, col="TotEng"):
    e = thermo.get(col)
    steps = thermo.get("Step")
    slope = float(np.polyfit(steps, e, 1)[0])
    return {"slope_per_step": slope, "rel_drift": float(abs(e[-1] - e[0]) / abs(e[0])) if e[0] else float("nan"),
            "mean": float(e.mean()), "std": float(e.std())}


def elastic_from_stress(strains, stresses):
    """Cubic constants from stress-strain pairs (stress = -pressure tensor, same units in and out)."""
    e11, s11, s22, g23, s23 = [], [], [], [], []
    for eps, sig in zip(strains, stresses):
        eps, sig = np.asarray(eps, float), np.asarray(sig, float)
        if abs(eps[0, 0]) > 0 and abs(eps[1, 2]) == 0:
            e11.append(eps[0, 0])
            s11.append(sig[0, 0])
            s22.append(sig[1, 1])
        elif abs(eps[1, 2]) > 0:
            g23.append(2 * eps[1, 2])
            s23.append(sig[1, 2])
    C11 = -np.polyfit(e11, s11, 1)[0] if e11 else float("nan")
    C12 = -np.polyfit(e11, s22, 1)[0] if e11 else float("nan")
    C44 = -np.polyfit(g23, s23, 1)[0] if g23 else float("nan")
    return {"C11": float(C11), "C12": float(C12), "C44": float(C44)}


def load_benchmark(name):
    with open(os.path.join(BENCHMARKS, name + ".json"), encoding="utf-8") as f:
        b = json.load(f)
    if "provenance" not in b or "entries" not in b:
        raise ValueError("benchmark %s lacks provenance/entries" % name)
    return b


@dataclass
class Comparison:
    value: float
    reference: float
    error: float
    diff: float
    within: bool
    tolerance: float


def compare(value, entry, tolerance=None):
    ref = float(entry["value"])
    err = float(entry.get("error", 0.0) or 0.0)
    tol = float(tolerance) if tolerance is not None else (2.0 * err if err else abs(ref) * 0.01)
    diff = float(value) - ref
    return Comparison(float(value), ref, err, diff, abs(diff) <= tol, tol)
