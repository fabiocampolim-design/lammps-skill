# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
import verify_lammps


def test_main_without_lammps_passes_and_with_requirement_fails_when_absent(monkeypatch, capsys):
    monkeypatch.setattr(verify_lammps, "detect_lammps", lambda **kw: [])
    assert verify_lammps.main(["--no-lammps"]) == 0
    assert verify_lammps.main(["--require-lammps"]) == 1
    out = capsys.readouterr().out
    assert "ALL CHECKS PASSED" in out and "FAILED" in out


def test_quiet_prints_one_line(monkeypatch, capsys):
    monkeypatch.setattr(verify_lammps, "detect_lammps", lambda **kw: [])
    verify_lammps.main(["-q", "--no-lammps"])
    assert len(capsys.readouterr().out.strip().splitlines()) == 1


def test_table_out_appends_markdown_rows(monkeypatch, tmp_path):
    from lammpskill.install.base import Installation, ProbeReport
    inst = Installation(route="fake", host="windows", executable="x", version="1 Jan 2000", packages=("A", "B"),
                        mpi=False, omp=False, library=None, python_module=False, launch=(), distro=None, python=None)
    monkeypatch.setattr(verify_lammps, "detect_lammps", lambda **kw: [inst])
    monkeypatch.setattr(verify_lammps.base, "probe", lambda i, w, steps=250: ProbeReport(True, 1.25, 4000, {"Step": 250}, "", None))
    out = tmp_path / "t.md"
    assert verify_lammps.main(["--probe", "--table-out", str(out), "--outdir", str(tmp_path)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "| fake | windows | 1 Jan 2000 |" in text and "| 1.25 |" in text
