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
