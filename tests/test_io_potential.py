# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
import numpy as np
import pytest

from lammpskill.io.potential import EAMSetfl, read_eam_setfl, synthetic_setfl, write_eam_setfl
from lammpskill.io.restart import read_restart_header


def test_synthetic_setfl_round_trip(tmp_path):
    s = synthetic_setfl(element="Xx", nr=200, nrho=150)
    assert s.F.shape == (1, 150) and s.rho.shape == (1, 200) and s.rphi.shape == (1, 200)
    p = tmp_path / "Xx.eam.alloy"
    write_eam_setfl(s, str(p))
    b = read_eam_setfl(str(p))
    assert b.elements == ["Xx"] and b.nr == 200 and b.nrho == 150 and abs(b.cutoff - s.cutoff) < 1e-12
    np.testing.assert_allclose(b.F, s.F, rtol=1e-10)
    np.testing.assert_allclose(b.rphi, s.rphi, rtol=1e-10)
    assert b.pair_index(0, 0) == 0 and b.r[1] - b.r[0] == pytest.approx(b.dr)


def test_two_element_pair_order():
    a = synthetic_setfl(element="Aa")
    b = synthetic_setfl(element="Bb")
    s = EAMSetfl(comments=["", "", ""], elements=["Aa", "Bb"], nrho=a.nrho, drho=a.drho, nr=a.nr, dr=a.dr, cutoff=a.cutoff,
                 atomic_number=[1, 2], mass=[1.0, 2.0], lattice_constant=[1.0, 1.0], lattice=["fcc", "fcc"],
                 F=np.vstack([a.F, b.F]), rho=np.vstack([a.rho, b.rho]), rphi=np.vstack([a.rphi, a.rphi, b.rphi]))
    assert s.pair_index(0, 0) == 0 and s.pair_index(1, 0) == 1 and s.pair_index(0, 1) == 1 and s.pair_index(1, 1) == 2


def test_restart_header_rejects_non_restart(tmp_path):
    p = tmp_path / "x.restart"
    p.write_bytes(b"not a restart")
    with pytest.raises(ValueError, match="not a LAMMPS restart"):
        read_restart_header(str(p))


def test_restart_header_from_lammps(lammps_exe, tmp_path):
    from lammpskill.install.base import LJ_MELT_TEXT, run_command
    (tmp_path / "in.r").write_text(LJ_MELT_TEXT.format(steps=10) + "write_restart r.restart\n", encoding="utf-8")
    p = run_command(lammps_exe, ["-in", "in.r", "-log", "log.r", "-screen", "none"], cwd=str(tmp_path), timeout=120)
    assert p.returncode == 0, p.stderr
    h = read_restart_header(str(tmp_path / "r.restart"))
    head = (tmp_path / "r.restart").read_bytes()[:64]
    assert h["magic"].startswith("LammpS Restart") and h["version"], head


def test_synthetic_potential_is_accepted_by_lammps(lammps_exe, tmp_path):
    from lammpskill.install.base import run_command
    s = synthetic_setfl(element="Xx")
    write_eam_setfl(s, str(tmp_path / "Xx.eam.alloy"))
    (tmp_path / "in.e").write_text(
        "units metal\natom_style atomic\nlattice fcc 4.0\nregion b block 0 3 0 3 0 3\ncreate_box 1 b\ncreate_atoms 1 box\n"
        "mass 1 1.0\npair_style eam/alloy\npair_coeff * * Xx.eam.alloy Xx\nthermo_style custom step pe\nrun 0\n", encoding="utf-8")
    p = run_command(lammps_exe, ["-in", "in.e", "-log", "log.e", "-screen", "none"], cwd=str(tmp_path), timeout=120)
    assert p.returncode == 0, p.stderr + (tmp_path / "log.e").read_text(errors="replace")
