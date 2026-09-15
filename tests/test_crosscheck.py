# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""S4: the residue between mdlite and LAMMPS is measured, stored in data/records, and the test reads the tolerance from the
record — never from a literal here. Without LAMMPS the records still exist (committed) and the test checks them."""

import json
import os

import pytest

from conftest import ROOT

RECORDS = os.path.join(ROOT, "data", "records")


def _rec(name):
    p = os.path.join(RECORDS, name + ".json")
    if not os.path.exists(p):
        pytest.skip("record %s not yet produced (scripts/run_benchmarks.py)" % name)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def test_lj_energy_vs_lammps_record_is_within_its_own_tolerance():
    r = _rec("lj_energy_vs_lammps")
    assert r["provenance"]["lammps_version"] and r["provenance"]["route"]
    assert abs(r["energy_mdlite"] - r["energy_lammps"]) <= r["tolerance_energy"]
    assert r["force_maxdiff"] <= r["tolerance_force"]


def test_lj_nvt_vs_nist_record():
    r = _rec("lj_nvt_nist")
    for q in ("P", "U"):
        assert abs(r[q + "_mdlite"] - r[q + "_nist"]) <= r["tolerance_" + q], q


def test_eam_cu_lattice_record():
    r = _rec("eam_cu_lattice")
    assert abs(r["a0_mdlite"] - r["a0_lammps"]) <= r["tolerance_a0"]
    assert abs(r["ecoh_mdlite"] - r["ecoh_lammps"]) <= r["tolerance_ecoh"]


def test_eam_cu_vacancy_record():
    r = _rec("eam_cu_vacancy")
    assert abs(r["e_formation_mdlite"] - r["e_formation_lammps"]) <= r["tolerance_E"]
    # exactly one atom removed on each side, or the two engines built different systems
    assert r["natoms_vacancy_lammps"] == r["natoms_perfect"] - 1


def test_polymer_vs_lammps_record_is_within_its_own_tolerance():
    r = _rec("polymer_vs_lammps")
    assert abs(r["energy_mdlite"] - r["energy_lammps"]) <= r["tolerance_energy"]
    assert r["force_maxdiff"] <= r["tolerance_force"]
    assert r["nbonds"] == r["natoms"] - 1   # one linear chain: n beads, n-1 bonds


def test_records_carry_measured_residue_and_a_reason():
    for name in ("lj_energy_vs_lammps", "lj_nvt_nist", "eam_cu_lattice", "eam_cu_vacancy", "polymer_vs_lammps"):
        r = _rec(name)
        assert "measured" in r and "why" in r["provenance"] and r["provenance"]["date"]
