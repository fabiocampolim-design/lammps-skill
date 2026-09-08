# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Chapter 02 — Forces and Integration. Both: mdlite runs unconditionally (no LAMMPS needed for its
half), and the LAMMPS side goes through run_or_load against a record that already exists, so the
chapter finishes either way."""

from nbbuild import code, md

CELLS = [
    md("""
## What velocity Verlet needs to get right

`mdlite.integrate.velocity_verlet` is the same update every MD code uses: a half-kick, a drift, a
force evaluation, a second half-kick. Two things have to hold for that to be trustworthy: the force
really is `-dE/dx` (checked against a numerical derivative), and energy stays constant as the
timestep shrinks (checked by running the same system at two timesteps).
"""),

    md("""
## Forces vs a numerical derivative

`LennardJones.energy_forces` returns forces analytically. Displacing one atom by `h` along one axis
and taking the central difference of the energy should reproduce that force component to `O(h^2)`.
"""),

    code('''\
import numpy as np

from mdlite.box import Box
from mdlite.neighbors import VerletList
from mdlite.pair import LennardJones


def fcc(n, rho):
    a = (4.0 / rho) ** (1.0 / 3.0)
    base = np.array([[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]) * a
    cells = np.array([[i, j, k] for i in range(n) for j in range(n) for k in range(n)]) * a
    return (cells[:, None, :] + base[None, :, :]).reshape(-1, 3), Box([n * a] * 3)


pos, box = fcc(2, 0.8442)
rng = np.random.default_rng(0)
pos = pos + rng.normal(0, 0.05, pos.shape)   # off-lattice, so the force is not accidentally zero
lj = LennardJones()
vl = VerletList(box, 2.5)
vl.update(pos)
E0, F, _ = lj.energy_forces(pos, box, vl.pairs)

h = 1e-6
worst = 0.0
for k, c in ((0, 0), (5, 2), (11, 1), (3, 1)):
    p = pos.copy()
    p[k, c] += h
    Ep = lj.energy_forces(p, box, vl.pairs)[0]
    p[k, c] -= 2 * h
    Em = lj.energy_forces(p, box, vl.pairs)[0]
    numeric = -(Ep - Em) / (2 * h)
    worst = max(worst, abs(F[k, c] - numeric))
print("largest |analytic - numerical| over 4 components:", worst)
assert worst < 1e-5
'''),

    md("""
## Energy conservation vs timestep

A correct integrator's energy drift shrinks as the timestep shrinks -- roughly as `dt^2` for
velocity Verlet. Running the same starting state at two timesteps and comparing the relative energy
drift after the same physical time makes that concrete rather than assumed.
"""),

    code('''\
from mdlite.integrate import State, velocity_verlet


def drift(dt, nsteps):
    pos, box = fcc(3, 0.8442)
    rng = np.random.default_rng(1)
    vel = rng.normal(0, 1.0, pos.shape)
    vel -= vel.mean(0)
    st = State(pos=pos, vel=vel, mass=1.0, box=box)
    rec = velocity_verlet(st, [LennardJones()], dt=dt, nsteps=nsteps, nlist=VerletList(box, 2.5), every=nsteps)
    E = [r["E_tot"] for r in rec]
    return abs(E[-1] - E[0]) / abs(E[0])


d_coarse = drift(0.02, 100)     # same physical time (2.0 reduced units), coarser step
d_fine = drift(0.005, 400)      # ... finer step
print("relative energy drift, dt=0.02 : %.3e" % d_coarse)
print("relative energy drift, dt=0.005: %.3e" % d_fine)
print("ratio (expect roughly (0.02/0.005)^2 = 16, drift is noisy so this is an order of magnitude, not a law):",
      round(d_coarse / max(d_fine, 1e-16), 1))
assert d_fine < d_coarse, "the finer timestep must conserve energy at least as well as the coarser one"
'''),

    md("""
## The same case in LAMMPS: forces at round-off

The comparison above stays inside `mdlite`. `data/records/lj_energy_vs_lammps.json` is the same
question asked across the toolkit boundary: 256 atoms, the same Lennard-Jones potential, forces
from `mdlite` compared to forces LAMMPS itself printed to a dump. It was not always this close --
chapter 08's N-5 is the reason it went from 5e-5 to round-off, by widening the dump's float format,
not by changing either force calculation.
"""),

    code('''\
from lammpskill.run import run_or_load


def compute():
    # regenerating this record from scratch is scripts/run_benchmarks.py's job (it sets
    # `thermo_modify norm no` and `dump_modify ... format float %20.15g` -- N-4 and N-5 from
    # chapter 08); this chapter only reads the record it already produced.
    raise RuntimeError("data/records/lj_energy_vs_lammps.json is expected to exist; "
                        "see scripts/run_benchmarks.py to regenerate it")


rec = run_or_load("lj_energy_vs_lammps", compute, records_dir="../data/records")
print("source:", rec["source"])
print("natoms:", rec["natoms"])
print("force max-diff (mdlite vs LAMMPS):", rec["measured"]["dF"], "| tolerance:", rec["tolerance_force"])
print("energy diff:                     ", rec["measured"]["dE"], "| tolerance:", rec["tolerance_energy"])
print(rec["provenance"]["why"])
assert rec["measured"]["dF"] < rec["tolerance_force"]
'''),

    md("""
## Reading it

- A force that is not `-dE/dx` to numerical precision is not a force worth integrating with --
  checking that first catches a whole class of bug before it ever shows up as bad energy
  conservation.
- Energy conservation is a *rate* statement (drift shrinks with the timestep), not a pass/fail on
  one run -- which is why this chapter runs two timesteps and compares, rather than asserting a
  single drift is "small".
- The two checks compose: `mdlite`'s own internal consistency (forces vs numerical derivative,
  drift vs timestep) is necessary but not sufficient -- the cross-check against LAMMPS is what
  makes the numbers `mdlite` teaches trustworthy outside `mdlite` itself.
"""),
]

TALLY = [
    ("worst < 1e-5", "mdlite's Lennard-Jones forces match a numerical derivative to 1e-5"),
    ("d_fine < d_coarse", "the finer timestep conserved energy at least as well as the coarser one"),
    ("rec['measured']['dF'] < rec['tolerance_force']",
     "mdlite forces agree with the recorded LAMMPS comparison within its stated tolerance"),
]
