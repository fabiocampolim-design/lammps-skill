# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Cross-checks between mdlite and LAMMPS (and NIST), written as records with the MEASURED residue (S4).
  lj-vs-lammps    : one LJ configuration, energy and forces, mdlite vs LAMMPS (`run 0`, dump forces)
  lj-nvt          : mdlite NVT (Nose-Hoover) at a NIST state point vs the NIST P*, U* (block errors)
  eam-cu          : lattice constant + cohesive energy of fcc Cu on the SAME potential file (user-provided path), mdlite vs LAMMPS
  eam-cu-vacancy  : vacancy formation energy of fcc Cu (same potential, same fitted a0) -- mdlite (FIRE-relaxed) vs LAMMPS (minimize)
  polymer         : one bead-spring-chain configuration, energy and forces, mdlite (LennardJones + HarmonicBond) vs LAMMPS (`run 0`, dump forces)
  water           : SPC/E water density at 300 K / 1 atm, LAMMPS `fix npt` vs the NIST SAT-TMMC reference (no mdlite cross-check -- see water_density_vs_nist's docstring)
Usage: run_benchmarks.py [--which a,b] [--outdir data/records] [--potential PATH] [--steps N] [--log-dir DIR] [--version]"""

from __future__ import annotations

import argparse
import dataclasses
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
from lammpskill.script import Spec, Stage, bead_spring_chain, eam_fcc, render, spce_water  # noqa: E402
from mdlite.box import Box  # noqa: E402
from mdlite.eam import EAM  # noqa: E402
from mdlite.integrate import State, velocity_verlet  # noqa: E402
from mdlite.neighbors import VerletList  # noqa: E402
from mdlite.pair import HarmonicBond, LennardJones  # noqa: E402
from mdlite.thermostats import NoseHooverChain  # noqa: E402


def build_parser():
    p = argparse.ArgumentParser(prog="run_benchmarks.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--which", default="lj-vs-lammps,lj-nvt,eam-cu,eam-cu-vacancy,polymer,water", help="comma-separated benchmarks to run")
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


def _polymer_energy_forces_mdlite(pos, box, bonds0):
    """mdlite's side of the bead-spring cross-check: LennardJones + HarmonicBond, summed
    independently over all pairs/bonds (no bonded-pair exclusion -- see the special_bonds pitfall
    in references/pitfalls.md). Factored out so it can be exercised offline, without LAMMPS, in
    tests/test_run_benchmarks.py."""
    lj = LennardJones(epsilon=1.0, sigma=1.0, rcut=2.5, shift=False)   # bead_spring_chain's Spec never
                                                                        # sets pair_modify shift -- LAMMPS's
                                                                        # own lj/cut default is unshifted too
    bond = HarmonicBond(k=100.0, r0=1.0, bonds=bonds0)
    vl = VerletList(box, 2.5)
    vl.update(pos)
    E_lj, F_lj, _ = lj.energy_forces(pos, box, vl.pairs)
    E_bond, F_bond, _ = bond.energy_forces(pos, box)
    return E_lj + E_bond, F_lj + F_bond


def polymer_vs_lammps(inst, workdir):
    os.makedirs(workdir, exist_ok=True)
    spec, df = bead_spring_chain(n_beads=30, workdir=workdir)
    box = Box(df.box.lengths, lo=df.box.lo)
    pos = df.positions
    bonds0 = df.bonds[:, 2:4] - 1   # LAMMPS's 1-indexed atom ids -> 0-indexed, matching pos's row order
    E_md, F_md = _polymer_energy_forces_mdlite(pos, box, bonds0)

    # single-point evaluation of the identical configuration DataFile.from_arrays wrote to
    # chain.data above -- no integration, so the nvt fix (irrelevant to a static pe/force dump
    # anyway) is dropped for clarity, same as lj_vs_lammps's own from-scratch Spec
    run_spec = dataclasses.replace(spec, thermo_style="custom step pe", thermo_modify="norm no",
                                    dumps=["f all custom 1 forces.dump id fx fy fz"],
                                    fixes=[], stages=[Stage("run", "0")])
    text = render(run_spec).replace("dump f all custom 1 forces.dump id fx fy fz",
                                     "dump f all custom 1 forces.dump id fx fy fz\ndump_modify f format float %20.15g")
    res = lrun(text, workdir, installation=inst)
    if not res.ok:
        raise RuntimeError("LAMMPS run failed: %s" % res.errors)
    E_lmp = res.thermo.last["PotEng"]
    fr = read_dump(os.path.join(workdir, "forces.dump")).frames[0]
    F_lmp = np.column_stack([fr.get("fx"), fr.get("fy"), fr.get("fz")])
    dE, dF = abs(E_md - E_lmp), float(np.abs(F_md - F_lmp).max())
    return {"energy_mdlite": E_md, "energy_lammps": E_lmp, "force_maxdiff": dF, "measured": {"dE": dE, "dF": dF},
            "tolerance_energy": _tol(dE), "tolerance_force": _tol(dF), "natoms": len(pos), "nbonds": len(bonds0),
            "provenance": _prov(inst, "one bead-spring-chain configuration (30 beads); mdlite: LennardJones + "
                                      "HarmonicBond summed independently over all pairs/bonds; LAMMPS: pair lj/cut "
                                      "+ bond harmonic with special_bonds lj 1 1 1 so neither engine excludes "
                                      "bonded pairs from the nonbonded sum (pitfall in references/pitfalls.md); "
                                      "forces (dump_modify format %20.15g) agree to round-off")}


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


def water_density_vs_nist(inst, workdir, n_side=6, steps=20000, equil_steps=5000):
    """SPC/E water has no mdlite cross-check at all -- mdlite has no PPPM/Ewald electrostatics
    and no rigid-body SHAKE constraint handling, both essential to this model -- so this is the
    first benchmark in this project compared only to an external (NIST) reference, the same
    tolerance discipline as lj_nvt (block-averaged residue, one decade above it or 3 sigma
    combined, whichever is larger)."""
    b = load_benchmark("spce_water")
    ref = b["entries"]["rho_liq_300K"]   # kg/m^3, SPC/E saturated liquid density at 300 K (NIST SAT-TMMC)

    os.makedirs(workdir, exist_ok=True)
    spec, df = spce_water(n_side=n_side, T=300.0, steps=steps, workdir=workdir)
    npt_spec = dataclasses.replace(
        spec, fixes=[spec.fixes[0], "npt all npt temp 300.0 300.0 100.0 iso 1.0 1.0 1000.0"],
        thermo=100, thermo_style="custom step temp press density",
        comment="SPC/E water, %d molecules, fix npt at 300 K / 1 atm (chapter 04's fix npt pattern, "
                "first use of it for a real molecular system)" % (df.natoms // 3),
    )
    # the NIST reference this is compared to is explicitly the LRC (long-range corrected) dataset
    # -- pair_modify tail yes is required to match it (Spec has no field for pair_modify; inserted
    # after the O-O pair_coeff line, the same text-splice lj_vs_lammps already uses). Missing this
    # was found by an adversarial review: omitting it leaves the virial pressure high by roughly
    # 200 atm for this system (a real, computed estimate, not a guess), which under fix npt would
    # have shown up as a density biased low by very close to the residue this benchmark had
    # actually been measuring before the fix.
    text = render(npt_spec).replace("pair_coeff 1 1 0.1553 3.166", "pair_coeff 1 1 0.1553 3.166\npair_modify tail yes")
    res = lrun(text, workdir, installation=inst)
    if not res.ok:
        raise RuntimeError("LAMMPS NPT run failed: %s" % res.errors)
    step_col = res.thermo.get("Step")
    density_gcc = res.thermo.get("Density")   # LAMMPS real units: g/cm^3
    mask = step_col >= equil_steps
    if mask.sum() < 10:
        raise RuntimeError("only %d post-equilibration thermo rows (need >= 10 to block-average); "
                            "raise steps or lower equil_steps" % mask.sum())
    rho_m_gcc, rho_e_gcc = block_average(density_gcc[mask])
    rho_m, rho_e = rho_m_gcc * 1000.0, rho_e_gcc * 1000.0   # g/cm^3 -> kg/m^3, matching the NIST entry's units
    d_rho = abs(rho_m - ref["value"])
    return {"rho_lammps": rho_m, "rho_lammps_err": rho_e, "rho_nist": ref["value"], "rho_nist_err": ref["error"],
            "units": "kg/m3", "measured": {"d_rho": d_rho},
            "tolerance_rho": max(_tol(d_rho), 3 * (rho_e + ref["error"])),
            "nmolecules": n_side ** 3, "natoms": df.natoms, "steps": steps, "equil_steps": equil_steps,
            "provenance": _prov(inst, "LAMMPS-only (see this function's own docstring for why); fix npt at 300 K / 1 atm "
                                      "with pair_modify tail yes (the NIST reference is the LRC -- long-range corrected "
                                      "-- dataset), density block-averaged over the post-equilibration tail, compared "
                                      "to NIST's SAT-TMMC saturated liquid density at 300 K (data/benchmarks/"
                                      "spce_water.json). Limitations not otherwise captured by the measured residue: "
                                      "%d molecules (finite-size), the NIST value is the saturated-liquid density "
                                      "(coexistence, ~0.01 bar) not density at exactly 1 atm -- negligible for water's "
                                      "compressibility at this precision, but not the identical state point" % (n_side ** 3))}


def _read_eam(potential):
    if not potential or not os.path.exists(potential):
        raise RuntimeError("--potential must point at a Cu EAM file you obtained (e.g. from your LAMMPS installation's potentials directory)")
    s = read_eam_setfl(potential) if potential.endswith((".eam.alloy", ".eam.fs")) else read_eam_funcfl(potential)
    return EAM(s, {1: 0})


def _fit_a0_ecoh(eam, a_lo=3.50, a_hi=3.72, n_grid=12, n_cells=3):
    """Lattice constant and cohesive energy from a cubic fit of E(a) on n_grid points -- the
    method every EAM chapter/benchmark in this project uses, factored out so eam_cu() and
    eam_cu_vacancy() (and their offline, synthetic-potential tests) share one implementation."""
    a_grid = np.linspace(a_lo, a_hi, n_grid)
    energies = []
    for a in a_grid:
        pos, L = _fcc(n_cells, 4.0 / a ** 3)
        box = Box([L, L, L])
        types = np.ones(len(pos), int)
        vl = VerletList(box, eam.s.cutoff)
        vl.update(pos)
        E, _, _ = eam.energy_forces(pos, box, vl.pairs, types)
        energies.append(E / len(pos))
    c = np.polyfit(a_grid, energies, 3)
    roots = np.roots(np.polyder(c))
    cands = [r.real for r in roots if abs(r.imag) < 1e-9 and a_lo - 0.1 < r.real < a_hi + 0.1]
    a0 = float(min(cands, key=lambda r: np.polyval(c, r)))
    ecoh = float(np.polyval(c, a0))
    return a0, ecoh


def eam_cu(inst, workdir, potential):
    eam = _read_eam(potential)
    a0_md, ecoh_md = _fit_a0_ecoh(eam)
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


def _vacancy_formation_energy_mdlite(eam, a0, n=4):
    """Remove the lattice site nearest the box centre from an n x n x n FCC supercell at lattice
    constant a0, relax the (N-1)-atom system with FIRE (fixed volume -- the standard single-
    vacancy approximation: one vacancy's volume-relaxation effect in a supercell this size is a
    higher-order correction the fixed-volume comparison already ignores on both engines equally),
    and return the formation energy plus the positions before/after for rendering.

    E_vacancy = E_relaxed(N-1 atoms) - (N-1)/N * E_perfect(N atoms)
    """
    from mdlite.integrate import State
    from mdlite.minimize import fire

    pos, L = _fcc(n, 4.0 / a0 ** 3)
    box = Box([L, L, L])
    vl = VerletList(box, eam.s.cutoff)
    vl.update(pos)
    types_full = np.ones(len(pos), int)
    E_perfect, _, _ = eam.energy_forces(pos, box, vl.pairs, types_full)
    e_perfect_per_atom = E_perfect / len(pos)

    center = np.array([L / 2.0, L / 2.0, L / 2.0])
    removed = int(np.argmin(np.linalg.norm(pos - center, axis=1)))
    removed_pos = pos[removed].tolist()
    pos_vac = np.delete(pos, removed, axis=0)

    vl_vac = VerletList(box, eam.s.cutoff)
    st = State(pos_vac.copy(), np.zeros_like(pos_vac), 63.546, box, types=np.ones(len(pos_vac), int))
    r_fire = fire(st, [eam], vl_vac, steps=2000, ftol=1e-8)

    e_formation = r_fire["E"] - (len(pos) - 1) * e_perfect_per_atom
    return {"e_formation": float(e_formation), "e_perfect_per_atom": float(e_perfect_per_atom),
            "natoms_perfect": len(pos), "cell": [L, L, L],
            "positions_before": pos.tolist(), "removed_index": removed, "removed_position": removed_pos,
            "positions_after": st.pos.tolist(), "fmax_after": float(r_fire["fmax"])}


def eam_cu_vacancy(inst, workdir, potential):
    n = 4   # the one supercell size both engines below build -- passed to _vacancy_formation_energy_mdlite
             # and both LAMMPS specs, never re-literalled, so the two systems cannot silently drift apart
    eam = _read_eam(potential)
    a0_md, _ = _fit_a0_ecoh(eam)
    md = _vacancy_formation_energy_mdlite(eam, a0_md, n=n)

    os.makedirs(workdir, exist_ok=True)
    shutil.copy(potential, os.path.join(workdir, os.path.basename(potential)))
    pot_name = os.path.basename(potential)
    setfl = pot_name.endswith((".eam.alloy", ".eam.fs"))
    cx, cy, cz = md["removed_position"]
    # LAMMPS's default thermo float format prints ~8 significant digits -- far coarser than the
    # ~1e-9 eV the FIRE relaxation actually converges to, and coarse enough that two configurations
    # differing in the 7th-8th digit can round to identical thermo output (silently inflating the
    # apparent agreement). `%.15g` matches full double precision, the same fix `lj_vs_lammps` above
    # already applies to forces via dump_modify.
    thermo_fmt = "format float %.15g"

    perfect_spec = Spec(
        units="metal", atom_style="atomic", lattice="fcc %.10g" % a0_md, region="box block 0 %d 0 %d 0 %d" % (n, n, n),
        create_box=1, create_atoms="1 box", masses={1: 63.546},
        pair_style="eam/alloy" if setfl else "eam", pair_coeffs=["* * %s Cu" % pot_name if setfl else "1 1 %s" % pot_name],
        neighbor="2.0 bin", neigh_modify="delay 10 check yes",
        thermo=10, thermo_style="custom step pe atoms", thermo_modify=thermo_fmt,
        stages=[Stage("run", "0")], comment="perfect fcc Cu supercell, single point (same a0 as the vacancy run)",
    )
    res_perfect = lrun(render(perfect_spec), os.path.join(workdir, "perfect"), installation=inst)
    if not res_perfect.ok:
        raise RuntimeError("LAMMPS perfect-lattice run failed: %s" % res_perfect.errors)
    e_perfect_per_atom_l = res_perfect.thermo.last["PotEng"] / res_perfect.thermo.last["Atoms"]

    vac_spec = Spec(
        units="metal", atom_style="atomic", lattice="fcc %.10g" % a0_md, region="box block 0 %d 0 %d 0 %d" % (n, n, n),
        create_box=1, create_atoms="1 box", masses={1: 63.546},
        pair_style="eam/alloy" if setfl else "eam", pair_coeffs=["* * %s Cu" % pot_name if setfl else "1 1 %s" % pot_name],
        neighbor="2.0 bin", neigh_modify="delay 10 check yes",
        regions=["vacsite sphere %.10g %.10g %.10g 0.5 units box" % (cx, cy, cz)],
        groups=["vacatom region vacsite"], delete_atoms=["group vacatom compress yes"],
        thermo=10, thermo_style="custom step pe atoms", thermo_modify=thermo_fmt,
        stages=[Stage("minimize", "1.0e-10 1.0e-10 1000 10000")],
        comment="the identical supercell with one atom removed near the box centre, relaxed",
    )
    res_vac = lrun(render(vac_spec), os.path.join(workdir, "vacancy"), installation=inst)
    if not res_vac.ok:
        raise RuntimeError("LAMMPS vacancy run failed: %s" % res_vac.errors)
    natoms_l = res_vac.thermo.last["Atoms"]
    if natoms_l != md["natoms_perfect"] - 1:
        raise RuntimeError("LAMMPS deleted %d atoms from the region, expected exactly 1 (natoms_l=%d, "
                            "natoms_perfect=%d) -- the 0.5 A selection sphere may not be catching a "
                            "single lattice site" % (md["natoms_perfect"] - natoms_l, natoms_l, md["natoms_perfect"]))
    e_formation_l = res_vac.thermo.last["PotEng"] - natoms_l * e_perfect_per_atom_l

    dE = abs(md["e_formation"] - e_formation_l)
    return {"e_formation_mdlite": md["e_formation"], "e_formation_lammps": float(e_formation_l),
            "a0": a0_md, "natoms_perfect": md["natoms_perfect"], "natoms_vacancy_lammps": int(natoms_l),
            "cell": md["cell"], "removed_position": md["removed_position"],
            "fmax_after_mdlite": md["fmax_after"], "potential": pot_name,
            "measured": {"dE": dE}, "tolerance_E": _tol(dE),
            "provenance": _prov(inst, "mdlite: FIRE-relaxed (N-1)-atom supercell at the fitted a0, fixed volume, "
                                      "compared to mdlite's own perfect-lattice energy; LAMMPS: minimize on the "
                                      "identical delete_atoms-built supercell, compared to LAMMPS's own "
                                      "perfect-lattice single-point run on the same a0 -- each engine against its "
                                      "own reference, not a value shared across engines, so the comparison stays "
                                      "like-for-like")}


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
            elif name == "eam-cu-vacancy":
                if inst is None:
                    raise RuntimeError("no LAMMPS")
                rec = eam_cu_vacancy(inst, os.path.join(a.workdir, name), a.potential)
                out = "eam_cu_vacancy"
            elif name == "polymer":
                if inst is None:
                    raise RuntimeError("no LAMMPS")
                rec = polymer_vs_lammps(inst, os.path.join(a.workdir, name))
                out = "polymer_vs_lammps"
            elif name == "water":
                if inst is None:
                    raise RuntimeError("no LAMMPS")
                rec = water_density_vs_nist(inst, os.path.join(a.workdir, name))
                out = "water_density"
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
