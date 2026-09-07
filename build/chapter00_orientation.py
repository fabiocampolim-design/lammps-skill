# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Chapter 00 — Orientation. Runs with no LAMMPS installed."""

from nbbuild import code, md

CELLS = [
    md("""
## What LAMMPS is, and what this chapter is not

LAMMPS is a classical molecular-dynamics code from Sandia National Laboratories, distributed under
the GPL-2.0. It is not installed by this package and never bundled with it: `lammps-skill` **drives**
a LAMMPS you obtained yourself, reads what it writes, and checks the numbers.

Cite the code as Thompson *et al.*, *Comput. Phys. Commun.* **271**, 108171 (2022),
[doi:10.1016/j.cpc.2021.108171](https://doi.org/10.1016/j.cpc.2021.108171).

This chapter takes about fifteen minutes and needs **no LAMMPS installation**. It answers four
questions: which LAMMPS you would install and why they differ, what this toolkit adds, what the
teaching engine `mdlite` is for, and how a chapter still works on a machine with no LAMMPS at all.
"""),

    md("""
## Two release lines, and why the difference matters

LAMMPS ships two lines from the same repository:

* a **stable** release, cut once a year and then *updated* for a long time — `stable_22Jul2025` was
  still receiving updates fourteen months later (update 6, September 2026);
* **feature** (patch) releases every six to eight weeks, cut alongside the stable updates.

A distribution package usually tracks the feature line without saying so. The Ubuntu 26.04 package
is `20251210` — the **10 December 2025 feature release**, not the stable. So "I installed LAMMPS"
does not identify what you are running, and neither does "the stable release": the update number is
part of the version.

Everything this toolkit records carries the full tag for that reason.
"""),

    code('''\
# What is actually here. detect_all() reads each route rather than assuming one.
for i in INSTALLATIONS:
    print("route      :", i.route)
    print("  version  :", i.version)
    print("  packages :", len(i.packages), "->", ", ".join(sorted(i.packages)[:8]), "...")
    print("  MPI/OMP  :", i.mpi, "/", i.omp, "| python module:", i.python_module)
    print()
if not INSTALLATIONS:
    print("Nothing detected -- the rest of this chapter still runs.")
'''),

    md("""
## Package *list*, never package *count*

The most common way to be wrong about a LAMMPS build is to assume a bigger package set is a
superset. It is not. Running the 314 shipped `examples/` cases on two builds of this machine:

| build | packages | cases that started |
|---|---|---|
| Ubuntu package, 10 Dec 2025 | 52 | 184 |
| our source build, `core` preset | 11 | 137 |

and yet **ten cases run on the 11-package build that the 52-package build cannot** — eight of them
need `EXTRA-FIX`, which the Ubuntu build does not carry and our preset does. Neither build
dominates.

So the question is never "how many packages", it is "is *this* style in *this* binary":
`Installation.packages` is parsed from `lmp -h`, and the toolkit refuses to guess.
"""),

    code('''\
# The same question, asked properly, for a style you care about.
def has(style_package, inst):
    return style_package in inst.packages

for i in INSTALLATIONS:
    for pkg in ("MOLECULE", "KSPACE", "GRANULAR", "EXTRA-FIX", "REAXFF", "ML-SNAP"):
        print("%-11s %-10s %s" % (i.route, pkg, "yes" if has(pkg, i) else "no"))
    print()
'''),

    md("""
## What this toolkit adds

`lammpskill` is the part that talks to LAMMPS:

* `install` — seven routes behind one contract, each *measured* rather than assumed;
* `script` — build an input from a `Spec`, and a checker with fourteen rules, each pointing at the
  manual page it comes from;
* `io` — read what LAMMPS writes: data files, dumps, logs (`one`, `multi` and `yaml` thermo styles),
  the restart header, EAM potential files;
* `run` — a subprocess backend for any host and an in-process backend through the official python
  module, both returning the same `Result`;
* `post` — RDF, MSD, diffusion, VACF, structure factor, block averages, and comparison against
  reference tables that carry their provenance.

Optional bridges to ASE, pymatgen, MDAnalysis and OVITO exist, and none of them is required: the
core is Apache-2.0 and depends on numpy and scipy only.
"""),

    md("""
## `mdlite`, and how it differs from pylj

`mdlite` is a small molecular-dynamics engine written from scratch in numpy: Lennard-Jones and EAM,
harmonic bonds, velocity Verlet, three thermostats, two minimisers. It is a **teaching object, not
an MD code** — nobody should run research on it.

The closest thing to it is **pylj** (McCluskey, Morgan, Edler and Parker, *Journal of Open Source
Education* **1**, 19 (2018), MIT licence): a Lennard-Jones teaching engine in Jupyter, written for
undergraduate exercises, with Monte Carlo as well as dynamics. If you want the gentlest possible
first contact with atomistic simulation, read pylj.

`mdlite` differs in two ways that matter for this book:

1. **It sits next to a toolkit that drives the production code**, so a chapter can compute something
   in twenty lines of readable numpy and then compute the same thing in LAMMPS and subtract.
2. **Its numbers are cross-checked against that production code, and the residues are recorded** —
   forces agree with LAMMPS to 3·10⁻¹³, the copper lattice constant and cohesive energy from EAM to
   3·10⁻⁵, and an NVT state point agrees with the NIST reference within three standard errors. Each
   record is a JSON file under `data/records/`, and the tests read their tolerances from it rather
   than from a number somebody typed.

That is the whole claim: not that `mdlite` is fast or complete, but that where it teaches a number,
that number has been checked against the code it is teaching you to use.
"""),

    code('''\
# The records exist whether or not LAMMPS does -- that is the point of them.
import json, glob, os
records = sorted(glob.glob(os.path.join("..", "data", "records", "*.json")))
for path in records:
    with open(path, encoding="utf-8") as f:
        rec = json.load(f)
    prov, measured = rec.get("provenance", {}), rec.get("measured", {})
    print("%-28s measured %s" % (os.path.basename(path),
                                 ", ".join("%s=%.3g" % kv for kv in measured.items()) or "-"))
    if prov.get("route") in (None, "none", ""):
        against = "mdlite vs a published reference (no LAMMPS run involved)"
    else:
        against = "mdlite vs LAMMPS %s on route %s" % (prov.get("lammps_version", "?"), prov["route"])
    print("%-28s   %s, %s" % ("", against, prov.get("date", "?")))
if not records:
    print("no records found (expected data/records/*.json)")
'''),

    md("""
## Record-or-run: why this chapter works without LAMMPS

Every later chapter that needs a real LAMMPS run goes through one helper:

```python
result = run_or_load("lj_melt_2000", compute, records_dir="../data/records")
```

* with LAMMPS present, `compute` runs and its result is written to the record;
* without LAMMPS, the record is loaded and the chapter continues;
* with neither, the cell says so and is skipped, visibly.

This is what makes the book reviewable by someone who has not installed anything, and it is why the
numbers in the text cannot drift away from the numbers in the records: the records *are* the source.
"""),

    md("""
## Where to go next

| chapter | what it does | needs LAMMPS |
|---|---|---|
| 01 First simulation | an LJ melt end to end, through the checker | yes |
| 02 Forces and integration | velocity Verlet, and forces against LAMMPS at 3e-13 | both |
| 07 Minimisation | why a fixed-step steepest descent explodes | no |
| 08 Reading what LAMMPS writes | the file formats, and the four pitfalls that cost us time | no |
| 09 Choosing a build | the sweep behind the table above | no |

Chapters 00, 07, 08 and 09 need nothing installed. If you have no LAMMPS yet, read
`references/install-routes.md` and pick a route — on Windows the quickest is the Ubuntu package
inside WSL, which is one script.
"""),
]

# (expression, label) -- evaluated in the notebook's namespace by the generated tally cell.
TALLY = [
    ("lammpskill.__version__", "the toolkit imported and reported its version"),
    ("isinstance(INSTALLATIONS, list)", "detect_all() returned a list (possibly empty -- that is allowed)"),
    ("all(hasattr(i, 'packages') for i in INSTALLATIONS)",
     "every detected installation carries a package list read from `lmp -h`"),
]
