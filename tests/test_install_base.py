# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
import os
import subprocess
import sys

import pytest

from conftest import FIXTURES
from lammpskill.install import base


def _help():
    with open(os.path.join(FIXTURES, "lmp_help_wsl_apt.txt"), encoding="utf-8") as f:
        return f.read()


def test_parse_help_reads_version_packages_and_mpi_from_the_apt_fixture():
    info = base.parse_help(_help())
    assert info["version"] and info["version"][0].isdigit()
    assert "MOLECULE" in info["packages"] and info["packages"] == tuple(sorted(info["packages"]))
    assert isinstance(info["mpi"], bool) and isinstance(info["omp"], bool)
    assert "Atom styles" in info["styles"] and "atomic" in info["styles"]["Atom styles"]


def test_parse_help_on_garbage_gives_empty_fields():
    info = base.parse_help("not a lammps help text")
    assert info["version"] == "" and info["packages"] == () and info["mpi"] is False


@pytest.mark.parametrize("win,posix", [
    (r"C:\Users\x\runs\a", "/mnt/c/Users/x/runs/a"),
    ("D:/claude-bulk/LAMMPS", "/mnt/d/claude-bulk/LAMMPS"),
    ("/home/u/runs", "/home/u/runs"),
])
def test_to_wsl_path(win, posix):
    assert base.to_wsl_path(win) == posix


def _fake_installation(tmp_path, body):
    stub = tmp_path / "fake_lmp.py"
    stub.write_text(body, encoding="utf-8")
    return base.Installation(route="fake", host="windows", executable=str(stub), version="0 Jan 2000",
                             packages=("MOLECULE",), mpi=False, omp=False, library=None, python_module=False,
                             launch=(sys.executable,), distro=None, python=sys.executable)


def test_run_command_uses_launch_prefix_and_captures_output(tmp_path):
    inst = _fake_installation(tmp_path, "import sys; print('args', sys.argv[1:]); print('err', file=sys.stderr)")
    p = base.run_command(inst, ["-in", "in.x"], cwd=str(tmp_path), timeout=30)
    assert isinstance(p, subprocess.CompletedProcess) and p.returncode == 0
    assert "args ['-in', 'in.x']" in p.stdout and "err" in p.stderr


def test_run_command_times_out_cleanly(tmp_path):
    inst = _fake_installation(tmp_path, "import time; time.sleep(30)")
    p = base.run_command(inst, [], cwd=str(tmp_path), timeout=1)
    assert p.returncode != 0 and "timeout" in p.stderr.lower()


def test_wsl_command_line_is_built_with_timeout_and_cd():
    inst = base.Installation(route="wsl-apt", host="wsl", executable="/usr/bin/lmp", version="x", packages=(),
                             mpi=True, omp=True, library=None, python_module=True,
                             launch=("wsl.exe", "-d", "Ubuntu", "-e", "bash", "-lc"), distro="Ubuntu", python="python3")
    cmd = base.build_command(inst, ["-in", "in.lj"], cwd=r"C:\r\x", timeout=42)
    assert cmd[:6] == ["wsl.exe", "-d", "Ubuntu", "-e", "bash", "-lc"]
    assert cmd[6].startswith("cd '/mnt/c/r/x' && timeout 42 /usr/bin/lmp -in in.lj")


def test_probe_on_fake_that_writes_a_log(tmp_path):
    body = (
        "import sys, os\n"
        "i = sys.argv.index('-log'); open(sys.argv[i+1], 'w').write(\n"
        "'LAMMPS (0 Jan 2000)\\nCreated 4000 atoms\\n   Step          Temp          E_pair  \\n"
        "         0   3              -6.7733681   \\n       250   1.6            -4.7\\nLoop time of 0.5 on 1 procs for 250 steps with 4000 atoms\\n')\n"
    )
    inst = _fake_installation(tmp_path, body)
    rep = base.probe(inst, str(tmp_path / "probe"))
    assert rep.ok and rep.natoms == 4000 and rep.thermo_last["Step"] == 250 and rep.wall >= 0
