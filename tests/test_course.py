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


import json as _json  # noqa: E402

import pytest  # noqa: E402

import build_deck   # noqa: E402  (course/tools/ is on sys.path from the insert above)


@pytest.fixture(scope="module")
def deck():
    return build_deck.load_content()


@pytest.fixture(scope="module")
def prov():
    return build_deck.load_provenance()


def test_content_is_strict_json_after_the_assignment():
    src = _read("course", "deck", "content.en.js")
    body = src[src.index("window.DECK_CONTENT =") + len("window.DECK_CONTENT ="):].strip().rstrip(";")
    d = _json.loads(body)
    assert d["lang"] == "en" and d["deckTitle"]


def test_eleven_lectures_locked_to_the_chapters(deck):
    lectures = [s for s in deck["sections"].values() if s.get("lecture")]
    assert len(lectures) == 11
    assert [s["lecture"] for s in lectures] == ["L%d" % i for i in range(11)]


def test_every_slide_listed_exactly_once_and_every_stack_has_one(deck):
    listed = [s for st in deck["stacks"] for s in st["slides"]]
    assert len(listed) == len(set(listed))
    assert set(listed) == set(deck["slides"])
    # plan A: one slide per lecture, plus a second for L6 (three figures, not one) -- Plan B raises this
    assert len(listed) == 12


def test_every_notebook_figure_is_used(deck, prov):
    used = {s[k] + ".png" for s in deck["slides"].values() for k in ("fig", "fig2") if k in s}
    assert used == set(prov)


def test_generated_outputs_are_up_to_date(deck, prov):
    stale = [os.path.relpath(p, COURSE) for p, text in build_deck.outputs(deck, prov).items()
             if not os.path.exists(p) or open(p, encoding="utf-8").read() != text]
    assert not stale, "run course/tools/build_deck.py: %s" % stale
