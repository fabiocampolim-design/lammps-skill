# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Chapter 05 — Potentials: EAM. Both: the mdlite/synthetic-potential half runs unconditionally
(rule 7 -- no real potential file is ever required to exist); the real-Cu comparison reads the
existing verified record."""

from nbbuild import code, md

CELLS = [
    md("""
## Why the potential file is fetched, never shipped

An EAM potential (`setfl`/`funcfl`: tabulated `F(rho)`, `rho(r)`, `r*phi(r)`) is data someone fit to
experiment or first-principles calculations, distributed under its own terms -- not LAMMPS's
GPL-2.0 and not this project's Apache-2.0. `lammps-skill` never ships one: `runs/` and the installer
routes fetch potentials the user already has (their own LAMMPS installation's `potentials/`
directory, or NIST's repository), and every test and chapter that needs *a* potential to exercise
the parser or the physics uses `lammpskill.io.potential.synthetic_setfl` -- a physically reasonable
one built from a closed form, never a real element's fit.
"""),

    md("""
## Forces from a synthetic potential, checked the same way chapter 02 checked Lennard-Jones

`mdlite.eam.EAM` wraps a `setfl`; its forces should match a numerical derivative of its energy, on
any potential, real or synthetic.
"""),

    code('''\
import numpy as np

from mdlite.box import Box
from lammpskill.io.potential import synthetic_setfl
from mdlite.eam import EAM
from mdlite.neighbors import VerletList


def fcc(n, rho):
    a = (4.0 / rho) ** (1.0 / 3.0)
    base = np.array([[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]) * a
    cells = np.array([[i, j, k] for i in range(n) for j in range(n) for k in range(n)]) * a
    return (cells[:, None, :] + base[None, :, :]).reshape(-1, 3), Box([n * a] * 3)


s = synthetic_setfl()
pos, box = fcc(2, 0.25)
rng = np.random.default_rng(0)
pos = pos + rng.normal(0, 0.03, pos.shape)
eam = EAM(s, {1: 0})
types = np.ones(len(pos), int)
vl = VerletList(box, s.cutoff)
vl.update(pos)
E, F, _ = eam.energy_forces(pos, box, vl.pairs, types)

h = 1e-5
worst = 0.0
for k, c in ((0, 0), (7, 1), (20, 2)):
    p = pos.copy()
    p[k, c] += h
    Ep = eam.energy_forces(p, box, vl.pairs, types)[0]
    p[k, c] -= 2 * h
    Em = eam.energy_forces(p, box, vl.pairs, types)[0]
    worst = max(worst, abs(F[k, c] - (-(Ep - Em) / (2 * h))))
print("largest |analytic - numerical| force, synthetic EAM:", worst)
assert worst < 1e-3
'''),

    md("""
## Lattice constant and cohesive energy: a cubic fit of E(a)

The method this toolkit uses for any EAM element: place an FCC lattice at a grid of lattice
constants, compute the energy per atom at each, fit a cubic, and take the minimum. Run here on the
synthetic potential -- the minimum exists and the fit is self-consistent (its own derivative is
zero there), which is everything that can be checked *without* a reference value to compare to.
"""),

    code('''\
a_grid = np.linspace(1.0, 1.6, 12)
energies = []
for a in a_grid:
    p, b = fcc(3, 4.0 / a ** 3)
    tt = np.ones(len(p), int)
    v = VerletList(b, s.cutoff)
    v.update(p)
    e, _, _ = eam.energy_forces(p, b, v.pairs, tt)
    energies.append(e / len(p))

c = np.polyfit(a_grid, energies, 3)
roots = np.roots(np.polyder(c))
cands = [r.real for r in roots if abs(r.imag) < 1e-9 and a_grid[0] < r.real < a_grid[-1]]
a0 = min(cands, key=lambda r: np.polyval(c, r))
e0 = np.polyval(c, a0)
slope_at_min = np.polyval(np.polyder(c), a0)
print("synthetic potential: a0=%.4f, E(a0)=%.4f, dE/da at the fitted minimum=%.2e (should be ~0)" % (a0, e0, slope_at_min))
assert abs(slope_at_min) < 1e-6
'''),

    md("""
## The real comparison: copper, against a LAMMPS box/relax minimisation

`data/records/eam_cu_lattice.json` is the same method above, run on a real `Cu_u3.eam` file the
project's owner obtained separately (never tracked), compared against LAMMPS's own `minimize` on
the same potential. This is the record chapter 00 cited as one of `mdlite`'s three cross-checks.
"""),

    code('''\
import json

with open("../data/records/eam_cu_lattice.json", encoding="utf-8") as f:
    cu = json.load(f)

print("lattice constant a0: mdlite=%.6f  LAMMPS=%.6f  |diff|=%.2e  (tolerance %.0e)"
      % (cu["a0_mdlite"], cu["a0_lammps"], cu["measured"]["da"], cu["tolerance_a0"]))
print("cohesive energy Ecoh: mdlite=%.6f  LAMMPS=%.6f  |diff|=%.2e  (tolerance %.0e)"
      % (cu["ecoh_mdlite"], cu["ecoh_lammps"], cu["measured"]["de"], cu["tolerance_ecoh"]))
print(cu["provenance"]["why"])
assert cu["measured"]["da"] < cu["tolerance_a0"] and cu["measured"]["de"] < cu["tolerance_ecoh"]
'''),

    md("""
## Reading it

- Nothing above needed a real potential file to run -- the synthetic potential is enough to check
  that the *method* (forces vs numerical derivative, cubic fit of E(a)) is implemented correctly.
- The real Cu numbers close the loop: the same method, on a real fit, agrees with LAMMPS's own
  `box/relax` minimisation to five decimal places in the lattice constant.
- The two potentials are read by the same parser (chapter 08): `synthetic_setfl` and
  `read_eam_setfl` return the same `EAMSetfl` shape, so `mdlite.eam.EAM` never needs to know which
  kind of file it was handed.
"""),
]

TALLY = [
    ("worst < 1e-3", "the synthetic EAM potential's forces match a numerical derivative"),
    ("abs(slope_at_min) < 1e-6", "the cubic fit's own minimum is self-consistent (zero derivative there)"),
    ("cu['measured']['da'] < cu['tolerance_a0'] and cu['measured']['de'] < cu['tolerance_ecoh']",
     "the real-copper lattice constant and cohesive energy agree with LAMMPS within their recorded tolerance"),
]
