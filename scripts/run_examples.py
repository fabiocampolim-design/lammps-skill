#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Run LAMMPS's own bench/ and examples/ cases on one install route and record what happened.

The inputs belong to the LAMMPS developers (GPL-2.0) and are never copied into this repository:
each case is copied from the *installed* tree into a scratch run directory on the host that runs
it, and only the outcome -- return code, wall time, thermo numbers, error text, and the comparison
with the reference log upstream ships next to the input -- is written here.

Three things this script refuses to assume, each from a measurement on 2026-09-06:

* **The return code says nothing.** Both LAMMPS builds on this machine exit 0 after a fatal input
  error ("ERROR: Unknown command: ..."), so a sweep scored on `rc` marks every broken case as a
  pass. The log is the only witness (finding N-15).
* **A missing package is not a failure of the case.** "is part of the <PKG> package which is not
  enabled in this LAMMPS binary" is a fact about the build, and is recorded as such so the route
  comparison stays honest.
* **A case is its whole directory.** Inputs read data files and potentials next to them; copying
  only `in.<name>` produces a "Cannot open file" that looks like a broken example.

Usage:
    python scripts/run_examples.py --route wsl-source --set bench --procs 1 --procs 4
    python scripts/run_examples.py --route wsl-apt --set examples --time-limit 60 --only melt
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lammpskill.install import get_route                     # noqa: E402
from lammpskill.install.base import run_command, to_wsl_path  # noqa: E402
from lammpskill.io.log import parse_log                      # noqa: E402

# "ERROR: Unrecognized pair style 'reaxff' is part of the REAXFF package which is not enabled in
# this LAMMPS binary." -- captured from lmp_core (22 Jul 2025 update 6) on 2026-09-06.
MISSING_PKG_RE = re.compile(r"is part of the (\S+) package which is not enabled")
ERROR_RE = re.compile(r"^ERROR(?:\s+on proc \d+)?:", re.M)
# bench/log.15Jul25.lj.fixed.g++.1 -- upstream's own reference run, one file per process count.
REF_RE = re.compile(r"^log\..*\.g\+\+\.(\d+)$")
# Wall-clock columns: comparing them against a reference log compares two machines, not two runs.
TIMING_COLUMNS = frozenset({"CPU", "Elapsed", "Time", "T/CPU", "S/CPU", "CPULeft", "Wall"})


@dataclass
class Case:
    name: str
    directory: str
    input_name: str
    reference: dict = field(default_factory=dict)


class LocalFs:
    """The tree is on the machine running this script."""

    def join(self, *parts):
        return os.path.join(*parts)

    def isdir(self, path):
        return os.path.isdir(path)

    def listdir(self, path):
        return sorted(os.listdir(path)) if os.path.isdir(path) else []

    def read(self, path):
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()

    def home(self):
        return os.path.expanduser("~")

    def walk(self, base, depth):
        """{directory: [file name, ...]} for `base` and, when depth > 1, its subdirectories."""
        tree = {}
        if not os.path.isdir(base):
            return tree
        tree[base] = [e for e in sorted(os.listdir(base)) if os.path.isfile(os.path.join(base, e))]
        if depth > 1:
            for e in sorted(os.listdir(base)):
                d = os.path.join(base, e)
                if os.path.isdir(d):
                    tree[d] = [x for x in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, x))]
        return tree


