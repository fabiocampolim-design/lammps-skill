# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Chapter 09 — Choosing a Build. Runs with no LAMMPS installed: every number here is a record of
the 314-case examples/ sweep in docs/04-examples-run-log.md, run on both routes on this machine
2026-09-07. The sweep's own JSON output stays in out/ (gitignored, rule 7 -- upstream's example
inputs are never copied here); this chapter carries only the aggregated outcome counts."""

from nbbuild import code, md

CELLS = [
    md("""
## The question is never "which build is better"

Two LAMMPS builds live on this machine: the Ubuntu package (10 Dec 2025 feature release, 52
packages) and a source build of the stable line (`stable_22Jul2025_update6`, `core` preset, 11
packages). Running the **314 cases** LAMMPS ships under `examples/` on both -- one process, 20 s
per case, the same source tree copied out for each run -- answers a sharper question than "which is
bigger": *for the style I need, which binary has it?*
"""),

    md("""
## The sweep's own numbers

Everything below is a fixed record of `lammps-skill/scripts/run_examples.py`'s 314-case sweep,
completed 2026-09-07 (`docs/04-examples-run-log.md`); the sweep's own JSON output stays in `out/`
(gitignored -- upstream's example inputs are never copied into this repository, rule 7). Defining
the numbers as data, once, means the sections below and the tally cell at the end can't drift apart.
"""),

    code('''\
# outcome counts from the full 314-case examples/ sweep, one process, 20s/case, both routes.
SWEEP_314 = {
    "wsl-source (stable, 11 packages)": {"ok": 108, "ok-no-thermo": 0, "timeout-after-start": 29,
                                          "missing-package": 130, "timeout": 24, "error": 23},
    "wsl-apt (10 Dec 2025, 52 packages)": {"ok": 138, "ok-no-thermo": 4, "timeout-after-start": 42,
                                            "missing-package": 66, "timeout": 32, "error": 32},
}

# case -> which package(s) it needs that the OTHER route lacks. All ten run on the 11-package
# source build; none run on the 52-package apt build.
SOURCE_ONLY_CASES = {
    "wall/wall.ccl": "EXTRA-FIX", "wall/wall.diffusive": "EXTRA-FIX", "wall/wall.maxwell": "EXTRA-FIX",
    "VISCOSITY/mp.2d": "EXTRA-FIX", "controller/controller.temp": "EXTRA-FIX", "mesh/mesh_box": "EXTRA-FIX",
    "numdiff/numdiff": "EXTRA-FIX", "ttm/ttm.mod": "EXTRA-FIX", "relres/22DMH.respa": "EXTRA-MOLECULE",
    "atm/atm": "(ran out of the 20s cap on apt only)",
}

# package -> (cases blocked on source, cases blocked on apt).
BLOCKED_BY_PACKAGE = {
    "GRANULAR": (16, 0), "ML-SNAP": (15, 15), "EXTRA-FIX": (0, 15), "ML-IAP": (14, 14),
    "REPLICA": (13, 0), "MC": (10, 0), "AMOEBA": (7, 7), "REAXFF": (5, 5), "MDI": (5, 5),
    "POEMS": (5, 0), "BODY": (5, 0), "PERI": (5, 0), "CORESHELL": (4, 0), "MEAM": (4, 0),
    "QEQ": (4, 0), "VORONOI": (3, 0), "EXTRA-MOLECULE": (0, 3), "LEPTON": (1, 2),
}
print("sweep loaded:", sum(sum(c.values()) for c in SWEEP_314.values()), "case-outcomes across", len(SWEEP_314), "routes")
'''),

    md("""
## First: both builds agree with upstream, where they can be compared

Before coverage, correctness. `bench/`'s five canonical cases ship a reference log from the LAMMPS
developers themselves; the sweep's numbers here are exact-match or explained, not "close":
"""),

    code('''\
bench_result = {
    "lj": "identical on both routes, both process counts",
    "chain": "identical on both",
    "eam": "identical on both",
    "chute": "identical (apt only -- the source build has no GRANULAR package)",
    "rhodo": "1 proc: worst 4.0e-9 in TotEng (last printed digit, i.e. print precision); 4 procs: identical",
}
for case, result in bench_result.items():
    print("%-8s %s" % (case, result))
'''),

    md("""
## Then: coverage, counted honestly

Every case is scored from its **log**, never its exit status (chapter 08 and N-15: LAMMPS exits 0
after a fatal input error). Six outcomes, on the full 314-case tree:
"""),

    code('''\
for route, counts in SWEEP_314.items():
    started = counts["ok"] + counts["ok-no-thermo"] + counts["timeout-after-start"]
    print("%-38s started %3d / 314  (%s)" % (route, started,
          ", ".join("%s=%d" % kv for kv in counts.items())))
'''),

    md("""
## The result worth the whole sweep: more packages is not more coverage

The 52-package build starts more cases overall (184 vs 137) -- but coverage is not a superset.
**Ten cases run on the 11-package source build that the 52-package apt build cannot run at all:**
"""),

    code('''\
for case, needs in SOURCE_ONLY_CASES.items():
    print("%-28s needs %s" % (case, needs))
print()
print("Neither build dominates: 40 cases go the other way, 29 of them blocked on the source build")
print("by GRANULAR, REPLICA, MC or another package the 11-package `core` preset omits.")
'''),

    md("""
## What blocks the rest, by package

`ML-SNAP`, `ML-IAP`, `AMOEBA`, `REAXFF` and `MDI` are missing from **both** builds -- exactly the
machine-learning and reactive packages the owner staged for later, accounting for 41 blocked cases
between them. Reading this table the wrong way round ("just install more packages") misses the
point of the section above: no single build has everything, and some packages actively conflict
with others' build requirements.
"""),

    code('''\
print("%-16s %8s %8s" % ("package", "source", "apt"))
for pkg, (source, apt) in sorted(BLOCKED_BY_PACKAGE.items(), key=lambda kv: -sum(kv[1])):
    print("%-16s %8d %8d" % (pkg, source, apt))
'''),

    md("""
## POEMS: the two release lines can disagree about what exists at all

Five `POEMS` examples come from the tree the source build was compiled from
(`stable_22Jul2025_update6`), so the **source** build reports them `missing-package: POEMS` -- the
`core` preset simply omits it. The **apt** build (10 Dec 2025, months later on the feature line)
answers `Fix style poems is no longer available.` -- LAMMPS's own deprecated-style mechanism. `git
log` on the upstream mirror shows `remove POEMS package, docs, and examples`, dated the same day as
the `stable_22Jul2025` tag: POEMS was *removed upstream*, not merely unbuilt. A route can therefore
answer "not installed" or "no longer exists" for the same style, and only the second one means
recompiling will never help.
"""),

    md("""
## How to choose, in code: package *list*, never package *count*

`Installation.packages` is parsed from `lmp -h`, per route, every time `detect_all()` runs -- so
the question "does *this* binary have *this* style" never depends on which build happened to be
bigger the day someone checked.
"""),

    code('''\
def has(style_package, inst):
    return style_package in inst.packages

# INSTALLATIONS comes from the Setup cell; on a machine with neither build this loop prints nothing
# and the chapter still finishes -- the question the code answers does not depend on an answer existing.
for i in INSTALLATIONS:
    print(i.route, i.version, "-- %d packages" % len(i.packages))
    for pkg in ("GRANULAR", "EXTRA-FIX", "POEMS", "ML-SNAP", "REAXFF"):
        print("   %-10s %s" % (pkg, "yes" if has(pkg, i) else "no"))
'''),

    md("""
## Reading it

- **Correctness first.** Both builds reproduce upstream's own reference numbers on every bench case
  they can run at all -- to the last printed digit, or to one unit of print precision.
- **Coverage is not ordered by package count.** The bigger build starts more cases in total, and
  still cannot run ten the smaller one runs.
- **A build's package list can differ from another build of the same tag** for reasons that are not
  bugs: a different preset, a different point in the package's own history (POEMS), or a package
  that genuinely needs more setup (KIM's model download, MDI's separate build).
- **Ask the binary, not the changelog.** `Installation.packages`, read from `lmp -h`, is the only
  source of truth this toolkit trusts for "can I use style X here" -- exactly the discipline chapter
  00 opened with.
"""),
]

TALLY = [
    ("sum(SWEEP_314['wsl-source (stable, 11 packages)'].values()) == 314",
     "the source-route outcome counts add up to the full 314-case sweep"),
    ("sum(SWEEP_314['wsl-apt (10 Dec 2025, 52 packages)'].values()) == 314",
     "the apt-route outcome counts add up to the full 314-case sweep"),
    ("len(SOURCE_ONLY_CASES) == 10",
     "ten cases run on the 11-package build that the 52-package build cannot (the sweep's headline result)"),
    ("BLOCKED_BY_PACKAGE['ML-SNAP'] == (15, 15) and BLOCKED_BY_PACKAGE['REAXFF'] == (5, 5)",
     "the staged-for-later packages (ML-SNAP, REAXFF, ...) are missing from both builds, not one"),
]
