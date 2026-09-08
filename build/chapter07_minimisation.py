# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Chapter 07 — Minimisation. Runs with no LAMMPS installed: everything here is mdlite."""

from nbbuild import code, md

CELLS = [
    md("""
## A fixed step is not a line search

Steepest descent moves every atom by `alpha * F`: simple, and dangerous near a steep repulsive
wall, where `F` can be enormous and a fixed step overshoots straight through the minimum into an
even steeper part of the potential. **N-7 is the lesson this chapter teaches**: the first version
of `mdlite.minimize.steepest_descent` had no cap on the step size, and on a pair of atoms placed
deep in the Lennard-Jones repulsive core, it diverged -- `fmax` reached `2.6e14` instead of
shrinking. The fix is one line: cap every displacement at `dmax`, so a huge force still moves the
atom only a small, bounded distance.
"""),

    md("""
## Reproducing it: the LJ wall

Two atoms at `r=0.3 sigma`, deep inside the repulsive core (the potential's minimum is near
`r=2^(1/6) sigma ~= 1.12`). The force there is enormous -- `alpha * F` with the textbook default
`alpha=0.01` is millions of reduced-distance units, not the small correction a minimiser should
take.
"""),

    code('''\
import numpy as np

from mdlite.box import Box
from mdlite.integrate import State
from mdlite.minimize import steepest_descent
from mdlite.neighbors import VerletList
from mdlite.pair import LennardJones


def lj_wall():
    pos = np.array([[0.0, 0.0, 0.0], [0.3, 0.0, 0.0]])
    box = Box([10.0, 10.0, 10.0])
    return State(pos, np.zeros_like(pos), 1.0, box), box


st, box = lj_wall()
vl = VerletList(box, 2.5)
r0 = steepest_descent(st, [LennardJones()], vl, steps=50, dmax=1e8)   # dmax effectively disabled: N-7's bug, reproduced on purpose
print("uncapped step: fmax after %d iterations = %.3e (should be shrinking toward 0; it is not)" % (r0["steps"], r0["fmax"]))
assert r0["fmax"] > 1e6, "the point of this cell is to reproduce the explosion, not avoid it"
'''),

    code('''\
st, box = lj_wall()
vl = VerletList(box, 2.5)
r1 = steepest_descent(st, [LennardJones()], vl, steps=200)   # default dmax=0.05 -- the fix
print("capped step (default dmax): fmax after %d iterations = %.3e" % (r1["steps"], r1["fmax"]))
assert r1["fmax"] < 1.0, "the same starting geometry, with the displacement cap, actually minimises"
'''),

    md("""
## Steepest descent vs FIRE, on a real (if small) system

A perturbed FCC lattice -- every atom nudged off its lattice site -- is a more representative test
than the pathological two-atom case above. FIRE (Bitzek et al. 2006) adapts its own step by
tracking whether the last move lowered the energy, so it does not need a hand-picked `alpha` at
all; steepest descent, even with the displacement cap, still needs many more iterations to reach
the same force tolerance.
"""),

    code('''\
from mdlite.minimize import fire


def fcc(n, rho):
    a = (4.0 / rho) ** (1.0 / 3.0)
    base = np.array([[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]) * a
    cells = np.array([[i, j, k] for i in range(n) for j in range(n) for k in range(n)]) * a
    return (cells[:, None, :] + base[None, :, :]).reshape(-1, 3), Box([n * a] * 3)


pos, box = fcc(3, 0.8442)
rng = np.random.default_rng(1)
perturbed = pos + rng.normal(0, 0.05, pos.shape)

st_sd = State(perturbed.copy(), np.zeros_like(perturbed), 1.0, box)
r_sd = steepest_descent(st_sd, [LennardJones()], VerletList(box, 2.5), steps=400, ftol=1e-4)

st_fire = State(perturbed.copy(), np.zeros_like(perturbed), 1.0, box)
r_fire = fire(st_fire, [LennardJones()], VerletList(box, 2.5), steps=2000, ftol=1e-4)

print("steepest descent: %4d iterations, fmax=%.2e, E=%.6f" % (r_sd["steps"], r_sd["fmax"], r_sd["E"]))
print("FIRE:              %4d iterations, fmax=%.2e, E=%.6f" % (r_fire["steps"], r_fire["fmax"], r_fire["E"]))
assert r_sd["fmax"] < 1e-4 and r_fire["fmax"] < 1e-4
assert r_fire["E"] <= r_sd["E"] + 1e-6, "FIRE should reach at least as low an energy"
'''),

    md("""
## Reading it

- A minimiser is not "correct" merely because it eventually stops moving -- `steepest_descent`
  without a displacement cap stops too, just not at a minimum: it stops because the numbers involved
  overflow, which is what `fmax=2.6e14` actually means.
- The cap trades a little speed (more iterations near a steep wall) for the guarantee that no single
  step can leave the region the force evaluation is even meaningful in.
- FIRE's adaptive step is a more general answer to the same problem: rather than one global cap
  chosen by hand, it shrinks its own step whenever the last move made things worse.
"""),
]

TALLY = [
    ("r0['fmax'] > 1e6", "an uncapped steepest-descent step really does diverge on the LJ wall (N-7, reproduced)"),
    ("r1['fmax'] < 1.0", "the same case, with the displacement cap restored, actually minimises"),
    ("r_sd['fmax'] < 1e-4 and r_fire['fmax'] < 1e-4", "both minimisers converge on the perturbed FCC lattice"),
    ("r_fire['E'] <= r_sd['E'] + 1e-6", "FIRE reaches at least as low an energy as capped steepest descent"),
]
