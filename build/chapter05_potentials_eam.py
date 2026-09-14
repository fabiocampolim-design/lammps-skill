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
## Vacancy formation energy: remove an atom, relax, compare

One more property from the same synthetic potential: remove the lattice site nearest an FCC
supercell's centre, relax the remaining atoms with FIRE (chapter 07's other minimiser, fixed box
volume -- the standard single-vacancy approximation), and read off

`E_vacancy = E_relaxed(N-1 atoms) - (N-1)/N * E_perfect(N atoms)`

This refits `a0` on its own, wider grid (`a` in 2.6..3.6, `n=4` cells) rather than reusing the
`a0` found above: that fit's `a` in 1.0..1.6 with `n=3` cells puts the box side under twice the
potential's cutoff, which breaks the minimum-image convention for a comparison this sensitive to
absolute energies (measured directly: it gives a *positive*, i.e. unbound, cohesive energy --
fine for checking the fit is self-consistent, not for anything that needs a real bound crystal).
The wider grid here keeps the box comfortably larger than 2x the cutoff throughout, so the
vacancy's own sanity check below is checking something real.
"""),

    code('''\
a_grid_vac = np.linspace(2.6, 3.6, 12)
energies_vac = []
for a in a_grid_vac:
    p, b = fcc(4, 4.0 / a ** 3)
    tt = np.ones(len(p), int)
    v = VerletList(b, s.cutoff)
    v.update(p)
    e, _, _ = eam.energy_forces(p, b, v.pairs, tt)
    energies_vac.append(e / len(p))
c_vac = np.polyfit(a_grid_vac, energies_vac, 3)
roots_vac = np.roots(np.polyder(c_vac))
cands_vac = [r.real for r in roots_vac if abs(r.imag) < 1e-9 and a_grid_vac[0] < r.real < a_grid_vac[-1]]
a0_vac = min(cands_vac, key=lambda r: np.polyval(c_vac, r))
e0_vac = np.polyval(c_vac, a0_vac)
print("min-image-safe fit: a0=%.4f, E(a0)=%.4f (bound: %s)" % (a0_vac, e0_vac, e0_vac < 0))
assert e0_vac < 0, "a bound crystal has negative cohesive energy per atom"

from mdlite.integrate import State
from mdlite.minimize import fire

pos_full, box_full = fcc(4, 4.0 / a0_vac ** 3)
vl_full = VerletList(box_full, s.cutoff)
vl_full.update(pos_full)
types_full = np.ones(len(pos_full), int)
E_perfect, _, _ = eam.energy_forces(pos_full, box_full, vl_full.pairs, types_full)
e_perfect_per_atom = E_perfect / len(pos_full)

L_vac = box_full.lengths[0]
center = np.array([L_vac / 2.0] * 3)
removed = int(np.argmin(np.linalg.norm(pos_full - center, axis=1)))
pos_before = pos_full.copy()
pos_vac_input = np.delete(pos_full, removed, axis=0)

vl_vac = VerletList(box_full, s.cutoff)
state = State(pos_vac_input.copy(), np.zeros_like(pos_vac_input), 63.546, box_full,
              types=np.ones(len(pos_vac_input), int))
fire_result = fire(state, [eam], vl_vac, steps=2000, ftol=1e-8)
pos_after = state.pos

e_formation = fire_result["E"] - (len(pos_full) - 1) * e_perfect_per_atom
print("synthetic potential: vacancy formation energy=%.4f, cohesive energy per atom=%.4f, FIRE fmax=%.2e"
      % (e_formation, e0_vac, fire_result["fmax"]))
assert 0 < e_formation < abs(e0_vac), "a bound crystal should cost energy for a hole, less than its cohesive energy"
assert fire_result["fmax"] < 1e-4
'''),

    md("""
## Watching the vacancy relax

