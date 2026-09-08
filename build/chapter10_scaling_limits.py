# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Chapter 10 — Scaling and Limits. Needs LAMMPS; the measurement itself is bounded by how many
cores this session is allowed to use (KEEP rules/13 compute-sharing), and the chapter says so."""

from nbbuild import code, md

CELLS = [
    md("""
## Where speed-up stops, and why this measurement is itself limited

Parallel speed-up is not free above some rank count: communication between MPI ranks (or threads)
costs time that grows with how many of them there are, so past some point adding ranks buys less
than it costs. This chapter measures that on the one case it can actually run -- and the honest
first thing to say is *how much of the machine it was allowed to use*: this session claimed 2 CPU
cores under this project's compute-sharing policy (`KEEP/compute.py`, rules/13) because other
sessions were active on the same host at the time. The host itself has more cores than that; this
measurement does not speak to full-machine scaling, only to 1 vs 2.
"""),

    md("""
## The case: an LJ melt, run at 1 and 2 MPI ranks

Same case as chapter 01 (4000 atoms), more steps (1000) so the timing signal is not dominated by
start-up.
"""),

    code('''\
import tempfile

from lammpskill.run import run, run_or_load
from lammpskill.script import Stage, lj_melt

scaling_spec = lj_melt(steps=1000)
scaling_spec.thermo = 500   # a coarser thermo interval; the point of this run is wall time, not thermo output


def compute():
    inst = next((i for i in INSTALLATIONS if i.executable and not i.extra.get("pinned")), None)
    if inst is None:
        raise RuntimeError("no LAMMPS installation usable for the scaling measurement")

    def one(nprocs):
        workdir = tempfile.mkdtemp(prefix="ch10_scale_%d_" % nprocs)
        r = run(scaling_spec, workdir, installation=inst, mpi=nprocs, time_limit=300)
        if not r.ok:
            raise RuntimeError("mpi=%d run failed: %s" % (nprocs, r.errors or r.stderr))
        return r.thermo.loop_time

    t1 = one(1)
    t2 = one(2)
    out = {"route": inst.route, "lammps_version": inst.version, "mpi_available": inst.mpi,
           "loop_time_1proc": t1, "loop_time_2proc": t2, "speedup_2proc": t1 / t2 if t2 else None}

    if inst.omp:
        workdir = tempfile.mkdtemp(prefix="ch10_scale_omp2_")
        r = run(scaling_spec, workdir, installation=inst, omp=2, time_limit=300)
        if r.ok:
            out["loop_time_omp2"] = r.thermo.loop_time
            out["speedup_omp2"] = t1 / r.thermo.loop_time if r.thermo.loop_time else None
    else:
        out["loop_time_omp2"] = None
    return out


rec = run_or_load("lj_scaling_ch10", compute, records_dir="../data/records")
print("source:", rec["source"])
'''),

    code('''\
if rec["source"] != "skip":
    print("route: %s (%s), MPI available: %s" % (rec["route"], rec["lammps_version"], rec["mpi_available"]))
    print("loop time, 1 MPI rank: %.3f s" % rec["loop_time_1proc"])
    print("loop time, 2 MPI ranks: %.3f s  (speed-up: %.2fx, ideal would be 2.00x)"
          % (rec["loop_time_2proc"], rec["speedup_2proc"]))
    if rec.get("loop_time_omp2") is not None:
        print("loop time, 2 OpenMP threads: %.3f s  (speed-up: %.2fx)" % (rec["loop_time_omp2"], rec["speedup_omp2"]))
    else:
        print("OpenMP: not available in this build (Installation.omp is False) -- honestly, not measured")
else:
    print("no LAMMPS available and no record yet:", rec.get("reason"))
'''),

    md("""
## Reading the number, not just printing it

2x is the ideal; this system is small (4000 atoms) and the run is short, so MPI's per-rank
overhead (domain decomposition, communicating the boundary between two halves of a small box) is a
real fraction of the total time, not a rounding error. A speed-up well under 2x here is not a bug --
it is what small-system, low-rank-count scaling actually looks like, and it is exactly why the
bench cases in `docs/04` use 32000 atoms rather than 4000: at that size, communication is a smaller
fraction of the work and speed-up tracks closer to ideal.
"""),

    md("""
## What this machine cannot do, said honestly

- **No GPU.** Every route on this machine (`references/platforms.md`) is CPU-only; GPU and KOKKOS-
  CUDA are out of scope by hardware, not by choice.
- **No `-partition` methods.** NEB, TAD, PRD and other replica-based methods need LAMMPS launched
  with `-partition`, splitting ranks into independent partitions. `docs/04`'s examples sweep runs one
  process and correctly reports these as errors, not passes -- N-15's lesson (LAMMPS exits 0 after a
  fatal error) applies here too: a `-partition` method run without `-partition` does not silently
  degrade, it fails, and the sweep has to say so rather than call it a success.
- **This chapter's own ceiling.** The 1-vs-2-rank measurement above is what this session's compute
  claim allowed, not what the host's full core count would show. A future run with a larger claim
  (or run when the host is otherwise idle) could extend this table -- the honest thing this chapter
  can say today is what it actually measured, not what a bigger claim might have shown.
"""),
]

TALLY = [
    ("rec['source'] in ('run', 'record', 'skip')", "run_or_load returned one of its three documented outcomes"),
]
