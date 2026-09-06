# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Cross-checks between mdlite and LAMMPS (and NIST), written as records with the MEASURED residue (S4).
  lj-vs-lammps : one LJ configuration, energy and forces, mdlite vs LAMMPS (`run 0`, dump forces)
  lj-nvt       : mdlite NVT (Nose-Hoover) at a NIST state point vs the NIST P*, U* (block errors)
  eam-cu       : lattice constant + cohesive energy of fcc Cu on the SAME potential file (user-provided path), mdlite vs LAMMPS
Usage: run_benchmarks.py [--which a,b] [--outdir data/records] [--potential PATH] [--steps N] [--log-dir DIR] [--version]"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lammpskill import __version__  # noqa: E402
from lammpskill.install import detect_all  # noqa: E402
from lammpskill.io.box import Box as IOBox  # noqa: E402
from lammpskill.io.data import DataFile, write_data  # noqa: E402
from lammpskill.io.dump import read_dump  # noqa: E402
from lammpskill.io.potential import read_eam_funcfl, read_eam_setfl  # noqa: E402
from lammpskill.post import block_average, load_benchmark  # noqa: E402
from lammpskill.run import run as lrun  # noqa: E402
from lammpskill.script import Spec, Stage, eam_fcc, render  # noqa: E402
from mdlite.box import Box  # noqa: E402
from mdlite.eam import EAM  # noqa: E402
from mdlite.integrate import State, velocity_verlet  # noqa: E402
from mdlite.neighbors import VerletList  # noqa: E402
from mdlite.pair import LennardJones  # noqa: E402
from mdlite.thermostats import NoseHooverChain  # noqa: E402


def build_parser():
    p = argparse.ArgumentParser(prog="run_benchmarks.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--which", default="lj-vs-lammps,lj-nvt,eam-cu", help="comma-separated benchmarks to run")
    p.add_argument("--outdir", default=os.path.join(ROOT, "data", "records"), help="where the record JSON files are written")
    p.add_argument("--workdir", default=os.path.join(ROOT, "out", "benchmarks"), help="scratch directory for the LAMMPS runs")
    p.add_argument("--potential", default=None, help="path to a Cu EAM file (funcfl .eam or setfl .eam.alloy) you obtained yourself")
    p.add_argument("--steps", type=int, default=20000, help="production steps for lj-nvt (default 20000)")
    p.add_argument("--state-point", default=None, help="NIST key prefix for lj-nvt, e.g. T0.85_rho0.776 (default: the first MC entry)")
    p.add_argument("--log-dir", default=None, help="append a one-line log per invocation to this directory")
    p.add_argument("--version", action="version", version="lammps-skill " + __version__)
    return p


