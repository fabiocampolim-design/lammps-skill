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


# thermo_style multi, exactly as bench/in.rhodo produced it here on 2026-09-06 (finding N-18:
# the parser knew `one` and `yaml` only, so a 42 s rhodo run was scored "no thermo output").
MULTI = """LAMMPS (22 Jul 2025 - Update 6)
Per MPI rank memory allocation (min/avg/max) = 49.25 | 49.35 | 49.64 Mbytes
------------ Step              0 ----- CPU =            0 (sec) -------------
TotEng   =    -25356.2057 KinEng   =     21444.8313 Temp     =       299.0397
PotEng   =    -46801.0370 E_bond   =      2537.9940 E_angle  =     10921.3742
E_dihed  =      5211.7865 E_impro  =       213.5116 E_vdwl   =     -2307.8634
E_coul   =    207025.8934 E_long   =   -270403.7333 Press    =      -149.3300
Volume   =    307995.0335
------------ Step             50 ----- CPU =     15.07474 (sec) -------------
TotEng   =    -25330.0307 KinEng   =     21501.0009 Temp     =       299.8229
PotEng   =    -46831.0316 E_bond   =      2471.7035 E_angle  =     10836.5102
E_dihed  =      5239.6319 E_impro  =       227.1218 E_vdwl   =     -1993.2873
E_coul   =    206797.6807 E_long   =   -270410.3925 Press    =       237.6572
Volume   =    308031.6762
Loop time of 42.1 on 4 procs for 100 steps with 32000 atoms
Total wall time: 0:00:42
"""


def test_multi_style_block_is_parsed_into_columns_and_rows():
    lf = parse_log(MULTI)
    assert len(lf.runs) == 1
    run = lf.runs[0]
    assert run.columns[:3] == ["Step", "CPU", "TotEng"]
    assert "Volume" in run.columns and "E_long" in run.columns
    assert run.data.shape == (2, len(run.columns))
    assert run.last["Step"] == 50
    assert run.last["TotEng"] == -25330.0307
    assert run.last["Volume"] == 308031.6762
    assert run.last["CPU"] == 15.07474
    assert run.loop_time == 42.1 and run.nprocs == 4 and run.nsteps == 100 and run.natoms == 32000


def test_multi_style_does_not_disturb_a_one_style_log():
    lf = parse_log(MULTI + "\nStep Temp\n0 1.0\n1 2.0\nLoop time of 1 on 1 procs for 1 steps with 2 atoms\n")
    assert len(lf.runs) == 2
    assert lf.runs[1].columns == ["Step", "Temp"]
