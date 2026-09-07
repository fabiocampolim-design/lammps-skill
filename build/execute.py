# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Execute the assembled chapter notebooks on the pinned kernel and write them back with outputs.

Assembly and execution are separate on purpose: `assemble.py` is pure text and runs anywhere, while
this needs the `lammps` environment (and, for the chapters that say so, a LAMMPS installation).
A chapter that fails is reported and the others still run -- the exit code says how many failed.

Usage:
    python build/execute.py                    # every chapter in chapters/
    python build/execute.py --which 00         # one
    python build/execute.py --timeout 1800     # per-notebook cell timeout in seconds
    python build/execute.py --check-size       # fail if a notebook exceeds the rule-25 cap
"""

import argparse
import datetime as dt
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

from lammpskill import __version__      # noqa: E402

NB_WARN, NB_MAX = 1_000_000, 1_500_000   # rule 25


def build_parser():
    ap = argparse.ArgumentParser(prog="execute", description=__doc__.splitlines()[0])
    ap.add_argument("--which", default="all", help="chapter key (e.g. 00) or 'all'")
    ap.add_argument("--chapters-dir", default=os.path.join(ROOT, "chapters"),
                    help="where the assembled notebooks are")
    ap.add_argument("--timeout", type=int, default=1800, help="per-cell timeout in seconds")
    ap.add_argument("--kernel", default="lammps-mc", help="Jupyter kernel name")
    ap.add_argument("--check-size", action="store_true",
                    help="fail when an executed notebook exceeds the rule-25 cap")
    ap.add_argument("--log-dir", default=None, help="audit log directory (default <chapters-dir>/logs)")
    ap.add_argument("-q", "--quiet", action="store_true")
    ap.add_argument("--version", action="version", version="lammps-skill %s" % __version__)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        import nbformat
        from nbclient import NotebookClient
    except ImportError as e:
        print("execute needs nbformat + nbclient (pip install nbclient): %s" % e)
        return 2

    pattern = "LAMMPS_%s_*.ipynb" % ("*" if a.which == "all" else a.which)
    paths = sorted(glob.glob(os.path.join(a.chapters_dir, pattern)))
    if not paths:
        print("no notebooks matching %s in %s (run build/assemble.py first)" % (pattern, a.chapters_dir))
        return 2

    failed, oversized = [], []
    for path in paths:
        name = os.path.basename(path)
        nb = nbformat.read(path, as_version=4)
        client = NotebookClient(nb, timeout=a.timeout, kernel_name=a.kernel,
                                resources={"metadata": {"path": a.chapters_dir}})
        try:
            client.execute()
            nbformat.write(nb, path)
            size = os.path.getsize(path)
            if size > NB_MAX:
                oversized.append((name, size))
            status = "OK" if size <= NB_WARN else "OK (large: %.2f MB)" % (size / 1e6)
        except Exception as e:                                  # noqa: BLE001 - report, do not abort
            failed.append((name, "%s: %s" % (type(e).__name__, str(e).splitlines()[0][:160])))
            status = "FAIL"
        if not a.quiet:
            print("%-44s %s" % (name, status))

    for name, why in failed:
        print("FAILED %s -- %s" % (name, why))
    for name, size in oversized:
        print("OVERSIZE %s -- %.2f MB exceeds the rule-25 cap" % (name, size / 1e6))

    log_dir = a.log_dir or os.path.join(a.chapters_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "execute.log"), "a", encoding="utf-8", newline="\n") as f:
        f.write("%s lammps-skill %s executed %d, failed %d, oversize %d\n"
                % (dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), __version__,
                   len(paths), len(failed), len(oversized)))
    return 1 if failed or (a.check_size and oversized) else 0


if __name__ == "__main__":
    raise SystemExit(main())