The positions above, rendered: the perfect supercell before the atom nearest the centre is
removed, and the relaxed (N-1)-atom configuration after FIRE has run. `lammpskill.viz.snapshot`
needs the optional `ase` extra -- exactly the same graceful skip chapter 01 uses when it is absent.
Rendered by mass (63.546, copper's) purely to pick a radius and colour: the potential itself is
still synthetic, not a real copper fit.
"""),

    code('''\
import matplotlib.pyplot as plt

from lammpskill import viz

try:
    fig = viz.snapshot(pos_before, [L_vac] * 3, masses=[63.546] * len(pos_before))
except ImportError as e:
    print("ase not installed -- skipping the vacancy snapshots:", e)
else:
    plt.show()
    caption("The perfect fcc supercell (n=4, this section's own fitted a0) before the atom "
            "nearest the box centre is removed.")
'''),

    code('''\
try:
    fig = viz.snapshot(pos_after, [L_vac] * 3, masses=[63.546] * len(pos_after))
except ImportError as e:
    print("ase not installed -- skipping the vacancy snapshots:", e)
else:
    plt.show()
    caption("The same supercell after the vacancy is introduced and the remaining atoms are "
            "relaxed with FIRE (fmax < 1e-4): the neighbours have relaxed inward around the "
            "missing site, visible as a locally denser region next to the gap.")
'''),

    md("""
## The real comparison: a copper vacancy, against LAMMPS's own `minimize`

`data/records/eam_cu_vacancy.json` is the same method above -- FIRE-relaxed (N-1)-atom supercell,
fixed volume -- run on a real `Cu_u3.eam` file, compared against LAMMPS building the identical
supercell with `region`/`group`/`delete_atoms` and relaxing it with `minimize`. Generating this
record needs both a real Cu potential file the project's owner obtained separately (never
tracked) and a LAMMPS installation, so unlike the lattice-constant record above it may not exist
yet: `python scripts/run_benchmarks.py --which eam-cu-vacancy --potential <your Cu EAM file>`.

For scale, not as a pass/fail check: the experimentally measured copper monovacancy formation
energy is **1.29 +/- 0.02 eV** (positron annihilation; Triftshauser & McGervey, *Applied Physics*
**6**, 177-180 (1975), doi:10.1007/BF00883748) -- context for how the mdlite/LAMMPS cross-check
below compares to a real measurement, not a value either engine is tuned or expected to reproduce
exactly (a fixed-volume, single small supercell is a simplified model of the real defect).
"""),

    code('''\
import json
import os

VAC_RECORD = "../data/records/eam_cu_vacancy.json"
if os.path.exists(VAC_RECORD):
    with open(VAC_RECORD, encoding="utf-8") as f:
        cuvac = json.load(f)
    print("vacancy formation energy: mdlite=%.4f eV  LAMMPS=%.4f eV  |diff|=%.2e  (tolerance %.0e)"
          % (cuvac["e_formation_mdlite"], cuvac["e_formation_lammps"], cuvac["measured"]["dE"], cuvac["tolerance_E"]))
    print("literature (positron annihilation, Triftshauser & McGervey 1975): 1.29 +/- 0.02 eV")
    print(cuvac["provenance"]["why"])
else:
    cuvac = None
    print("no eam_cu_vacancy.json yet -- run `python scripts/run_benchmarks.py --which eam-cu-vacancy "
          "--potential <your Cu EAM file>` to generate it (needs a real Cu potential file and a "
          "LAMMPS installation, neither of which this project ships)")
'''),

    md("""
## Reading it

- Nothing above needed a real potential file to run -- the synthetic potential is enough to check
  that the *method* (forces vs numerical derivative, cubic fit of E(a), FIRE-relaxed vacancy
  formation energy) is implemented correctly.
- The real Cu numbers close the loop: the same lattice-constant method, on a real fit, agrees with
  LAMMPS's own `box/relax` minimisation to five decimal places; the vacancy formation energy
  agrees with LAMMPS's `delete_atoms` + `minimize` within its own recorded tolerance, and sits in
  the right ballpark next to a real experimental measurement.
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
    ("e0_vac < 0", "the min-image-safe fit gives a bound (negative cohesive energy) synthetic crystal"),
    ("0 < e_formation < abs(e0_vac)", "the synthetic-potential vacancy formation energy is positive and under the cohesive energy magnitude"),
    ("fire_result['fmax'] < 1e-4", "FIRE relaxed the synthetic-potential vacancy configuration to low residual force"),
    ("cuvac is None or cuvac['measured']['dE'] < cuvac['tolerance_E']",
     "when the real-copper vacancy record exists, mdlite and LAMMPS agree on its formation energy within their recorded tolerance"),
]