class WslFs:
    """The tree is inside WSL. Windows cannot glob an ext4 path, and a `\\\\wsl.localhost` UNC would
    have to be translated back for every command, so the listing is done by the shell that will run
    the case (finding N-16: the first version discovered nothing and reported "0 cases")."""

    def __init__(self, installation, run=None):
        self.launch = list(installation.launch)
        self._run = run or self._default_run

    def _default_run(self, cmd):
        return subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120,
                              creationflags=_CNW if sys.platform == "win32" else 0)

    def _sh(self, script):
        p = self._run(self.launch + [script])
        return (p.stdout or "") if p.returncode == 0 else ""

    def join(self, *parts):
        return "/".join(p.rstrip("/") for p in parts if p != "")

    def isdir(self, path):
        return self._sh("test -d %s && echo yes" % _q(path)).strip() == "yes"

    def listdir(self, path):
        out = self._sh("ls -1A %s 2>/dev/null" % _q(path))
        return sorted(x for x in out.replace("\x00", "").splitlines() if x.strip())

    def read(self, path):
        return self._sh("cat %s 2>/dev/null" % _q(path))

    def home(self):
        # Resolved once, never passed on as "$HOME": build_command single-quotes the working
        # directory, so `cd '$HOME/runs/...'` never expands and every run fails silently (N-17).
        return self._sh("echo $HOME").strip() or "/root"

    def walk(self, base, depth):
        """One `find` for the whole tree. Per-directory `ls`/`test -d` meant one wsl.exe launch
        each -- 300+ of them for examples/, minutes before the first case ran (N-19). `-printf %y`
        says whether each path is a directory or a file, so nothing has to be inferred."""
        base = base.rstrip("/")
        out = self._sh(r"find %s -maxdepth %d -printf '%%y\t%%p\n' 2>/dev/null" % (_q(base), int(depth)))
        tree = {base: []}
        for line in out.replace("\x00", "").splitlines():
            kind, _, path = line.partition("\t")
            path = path.rstrip("/")
            if not path or path == base:
                continue
            if kind == "d":
                tree.setdefault(path, [])
            elif kind == "f" and "/" in path:
                tree.setdefault(path[:path.rindex("/")], []).append(path[path.rindex("/") + 1:])
        return {d: sorted(v) for d, v in tree.items()}


def _q(s):
    return "'" + str(s).replace("'", "'\\''") + "'"


def fs_for(installation):
    return WslFs(installation) if installation.host == "wsl" else LocalFs()


def discover(root, which, only=None, fs=None):
    """Cases under `root`. bench/ is one flat directory of `in.*`; examples/ is one directory per
    case, each possibly holding several `in.*` (min/in.min, min/in.min2d)."""
    fs = fs or LocalFs()
    base = fs.join(root, "bench" if which == "bench" else "examples")
    depth = 1 if which == "bench" else 2
    tree = fs.walk(base, depth)                 # {directory: [entry, ...]}, one round trip on WSL
    cases = []
    for d in sorted(tree):
        if which == "bench" and d != base:
            continue
        if which == "examples" and d == base:
            continue                            # examples/README and friends are not cases
        entries = tree[d]
        refs = _reference_index(d, entries, fs)
        for fn in sorted(entries):
            if fn.startswith("in."):
                stem = fn[3:]
                name = stem if which == "bench" else "%s/%s" % (os.path.basename(d.rstrip("/")), stem)
                cases.append(Case(name, d, fn, refs.get(stem, {})))
    if only:
        cases = [c for c in cases if only in c.name]
    return cases


def _reference_index(directory, entries, fs):
    """{case stem: {procs: path}} for the reference logs sitting in one directory."""
    out = {}
    for fn in entries:
        m = REF_RE.match(fn)
        if not m:
            continue
        parts = fn.split(".")
        if len(parts) < 3:
            continue
        if "scaled" in parts:            # scaled runs change the problem size with the rank count
            continue
        out.setdefault(parts[2], {})[int(m.group(1))] = fs.join(directory, fn)
    return out


def reference_logs(directory, name, fs=None):
    """Upstream ships its own run next to the input: log.<date>.<case>[.variant].g++.<procs>."""
    fs = fs or LocalFs()
    return _reference_index(directory, fs.listdir(directory), fs).get(name, {})


