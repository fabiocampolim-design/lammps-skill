# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Rule 15: the suite guards the docs — every CLI flag is documented in AGENTS.md and docs/USER_MANUAL.md; VERSION,
CITATION and CHANGELOG agree; SKILL.md points at existing files; every references/ file the spec promises exists and
is substantial; the checker's codes are all explained in pitfalls.md; the platform table has one row per route."""

import os
import re

import pytest

from conftest import ROOT
from lammpskill.install import ROUTES, get_route
from lammpskill.script import CHECKS


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flags(parser):
    return {s for a in parser._actions for s in a.option_strings if s.startswith("--") and s != "--help"}


def test_build_manual_writes_html_without_pandoc(tmp_path, monkeypatch):
    import build_manual
    monkeypatch.setattr(build_manual.shutil, "which", lambda name: None)
    assert build_manual.main(["--outdir", str(tmp_path), "--no-pdf"]) == 0
    out = (tmp_path / "USER_MANUAL.html").read_text(encoding="utf-8")
    assert "<title>lammps-skill" in out and "<h2>" in out and "scripts/verify_lammps.py" in out


@pytest.mark.parametrize("module", ["verify_lammps", "run_benchmarks", "run_examples", "watch_upstream", "build_manual",
                                   "lammpskill.cli"])
def test_script_flags_are_documented(module):
    mod = __import__(module, fromlist=["build_parser"])
    agents, manual = _read("AGENTS.md"), _read("docs", "USER_MANUAL.md")
    parser = mod.build_parser()
    flags = _flags(parser)
    for a in parser._actions:
        if hasattr(a, "choices") and isinstance(a.choices, dict):
            for sp in a.choices.values():
                flags |= _flags(sp)
    for f in flags:
        assert f in agents, f"{module}: {f} missing from AGENTS.md"
        assert f in manual, f"{module}: {f} missing from docs/USER_MANUAL.md"


def test_version_citation_changelog_agree():
    v = _read("VERSION").strip()
    assert f'version: "{v}"' in _read("CITATION.cff")
    assert f"## {v}" in _read("CHANGELOG.md")
    assert f"lammps-skill {v}" in _read("SKILL.md")


def test_skill_references_exist():
    text = _read("SKILL.md")
    for ref in set(re.findall(r"`(references/[\w./-]+|scripts/[\w./-]+|docs/[\w./-]+)`", text)):
        assert os.path.exists(os.path.join(ROOT, ref)), ref


@pytest.mark.parametrize("name", ["input-script", "file-formats", "packages", "install-routes", "platforms", "backends",
                                  "benchmarks", "pitfalls", "ecosystem", "analysis"])
def test_reference_files_exist_and_are_substantial(name):
    assert len(_read("references", name + ".md")) > 800, name


def test_pitfalls_explain_every_checker_code():
    p = _read("references", "pitfalls.md")
    for code, level, manual, desc in CHECKS:
        assert code in p, code


def test_platform_table_has_a_row_per_route():
    p = _read("references", "platforms.md")
    for r in ROUTES:
        assert "| %s |" % r in p, r


def test_readme_has_the_product_sections():
    r = _read("README.md")
    for h in ("## What it does", "## Install", "## Quick start", "## What is verified", "## Layout", "## Licence", "### Disclaimer"):
        assert h in r, h


def test_install_routes_doc_describes_every_route_with_its_module_text():
    doc = _read("references", "install-routes.md")
    for r in ROUTES:
        first_sentence = get_route(r).describe().split(".")[0]
        assert first_sentence[:40] in doc, r
