# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Chapter 11 — Polymers. Both: the mdlite/checker half runs unconditionally (rule 7 -- no
external file is ever needed, unlike the EAM chapter's potential file); the record-or-run
trajectory needs a LAMMPS installation, the same discipline chapter 01 established."""

from nbbuild import code, md

CELLS = [
    md("""
## A simplified bead-spring model, not the field-standard one

The field-standard bead-spring polymer model (Kremer & Grest, *J. Chem. Phys.* 92, 5057 (1990))
uses FENE bonds (a finite-extensibility spring that cannot be stretched past a hard limit) and WCA
repulsion (Lennard-Jones truncated at its minimum, purely repulsive) so chains cannot cross
themselves. `mdlite` has neither `FENE` nor `WCA` -- only `HarmonicBond` and the full
(attractive+repulsive) `LennardJones` it already uses everywhere else -- so this chapter builds a
simplified model from exactly those two: a harmonic bond along the backbone, plain Lennard-Jones
between every pair (bonded neighbours included). It behaves like a real polymer -- a bound chain
that explores conformations under thermal motion -- without claiming to be the textbook model.
"""),

    md("""
## The preset: `lammpskill.script.bead_spring_chain`

30 beads in reduced (`lj`) units, starting near-straight along `x` with a small jitter so no force
is accidentally zero. One deliberate correctness detail: LAMMPS excludes directly-bonded pairs
from its nonbonded sum by default (`special_bonds lj 0 0 0`); `mdlite`'s `LennardJones` and
`HarmonicBond` have no such concept -- they sum independently over all pairs and all bonds -- so
the preset sets `special_bonds lj 1.0 1.0 1.0` to keep both engines describing the same system
(`references/pitfalls.md`, 2026-09-15).
"""),

    code('''\
from lammpskill.script import bead_spring_chain, check, render

spec, df = bead_spring_chain(n_beads=30)
text = render(spec)
print(text)
print("natoms:", df.natoms, "nbonds:", df.bonds.shape[0])

findings = check(text)
for f in findings:
    print(f.level.upper(), f.code, "--", f.message)
assert all(f.level != "error" for f in findings), "the preset should carry no checker error"
'''),

    md("""
## The real comparison: one configuration, mdlite against LAMMPS

`data/records/polymer_vs_lammps.json` is the same configuration `bead_spring_chain()` builds
above, evaluated once (`run 0`, no integration): `mdlite.pair.LennardJones` +
`mdlite.pair.HarmonicBond`, summed independently, against LAMMPS's `pair_style lj/cut` +
`bond_style harmonic` on the identical positions and topology. No external file was needed to
generate it -- unlike the EAM chapter's potential, a bead-spring chain has no real-element
dependency, so this record is committed and always present.
"""),

    code('''\
import json

with open("../data/records/polymer_vs_lammps.json", encoding="utf-8") as f:
    poly = json.load(f)

print("energy: mdlite=%.6f  LAMMPS=%.6f  |diff|=%.2e  (tolerance %.0e)"
      % (poly["energy_mdlite"], poly["energy_lammps"], poly["measured"]["dE"], poly["tolerance_energy"]))
print("force max-diff (mdlite vs LAMMPS):", poly["force_maxdiff"], "| tolerance:", poly["tolerance_force"])
print(poly["provenance"]["why"])
assert poly["measured"]["dE"] < poly["tolerance_energy"] and poly["force_maxdiff"] < poly["tolerance_force"]
'''),

    md("""
## Watching the chain relax

