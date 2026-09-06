# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Every route module honours the same contract; detection is exercised with fakes, never assumed."""

import os
import subprocess
import sys
import types

import pytest

from conftest import FIXTURES
from lammpskill import install
from lammpskill.install import ROUTES, get_route


def _help():
    with open(os.path.join(FIXTURES, "lmp_help_wsl_apt.txt"), encoding="utf-8") as f:
        return f.read()


@pytest.mark.parametrize("name", ROUTES)
def test_route_module_contract(name):
    mod = get_route(name)
    assert mod.NAME == name
    assert callable(mod.detect) and isinstance(mod.describe(), str) and len(mod.describe()) > 40


def test_wsl_apt_detect_with_a_fake_runner():
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        if "command -v lmp" in cmd[-1]:
            return subprocess.CompletedProcess(cmd, 0, stdout="/usr/bin/lmp\n", stderr="")
        if "lmp -h" in cmd[-1]:
            return subprocess.CompletedProcess(cmd, 0, stdout=_help(), stderr="")
        if "import lammps" in cmd[-1]:
            return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    inst = get_route("wsl-apt").detect(env={"LAMMPSKILL_WSL_DISTRO": "Ubuntu"}, run=fake_run)
    assert inst is not None and inst.route == "wsl-apt" and inst.host == "wsl"
    assert inst.executable == "/usr/bin/lmp" and "MOLECULE" in inst.packages and inst.python_module is True
    assert inst.launch[:2] == ("wsl.exe", "-d")


def test_wsl_apt_detect_returns_none_when_wsl_is_absent():
    def fake_run(cmd, **kw):
        raise FileNotFoundError("wsl.exe")
    assert get_route("wsl-apt").detect(env={}, run=fake_run) is None


def test_wsl_source_detect_prefers_env_override():
    def fake_run(cmd, **kw):
        if "-h" in cmd[-1]:
            return subprocess.CompletedProcess(cmd, 0, stdout=_help(), stderr="")
        if "test -x" in cmd[-1]:
            return subprocess.CompletedProcess(cmd, 0, stdout="/home/u/.local/bin/lmp_core\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")
    inst = get_route("wsl-source").detect(env={"LAMMPSKILL_WSL_LMP": "/home/u/.local/bin/lmp_core"}, run=fake_run)
    assert inst is not None and inst.executable == "/home/u/.local/bin/lmp_core" and inst.route == "wsl-source"


def test_wsl_source_cmake_command_names_every_preset_package():
    from lammpskill.install import wsl_source
    line = wsl_source.cmake_command("core")
    for p in wsl_source.PRESET_PACKAGES["core"].split():
        assert "-D PKG_%s=yes" % p in line
    assert "BUILD_SHARED_LIBS=yes" in line and "LAMMPS_MACHINE=core" in line
    assert "most.cmake" in wsl_source.cmake_command("all-cpu")


def test_windows_detect_with_a_fake_path(tmp_path, monkeypatch):
    exe = tmp_path / "lmp.exe"
    exe.write_text("")
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setenv("LAMMPS_POTENTIALS", str(tmp_path / "pot"))

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout=_help(), stderr="")
    inst = get_route("windows").detect(env=dict(os.environ), run=fake_run)
    assert inst is not None and inst.host == "windows" and inst.launch == () and inst.extra["potentials"].endswith("pot")


def test_wheel_detect_reports_in_process_only(monkeypatch):
    fake = types.ModuleType("lammps")

    class L:
        installed_packages = ["MOLECULE", "KSPACE"]

        def __init__(self, cmdargs=None):
            pass

        def version(self):
            return 20250722

        def close(self):
            pass
    fake.lammps = L
    monkeypatch.setitem(sys.modules, "lammps", fake)
    inst = get_route("wheel").detect(env={}, run=None)
    assert inst is not None and inst.executable is None and inst.python_module is True and inst.version == "20250722"
    assert inst.packages == ("KSPACE", "MOLECULE")


def test_docker_and_remote_are_contracts_with_fakes():
    def fake_docker(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout="lammps/lammps:stable_22Jul2025_update6\n", stderr="")
    d = get_route("docker").detect(env={"LAMMPSKILL_DOCKER_IMAGE": "lammps/lammps:stable_22Jul2025_update6"}, run=fake_docker)
    assert d is not None and d.route == "docker" and d.extra["pinned"] is True
    r = get_route("remote").detect(env={"LAMMPSKILL_REMOTE": "user@cluster:/opt/lammps/bin/lmp"}, run=None)
    assert r is not None and r.host == "remote" and r.extra["pinned"] is True
    assert get_route("docker").detect(env={}, run=fake_docker) is None
    assert get_route("remote").detect(env={}, run=None) is None


def test_detect_all_drops_none_and_keeps_route_order(monkeypatch):
    for name in ROUTES:
        monkeypatch.setattr(get_route(name), "detect", lambda env=None, run=None: None)
    monkeypatch.setattr(get_route("windows"), "detect", lambda env=None, run=None: install.base.Installation(
        route="windows", host="windows", executable="x", version="v", packages=(), mpi=False, omp=False, library=None,
        python_module=False, launch=(), distro=None, python=None))
    found = install.detect_all()
    assert [i.route for i in found] == ["windows"]


def test_real_detection_if_any(lammps_installations):
    """Skipped when nothing is installed; otherwise every found installation has a version and either an executable or the module."""
    for inst in lammps_installations:
        assert inst.version and (inst.executable or inst.python_module)