def classify(returncode, log_text):
    """(outcome, detail). The return code only ever tells us about a timeout (N-15)."""
    if returncode == 124:
        return "timeout", ""
    m = MISSING_PKG_RE.search(log_text)
    if m:
        return "missing-package", m.group(1)
    if ERROR_RE.search(log_text):
        line = ERROR_RE.split(log_text, 1)
        detail = log_text[log_text.index("ERROR"):].splitlines()[0][:200]
        return "error", detail.strip() if line else ""
    log = parse_log(log_text)
    if not log.runs:
        return "no-run", "no thermo output"
    return "ok", ""


def compare_final_thermo(ours_text, theirs_text):
    """Compare the last thermo row of two logs column by column; report the worst relative gap."""
    ours, theirs = parse_log(ours_text), parse_log(theirs_text)
    if not ours.runs or not theirs.runs:
        return {"comparable": False, "note": "one side has no thermo output", "columns": {}}
    a, b = ours.runs[-1].last, theirs.runs[-1].last
    if sorted(a) != sorted(b):
        return {"comparable": False, "note": "columns differ: %s vs %s" % (sorted(a), sorted(b)), "columns": {}}
    cols, worst, worst_col, ignored = {}, 0.0, None, []
    for c in a:
        scale = max(abs(a[c]), abs(b[c]))
        rel = 0.0 if scale == 0 else abs(a[c] - b[c]) / scale
        cols[c] = {"ours": a[c], "theirs": b[c], "rel": rel}
        if c in TIMING_COLUMNS:
            ignored.append(c)          # recorded, never the headline: it is wall time on their machine
            continue
        if rel > worst:
            worst, worst_col = rel, c
    return {"comparable": True, "note": "", "columns": cols, "worst": worst, "worst_column": worst_col,
            "ignored": ignored}


def _scratch_root(fs):
    """Where a copy of the case runs. Never the installed tree, never /mnt when the host is WSL,
    and always an absolute path -- see WslFs.home (N-17)."""
    return fs.join(fs.home(), "runs", "examples")


def run_case(case, installation, procs=1, time_limit=120, potentials=None, run_root=None, fs=None):
    """Copy the case out of the installed tree, run it, return one record."""
    fs = fs or fs_for(installation)
    safe = case.name.replace("/", "__")
    if installation.host == "wsl":
        workdir = "%s/%s" % (run_root, safe)
        prep = "rm -rf %s && mkdir -p %s && cp -r %s/. %s/" % (workdir, workdir,
                                                              to_wsl_path(case.directory), workdir)
        subprocess.run(list(installation.launch) + [prep], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=300,
                       creationflags=_CNW if sys.platform == "win32" else 0)
    else:
        workdir = os.path.join(run_root, safe)
        shutil.rmtree(workdir, ignore_errors=True)
        shutil.copytree(case.directory, workdir)

    args = ["-in", case.input_name, "-log", "log.run", "-screen", "none"]
    exe = installation
    if procs > 1:
        from lammpskill.install.base import Installation
        exe = Installation(**{**installation.as_dict(),
                              "executable": "mpirun -np %d %s" % (procs, installation.executable)})
    env = None
    if potentials:
        env = dict(os.environ)
    t0 = time.perf_counter()
    p = run_command(exe, args, cwd=workdir, timeout=time_limit, env=env)
    wall = time.perf_counter() - t0

    text = _read_remote(installation, workdir, "log.run")
    outcome, detail = classify(p.returncode, text + "\n" + (p.stdout or "") + "\n" + (p.stderr or ""))
    log = parse_log(text)
    rec = dict(case=case.name, route=installation.route, procs=procs, outcome=outcome, detail=detail,
               wall=round(wall, 2), rc=p.returncode,
               steps=(log.runs[-1].nsteps if log.runs else None),
               natoms=(log.runs[-1].natoms if log.runs else None),
               loop_time=(log.runs[-1].loop_time if log.runs else None),
               reference=None)
    ref = case.reference.get(procs)
    if ref and outcome == "ok":
        rec["reference"] = compare_final_thermo(text, fs.read(ref))
        rec["reference"]["file"] = os.path.basename(ref)
    return rec


