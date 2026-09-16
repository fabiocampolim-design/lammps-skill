# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Chapter 12 — Water (Molecular Systems). Needs LAMMPS throughout -- SPC/E water needs PPPM
electrostatics and rigid-body SHAKE constraints, neither of which `mdlite` implements, so unlike
every earlier chapter this one has no offline, no-LAMMPS half at all."""

from nbbuild import code, md

CELLS = [
    md("""
## The first chapter with no `mdlite` comparison

Every earlier chapter that cross-checks LAMMPS does it against `mdlite`: the same forces, the same
integrator, on the same system. That stops here. SPC/E water is a *rigid* three-site model (bond
and angle geometry enforced by `fix shake`, not integrated as flexible degrees of freedom) held
together by long-range Coulomb interactions (`kspace_style pppm`) on top of Lennard-Jones.
`mdlite` implements neither rigid-body constraints nor Ewald/PPPM electrostatics -- adding either
would be new physics well beyond this roadmap item's own scope (the design spec named this
explicitly: validation against a *published* reference, not a new `mdlite` capability).

So this chapter's cross-check is against the literature instead: the SPC/E model's own saturated
liquid density at 300 K, from a real NIST reference table, the same public-domain SRSW-style
source this project's `references/benchmarks.md` already uses for the Lennard-Jones fluid.
"""),

    md("""
## The preset: `lammpskill.script.spce_water`

Already built and tested (`tests/test_script.py`) before this chapter existed -- a cubic lattice of
rigid SPC/E molecules, `fix shake` to hold the O-H bonds and H-O-H angle rigid, `kspace_style pppm`
for the long-range electrostatics. The lattice spacing (3.1 A) was chosen to already sit close to
water's real density, so nothing here starts from a wildly wrong configuration.
"""),

    code('''\
from lammpskill.script import check, render, spce_water

spec, df = spce_water(n_side=6)
text = render(spec)
print(text)
print("natoms:", df.natoms, "nmolecules:", df.natoms // 3, "nbonds:", df.bonds.shape[0], "nangles:", df.angles.shape[0])

findings = check(text)
for f in findings:
    print(f.level.upper(), f.code, "--", f.message)
assert all(f.level != "error" for f in findings), "the preset should carry no checker error"
'''),

    md("""
## The real comparison: density against a NIST reference

