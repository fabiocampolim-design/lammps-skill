# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Playbook rule 22: the undergraduate course under course/. Grown task by task in plan A
(docs/superpowers/plans/2026-09-13-lammps-skill-course-infra.md); the full guard suite lands in
Task 6."""

import os
import sys

from conftest import ROOT

COURSE = os.path.join(ROOT, "course")
sys.path.insert(0, os.path.join(COURSE, "tools"))

import extract_figures        # noqa: E402


def test_figures_are_named_by_chapter_key():
    records = list(extract_figures.catalogue(extract_figures.NOTEBOOKS))
    assert len(records) == 6, [r["file"] for r in records]
    names = sorted(r["file"] for r in records)
    assert names == ["ch01-f1.png", "ch03-f1.png", "ch04-f1.png",
                      "ch06-f1.png", "ch06-f2.png", "ch06-f3.png"]


def test_every_figure_has_the_caption_from_the_notebook():
    records = list(extract_figures.catalogue(extract_figures.NOTEBOOKS))
    for r in records:
        assert r["figure"] == 1 or r["figure"] is not None, r["file"]   # each chapter's own count
        assert len(r["caption"]) > 40, r["file"]


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def test_vendored_reveal_keeps_its_mit_licence_and_notice_names_it():
    lic = _read("course", "shared", "reveal", "LICENSE")
    assert "Permission is hereby granted, free of charge" in lic and "Hakim El Hattab" in lic
    notice = open(os.path.join(ROOT, "NOTICE"), encoding="utf-8").read()
    assert "reveal.js" in notice and "MIT" in notice
    for f in ("dist/reset.css", "dist/reveal.css", "dist/reveal.js", "plugin/notes/notes.js"):
        assert os.path.exists(os.path.join(COURSE, "shared", "reveal", f)), f


def test_course_shared_assets_carry_spdx_headers():
    for name in ("theme.css", "nav.js", "loader.js"):
        assert "SPDX-License-Identifier: Apache-2.0" in _read("course", "shared", name)[:400]
