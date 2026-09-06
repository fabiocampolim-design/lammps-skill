# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""The `lammpskill` command: detect / verify / new / check / run / log / dump / rdf. Every invocation is appended to an
audit log (JSONL) when --log-dir is given (rule 12)."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

from . import __version__
from .install import ROUTES, detect_all
from .io.dump import read_dump
from .io.log import read_log
from .post import rdf_trajectory
from .script import check, eam_fcc, lj_melt, render, spce_water

PRESETS = {"lj_melt": lj_melt, "eam_fcc": eam_fcc, "spce_water": spce_water}


def _detect(routes=None):
    return detect_all(routes=routes)


def build_parser():
    p = argparse.ArgumentParser(prog="lammpskill", description=__doc__)
    p.add_argument("--log-dir", default=None, help="append an audit record (JSONL) per command to this directory")
    p.add_argument("--version", action="version", version="lammps-skill " + __version__)
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("detect", help="list every LAMMPS installation found")
    d.add_argument("--route", choices=ROUTES, help="detect only this route")
    d.add_argument("--json", action="store_true", help="machine-readable output")
    v = sub.add_parser("verify", help="run verify_lammps.py")
    v.add_argument("--probe", action="store_true", help="also run the LJ-melt probe on every route")
    n = sub.add_parser("new", help="write an input script (and data file) from a preset")
    n.add_argument("--preset", choices=sorted(PRESETS), required=True, help="which chapter system")
    n.add_argument("--out", required=True, help="case directory to create")
    n.add_argument("--steps", type=int, default=None, help="number of MD steps")
    n.add_argument("--n", type=int, default=None, help="lattice repetitions per side (spce_water: molecules per side)")
    c = sub.add_parser("check", help="check an input script for the mistakes the manual warns about")
    c.add_argument("file")
    c.add_argument("--workdir", help="directory the script runs in (for read_data checks; default: the script's directory)")
    r = sub.add_parser("run", help="run a case directory")
    r.add_argument("dir")
    r.add_argument("--in", dest="input", default="in.lammps", help="input script name inside the directory")
    r.add_argument("--route", choices=ROUTES + ("fake",), help="use this install route")
    r.add_argument("--backend", choices=("auto", "subprocess", "library"), default="auto", help="how to run LAMMPS")
    r.add_argument("--mpi", type=int, help="MPI ranks (only when the build has MPI)")
    r.add_argument("--omp", type=int, help="OpenMP threads (only when the build has OPENMP)")
    r.add_argument("--time-limit", type=int, default=3600, help="seconds before the run is killed")
    lg = sub.add_parser("log", help="thermo output of a log file")
    lg.add_argument("file")
    lg.add_argument("--csv", help="write the last thermo block to this CSV file")
    lg.add_argument("--last", action="store_true", help="print only the last thermo row as JSON")
    du = sub.add_parser("dump", help="inspect a dump file")
    du.add_argument("file")
    du.add_argument("--info", action="store_true", help="frame count, atoms, columns, box")
    du.add_argument("--frames", action="store_true", help="one line per frame")
    g = sub.add_parser("rdf", help="radial distribution function from a dump")
    g.add_argument("file")
    g.add_argument("--nbins", type=int, default=100, help="number of bins")
    g.add_argument("--rmax", type=float, help="largest distance (default half the smallest box length)")
    g.add_argument("--out", help="output file: .csv or .png (default: print)")
    return p


