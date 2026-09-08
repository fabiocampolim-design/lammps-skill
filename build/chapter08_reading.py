# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Chapter 08 — Reading What LAMMPS Writes. Runs with no LAMMPS installed: every cell reads a
fixture already committed under tests/fixtures/ or a short literal written the same way the io
tests write theirs. Nothing here is copied from an upstream example (rule 7) -- these are outputs
this project produced, or synthetic text in the format LAMMPS documents."""

from nbbuild import code, md

CELLS = [
    md("""
## Four files, one job each

LAMMPS writes four kinds of file this toolkit reads back: a **data** file (the starting structure,
`write_data`/`read_data`), a **dump** (a trajectory, `dump`/`dump_modify`), a **log** (everything
printed to screen, in one of three thermo styles), and a **restart** (a binary checkpoint,
`write_restart`/`read_restart`). Each parser lives in `lammpskill/io/`, was written from the
manual's description of the format plus files LAMMPS actually wrote on this machine, and every
example below is a fixture already committed to the test suite -- reading it needs no LAMMPS.

Four of the parsers exist *because* a first version got the format wrong in a way that changed a
result silently. This chapter shows each one: what was assumed, what was actually true, and the
test that now pins it down.
"""),

    md("""
## Data files: the starting structure

`read_data` returns a `DataFile`: a box, per-type masses, and one array per atom column (`id`,
`type`, `x`, `y`, `z`, ...). The fixture below is a real `write_data` output from a 4000-atom LJ
melt.
"""),

    code('''\
from lammpskill.io.data import read_data

df = read_data("../tests/fixtures/data_lj_melt.data")
print("comment  :", df.comment)
print("natoms   :", df.natoms, "| ntypes:", df.ntypes, "| atom_style:", df.atom_style)
print("box      :", df.box.lo, "->", df.box.hi, "| volume", round(df.box.volume, 3))
print("first 3 ids/types:", df.ids[:3], df.types[:3])
'''),

    md("""
## Dump files: xs is not x

A dump can print unscaled (`x y z`), unwrapped (`xu yu zu`) or *scaled* (`xs ys zs`) coordinates,
and the header names which one it holds. `Frame.positions` picks the right conversion by reading
the column names, so a frame written with `xs ys zs` still comes back in the box's own units.
Frames are also re-sorted by atom id: LAMMPS writes them in whatever order the last neighbour list
put them in, and two frames of the same trajectory need not agree.
"""),

    code('''\
import os
import tempfile

from lammpskill.io.dump import read_dump

# a two-frame dump, written in the ITEM: format the manual documents. Frame 0 is unscaled and out
# of id order (2 then 1); frame 1 is scaled (xs ys zs) in a 10x10x10 box.
TWO_FRAME_DUMP = """ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id type x y z
2 1 5 5 5
1 1 1 1 1
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
fd, dump_path = tempfile.mkstemp(suffix=".dump")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write(TWO_FRAME_DUMP)
try:
    traj = read_dump(dump_path)
finally:
    os.remove(dump_path)
print("timesteps:", traj.timesteps)
print("frame 0 positions (already sorted by id, unscaled):\\n", traj.positions[0])
print("frame 1 positions (xs*10 -> cartesian):\\n", traj.positions[1])
'''),

    md("""
## N-5: the dump's default float format cost two orders of magnitude

`dump custom` writes floats with six significant digits by default -- enough to plot, not enough to
cross-check a force against an independent code. The first LJ-melt comparison of `mdlite` against
LAMMPS forces landed at 5e-5 and stalled there for the wrong reason: the *comparison* was fine, the
*dump* was truncating. Adding `dump_modify ... format float %20.15g` to the case script -- not a
change to the parser -- took the same comparison to round-off.
"""),

    code('''\
import json

with open("../data/records/lj_energy_vs_lammps.json", encoding="utf-8") as f:
    rec = json.load(f)
print("force max-diff with the wide dump format:", rec["measured"]["dF"])
print("tolerance:                                ", rec["tolerance_force"])
print("why:", rec["provenance"]["why"])
assert rec["measured"]["dF"] < 1e-4, "the default 6-digit dump format; a decade or two above this"
'''),

    md("""
## Log files: three thermo styles, and the one the first parser missed

`thermo_style` has three faces in a log file: `one` (a header line, then columns -- the common
case), `yaml` (a fenced YAML block, easy to parse and easy to over-trust), and `multi` (one block
per timestep, four `Name = value` pairs to a line, framed by a `---- Step N ----` banner). `parse_log`
learned `one` and `yaml` first; `multi` was still being read as "no thermo output" when
`bench/in.rhodo` -- which uses it -- ran for 42 real seconds and was scored a failure anyway (N-18).
The fixture below is the same shape `in.rhodo`'s log has.
""" ),

    code('''\
from lammpskill.io.log import parse_log