def _fcc(n, rho):
    a = (4.0 / rho) ** (1.0 / 3.0)
    base = np.array([[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]) * a
    cells = np.array([[i, j, k] for i in range(n) for j in range(n) for k in range(n)]) * a
    return (cells[:, None, :] + base[None, :, :]).reshape(-1, 3), n * a


def _prov(inst, why):
    return {"route": inst.route if inst else "none", "lammps_version": inst.version if inst else "",
            "date": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d"), "lammps_skill": __version__, "why": why}


def _tol(residue):
    """One decade above the measured residue (never below 1e-12)."""
    return float(10 ** np.ceil(np.log10(max(abs(residue), 1e-12))))


def lj_vs_lammps(inst, workdir):
    rng = np.random.default_rng(7)
    pos, L = _fcc(4, 0.8442)
    pos = pos + rng.normal(0, 0.05, pos.shape)
    box = Box([L, L, L])
    pos = box.wrap(pos)
    vl = VerletList(box, 2.5)
    vl.update(pos)
    E_md, F_md, _ = LennardJones().energy_forces(pos, box, vl.pairs)
    df = DataFile.from_arrays(box=IOBox(0, L, 0, L, 0, L), types=np.ones(len(pos), int), positions=pos, masses={1: 1.0})
    os.makedirs(workdir, exist_ok=True)
    write_data(df, os.path.join(workdir, "conf.data"))
    # thermo_modify norm: in `units lj` LAMMPS normalises thermo energies PER ATOM by default (pitfall P-norm in
    # references/pitfalls.md, found 2026-09-06: -6.04 vs -1545.7); `norm no` makes pe the total. The dump's default
    # float format has 6 significant digits; dump_modify widens it so the force residue is round-off, not formatting.
    spec = Spec(units="lj", atom_style="atomic", read_data="conf.data", pair_style="lj/cut 2.5", pair_coeffs=["1 1 1.0 1.0 2.5"],
                thermo_style="custom step pe", thermo_modify="norm no",
                dumps=["f all custom 1 forces.dump id fx fy fz"], stages=[Stage("run", "0")])
    # LAMMPS accepts pair_modify only after pair_style and dump_modify only after its dump: insert both in place
    text = render(spec).replace("pair_coeff 1 1 1.0 1.0 2.5", "pair_coeff 1 1 1.0 1.0 2.5\npair_modify shift yes")
    text = text.replace("dump f all custom 1 forces.dump id fx fy fz", "dump f all custom 1 forces.dump id fx fy fz\ndump_modify f format float %20.15g")
    res = lrun(text, workdir, installation=inst)
    if not res.ok:
        raise RuntimeError("LAMMPS run failed: %s" % res.errors)
    E_lmp = res.thermo.last["PotEng"]
    fr = read_dump(os.path.join(workdir, "forces.dump")).frames[0]
    F_lmp = np.column_stack([fr.get("fx"), fr.get("fy"), fr.get("fz")])
    dE, dF = abs(E_md - E_lmp), float(np.abs(F_md - F_lmp).max())
    return {"energy_mdlite": E_md, "energy_lammps": E_lmp, "force_maxdiff": dF, "measured": {"dE": dE, "dF": dF},
            "tolerance_energy": _tol(dE), "tolerance_force": _tol(dF), "natoms": len(pos),
            "provenance": _prov(inst, "double precision both sides; forces (dump_modify format %20.15g) agree to round-off; the energy residue is "
                                      "the thermo print precision (pe printed with ~8 significant digits); tolerance one decade above measured")}


def lj_nvt(inst, workdir, steps, state_point=None):
    b = load_benchmark("nist_lj")
    key = state_point or next(k[:-2] for k in b["entries"] if k.endswith("_P") and b["entries"][k].get("method") == "NVT MC")
    T0 = float(key.split("_")[0][1:])
    rho = float(key.split("_")[1][3:])
    pos, L = _fcc(5, rho)          # 500 atoms, as NIST
    box = Box([L, L, L])
    rng = np.random.default_rng(11)
    vel = rng.normal(0, np.sqrt(T0), pos.shape)
    vel -= vel.mean(0)
    st = State(pos, vel, 1.0, box)
    lj = LennardJones(rcut=3.0, shift=False)      # NIST: rc = 3 sigma, long-range corrections added analytically below
    vl = VerletList(box, 3.0)
    velocity_verlet(st, [lj], dt=0.005, nsteps=max(2000, steps // 5), nlist=vl, thermostat=NoseHooverChain(T0, 0.5), every=10 ** 9)
    rec = velocity_verlet(st, [lj], dt=0.005, nsteps=steps, nlist=vl, thermostat=NoseHooverChain(T0, 0.5), every=10)
    n = len(pos)
    U = np.array([r["E_pot"] for r in rec]) / n
    P = np.array([r["P"] for r in rec])
    rc = 3.0
    u_tail = 8.0 / 3.0 * np.pi * rho * (rc ** -9 / 3.0 - rc ** -3)
    p_tail = 16.0 / 3.0 * np.pi * rho ** 2 * (2.0 / 3.0 * rc ** -9 - rc ** -3)
    Um, Ue = block_average(U + u_tail)
    Pm, Pe = block_average(P + p_tail)
    Pn, Un = b["entries"][key + "_P"], b["entries"][key + "_U"]
    dP, dU = abs(Pm - Pn["value"]), abs(Um - Un["value"])
    return {"state_point": key, "P_mdlite": Pm, "P_err": Pe, "P_nist": Pn["value"], "P_nist_err": Pn.get("error") or 0.0,
            "U_mdlite": Um, "U_err": Ue, "U_nist": Un["value"], "U_nist_err": Un.get("error") or 0.0,
            "measured": {"dP": dP, "dU": dU},
            "tolerance_P": max(_tol(dP), 3 * (Pe + (Pn.get("error") or 0.0))), "tolerance_U": max(_tol(dU), 3 * (Ue + (Un.get("error") or 0.0))),
            "steps": steps, "natoms": n,
            "provenance": _prov(None, "finite-size (500 atoms) and sampling; tolerance = max(decade above measured, 3 sigma combined)")}


def eam_cu(inst, workdir, potential):
    if not potential or not os.path.exists(potential):
        raise RuntimeError("--potential must point at a Cu EAM file you obtained (e.g. from your LAMMPS installation's potentials directory)")
    s = read_eam_setfl(potential) if potential.endswith((".eam.alloy", ".eam.fs")) else read_eam_funcfl(potential)
    eam = EAM(s, {1: 0})
    a_grid = np.linspace(3.50, 3.72, 12)
    energies = []
    for a in a_grid:
        pos, L = _fcc(3, 4.0 / a ** 3)
        box = Box([L, L, L])
        types = np.ones(len(pos), int)
        vl = VerletList(box, s.cutoff)
        vl.update(pos)
        E, _, _ = eam.energy_forces(pos, box, vl.pairs, types)
        energies.append(E / len(pos))
    c = np.polyfit(a_grid, energies, 3)
    roots = np.roots(np.polyder(c))
    cands = [r.real for r in roots if abs(r.imag) < 1e-9 and 3.4 < r.real < 3.8]
    a0_md = float(min(cands, key=lambda r: np.polyval(c, r)))
    ecoh_md = float(np.polyval(c, a0_md))
    os.makedirs(workdir, exist_ok=True)
    shutil.copy(potential, os.path.join(workdir, os.path.basename(potential)))
    spec = eam_fcc(potential=os.path.basename(potential), n=3)
    spec.thermo_style = "custom step pe lx atoms"
    res = lrun(render(spec), workdir, installation=inst)
    if not res.ok:
        raise RuntimeError("LAMMPS run failed: %s" % res.errors)
    last = res.thermo.last
    a0_l = last["Lx"] / 3.0
    ecoh_l = last["PotEng"] / last["Atoms"]
    da, de = abs(a0_md - a0_l), abs(ecoh_md - ecoh_l)
    return {"a0_mdlite": a0_md, "a0_lammps": a0_l, "ecoh_mdlite": ecoh_md, "ecoh_lammps": ecoh_l, "potential": os.path.basename(potential),
            "measured": {"da": da, "de": de}, "tolerance_a0": _tol(da), "tolerance_ecoh": _tol(de),
            "provenance": _prov(inst, "mdlite: cubic fit of E(a) on 12 points; LAMMPS: box/relax minimisation; spline vs LAMMPS's own table interpolation")}


def main(argv=None):
    a = build_parser().parse_args(argv)
    found = detect_all()
    inst = next((i for i in found if i.executable and not i.extra.get("pinned")), None)
    os.makedirs(a.outdir, exist_ok=True)
    rc = 0
    for name in a.which.split(","):
        try:
            if name == "lj-vs-lammps":
                if inst is None:
                    raise RuntimeError("no LAMMPS")
                rec = lj_vs_lammps(inst, os.path.join(a.workdir, name))
                out = "lj_energy_vs_lammps"
            elif name == "lj-nvt":
                rec = lj_nvt(inst, os.path.join(a.workdir, name), a.steps, a.state_point)
                out = "lj_nvt_nist"
            elif name == "eam-cu":
                if inst is None:
                    raise RuntimeError("no LAMMPS")
                rec = eam_cu(inst, os.path.join(a.workdir, name), a.potential)
                out = "eam_cu_lattice"
            else:
                print("unknown benchmark", name)
                rc = 2
                continue
            with open(os.path.join(a.outdir, out + ".json"), "w", encoding="utf-8", newline="\n") as f:
                json.dump(rec, f, indent=1, sort_keys=True)
            print("%-14s OK   %s" % (name, json.dumps(rec["measured"])))
        except Exception as e:
            print("%-14s FAIL %s: %s" % (name, type(e).__name__, e))
            rc = 1
    if a.log_dir:
        os.makedirs(a.log_dir, exist_ok=True)
        with open(os.path.join(a.log_dir, "run_benchmarks.log"), "a", encoding="utf-8") as f:
            f.write("%s which=%s rc=%d\n" % (_dt.datetime.now().isoformat(timespec="seconds"), a.which, rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
