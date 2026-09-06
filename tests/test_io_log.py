# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
import os

import numpy as np

from conftest import FIXTURES
from lammpskill.io.log import parse_log, read_log

YAML_LOG = """LAMMPS (1 Jan 2000)
---
keywords: ['Step', 'Temp', 'PotEng', ]
data:
  - [0, 3, -6.7733681, ]
  - [50, 1.6758903, -4.7955425, ]
...
Loop time of 0.1 on 1 procs for 50 steps with 100 atoms
"""

TWO_RUNS = """LAMMPS (1 Jan 2000)
Created 8 atoms
WARNING: something benign (src/x.cpp:1)
   Step          Temp          E_pair
         0   1.0           -1.5
        10   0.9           -1.4
Loop time of 0.01 on 1 procs for 10 steps with 8 atoms

   Step          Temp          E_pair         Press
        10   0.9           -1.4            0.2
        20   0.8           -1.3            0.1
Loop time of 0.02 on 2 procs for 10 steps with 8 atoms
ERROR: Unknown command: bogus (src/input.cpp:1)
"""


def test_fixture_log_has_one_run_with_six_rows_and_the_custom_columns():
    lf = read_log(os.path.join(FIXTURES, "log_lj_melt.lammps"))
    assert lf.version and len(lf.runs) == 1
    t = lf.thermo
    assert t.columns[:2] == ["Step", "Temp"] and t.data.shape == (6, 6)
    assert t.get("Step")[0] == 0 and t.get("Step")[-1] == 250
    assert t.loop_time is not None and t.natoms == 4000 and t.nsteps == 250
    assert lf.natoms == 4000 and lf.errors == []


def test_two_runs_warnings_errors_and_columns_per_run():
    lf = parse_log(TWO_RUNS)
    assert len(lf.runs) == 2
    assert lf.runs[0].columns == ["Step", "Temp", "E_pair"] and lf.runs[1].columns[-1] == "Press"
    assert lf.runs[1].nprocs == 2
    assert lf.warnings == ["WARNING: something benign (src/x.cpp:1)"]
    assert lf.errors == ["ERROR: Unknown command: bogus (src/input.cpp:1)"]
    assert lf.thermo.last == {"Step": 20.0, "Temp": 0.8, "E_pair": -1.3, "Press": 0.1}


def test_yaml_style_block():
    lf = parse_log(YAML_LOG)
    assert lf.thermo.columns == ["Step", "Temp", "PotEng"]
    np.testing.assert_allclose(lf.thermo.get("PotEng"), [-6.7733681, -4.7955425])
    assert lf.thermo.natoms == 100


def test_no_thermo_raises_a_clear_error():
    lf = parse_log("LAMMPS (1 Jan 2000)\nTotal wall time: 0:00:00\n")
    assert lf.runs == []
    try:
        lf.thermo
    except ValueError as e:
        assert "no thermo" in str(e)
    else:
        raise AssertionError("expected ValueError")