`data/records/water_density.json` runs `spce_water()` under `fix npt` at 300 K / 1 atm (chapter
04's own `fix npt` pattern, its first use on a real molecular system) for 20000 steps, discards the
first 5000 as equilibration, and block-averages the density over the rest. The reference is NIST's
own SPC/E benchmark table (`data/benchmarks/spce_water.json`) -- the *saturated* liquid density at
300 K from grand-canonical Wang-Landau/transition-matrix Monte Carlo, not liquid water at exactly 1
atm, a distinction stated rather than glossed over (for a liquid this incompressible the two differ
far below what this comparison can resolve anyway).
"""),

    code('''\
import json

with open("../data/records/water_density.json", encoding="utf-8") as f:
    water = json.load(f)

print("density: LAMMPS=%.2f +/- %.2f kg/m3  NIST=%.2f +/- %.2f kg/m3  |diff|=%.2f  (tolerance %.1f)"
      % (water["rho_lammps"], water["rho_lammps_err"], water["rho_nist"], water["rho_nist_err"],
         water["measured"]["d_rho"], water["tolerance_rho"]))
print(water["provenance"]["why"])
assert water["measured"]["d_rho"] < water["tolerance_rho"]
'''),

    md("""
## Watching the water box

A separate real run -- the same preset, `fix shake` and `kspace_style pppm` unchanged, a
trajectory dump added -- for the structural and visual payoff: the oxygen-oxygen radial
distribution function (the box's own structure, not part of the density check above) and the
molecules themselves, rendered and animated.
"""),

    code('''\
import dataclasses
import os
import tempfile

import numpy as np

from lammpskill.io.dump import Trajectory, read_dump
from lammpskill.post import rdf_trajectory
from lammpskill.run import run, run_or_load

DUMP_EVERY = 100
N_FRAMES = 12


def compute_water_traj():
    workdir = tempfile.mkdtemp(prefix="ch12_traj_")
    base_spec, _ = spce_water(n_side=6, steps=5000, workdir=workdir)
    traj_spec = dataclasses.replace(
        base_spec, dumps=["1 all custom %d traj.dump id type xu yu zu" % DUMP_EVERY],
        comment="the same SPC/E water box as above, with a trajectory dump for structure and the atom views")
    result = run(traj_spec, workdir, time_limit=600)
    if not result.ok:
        raise RuntimeError("trajectory run failed (rc=%s): %s" % (result.returncode, "; ".join(result.errors) or result.stderr))
    traj = read_dump(os.path.join(workdir, "traj.dump"))
    nframes = len(traj)

    # O-O RDF from the second half only -- the first half is still relaxing off the lattice start.
    eq = Trajectory(traj.frames[nframes // 2:])
    r, g = rdf_trajectory(eq, nbins=100, pair=(1, 1))

    step = max(1, nframes // N_FRAMES)
    frames = [f.positions.tolist() for f in traj.frames[::step]]
    types0 = traj.frames[0].types.tolist()
    return {"nframes": nframes, "frames": frames, "types": types0, "cell": traj.box.lengths.tolist(),
            "rdf_r": r.tolist(), "rdf_g": g.tolist(),
            "route": result.installation.route if result.installation else None}


traj_rec = run_or_load("spce_water_traj_ch12", compute_water_traj, records_dir="../data/records")
print("source:", traj_rec["source"], "| frames:", traj_rec.get("nframes"))
'''),

    md("""
## Oxygen-oxygen structure: g_OO(r)

For scale, not a pass/fail check: published SPC/E O-O radial distribution functions place the
first peak at approximately 2.7-2.8 A (e.g. Mark & Nilsson, *J. Phys. Chem. A* 105, 9954 (2001);
Camisasca, Pathak, Wikfeldt & Pettersson, *J. Chem. Phys.* 151, 044502 (2019), comparing SPC/E
directly to experimental X-ray diffraction) -- context for where this box's own g_OO(r) peak
should land, not a hard test this project could not independently re-derive an exact literature
decimal for.
"""),

    code('''\
import matplotlib.pyplot as plt

if traj_rec["source"] != "skip":
    r, g = np.array(traj_rec["rdf_r"]), np.array(traj_rec["rdf_g"])
    fig, ax = plt.subplots(figsize=(5.5, 3.2), dpi=90)
    ax.plot(r, g, lw=1.2)
    ax.axhline(1.0, color="k", ls="--", lw=0.7)
    ax.set_xlabel("r (Angstrom)"); ax.set_ylabel("g_OO(r)"); ax.set_title("oxygen-oxygen radial distribution")
    fig.tight_layout()
    plt.show()
    imax = int(np.argmax(g))
    caption("The oxygen-oxygen radial distribution function from this box's own equilibrated "
            "trajectory: a first peak near the O-O hydrogen-bonding distance, decaying to the "
            "ideal-gas value of 1 at large r -- computed by lammpskill.post.rdf_trajectory, the "
            "same tool chapter 06 uses.")
    print("g_OO(r) first peak: r=%.3f A, g=%.2f (literature range ~2.7-2.8 A)" % (r[imax], g[imax]))
else:
    print("no LAMMPS and no record: nothing to analyse")
'''),

    code('''\
from lammpskill import viz

_MASS = {1: 15.9994, 2: 1.008}   # spce_water(): type 1 = O, type 2 = H

if traj_rec["source"] != "skip":
    pos0 = np.array(traj_rec["frames"][0])
    masses0 = [_MASS[t] for t in traj_rec["types"]]
    cell = np.array(traj_rec["cell"])
    try:
        fig = viz.snapshot(pos0, cell, masses=masses0)
    except ImportError as e:
        print("ase not installed -- skipping the water snapshot:", e)
    else:
        plt.show()
        caption("The SPC/E water box near the start of the run -- real atomic masses (15.9994, "
                "1.008), so lammpskill.viz's own mass-to-symbol guess correctly renders oxygen "
                "and hydrogen, unlike every earlier reduced-unit chapter, which had to pick a "
                "conventional stand-in element by hand.")
else:
    print("no LAMMPS and no record: nothing to show")
'''),

    code('''\
from IPython.display import Image, display

if traj_rec["source"] != "skip":
    frames = [np.array(f) for f in traj_rec["frames"]]
    masses_per_frame = [_MASS[t] for t in traj_rec["types"]]
    cell = np.array(traj_rec["cell"])
    gif_workdir = tempfile.mkdtemp(prefix="ch12_gif_")
    try:
        gif_path = viz.animate_gif(frames, cell, os.path.join(gif_workdir, "water.gif"),
                                   masses=masses_per_frame, fps=4)
    except ImportError as e:
        print("ase not installed -- skipping the animation:", e)
    else:
        display(Image(filename=gif_path))
        caption("The same water box animated across the run: rigid molecules (fix shake) jiggling "
                "and reorienting under thermal motion, the same physical case the density and "
                "g_OO(r) checks above both drew from.")
else:
    print("no LAMMPS and no record: nothing to animate")
'''),

    md("""
## Reading it

- This chapter has no `mdlite` half at all -- the first one -- because SPC/E water needs rigid-body
  constraints and long-range electrostatics `mdlite` does not implement, named up front rather than
  discovered partway through.
- The density check is a real, external validation, not an internal cross-check: LAMMPS's own
  `fix npt`, compared to a public-domain NIST reference table, agreeing within a tolerance derived
  from what was actually measured (the same S4 discipline as every other record in this project).
- The O-O structure and the atom views are a second, separate real run -- shown for context and
  understanding, not asserted as an independent validation the way the density check is.
"""),
]

TALLY = [
    ("all(f.level != 'error' for f in findings)", "the spce_water preset carries no checker error"),
    ("water['measured']['d_rho'] < water['tolerance_rho']", "LAMMPS's fix npt density agrees with the NIST reference within its recorded tolerance"),
    ("traj_rec['source'] in ('run', 'record', 'skip')", "run_or_load returned one of its three documented outcomes"),
]
