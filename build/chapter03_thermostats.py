# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Chapter 03 — Thermostats. Both: the three mdlite thermostats and the NIST record run
unconditionally; the LAMMPS `fix nvt` case goes through record-or-run."""

from nbbuild import code, md

CELLS = [
    md("""
## Three thermostats, three different promises

A thermostat holds a simulation at a target temperature, and each way of doing that trades
something different. This chapter runs all three `mdlite` implements on the same starting state and
target, so what each conserves and what each distorts is visible on the same axes rather than taken
on faith.

* **Berendsen** (weak coupling): rescales velocities toward the target every step. Simple, and
  *not* canonical -- it does not sample the true NVT ensemble, only its mean temperature.
* **Langevin**: the O-step of BAOAB, a friction-plus-noise pair that does sample the canonical
  ensemble, at the cost of an extra parameter (the friction `gamma`) that sets how fast memory of
  the old velocity is lost.
* **Nosé–Hoover chain**: an extended-system method with its own conserved quantity (`H = E_tot +
  H_extra`) -- correct sampling *and* a built-in check that the thermostat's own bookkeeping is
  consistent, which is why chapter 08's discipline (trust a record, not a description) applies here
  too.
"""),

    code('''\
import numpy as np

from mdlite.box import Box
from mdlite.integrate import State, velocity_verlet
from mdlite.neighbors import VerletList
from mdlite.pair import LennardJones
from mdlite.thermostats import Berendsen, Langevin, NoseHooverChain


def fcc(n, rho):
    a = (4.0 / rho) ** (1.0 / 3.0)
    base = np.array([[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]) * a
    cells = np.array([[i, j, k] for i in range(n) for j in range(n) for k in range(n)]) * a
    return (cells[:, None, :] + base[None, :, :]).reshape(-1, 3), Box([n * a] * 3)


T_TARGET = 1.0
thermostats = {"Berendsen": Berendsen(T_TARGET, 0.1), "Langevin": Langevin(T_TARGET, 1.0, seed=0),
               "Nose-Hoover": NoseHooverChain(T_TARGET, 0.5)}
runs = {}
for name, thermo in thermostats.items():
    pos, box = fcc(3, 0.8442)
    rng = np.random.default_rng(4)
    vel = rng.normal(0, np.sqrt(2.0), pos.shape)   # start hot (T~2), let each thermostat cool it to 1.0
    vel -= vel.mean(0)
    st = State(pos, vel, 1.0, box)
    rec = velocity_verlet(st, [LennardJones()], dt=0.005, nsteps=1500, nlist=VerletList(box, 2.5), thermostat=thermo, every=10)
    runs[name] = rec
    T_last50 = np.array([r["T"] for r in rec[-50:]])
    print("%-12s final <T> over the last 50 samples: %.3f (target %.1f)" % (name, T_last50.mean(), T_TARGET))
'''),

    code('''\
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6.5, 3.5), dpi=90)
for name, rec in runs.items():
    step = [r["step"] for r in rec]
    T = [r["T"] for r in rec]
    ax.plot(step, T, label=name, lw=1.2)
ax.axhline(T_TARGET, color="k", ls="--", lw=0.8, label="target")
ax.set_xlabel("step"); ax.set_ylabel("T (reduced)"); ax.set_title("cooling to the target under three thermostats")
ax.legend(fontsize=8)
fig.tight_layout()
plt.show()
caption("Temperature against step for the same fcc lattice, started hot (T~2) and cooled by "
        "three thermostats -- Berendsen, Langevin, Nose-Hoover chain -- each converging toward "
        "the target (dashed line) by its own route.")
'''),

    md("""
## The Nosé–Hoover chain's own check

`H = E_tot + H_extra` should stay flat -- if it drifts, the thermostat's half-step bookkeeping is
wrong, independent of whether the temperature looks reasonable.
"""),

    code('''\
pos, box = fcc(3, 0.8442)
rng = np.random.default_rng(5)
vel = rng.normal(0, 1.0, pos.shape)
vel -= vel.mean(0)
st = State(pos, vel, 1.0, box)
nh = NoseHooverChain(1.0, 0.5)
rec_nh = velocity_verlet(st, [LennardJones()], dt=0.002, nsteps=1000, nlist=VerletList(box, 2.5), thermostat=nh, every=10)
H = np.array([r["E_tot"] + r["H_extra"] for r in rec_nh[1:]])
drift = abs(H[-1] - H[0]) / abs(H[0])
print("extended-energy relative drift over %d samples: %.3e" % (len(H), drift))
assert drift < 5e-3
'''),

    md("""
## Against a published reference: NIST's Lennard-Jones NVT table

