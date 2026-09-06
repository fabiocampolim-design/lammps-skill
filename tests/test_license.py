# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Playbook rule 17: the warranty disclaimer, the limitation of liability and the
non-affiliation paragraph must survive every rewrite."""

import glob
import os

from conftest import ROOT

NON_AFFIL = ("Sandia National Laboratories", "NTESS", "LAMMPS developers")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8", errors="replace") as f:
        return f.read()


def _one_line(text):
    return " ".join(text.split())


def test_license_is_apache_2_with_disclaimers():
    text = _read("LICENSE")
    assert "Apache License" in text and "Version 2.0" in text
    assert "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND" in text
    assert "Limitation of Liability" in text


def test_notice_names_project_upstream_and_status():
    text = _one_line(_read("NOTICE"))
    assert "lammps-skill" in text and "Apache License, Version 2.0" in text
    assert "contains no code from LAMMPS" in text and "GNU GPL v2" in text
    assert "not affiliated" in text
    for name in NON_AFFIL:
        assert name in text, name


def test_readme_carries_visible_disclaimer_and_non_affiliation():
    text = _read("README.md")
    assert "## Licence" in text and "### Disclaimer" in text
    assert text.index("## Licence") < text.index("### Disclaimer")
    low = text.lower()
    assert "without warrant" in low and "liable" in low and "not affiliated" in low
    flat = _one_line(text)
    for name in NON_AFFIL:
        assert name in flat, name


def test_skill_md_states_the_licence_and_the_gpl_boundary():
    flat = _one_line(_read("SKILL.md"))
    assert "license: Apache-2.0" in flat
    assert "GPL-2.0" in flat and "not included" in flat


def test_citation_matches_licence():
    assert "license: Apache-2.0" in _read("CITATION.cff")


def test_every_python_file_has_spdx_header():
    files = [f for pat in ("lammpskill/*.py", "lammpskill/*/*.py", "mdlite/*.py", "scripts/*.py", "tests/*.py", "docs/*.py", "build/*.py")
             for f in glob.glob(os.path.join(ROOT, pat))]
    assert files
    missing = [f for f in files if "SPDX-License-Identifier: Apache-2.0" not in _read(f)[:300]]
    assert not missing, [os.path.relpath(m, ROOT) for m in missing]
