# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""run_examples.py: the sweep over LAMMPS's own bench/ and examples/ trees.

Upstream inputs are never copied into this repository (rule 7): the tests build their own tiny
tree with the *shape* of the upstream one and check the logic, never a shipped input.
"""

import os

import pytest

import run_examples as rx


def _tree(tmp_path):
    """A stand-in for the installed tree: bench/ with reference logs, examples/<case>/in.<case>."""
    bench = tmp_path / "bench"
    bench.mkdir()
    (bench / "in.lj").write_text("units lj\nrun 100\n")
    (bench / "in.chain").write_text("units lj\nrun 100\n")
    (bench / "data.chain").write_text("data\n")
    (bench / "log.15Jul25.lj.fixed.g++.1").write_text("ref 1 proc\n")
    (bench / "log.15Jul25.lj.fixed.g++.4").write_text("ref 4 procs\n")
    ex = tmp_path / "examples"
    (ex / "melt").mkdir(parents=True)
    (ex / "melt" / "in.melt").write_text("units lj\nrun 100\n")
    (ex / "min").mkdir()
    (ex / "min" / "in.min").write_text("units lj\nminimize 0 0 10 10\n")
    (ex / "min" / "in.min2d").write_text("units lj\nminimize 0 0 10 10\n")
    (ex / "PACKAGES").mkdir()          # a directory with no in.* of its own
    (ex / "README").write_text("not a case\n")
    return tmp_path


def test_discover_bench_finds_each_input_in_one_shared_directory(tmp_path):
    root = _tree(tmp_path)
    cases = rx.discover(str(root), "bench")
    names = sorted(c.name for c in cases)
    assert names == ["chain", "lj"]
    for c in cases:
        assert os.path.basename(c.directory) == "bench" and c.input_name.startswith("in.")


def test_discover_examples_walks_one_directory_per_case_and_keeps_every_input(tmp_path):
    root = _tree(tmp_path)
    cases = rx.discover(str(root), "examples")
    names = sorted(c.name for c in cases)
    assert names == ["melt/melt", "min/min", "min/min2d"]
    assert not any("README" in c.name or "PACKAGES" in c.name for c in cases)


def test_discover_only_filters_by_substring(tmp_path):
    root = _tree(tmp_path)
    assert [c.name for c in rx.discover(str(root), "examples", only="min2d")] == ["min/min2d"]


def test_reference_logs_are_indexed_by_process_count(tmp_path):
    root = _tree(tmp_path)
    refs = rx.reference_logs(str(root / "bench"), "lj")
    assert set(refs) == {1, 4}
    assert refs[4].endswith("log.15Jul25.lj.fixed.g++.4")
    assert rx.reference_logs(str(root / "bench"), "chain") == {}


# The exact texts below were captured on this machine on 2026-09-06 (lmp_core, 22Jul2025 update 6).
MISSING_PKG = ("ERROR: Unrecognized pair style 'reaxff' is part of the REAXFF package which is not "
               "enabled in this LAMMPS binary.\nFor more information see https://docs.lammps.org/err0010 "
               "(src/force.cpp:275)\n")
UNKNOWN_CMD = "ERROR: Unknown command: nonsense_command 1 2 3 (src/input.cpp:315)\n"
MISSING_FILE = "ERROR: Cannot open file data.eim: No such file or directory (src/read_data.cpp:380)\n"
GOOD = """LAMMPS (22 Jul 2025 - Update 6)
Step Temp E_pair TotEng Press
       0            3   -6.7733681            1.5        -5.0196
     100    1.6758903   -4.7955425    1.6538988    5.8691042
