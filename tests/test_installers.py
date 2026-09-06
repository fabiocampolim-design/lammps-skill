# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Rule 24: installers have a dry-run contract and a tested failure path."""

import os
import shutil
import subprocess
import sys

import pytest

from conftest import ROOT

SCRIPTS = os.path.join(ROOT, "scripts")
BASH = shutil.which("bash")


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kw)


@pytest.mark.skipif(BASH is None, reason="bash not on PATH")
def test_install_env_sh_dry_run_lists_every_step_without_running_anything(tmp_path):
    fake_conda = tmp_path / "conda"
    fake_conda.write_text("#!/bin/sh\necho SHOULD-NOT-RUN >&2; exit 9\n")
    fake_conda.chmod(0o755)
    p = _run([BASH, os.path.join(SCRIPTS, "install_env.sh"), "--dry-run", "--conda", str(fake_conda)])
    assert p.returncode == 0, p.stdout + p.stderr
    for step in ("create-env", "register-kernel", "verify-imports"):
        assert f"{step} : DRY-RUN" in p.stdout
    assert "SHOULD-NOT-RUN" not in p.stderr


@pytest.mark.skipif(BASH is None, reason="bash not on PATH")
def test_install_env_sh_fails_loudly_when_a_step_fails(tmp_path):
    fake_conda = tmp_path / "conda"
    fake_conda.write_text("#!/bin/sh\nexit 3\n")
    fake_conda.chmod(0o755)
    p = _run([BASH, os.path.join(SCRIPTS, "install_env.sh"), "--conda", str(fake_conda)])
    assert p.returncode == 1
    assert "create-env : FAIL" in p.stdout


@pytest.mark.skipif(BASH is None, reason="bash not on PATH")
def test_install_lammps_wsl_apt_dry_run_and_root_refusal():
    script = os.path.join(SCRIPTS, "install_lammps_wsl.sh")
    p = _run([BASH, script, "--dry-run"])
    assert p.returncode == 0, p.stdout + p.stderr
    for step in ("update", "install", "verify"):
        assert f"{step} : DRY-RUN" in p.stdout
    env = dict(os.environ, LAMMPSKILL_FAKE_UID="1000")
    p = _run([BASH, script], env=env)
    assert p.returncode == 2
    assert "wsl -d Ubuntu -u root" in p.stdout


@pytest.mark.skipif(BASH is None, reason="bash not on PATH")
def test_install_lammps_wsl_source_dry_run_prints_the_cmake_line():
    script = os.path.join(SCRIPTS, "install_lammps_wsl.sh")
    p = _run([BASH, script, "--dry-run", "--source", "--tag", "stable_22Jul2025_update6", "--preset", "core"])
    assert p.returncode == 0, p.stdout + p.stderr
    for step in ("deps", "fetch", "configure", "build", "install", "verify"):
        assert f"{step} : DRY-RUN" in p.stdout
    assert "-D BUILD_SHARED_LIBS=yes" in p.stdout and "-D PKG_PYTHON=yes" in p.stdout
    assert "-D PKG_MOLECULE=yes" in p.stdout and "-D PKG_KSPACE=yes" in p.stdout and "-D PKG_MANYBODY=yes" in p.stdout
    assert "stable_22Jul2025_update6" in p.stdout


@pytest.mark.skipif(BASH is None, reason="bash not on PATH")
def test_install_lammps_wsl_reports_a_failed_step(tmp_path):
    """Failure path: a fake apt-get on PATH that fails makes the script exit 1 naming the step."""
    fake = tmp_path / "apt-get"
    fake.write_text("#!/bin/sh\nexit 100\n")
    fake.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ["PATH"], LAMMPSKILL_FAKE_UID="0")
    p = _run([BASH, os.path.join(SCRIPTS, "install_lammps_wsl.sh")], env=env)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "update : FAIL" in p.stdout


@pytest.mark.skipif(sys.platform != "win32" or shutil.which("powershell") is None, reason="Windows only")
def test_install_env_windows_dry_run():
    p = _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
              os.path.join(SCRIPTS, "install_env_windows.ps1"), "-DryRun"])
    assert p.returncode == 0, p.stdout + p.stderr
    assert "create-env : DRY-RUN" in p.stdout and "register-kernel : DRY-RUN" in p.stdout


@pytest.mark.skipif(BASH is None, reason="bash not on PATH")
def test_install_lammps_wsl_source_dry_run_sets_an_rpath_and_a_venv():
    """N-10/N-11 (both PROVEN on the 22Jul2025_update6 build, 2026-09-06):

    * the installed lmp_<preset> could not find liblammps_<preset>.so because $HOME/.local/lib is not
      on the loader path -> the configure line must set an install RPATH;
    * `cmake --build . --target install-python` pip-installs into system site-packages, which Ubuntu
      26.04 (PEP 668) refuses -> the module goes into a per-preset venv through upstream's install.py.
    """
    script = os.path.join(SCRIPTS, "install_lammps_wsl.sh")
    p = _run([BASH, script, "--dry-run", "--source", "--preset", "core"])
    assert p.returncode == 0, p.stdout + p.stderr
    assert "-D CMAKE_INSTALL_RPATH=" in p.stdout
    assert "python-module : DRY-RUN" in p.stdout
    assert "venv-lammps-core" in p.stdout and "python/install.py" in p.stdout
    # P-1: install.py reads VIRTUAL_ENV, so the venv must be activated, not merely used as the interpreter.
    assert "venv-lammps-core/bin/activate" in p.stdout
    assert "--target install-python" not in p.stdout
