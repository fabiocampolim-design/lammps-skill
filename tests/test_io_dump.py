# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
import gzip

import numpy as np

from lammpskill.io.box import Box
from lammpskill.io.dump import Frame, iter_dump, read_dump, write_dump

DUMP = """ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id type x y z vx vy vz
2 1 5 5 5 0.1 0 0
1 1 1 1 1 0 0.2 0
ITEM: TIMESTEP
100
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id type xs ys zs
1 1 0.2 0.2 0.2
2 1 0.6 0.6 0.6
"""


def test_two_frames_ordering_by_id_and_scaled_coordinates(tmp_path):
    p = tmp_path / "d.dump"
    p.write_text(DUMP, encoding="utf-8")
    tr = read_dump(str(p))
    assert tr.timesteps == [0, 100] and tr.frames[0].natoms == 2
    f0 = tr.frames[0]
    assert f0.boundary == ("pp", "pp", "pp") and f0.columns[-1] == "vz"
    np.testing.assert_allclose(tr.positions[0], [[1, 1, 1], [5, 5, 5]])       # ordered by id
    np.testing.assert_allclose(tr.positions[1], [[2, 2, 2], [6, 6, 6]])       # xs -> cartesian
    assert f0.box.volume == 1000.0


def test_every_and_max_frames_and_gzip(tmp_path):
    p = tmp_path / "d.dump.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(DUMP * 3)
    assert len(read_dump(str(p)).frames) == 6
    assert read_dump(str(p), every=2).timesteps == [0, 0, 0]
    assert len(read_dump(str(p), max_frames=1).frames) == 1
    assert sum(1 for _ in iter_dump(str(p))) == 6


def test_write_then_read_round_trip(tmp_path):
    box = Box(0, 4, 0, 4, 0, 4)
    fr = Frame(timestep=7, natoms=2, box=box, boundary=("pp", "pp", "ff"), columns=["id", "type", "x", "y", "z"],
               data=np.array([[1, 1, 0.5, 0.5, 0.5], [2, 2, 1.5, 1.5, 1.5]]))
    p = tmp_path / "w.dump"
    write_dump([fr], str(p))
    back = read_dump(str(p)).frames[0]
    assert back.timestep == 7 and back.boundary == ("pp", "pp", "ff") and back.columns == fr.columns
    np.testing.assert_allclose(back.data, fr.data)


def test_triclinic_bounds_are_read(tmp_path):
    txt = DUMP.split("ITEM: TIMESTEP\n100")[0].replace("BOX BOUNDS pp pp pp\n0 10\n0 10\n0 10",
                                                       "BOX BOUNDS xy xz yz pp pp pp\n0 10 1\n0 10 0\n0 10 0")
    p = tmp_path / "t.dump"
    p.write_text(txt, encoding="utf-8")
    fr = read_dump(str(p)).frames[0]
    # manual: xlo_bound = xlo + min(0,xy,xz,xy+xz), xhi_bound = xhi + max(0,xy,xz,xy+xz)
    assert fr.box.is_triclinic and fr.box.xy == 1.0 and fr.box.xlo == 0.0 and fr.box.xhi == 9.0


def test_dump_written_by_lammps_is_read(lammps_exe, tmp_path):
    from lammpskill.install.base import LJ_MELT_TEXT, run_command
    text = LJ_MELT_TEXT.format(steps=20).replace("run             20", "dump d all custom 10 d.dump id type x y z vx vy vz\nrun 20")
    (tmp_path / "in.d").write_text(text, encoding="utf-8")
    p = run_command(lammps_exe, ["-in", "in.d", "-log", "log.d", "-screen", "none"], cwd=str(tmp_path), timeout=120)
    assert p.returncode == 0, p.stderr
    tr = read_dump(str(tmp_path / "d.dump"))
    assert tr.timesteps == [0, 10, 20] and tr.frames[0].natoms == 4000 and tr.positions.shape == (3, 4000, 3)