def _audit(a, rc):
    if not a.log_dir:
        return
    os.makedirs(a.log_dir, exist_ok=True)
    rec = {"time": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "command": a.command, "rc": rc,
           "args": {k: v for k, v in vars(a).items() if k not in ("command", "log_dir")}, "version": __version__}
    with open(os.path.join(a.log_dir, "lammpskill-audit.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def _cmd_detect(a):
    found = _detect([a.route] if a.route else None)
    if a.json:
        print(json.dumps([i.as_dict() for i in found], indent=1))
    elif not found:
        print("no LAMMPS installation detected (routes: %s)" % ", ".join(ROUTES))
        return 1
    else:
        for i in found:
            print("%-11s %-8s %-28s exe=%s module=%s mpi=%s omp=%s packages=%d%s" % (
                i.route, i.host, i.version, i.executable or "-", i.python_module, i.mpi, i.omp, len(i.packages),
                "  [PINNED]" if i.extra.get("pinned") else ""))
    return 0


def _cmd_verify(a):
    import verify_lammps
    return verify_lammps.main(["--probe"] if a.probe else [])


def _cmd_new(a):
    os.makedirs(a.out, exist_ok=True)
    fn = PRESETS[a.preset]
    kw = {}
    if a.steps is not None:
        kw["steps"] = a.steps
    if a.n is not None:
        kw["n" if a.preset != "spce_water" else "n_side"] = a.n
    if a.preset == "spce_water":
        spec, _ = fn(workdir=a.out, **kw)
    else:
        spec = fn(**kw)
    with open(os.path.join(a.out, "in.lammps"), "w", encoding="utf-8", newline="\n") as f:
        f.write(render(spec))
    print("wrote", os.path.join(a.out, "in.lammps"))
    return 0


def _cmd_check(a):
    with open(a.file, encoding="utf-8", errors="replace") as f:
        text = f.read()
    findings = check(text, workdir=a.workdir or os.path.dirname(os.path.abspath(a.file)))
    for x in findings:
        print("%-7s %s line %-4s %s  [manual: %s]" % (x.level, x.code, x.line or "-", x.message, x.manual))
    if not findings:
        print("no findings")
    return 1 if any(x.level == "error" for x in findings) else 0


def _cmd_run(a):
    from .run import run
    inst = None
    if a.route:
        found = _detect(None if a.route == "fake" else [a.route])
        inst = found[0] if found else None
        if inst is None:
            print("route %s not detected" % a.route)
            return 1
    with open(os.path.join(a.dir, a.input), encoding="utf-8") as f:
        text = f.read()
    kw = {"time_limit": a.time_limit}
    if a.backend != "library":
        kw.update({"mpi": a.mpi, "omp": a.omp})
    res = run(text, a.dir, installation=inst, backend=a.backend, input_name=a.input, **kw)
    for w in res.warnings:
        print("WARNING", w)
    if res.log.runs:
        t = res.thermo
        print(" ".join("%12s" % c for c in t.columns))
        for row in t.data:
            print(" ".join("%12.6g" % v for v in row))
    print("%s in %.2f s (%s, %s)" % ("OK" if res.ok else "FAILED", res.elapsed, res.backend, res.installation.route if res.installation else "?"))
    for e in res.errors:
        print("ERROR", e)
    return 0 if res.ok else 1


def _cmd_log(a):
    lf = read_log(a.file)
    if not lf.runs:
        print("no thermo output")
        return 1
    t = lf.thermo
    if a.csv:
        with open(a.csv, "w", encoding="utf-8", newline="\n") as f:
            f.write(",".join(t.columns) + "\n")
            for row in t.data:
                f.write(",".join("%.10g" % v for v in row) + "\n")
        print("wrote", a.csv)
    elif a.last:
        print(json.dumps(t.last))
    else:
        print(" ".join("%12s" % c for c in t.columns))
        for row in t.data:
            print(" ".join("%12.6g" % v for v in row))
    return 0


def _cmd_dump(a):
    tr = read_dump(a.file)
    if a.info or not a.frames:
        f0 = tr.frames[0]
        print("%d frame%s, %d atoms, columns %s, box %s" % (len(tr), "" if len(tr) == 1 else "s", f0.natoms, f0.columns, f0.box))
    if a.frames:
        for fr in tr.frames:
            print(fr.timestep, fr.natoms)
    return 0


def _cmd_rdf(a):
    tr = read_dump(a.file)
    r, g = rdf_trajectory(tr, nbins=a.nbins, rmax=a.rmax)
    if a.out and a.out.lower().endswith(".png"):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5, 3.2))
        ax.plot(r, g)
        ax.set_xlabel("r")
        ax.set_ylabel("g(r)")
        fig.tight_layout()
        fig.savefig(a.out, dpi=120)
        print("wrote", a.out)
    elif a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write("r,g\n" + "".join("%.8g,%.8g\n" % (x, y) for x, y in zip(r, g)))
        print("wrote", a.out)
    else:
        for x, y in zip(r, g):
            print("%.5f %.5f" % (x, y))
    return 0


def main(argv=None):
    a = build_parser().parse_args(argv)
    rc = {"detect": _cmd_detect, "verify": _cmd_verify, "new": _cmd_new, "check": _cmd_check, "run": _cmd_run,
          "log": _cmd_log, "dump": _cmd_dump, "rdf": _cmd_rdf}[a.command](a)
    _audit(a, rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