Loop time of 0.5 on 1 procs for 100 steps with 4000 atoms
Total wall time: 0:00:01
"""


def test_classify_names_the_missing_package():
    outcome, detail = rx.classify(0, MISSING_PKG)
    assert outcome == "missing-package" and detail == "REAXFF"


def test_classify_separates_a_real_error_from_a_missing_package():
    assert rx.classify(0, UNKNOWN_CMD)[0] == "error"
    assert rx.classify(0, MISSING_FILE)[0] == "error"


def test_classify_does_not_trust_the_return_code():
    """N-15 (PROVEN 2026-09-06): both builds here exit 0 on a fatal input error, so a sweep that
    scores on the return code marks every broken case as a pass."""
    assert rx.classify(0, UNKNOWN_CMD)[0] == "error"
    assert rx.classify(0, GOOD)[0] == "ok"


def test_classify_reports_a_timeout():
    assert rx.classify(124, "")[0] == "timeout"
    assert rx.classify(124, "LAMMPS (22 Jul 2025)\nSetting up run ...\n")[0] == "timeout"


def test_classify_flags_a_log_with_no_run_at_all():
    assert rx.classify(0, "LAMMPS (22 Jul 2025)\nTotal wall time: 0:00:00\n")[0] == "no-run"


def test_compare_final_thermo_reports_the_worst_relative_difference():
    ours = GOOD
    theirs = GOOD.replace("1.6758903", "1.6758920")     # 1.0e-6 relative
    cmp = rx.compare_final_thermo(ours, theirs)
    assert cmp["columns"]["Temp"]["ours"] == pytest.approx(1.6758903)
    assert cmp["worst"] == pytest.approx(1.0e-6, rel=0.2)
    assert cmp["worst_column"] == "Temp"


def test_compare_final_thermo_says_so_when_the_columns_differ():
    cmp = rx.compare_final_thermo(GOOD, GOOD.replace("E_pair", "E_bond"))
    assert cmp["comparable"] is False and "columns differ" in cmp["note"]


def test_compare_final_thermo_says_so_when_a_side_has_no_thermo():
    cmp = rx.compare_final_thermo(GOOD, "LAMMPS (22 Jul 2025)\n")
    assert cmp["comparable"] is False


def test_markdown_table_has_one_row_per_record_and_escapes_pipes():
    rows = [dict(case="lj", route="wsl-apt", procs=1, outcome="ok", wall=1.23, steps=100, natoms=4000,
                 detail="a|b", reference=None)]
    md = rx.markdown_table(rows)
    assert md.count("\n") >= 3 and "| lj |" in md and "a\\|b" in md


class _FakeInstallation:
    host = "wsl"
    launch = ("wsl.exe", "-d", "Ubuntu", "-e", "bash", "-lc")
    route = "wsl-source"


def test_scratch_root_is_an_absolute_path_not_a_shell_variable():
    """N-17 (PROVEN 2026-09-06): build_command single-quotes the working directory, so a scratch
    root of "$HOME/runs/examples" produced `cd '$HOME/runs/examples/lj'` -- every one of the 16
    bench runs failed in 0.3 s and was scored "no-run" while the copies sat there correctly."""
    import subprocess as sp

    calls = []

    def fake_run(cmd):
        calls.append(cmd[-1])
        return sp.CompletedProcess(cmd, 0, stdout="/home/u\n", stderr="")

    fs = rx.WslFs(_FakeInstallation(), run=fake_run)
    root = rx._scratch_root(fs)
    assert root == "/home/u/runs/examples"
    assert "$" not in root
    assert any("echo $HOME" in c or "echo ${HOME}" in c for c in calls)


MULTI_OURS = """LAMMPS (22 Jul 2025 - Update 6)
------------ Step            100 ----- CPU =     58.16219 (sec) -------------
TotEng   =    -25290.7360 Temp     =       301.0906
Loop time of 58.2 on 1 procs for 100 steps with 32000 atoms
"""
MULTI_THEIRS = MULTI_OURS.replace("58.16219", "14.20402").replace("Loop time of 58.2", "Loop time of 14.2")


def test_compare_final_thermo_ignores_the_timing_columns():
    """CPU is wall time on whoever's machine produced the log: upstream's rhodo reference ran in
    14.2 s and ours in 58.2 s, which reported "worst 7.6e-01 (CPU)" and buried the fact that every
    physical column agreed to every printed digit."""
    cmp = rx.compare_final_thermo(MULTI_OURS, MULTI_THEIRS)
    assert cmp["comparable"] is True
    assert cmp["columns"]["CPU"]["rel"] > 0.5          # still recorded ...
    assert cmp["worst"] == 0.0                          # ... but never the headline
    assert cmp["ignored"] == ["CPU"]


def test_markdown_table_says_identical_instead_of_worst_zero():
    rows = [dict(case="lj", route="wsl-apt", procs=1, outcome="ok", wall=1.0, steps=100, natoms=4000,
                 detail="", reference={"comparable": True, "worst": 0.0, "worst_column": None,
                                       "columns": {}, "ignored": []})]
    assert "identical" in rx.markdown_table(rows)


def test_wsl_discovery_uses_one_round_trip_not_one_per_directory():
    """N-19 (PROVEN 2026-09-06): discovery called `test -d` + `ls` per directory, one wsl.exe launch
    each. Over examples/'s 89 directories that is 300+ launches at ~0.5 s -- the first sweep spent
    minutes before running a single case and had to be killed. One `find` does the whole tree."""
    import subprocess as sp

    # what `find -maxdepth 2 -printf '%y\t%p\n'` returns: the type, a tab, the path
    listing = "\n".join([
        "d\t/t/examples",
        "f\t/t/examples/README",
        "d\t/t/examples/melt",
        "f\t/t/examples/melt/in.melt",
        "d\t/t/examples/min",
        "f\t/t/examples/min/in.min",
        "f\t/t/examples/min/in.min2d",
        "f\t/t/examples/min/log.1Jan25.min.g++.1",
    ])
    calls = []

    def fake_run(cmd):
        calls.append(cmd[-1])
        return sp.CompletedProcess(cmd, 0, stdout=listing + "\n", stderr="")

    fs = rx.WslFs(_FakeInstallation(), run=fake_run)
    cases = rx.discover("/t", "examples", fs=fs)
    assert sorted(c.name for c in cases) == ["melt/melt", "min/min", "min/min2d"]
    assert len(calls) == 1, calls
    assert dict(next(c for c in cases if c.name == "min/min").reference) == {1: "/t/examples/min/log.1Jan25.min.g++.1"}


def test_classify_separates_a_timeout_that_had_already_started_running():
    """A sweep needs a cap, but "hit the cap" and "produced nothing" are different facts: a case
    that wrote thermo rows before the cap does run on this route, it is just longer than the sweep
    allows. Reporting both as `timeout` would hide that (2026-09-06)."""
    assert rx.classify(124, GOOD)[0] == "timeout-after-start"
    assert rx.classify(124, "LAMMPS (22 Jul 2025)\n")[0] == "timeout"
    assert rx.classify(124, MISSING_PKG)[0] == "missing-package"


def test_potentials_directory_is_exported_into_the_run(monkeypatch):
    """N-20 (PROVEN 2026-09-06): LAMMPS finds a shipped potential through $LAMMPS_POTENTIALS, and
    the first full sweep never set it -- 20+ cases came back as `error: cannot open sw potential
    file Si.sw`, which reads like a broken example but is a missing environment variable. The
    variable must reach the shell *inside* WSL, so it goes in front of the executable: a Windows
    `env=` never crosses the wsl.exe boundary."""
    import subprocess as sp

    seen = {}

    class Inst:
        host, route, mpi, omp = "wsl", "wsl-source", True, True
        launch = ("wsl.exe", "-d", "Ubuntu", "-e", "bash", "-lc")
        executable = "/home/u/.local/bin/lmp_core"
        version, packages, library, python_module, distro, python = "x", (), None, True, "Ubuntu", "python3"
        extra = {}

        def as_dict(self):
            return dict(host=self.host, route=self.route, mpi=self.mpi, omp=self.omp, launch=self.launch,
                        executable=self.executable, version=self.version, packages=self.packages,
                        library=self.library, python_module=self.python_module, distro=self.distro,
                        python=self.python, extra=self.extra)

    def fake_run_command(inst, args, cwd, timeout=600, env=None, log=None):
        seen["exe"] = inst.executable
        return sp.CompletedProcess(["x"], 0, stdout="", stderr="")

    monkeypatch.setattr(rx, "run_command", fake_run_command)
    monkeypatch.setattr(rx, "_read_remote", lambda *a, **k: GOOD)

    class FsStub:
        def join(self, *p):
            return "/".join(p)

        def read(self, p):
            return ""

    monkeypatch.setattr(rx.subprocess, "run", lambda *a, **k: sp.CompletedProcess(["x"], 0, stdout="", stderr=""))
    case = rx.Case("melt/melt", "/t/examples/melt", "in.melt", {})
    rx.run_case(case, Inst(), procs=1, time_limit=5, potentials="/t/potentials", run_root="/home/u/runs",
                fs=FsStub())
    # `env VAR=...`, never a bare `VAR=... prog`: build_command runs the executable under `timeout`,
    # which execs its argument directly, so a shell assignment there becomes the program name and
    # every case fails with "timeout: failed to execute process" (N-22, 191 cases scored no-run).
    assert seen["exe"].startswith("env LAMMPS_POTENTIALS='/t/potentials' ")
    assert seen["exe"].endswith("/home/u/.local/bin/lmp_core")


def test_early_abort_when_the_first_cases_all_fail_the_same_way():
    """A broken command line (N-22: `timeout N VAR=x prog`) produced 191 consecutive no-run rows
    before anyone looked. A sweep that starts with nothing but no-run is not data, it is a bug."""
    assert rx.early_abort_reason([{"outcome": "no-run"}] * 5) is not None
    assert "no-run" in rx.early_abort_reason([{"outcome": "no-run"}] * 5)
    # fewer than the probe count, or any case that actually ran, is not a reason to stop
    assert rx.early_abort_reason([{"outcome": "no-run"}] * 4) is None
    assert rx.early_abort_reason([{"outcome": "no-run"}] * 4 + [{"outcome": "ok"}]) is None
    assert rx.early_abort_reason([{"outcome": "missing-package"}] * 9) is None
