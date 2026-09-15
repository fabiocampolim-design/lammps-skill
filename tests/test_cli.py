# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Rule 11 (fair CLI) and rule 12 (audit log) for the lammpskill command."""

import json
import os
import sys

import numpy as np

from conftest import FIXTURES
from lammpskill import cli
from lammpskill.install.base import Installation


def test_new_check_and_audit_log(tmp_path, capsys):
    out = tmp_path / "lj"
    logs = str(tmp_path / "logs")
    assert cli.main(["--log-dir", logs, "new", "--preset", "lj_melt", "--out", str(out), "--steps", "10"]) == 0
    assert (out / "in.lammps").exists()
    assert cli.main(["--log-dir", logs, "check", str(out / "in.lammps")]) == 0
    text = capsys.readouterr().out
    assert "C13" in text or "info" in text
    lines = (tmp_path / "logs" / "lammpskill-audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["command"] == "new"


def test_new_bead_spring_chain_writes_both_the_script_and_its_data_file(tmp_path):
    """bead_spring_chain, like spce_water, returns (Spec, DataFile) and needs --out as its
    workdir so `new` can write chain.data alongside in.lammps."""
    out = tmp_path / "chain"
    assert cli.main(["new", "--preset", "bead_spring_chain", "--out", str(out), "--n", "10"]) == 0
    assert (out / "in.lammps").exists() and (out / "chain.data").exists()
    text = (out / "in.lammps").read_text(encoding="utf-8")
    assert "read_data chain.data" in text and "bond_style harmonic" in text


def test_check_exit_code_is_one_on_errors(tmp_path):
    bad = tmp_path / "bad.in"
    bad.write_text("units lj\natom_style atomic\npair_coeff * * 1 1\npair_style lj/cut 2.5\nrun 10\n", encoding="utf-8")
    assert cli.main(["--log-dir", str(tmp_path / "l"), "check", str(bad)]) == 1


def test_log_to_csv_and_dump_info(tmp_path, capsys):
    csv = tmp_path / "t.csv"
    assert cli.main(["log", os.path.join(FIXTURES, "log_lj_melt.lammps"), "--csv", str(csv)]) == 0
    rows = csv.read_text(encoding="utf-8").strip().splitlines()
    assert rows[0].startswith("Step,") and len(rows) == 7
    d = tmp_path / "d.dump"
    d.write_text("ITEM: TIMESTEP\n0\nITEM: NUMBER OF ATOMS\n1\nITEM: BOX BOUNDS pp pp pp\n0 1\n0 1\n0 1\nITEM: ATOMS id type x y z\n1 1 0.5 0.5 0.5\n", encoding="utf-8")
    assert cli.main(["dump", str(d), "--info"]) == 0
    assert "1 frame" in capsys.readouterr().out


def test_detect_json_and_run_with_fake(tmp_path, monkeypatch, capsys):
    stub = tmp_path / "stub.py"
    stub.write_text('import sys\ni=sys.argv.index("-log"); open(sys.argv[i+1],"w").write("LAMMPS (0 Jan 2000)\\n   Step          Temp\\n         0   1\\n        10   1\\nLoop time of 0.1 on 1 procs for 10 steps with 8 atoms\\n")\n', encoding="utf-8")
    inst = Installation(route="fake", host="windows", executable=str(stub), version="0 Jan 2000", packages=(), mpi=False, omp=False,
                        library=None, python_module=False, launch=(sys.executable,), distro=None, python=None)
    monkeypatch.setattr(cli, "_detect", lambda routes=None: [inst])
    assert cli.main(["detect", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["route"] == "fake"
    case = tmp_path / "case"
    cli.main(["new", "--preset", "lj_melt", "--out", str(case), "--steps", "10"])
    assert cli.main(["run", str(case), "--route", "fake"]) == 0
    assert "Step" in capsys.readouterr().out


def test_rdf_from_dump(tmp_path):
    rng = np.random.default_rng(0)
    n = 200
    pos = rng.uniform(0, 10, (n, 3))
    lines = ["ITEM: TIMESTEP", "0", "ITEM: NUMBER OF ATOMS", str(n), "ITEM: BOX BOUNDS pp pp pp", "0 10", "0 10", "0 10", "ITEM: ATOMS id type x y z"]
    lines += ["%d 1 %f %f %f" % (i + 1, *pos[i]) for i in range(n)]
    d = tmp_path / "r.dump"
    d.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = tmp_path / "g.csv"
    assert cli.main(["rdf", str(d), "--nbins", "20", "--out", str(out)]) == 0
    rows = out.read_text(encoding="utf-8").strip().splitlines()
    assert rows[0] == "r,g" and len(rows) == 21
