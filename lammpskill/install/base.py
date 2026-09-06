# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""The one contract every install route implements, plus the helpers that launch a LAMMPS
executable hidden (KEEP rules/12) on Windows, in WSL or through a fake."""

from __future__ import annotations

import dataclasses
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Our own LJ melt (reduced units; fcc at rho*=0.8442, T*=3.0, rc=2.5): the probe every route runs.
LJ_MELT_TEXT = """# lammps-skill probe: Lennard-Jones melt
units           lj
atom_style      atomic
lattice         fcc 0.8442
region          box block 0 10 0 10 0 10
create_box      1 box
create_atoms    1 box
mass            1 1.0
velocity        all create 3.0 87287 loop geom
pair_style      lj/cut 2.5
pair_coeff      1 1 1.0 1.0 2.5
neighbor        0.3 bin
neigh_modify    every 20 delay 0 check no
fix             1 all nve
thermo          50
thermo_style    custom step temp epair emol etotal press
run             {steps}
"""


@dataclass(frozen=True)
class Installation:
    route: str
    host: str
    executable: str | None
    version: str
    packages: tuple
    mpi: bool
    omp: bool
    library: str | None
    python_module: bool
    launch: tuple
    distro: str | None
    python: str | None
    extra: dict = field(default_factory=dict)

    def as_dict(self):
        return dataclasses.asdict(self)


@dataclass
class ProbeReport:
    ok: bool
    wall: float
    natoms: int | None
    thermo_last: dict
    stdout_tail: str
    error: str | None


_VERSION_RE = re.compile(r"Massively Parallel Simulator\s*-\s*(.+?)\s*$", re.M)


def parse_help(text: str) -> dict:
    """Read `lmp -h` output. Everything is optional; missing parts are empty, never guessed."""
    info = {"version": "", "packages": (), "mpi": False, "omp": False, "os": "", "compiler": "", "styles": {}}
    m = _VERSION_RE.search(text)
    if m:
        info["version"] = m.group(1).strip()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("OS:"):
            info["os"] = s[3:].strip()
        elif s.startswith("Compiler:"):
            info["compiler"] = s[9:].strip()
        elif s.startswith("MPI v") and "STUBS" not in s.upper():
            info["mpi"] = True
        elif s.startswith("Installed packages:"):
            words = []
            started = False
            for nxt in lines[i + 1:]:
                if not nxt.strip():
                    if started:
                        break
                    continue
                started = True
                words.extend(nxt.split())
            info["packages"] = tuple(sorted(set(w.upper() for w in words)))
        elif s.startswith("* ") and s.endswith(":"):
            title = s[2:-1].strip()
            items = []
            started = False
            for nxt in lines[i + 1:]:          # a blank line follows the title; the list ends at the next blank
                if not nxt.strip():
                    if started:
                        break
                    continue
                if nxt.strip().startswith("* "):
                    break
                started = True
                items.extend(nxt.split())
            info["styles"][title] = items
    info["omp"] = "OPENMP" in info["packages"]
    return info


def to_wsl_path(path: str) -> str:
    p = str(path).replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    if m:
        return "/mnt/%s/%s" % (m.group(1).lower(), m.group(2))
    return p


def _quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def build_command(inst: Installation, args, cwd: str, timeout: int) -> list:
    """The argv that runs `inst.executable args` in `cwd` on the installation's host."""
    if inst.executable is None:
        raise ValueError("%s is an in-process route (no executable); use lammpskill.run.LibraryBackend" % inst.route)
    args = [str(a) for a in args]
    if inst.host == "wsl":
        inner = "cd %s && timeout %d %s %s" % (_quote(to_wsl_path(cwd)), int(timeout), inst.executable, " ".join(args))
        return list(inst.launch) + [inner]
    if inst.host == "remote":
        raise NotImplementedError("remote route is pinned: %s" % inst.extra.get("note", ""))
    return list(inst.launch) + [inst.executable] + args


def run_command(inst: Installation, args, cwd: str, timeout: int = 600, env=None, log=None) -> subprocess.CompletedProcess:
    cmd = build_command(inst, args, cwd, timeout)
    kw = dict(cwd=None if inst.host == "wsl" else cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
              env=env, timeout=timeout + 5)
    if sys.platform == "win32":
        kw["creationflags"] = CREATE_NO_WINDOW
    try:
        p = subprocess.run(cmd, **kw)
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        p = subprocess.CompletedProcess(cmd, 124, stdout=out, stderr=err + "\nTIMEOUT after %ss" % timeout)
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write("$ %s\n%s\n%s\n" % (" ".join(cmd), p.stdout, p.stderr))
    return p


_NUM_RE = re.compile(r"^-?[\d.]+(e[-+]?\d+)?$", re.I)


def _parse_probe_log(text: str) -> tuple:
    """natoms and the last thermo row of a LAMMPS log (a tiny parser; lammpskill.io.log is the real one)."""
    natoms = None
    m = re.search(r"Created (\d+) atoms", text)
    if m:
        natoms = int(m.group(1))
    m = re.search(r"Loop time of [\d.]+ on \d+ procs for \d+ steps with (\d+) atoms", text)
    if m:
        natoms = int(m.group(1))
    header, last = None, {}
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] == "Step":
            header = parts
        elif header and parts and all(_NUM_RE.match(p) for p in parts) and len(parts) == len(header):
            last = {k: (int(v) if k == "Step" else float(v)) for k, v in zip(header, parts)}
    return natoms, last


def probe(inst: Installation, workdir: str, steps: int = 250) -> ProbeReport:
    os.makedirs(workdir, exist_ok=True)
    with open(os.path.join(workdir, "in.probe"), "w", encoding="utf-8", newline="\n") as f:
        f.write(LJ_MELT_TEXT.format(steps=steps))
    logpath = os.path.join(workdir, "log.probe")
    t0 = time.perf_counter()
    if inst.executable is None:
        try:
            from lammpskill.run import LibraryBackend
            LibraryBackend().execute_file(os.path.join(workdir, "in.probe"), workdir, logfile="log.probe")
            rc, err = 0, ""
        except Exception as e:  # the report says why, the caller decides
            rc, err = 1, "%s: %s" % (type(e).__name__, e)
        out = ""
    else:
        p = run_command(inst, ["-in", "in.probe", "-log", "log.probe", "-screen", "none"], cwd=workdir, timeout=600)
        rc, err, out = p.returncode, p.stderr, p.stdout
    wall = time.perf_counter() - t0
    text = ""
    if os.path.exists(logpath):
        with open(logpath, encoding="utf-8", errors="replace") as f:
            text = f.read()
    natoms, last = _parse_probe_log(text)
    ok = rc == 0 and last.get("Step") == steps
    return ProbeReport(ok, wall, natoms, last, (out or text)[-800:], None if ok else (err or "no thermo row for step %d" % steps))
