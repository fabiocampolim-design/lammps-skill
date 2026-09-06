# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Health check for lammps-skill: imports, our own parsers on the fixtures, every LAMMPS route detected and
(optionally) probed with the LJ melt; prints the platform table. Exit 0 when every check passes or skips."""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lammpskill import __version__  # noqa: E402
from lammpskill.install import ROUTES, base, detect_all, get_route  # noqa: E402

_CACHE = {}


def detect_lammps(refresh=False, routes=None):
    key = tuple(routes or ROUTES)
    if refresh or key not in _CACHE:
        _CACHE[key] = detect_all(routes=key)
    return _CACHE[key]


def build_parser():
    p = argparse.ArgumentParser(prog="verify_lammps.py", description=__doc__)
    p.add_argument("--no-lammps", action="store_true", help="skip the route detection and probe (CI without LAMMPS)")
    p.add_argument("--require-lammps", action="store_true", help="fail when no installation is detected")
    p.add_argument("--route", choices=ROUTES, help="detect only this route and print why it fails")
    p.add_argument("--probe", action="store_true", help="run the LJ-melt probe on every detected route")
    p.add_argument("--steps", type=int, default=250, help="probe length in steps (default 250)")
    p.add_argument("--outdir", default=os.path.join(ROOT, "out", "probe"), help="where the probe runs are written")
    p.add_argument("--table-out", help="append the platform-table rows (Markdown) to this file")
    p.add_argument("--log-dir", default=None, help="directory for the audit log (default: no file)")
    p.add_argument("-q", "--quiet", action="store_true", help="one summary line")
    p.add_argument("--version", action="version", version="lammps-skill " + __version__)
    return p


def _check_imports():
    import numpy, scipy, matplotlib, yaml  # noqa: E401
    from lammpskill.io import log, data, dump
    import mdlite
    mods = [log, data, dump]
    return "numpy %s, scipy %s, matplotlib %s, yaml ok (%s), io modules %d, mdlite %s" % (
        numpy.__version__, scipy.__version__, matplotlib.__version__, yaml.__name__, len(mods), mdlite.__version__)


def _check_parsers():
    from lammpskill.io.log import parse_log
    from lammpskill.io.data import read_data
    fx = os.path.join(ROOT, "tests", "fixtures")
    if not os.path.isdir(fx):
        return "fixtures absent (installed package) — skipped"
    with open(os.path.join(fx, "log_lj_melt.lammps"), encoding="utf-8") as f:
        lf = parse_log(f.read())
    df = read_data(os.path.join(fx, "data_lj_melt.data"))
    return "log: %d thermo rows; data: %d atoms" % (lf.thermo.data.shape[0], df.natoms)


def _row(inst, rep):
    return "| %s | %s | %s | %s | %s | %s | %s | %s | %d | %s | %s |" % (
        inst.route, inst.host, inst.version, inst.executable or "(in-process)", inst.library or "-",
        "yes" if inst.python_module else "no", "yes" if inst.mpi else "no", "yes" if inst.omp else "no", len(inst.packages),
        ("%.2f" % rep.wall) if rep and rep.ok else ("FAIL" if rep else "-"), rep.natoms if rep and rep.ok else "-")


def main(argv=None):
    a = build_parser().parse_args(argv)
    results = []

    def check(name, fn):
        try:
            msg = fn()
            results.append((name, "PASS", msg))
        except Exception as e:
            results.append((name, "FAIL", "%s: %s" % (type(e).__name__, e)))

    check("imports", _check_imports)
    check("parsers", _check_parsers)
    rows = []
    if a.no_lammps:
        results.append(("lammps", "SKIP", "--no-lammps"))
    else:
        found = detect_lammps(refresh=True, routes=[a.route] if a.route else None)
        if a.route and not found:
            mod = get_route(a.route)
            results.append(("lammps", "FAIL", "route %s not detected. %s" % (a.route, mod.describe())))
        elif not found:
            results.append(("lammps", "FAIL" if a.require_lammps else "SKIP", "no installation detected on any route"))
        else:
            results.append(("lammps", "PASS", ", ".join("%s (%s)" % (i.route, i.version) for i in found)))
            if a.probe:
                for inst in found:
                    if inst.extra.get("pinned"):
                        rows.append(_row(inst, None))
                        continue
                    rep = base.probe(inst, os.path.join(a.outdir, inst.route), steps=a.steps)
                    rows.append(_row(inst, rep))
                    results.append(("probe " + inst.route, "PASS" if rep.ok else "FAIL",
                                    "%.2f s, %s atoms" % (rep.wall, rep.natoms) if rep.ok else (rep.error or "")))
    if rows and a.table_out:
        os.makedirs(os.path.dirname(os.path.abspath(a.table_out)), exist_ok=True)
        with open(a.table_out, "a", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")
    failed = [r for r in results if r[1] == "FAIL"]
    if a.quiet:
        print("verify_lammps: %s (%d checks, %d failed)" % ("FAILED" if failed else "ALL CHECKS PASSED", len(results), len(failed)))
    else:
        for name, st, msg in results:
            print("%-4s %-18s %s" % (st, name, msg))
        if rows:
            print("| route | host | version | executable | library | python | MPI | OMP | packages | LJ melt wall (s) | atoms |")
            print("|---|---|---|---|---|---|---|---|---|---|---|")
            print("\n".join(rows))
        print("-- %s --" % ("FAILED" if failed else "ALL CHECKS PASSED"))
    if a.log_dir:
        os.makedirs(a.log_dir, exist_ok=True)
        with open(os.path.join(a.log_dir, "verify_lammps.log"), "a", encoding="utf-8") as f:
            for name, st, msg in results:
                f.write("%s %s %s\n" % (st, name, msg))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