The cross-check above needed only one configuration. This section runs the case for real -- the
same preset, a trajectory dump added, `run_or_load` so the chapter still finishes without a
LAMMPS installation (chapter 01's own pattern) -- and renders what the numbers above were always
describing: a chain starting near-straight, exploring conformations under thermal motion at
`T*=1.0` as the run proceeds.

What actually happens is a real physical consequence of this chapter's own simplification, not a
surprise to explain away: full Lennard-Jones (attractive at long range, unlike WCA's purely
repulsive truncation) makes a homopolymer chain **collapse into a compact globule** rather than
wander as an extended, self-avoiding coil. This is the textbook coil-globule transition (a real
polymer physics result) -- it shows up here specifically *because* this model uses `mdlite`'s
existing `LennardJones` rather than WCA, exactly the trade-off the intro section named.
"""),

    code('''\
import dataclasses
import os
import tempfile

import numpy as np

from lammpskill.io.dump import read_dump
from lammpskill.run import run, run_or_load

DUMP_EVERY = 20
N_FRAMES = 12


def compute_traj():
    # bead_spring_chain writes chain.data (read_data reads it) -- unlike lj_melt()'s self-contained
    # lattice/create_atoms script, this preset needs its data file in the SAME directory the run
    # happens in, so it is rebuilt here rather than reusing the render-only `spec` from the cell
    # above (which was never given a workdir to write chain.data into).
    workdir = tempfile.mkdtemp(prefix="ch11_traj_")
    base_spec, _ = bead_spring_chain(n_beads=30, workdir=workdir)
    traj_spec = dataclasses.replace(
        base_spec, dumps=["1 all custom %d traj.dump id type xu yu zu" % DUMP_EVERY],
        comment="the same bead-spring chain as above (2000 steps already), with a trajectory dump for the atom views")
    result = run(traj_spec, workdir, time_limit=300)
    if not result.ok:
        raise RuntimeError("trajectory run failed (rc=%s): %s" % (result.returncode, "; ".join(result.errors) or result.stderr))
    traj = read_dump(os.path.join(workdir, "traj.dump"))
    step = max(1, len(traj) // N_FRAMES)
    frames = [f.positions.tolist() for f in traj.frames[::step]]
    return {"nframes": len(frames), "frames": frames, "cell": traj.box.lengths.tolist(),
            "route": result.installation.route if result.installation else None}


traj_rec = run_or_load("bead_spring_chain_traj_ch11", compute_traj, records_dir="../data/records")
print("source:", traj_rec["source"], "| frames:", traj_rec.get("nframes"))
'''),

    code('''\
import matplotlib.pyplot as plt

from lammpskill import viz

if traj_rec["source"] != "skip":
    pos0 = np.array(traj_rec["frames"][0])
    cell = np.array(traj_rec["cell"])
    try:
        fig = viz.snapshot(pos0, cell, symbols=["C"] * len(pos0))
    except ImportError as e:
        print("ase not installed -- skipping the chain snapshot:", e)
    else:
        plt.show()
        caption("The chain's starting conformation: near-straight, the small per-bead jitter "
                "`bead_spring_chain()` adds barely visible at this scale. Rendered as carbon-like "
                "spheres purely to pick a radius and colour -- reduced LJ units carry no real "
                "element, the same convention chapter 01's atom views use.")
else:
    print("no LAMMPS and no record: nothing to show")
'''),

    code('''\
from IPython.display import Image, display

if traj_rec["source"] != "skip":
    frames = [np.array(f) for f in traj_rec["frames"]]
    cell = np.array(traj_rec["cell"])
    gif_workdir = tempfile.mkdtemp(prefix="ch11_gif_")
    try:
        gif_path = viz.animate_gif(frames, cell, os.path.join(gif_workdir, "chain.gif"),
                                   symbols=["C"] * len(frames[0]), fps=4)
    except ImportError as e:
        print("ase not installed -- skipping the animation:", e)
    else:
        display(Image(filename=gif_path))
        caption("The same chain animated across the run: the near-straight starting conformation "
                "collapsing into a compact globule as thermal motion (T*=1.0) samples the space "
                "the harmonic bonds and full (attractive+repulsive) Lennard-Jones allow -- the "
                "coil-globule collapse a purely-repulsive WCA chain would not show, and the same "
                "physical case the energy/force cross-check above verified, seen directly rather "
                "than only through a single static configuration.")
else:
    print("no LAMMPS and no record: nothing to animate")
'''),

    md("""
## Reading it

- The cross-check needed exactly one configuration, no dynamics -- energy and forces agree with
  LAMMPS to round-off, the same standard chapters 02 and 05 hold every mdlite-vs-LAMMPS comparison
  to.
- `special_bonds` is the pitfall this chapter exists to surface: LAMMPS's default silently drops
  bonded neighbours from the nonbonded sum, which `mdlite` has no equivalent concept of -- a wrong
  default here would have shown up as a disagreement with no obvious cause.
- The animation is not part of the pass/fail check -- it is the same physical case, run for real,
  shown rather than only summarised by a single number, the same purpose chapter 01's atom views
  serve.
- The chain collapsing into a globule is not an artefact -- full Lennard-Jones really does predict
  that for a homopolymer, and it is a direct, visible consequence of the simplification this
  chapter named up front (full LJ instead of WCA). A model's limitations show up in its own
  results, not only in a disclaimer.
"""),
]

TALLY = [
    ("all(f.level != 'error' for f in findings)", "the bead-spring-chain preset carries no checker error"),
    ("poly['measured']['dE'] < poly['tolerance_energy'] and poly['force_maxdiff'] < poly['tolerance_force']",
     "mdlite and LAMMPS agree on the chain's energy and forces within their recorded tolerance"),
    ("traj_rec['source'] in ('run', 'record', 'skip')", "run_or_load returned one of its three documented outcomes"),
]
