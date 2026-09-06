# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Run LAMMPS: through any executable (subprocess, hidden window) or in-process through the official python module.
Both backends return the same Result. `run_or_load` is the record-or-run helper for the chapters (S11)."""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
import os
import time
from dataclasses import dataclass, field

from . import __version__
from .install import detect_all
from .install.base import Installation, run_command
from .io.log import LogFile, parse_log
from .script import Spec, render


@dataclass
class Result:
    ok: bool
    returncode: int
    elapsed: float
    log: LogFile
    workdir: str
    files: dict
    stdout: str = ""
    stderr: str = ""
    installation: Installation | None = None
    backend: str = ""
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def thermo(self):
        return self.log.thermo


def _detect():
    return detect_all()


def _write_input(spec_or_text, workdir, input_name):
    os.makedirs(workdir, exist_ok=True)
    text = render(spec_or_text) if isinstance(spec_or_text, Spec) else str(spec_or_text)
    with open(os.path.join(workdir, input_name), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return text


def _snapshot(workdir):
    return {name: os.path.join(workdir, name) for name in sorted(os.listdir(workdir))}


def _read_log(workdir, log_name):
    p = os.path.join(workdir, log_name)
    if os.path.exists(p):
        with open(p, encoding="utf-8", errors="replace") as f:
            return parse_log(f.read())
    return LogFile()


class SubprocessBackend:
    name = "subprocess"

    def run(self, spec_or_text, workdir, installation, *, mpi=None, omp=None, time_limit=600, input_name="in.lammps",
            log_name="log.lammps", extra_args=()) -> Result:
        if installation.extra.get("pinned"):
            raise NotImplementedError("route %s is pinned (%s)" % (installation.route, installation.extra.get("note", "")))
        if installation.executable is None:
            raise ValueError("installation %s has no executable; use LibraryBackend" % installation.route)
        _write_input(spec_or_text, workdir, input_name)
        warnings = []
        args = ["-in", input_name, "-log", log_name, "-screen", "none"]
        env = None
        if omp:
            if installation.omp:
                args += ["-sf", "omp", "-pk", "omp", str(int(omp))]
                env = dict(os.environ, OMP_NUM_THREADS=str(int(omp)))
            else:
                warnings.append("omp=%s ignored: OPENMP package not in this build" % omp)
        args += list(extra_args)
        launcher = installation
        if mpi and int(mpi) > 1:
            if not installation.mpi:
                warnings.append("mpi=%s ignored: no MPI in this build" % mpi)
            elif installation.host == "wsl":
                # the WSL command is one shell string, so the mpirun prefix becomes part of the executable text
                launcher = Installation(**{**installation.as_dict(), "executable": "mpirun -np %d %s" % (int(mpi), installation.executable)})
            else:
                # Windows (MS-MPI): mpiexec -n N lmp.exe args — the prefix goes in front of the executable, still hidden
                launcher = Installation(**{**installation.as_dict(), "launch": tuple(installation.launch) + ("mpiexec", "-n", str(int(mpi)))})
        t0 = time.perf_counter()
        p = run_command(launcher, args, cwd=workdir, timeout=time_limit, env=env)
        elapsed = time.perf_counter() - t0
        log = _read_log(workdir, log_name)
        ok = p.returncode == 0 and not log.errors and bool(log.runs)
        return Result(ok, p.returncode, elapsed, log, workdir, _snapshot(workdir), p.stdout, p.stderr, installation, self.name,
                      warnings + log.warnings, log.errors + ([p.stderr.strip()] if p.returncode and p.stderr.strip() else []))


class LibraryBackend:
    name = "library"

    def _lammps(self, workdir, log_name):
        import lammps  # GPL-2.0; the only import of the module outside install/wheel.py
        return lammps.lammps(cmdargs=["-log", os.path.join(workdir, log_name), "-screen", "none", "-nocite"])

    @contextlib.contextmanager
    def session(self, workdir, log_name="log.lammps"):
        os.makedirs(workdir, exist_ok=True)
        cwd = os.getcwd()
        os.chdir(workdir)
        L = self._lammps(workdir, log_name)
        try:
            yield L
        finally:
            try:
                L.close()
            finally:
                os.chdir(cwd)

    def execute_file(self, path, workdir, logfile="log.lammps"):
        with self.session(workdir, logfile) as L:
            L.file(os.path.basename(path) if os.path.dirname(os.path.abspath(path)) == os.path.abspath(workdir) else path)

    def run(self, spec_or_text, workdir, installation=None, *, time_limit=None, log_name="log.lammps", input_name="in.lammps") -> Result:
        text = _write_input(spec_or_text, workdir, input_name)
        t0 = time.perf_counter()
        err = ""
        rc = 0
        try:
            with self.session(workdir, log_name) as L:
                L.commands_string(text)
        except Exception as e:  # lammps raises on ERROR when built with exceptions (the default)
            err, rc = "%s: %s" % (type(e).__name__, e), 1
        elapsed = time.perf_counter() - t0
        log = _read_log(workdir, log_name)
        ok = rc == 0 and not log.errors and bool(log.runs)
        return Result(ok, rc, elapsed, log, workdir, _snapshot(workdir), "", err, installation, self.name, list(log.warnings),
                      log.errors + ([err] if err else []))


def run(spec_or_text, workdir, *, installation=None, backend="auto", **kw) -> Result:
    if installation is None:
        found = _detect()
        if backend in ("auto", "subprocess"):
            installation = next((i for i in found if i.executable and not i.extra.get("pinned")), None)
        if installation is None and backend in ("auto", "library"):
            installation = next((i for i in found if i.python_module), None)
        if installation is None:
            if found:
                raise RuntimeError("no LAMMPS installation usable for backend %r (routes found: %s)" % (backend, ", ".join(i.route for i in found)))
            raise RuntimeError("no LAMMPS installation detected on any route; see references/install-routes.md")
    if backend == "library" or (backend == "auto" and installation.executable is None):
        return LibraryBackend().run(spec_or_text, workdir, installation, **{k: v for k, v in kw.items() if k in ("time_limit", "log_name", "input_name")})
    return SubprocessBackend().run(spec_or_text, workdir, installation, **kw)


def run_or_load(name, compute, records_dir, *, installation=None, force=False) -> dict:
    os.makedirs(records_dir, exist_ok=True)
    path = os.path.join(records_dir, name + ".json")
    if os.path.exists(path) and not force:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        rec["source"] = "record"
        return rec
    try:
        data = dict(compute())
    except RuntimeError as e:
        if "no LAMMPS" in str(e):
            return {"source": "skip", "reason": str(e)}
        raise
    data.update({"source": "run", "date": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "lammps_skill": __version__,
                 "installation": installation.as_dict() if installation else None})
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    return data