MULTI_LOG = """LAMMPS (22 Jul 2025 - Update 6)
Per MPI rank memory allocation (min/avg/max) = 49.25 | 49.35 | 49.64 Mbytes
------------- Step              0 ----- CPU =            0 (sec) -------------
TotEng   =    -25356.2057 KinEng   =     21444.8313 Temp     =       299.0397
PotEng   =    -46801.0370 E_bond   =      2537.9940 E_angle  =     10921.3742
E_dihed  =      5211.7865 E_impro  =       213.5116 E_vdwl   =     -2307.8634
E_coul   =    207025.8934 E_long   =   -270403.7333 Press    =      -149.3300
Volume   =    307995.0335
------------- Step             50 ----- CPU =     15.07474 (sec) -------------
TotEng   =    -25330.0307 KinEng   =     21501.0009 Temp     =       299.8229
PotEng   =    -46831.0316 E_bond   =      2471.7035 E_angle  =     10836.5102
E_dihed  =      5239.6319 E_impro  =       227.1218 E_vdwl   =     -1993.2873
E_coul   =    206797.6807 E_long   =   -270410.3925 Press    =       237.6572
Volume   =    308031.6762
Loop time of 42.1 on 4 procs for 100 steps with 32000 atoms
Total wall time: 0:00:42
"""
lf = parse_log(MULTI_LOG)
run = lf.runs[0]
print("columns  :", run.columns)
print("last row :", run.last)
print("loop_time:", run.loop_time, "| nprocs:", run.nprocs, "| natoms:", run.natoms)
'''),

    md("""
## N-4: `thermo_modify norm` defaults to per-atom in `units lj`

The very first LJ cross-check compared `-6.04` (LAMMPS, `units lj`, per-atom energy -- the reduced
units default) with `-1545.7` (`mdlite`, total energy for the same 256 atoms). Nothing was wrong
with either number: `256 * -6.04 = -1546`, within rounding of `-1545.7`. `units lj` normalises
thermo output *per atom* unless the script says `thermo_modify norm no`; every case this toolkit
builds now sets it explicitly rather than relying on the default.
"""),

    code('''\
per_atom_energy = -6.04
natoms = 256
total_from_lammps_default = per_atom_energy * natoms
mdlite_total = -1545.7382640088708   # from the record read above
print("LAMMPS default (per-atom) x natoms:", total_from_lammps_default)
print("mdlite (already total)           :", mdlite_total)
print("agree once you know which is which:", abs(total_from_lammps_default - mdlite_total) < 1.0)
'''),

    md("""
## Restart headers: a 15-byte magic string in a 16-byte field

Restart files are binary and the manual says the format is not documented or portable -- this
toolkit reads only the header (magic string, endianness flag, version string) and leaves everything
else to LAMMPS itself via `read_restart` + `write_data`. The magic string is the 15 printable
characters `LammpS RestartT`, but LAMMPS writes it as a **16-byte NUL-terminated** field on disk;
the first header reader read only 15 bytes and never consumed the terminator, so the next field
(the endianness flag) was read one byte out of alignment and decoded as garbage on every restart.
Reading `len(MAGIC) + 1` bytes for the magic check -- comparing the 15 printable bytes, then
stepping past the 16th -- is the fix.
"""),

    code('''\
from lammpskill.io.restart import MAGIC

print("magic bytes:", MAGIC, "| length:", len(MAGIC), "| on-disk field:", len(MAGIC) + 1, "bytes (NUL-terminated)")
assert len(MAGIC) == 15, "the printable magic string itself"
'''),

    md("""
## EAM potential files: read, write, and a synthetic one for testing

`setfl`/`funcfl` EAM files are plain text tables (`F(rho)`, `rho(r)`, `r*phi(r)`, one grid per
element and per element pair). `synthetic_setfl` builds a physically reasonable one from a closed
form so tests -- and this chapter -- never need to fetch or ship a real potential file (rule 7:
potentials are the user's to obtain).
"""),

    code('''\
import os
import tempfile

from lammpskill.io.potential import read_eam_setfl, synthetic_setfl, write_eam_setfl

s = synthetic_setfl(element="Cu", nr=200, nrho=150)
fd, eam_path = tempfile.mkstemp(suffix=".eam.alloy")
os.close(fd)
try:
    write_eam_setfl(s, eam_path)
    back = read_eam_setfl(eam_path)
finally:
    os.remove(eam_path)
print("elements:", back.elements, "| grid: nr=%d nrho=%d | cutoff=%.3f" % (back.nr, back.nrho, back.cutoff))
print("F(rho) shape:", back.F.shape, "| rho(r) shape:", back.rho.shape, "| r*phi(r) shape:", back.rphi.shape)
'''),

    md("""
## What this cost, in one table

| finding | file kind | the wrong assumption | the fix |
|---|---|---|---|
| N-4 | log | `units lj` thermo output is already a total | `thermo_modify norm no` in every case script |
| N-5 | dump | the default 6-digit float format is precise enough for a force cross-check | `dump_modify ... format float %20.15g`; 5e-5 -> 3e-13 |
| N-6 | restart | reading 15 bytes for the magic string consumes the string but not its NUL terminator | read 16 bytes (`len(MAGIC) + 1`) so the next field starts aligned |
| N-18 | log | `parse_log` understood `one` and `yaml` | added the `multi` block reader (`_multi_block`) |

Every row has a test: `tests/test_io_log.py`, `tests/test_io_potential.py::test_restart_header_from_lammps`,
and `data/records/lj_energy_vs_lammps.json`.
"""),
]

TALLY = [
    ("df.natoms == 4000 and df.ntypes == 1", "the data fixture parsed to the recorded atom count"),
    ("list(traj.timesteps) == [0, 100]", "both dump frames were read, in timestep order"),
    ("run.columns[:3] == ['Step', 'CPU', 'TotEng'] and run.last['Volume'] == 308031.6762",
     "the multi-style thermo block (N-18) was parsed into columns and rows"),
    ("len(MAGIC) == 15", "the restart magic string; the on-disk field is one byte longer, a NUL terminator (N-6)"),
    ("back.F.shape == s.F.shape and back.rho.shape == s.rho.shape",
     "the synthetic EAM setfl round-tripped through write_eam_setfl/read_eam_setfl"),
]