`data/records/lj_nvt_nist.json` compares `mdlite`'s equilibrium pressure and energy at one NIST
reference state point (`T*=0.85, rho*=0.776`, 500 atoms) to the NIST Standard Reference Simulation
Website's own table -- no LAMMPS involved on either side, which is why `run_or_load` loads it with
`route: "none"` (chapter 00's records cell already showed that distinction).
"""),

    code('''\
import json

with open("../data/records/lj_nvt_nist.json", encoding="utf-8") as f:
    nist = json.load(f)

for prop in ("P", "U"):
    m, ref, ref_err = nist["%s_mdlite" % prop], nist["%s_nist" % prop], nist["%s_nist_err" % prop]
    diff = nist["measured"]["d%s" % prop]
    sigma = diff / ref_err if ref_err else float("inf")
    print("%s: mdlite=%.4f  NIST=%.4f +/- %.4f  |diff|=%.4f  (%.1f sigma)" % (prop, m, ref, ref_err, diff, sigma))
assert nist["measured"]["dP"] < nist["tolerance_P"] and nist["measured"]["dU"] < nist["tolerance_U"]
'''),

    md("""
## The same idea in LAMMPS: `fix nvt`

LAMMPS's own `fix nvt` is a Nosé–Hoover chain, the same physics as `mdlite.thermostats.NoseHooverChain`
above -- record-or-run gives a live number when LAMMPS is present, and the last verified one when it
is not.
"""),

    code('''\
import tempfile

from lammpskill.run import run, run_or_load
from lammpskill.script import Spec, Stage

nvt_spec = Spec(
    units="lj", atom_style="atomic", lattice="fcc 0.8442", region="box block 0 6 0 6 0 6",
    create_box=1, create_atoms="1 box", masses={1: 1.0}, pair_style="lj/cut 2.5", pair_coeffs=["1 1 1.0 1.0 2.5"],
    neighbor="0.3 bin", neigh_modify="every 20 delay 0 check no",
    velocity=["all create 2.0 87287 loop geom"], timestep=0.005,
    fixes=["1 all nvt temp 1.0 1.0 0.5"], thermo=50, thermo_style="custom step temp epair etotal",
    stages=[Stage("run", "1000")], comment="LJ, fix nvt to T*=1.0 from T*=2.0 -- same target as the mdlite runs above",
)


def compute():
    workdir = tempfile.mkdtemp(prefix="ch03_nvt_")
    result = run(nvt_spec, workdir, time_limit=300)
    if not result.ok:
        raise RuntimeError("fix nvt run failed (rc=%s): %s" % (result.returncode, "; ".join(result.errors) or result.stderr))
    t = result.thermo
    temps = t.get("Temp")
    n_tail = max(1, len(temps) // 4)
    return {"natoms": t.natoms, "route": result.installation.route if result.installation else None,
            "lammps_version": result.installation.version if result.installation else None,
            "T_mean_last_quarter": float(temps[-n_tail:].mean()), "T_final": float(temps[-1])}


nvt_rec = run_or_load("lj_nvt_ch03", compute, records_dir="../data/records")
print("source:", nvt_rec["source"])
if nvt_rec["source"] != "skip":
    print("route:", nvt_rec.get("route"), nvt_rec.get("lammps_version"))
    print("LAMMPS fix nvt: <T> over the last quarter of the run = %.3f (target 1.0)" % nvt_rec["T_mean_last_quarter"])
else:
    print("no LAMMPS available and no record yet:", nvt_rec.get("reason"))
'''),

    md("""
## Reading it

- Berendsen reaches the target fastest and samples nothing -- fine for equilibration, wrong for
  production statistics.
- Langevin and Nosé–Hoover both sample the canonical ensemble; Nosé–Hoover additionally hands you a
  conserved quantity to check its own bookkeeping against, which is why LAMMPS's `fix nvt` uses the
  same method.
- The NIST comparison and the `fix nvt` comparison are two different kinds of evidence: one says
  `mdlite`'s equilibrium averages match an independent published table; the other says the same
  target temperature, reached by LAMMPS's implementation of the same algorithm, lands in the same
  place `mdlite`'s does.
"""),
]

TALLY = [
    ("all(abs(np.array([r['T'] for r in rec[-50:]]).mean() - T_TARGET) < 0.15 for rec in runs.values())",
     "all three thermostats brought the system within 0.15 (reduced) of the target temperature"),
    ("drift < 5e-3", "the Nose-Hoover chain's extended energy stayed conserved to 5e-3"),
    ("nist['measured']['dP'] < nist['tolerance_P'] and nist['measured']['dU'] < nist['tolerance_U']",
     "mdlite's NVT state point agrees with the NIST reference table within its recorded tolerance"),
    ("nvt_rec['source'] in ('run', 'record', 'skip')", "run_or_load returned one of its three documented outcomes"),
]