_CNW = 0x08000000


def _read_remote(installation, workdir, name):
    if installation.host == "wsl":
        p = subprocess.run(list(installation.launch) + ["cat %s/%s 2>/dev/null" % (workdir, name)],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120,
                           creationflags=_CNW if sys.platform == "win32" else 0)
        return p.stdout or ""
    path = os.path.join(workdir, name)
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def markdown_table(rows):
    head = ("| case | route | procs | outcome | wall (s) | steps | atoms | vs reference | detail |\n"
            "|---|---|---|---|---|---|---|---|---|\n")
    out = []
    for r in rows:
        ref = r.get("reference")
        if not ref:
            reftxt = "—"
        elif not ref.get("comparable", False):
            reftxt = ref.get("note", "not comparable")
        elif ref["worst"] == 0.0:
            reftxt = "identical"
        else:
            reftxt = "worst %.1e (%s)" % (ref["worst"], ref["worst_column"])
        out.append("| %s | %s | %d | %s | %s | %s | %s | %s | %s |" % (
            r["case"], r["route"], r["procs"], r["outcome"],
            "" if r.get("wall") is None else r["wall"],
            "" if r.get("steps") is None else r["steps"],
            "" if r.get("natoms") is None else r["natoms"],
            _esc(reftxt), _esc(str(r.get("detail") or ""))))
    return head + "\n".join(out) + "\n"


def _esc(s):
    return str(s).replace("|", "\\|")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--route", required=True, help="install route to run on (e.g. wsl-apt, wsl-source)")
    ap.add_argument("--set", dest="which", default="bench", choices=("bench", "examples"))
    ap.add_argument("--root", help="the installed LAMMPS tree holding bench/ and examples/")
    ap.add_argument("--procs", type=int, action="append", default=None, help="repeatable (default 1)")
    ap.add_argument("--time-limit", type=int, default=120, help="seconds per case, enforced inside WSL")
    ap.add_argument("--only", help="substring filter on the case name")
    ap.add_argument("--outdir", default="out/examples", help="where the JSON record and table are written")
    ap.add_argument("--run-root", help="scratch directory for the copies (default ~/runs/examples)")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)

    inst = get_route(a.route).detect()
    if inst is None:
        print("route %s not detected" % a.route)
        return 2
    procs = a.procs or [1]
    root = a.root or os.environ.get("LAMMPSKILL_LAMMPS_TREE")
    if not root:
        print("give --root: the installed tree with bench/ and examples/")
        return 2
    fs = fs_for(inst)
    run_root = a.run_root or _scratch_root(fs)

    cases = discover(root, a.which, only=a.only, fs=fs)
    print("%d case(s) in %s/%s on %s (%s)" % (len(cases), root, a.which, inst.route, inst.version))
    rows = []
    for c in cases:
        for n in procs:
            if n > 1 and not inst.mpi:
                continue
            rec = run_case(c, inst, procs=n, time_limit=a.time_limit, run_root=run_root, fs=fs)
            rows.append(rec)
            print("  %-28s %d proc  %-16s %6ss  %s" % (c.name, n, rec["outcome"], rec["wall"],
                                                       rec["detail"][:60]))
    os.makedirs(a.outdir, exist_ok=True)
    stem = "%s-%s" % (inst.route, a.which)
    with open(os.path.join(a.outdir, stem + ".json"), "w", encoding="utf-8") as f:
        json.dump({"route": inst.route, "version": inst.version, "root": root,
                   "packages": list(inst.packages), "records": rows}, f, indent=1, default=str)
    with open(os.path.join(a.outdir, stem + ".md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(markdown_table(rows))
    counts = {}
    for r in rows:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    print("outcomes:", ", ".join("%s=%d" % kv for kv in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
