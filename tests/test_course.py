# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Playbook rule 22: the undergraduate course under course/.

Guards the contract of the course: the content file parses as strict JSON; every slide is listed
once, has a level, a known layout and lecturer notes with an anticipated question; each lecture
stack runs intro -> core -> math; every figure a slide shows exists, carries notebook provenance
and is byte-identical to the notebook's output (extract_figures --check); the generated deck,
handout and notes are up to date with the content (build_deck --check); every data-t key in
index.html resolves; the vendored reveal.js keeps its licence and NOTICE names it.

Numeric thresholds are calibrated to this project's actual scale (currently 15 figures, 68 slides
across 13 lectures) rather than copied from pythtb-skill's reference implementation (69 figures,
50+ slides); they are meant to keep growing as the atom-visuals roadmap adds more figures and
lectures (docs/superpowers/specs/2026-09-14-lammps-skill-atom-visuals-design.md) -- update them
here, not by loosening a check, whenever a real new figure or slide lands."""

import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from html import escape as html_escape

import pytest

from conftest import ROOT

COURSE = os.path.join(ROOT, "course")
sys.path.insert(0, os.path.join(COURSE, "tools"))

import build_deck             # noqa: E402
import extract_figures        # noqa: E402

LEVEL_RANK = {"intro": 0, "core": 1, "math": 2}


@pytest.fixture(scope="module")
def deck():
    return build_deck.load_content()


@pytest.fixture(scope="module")
def prov():
    return build_deck.load_provenance()


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- content ---

def test_content_is_strict_json_after_the_assignment():
    src = _read("course", "deck", "content.en.js")
    body = src[src.index("window.DECK_CONTENT =") + len("window.DECK_CONTENT ="):].strip().rstrip(";")
    d = json.loads(body)                 # raises on trailing commas, comments, single quotes
    assert d["lang"] == "en" and d["deckTitle"]


def test_thirteen_lectures_locked_to_the_chapters(deck):
    """Locked 1:1 with the chapter notebooks, L0..L12 -- renamed from "twelve" when the water
    chapter (L12, atom-visuals roadmap item 2, built after item 3/polymer) made it thirteen, the
    atom-visuals design spec's own item 5 anticipated retargeting."""
    lectures = [s for s in deck["sections"].values() if s.get("lecture")]
    assert len(lectures) == 13                       # L0 .. L12
    assert [s["lecture"] for s in lectures] == ["L%d" % i for i in range(13)]


def test_every_slide_listed_exactly_once_and_every_stack_has_one(deck):
    listed = [s for st in deck["stacks"] for s in st["slides"]]
    assert len(listed) == len(set(listed)), "a slide id appears in two stacks"
    assert set(listed) == set(deck["slides"]), set(listed) ^ set(deck["slides"])
    # atom visuals plan, task 7: L1 gains first-sim-atoms (the new snapshot+animation slide)
    # Cu vacancy feature: L5 gains eam-vacancy (the new snapshot pair, before/after FIRE relaxation)
    # Polymer chapter: L11 (6 slides) is new
    # Water chapter: L12 (5 slides) is new
    # Retrofit roadmap item, chapter 03: L3 gains thermostats-atoms (the new snapshot+animation slide)
    assert len(listed) == 69


def test_levels_run_intro_core_math_inside_each_stack(deck):
    for st in deck["stacks"]:
        ranks = [LEVEL_RANK[deck["slides"][s]["level"]] for s in st["slides"]]
        assert ranks == sorted(ranks), "%s: levels not non-decreasing %s" % (st["sec"], ranks)
        assert ranks[0] == 0, "%s: a stack must open with an intro slide" % st["sec"]
        # Plan B (docs/superpowers/plans/2026-09-13-lammps-skill-course-content-plan-b.md) gave
        # every lecture its full depth -- the escape hatch for a single-slide stack is gone.
        if deck["sections"][st["sec"]].get("lecture"):
            assert ranks[-1] == 2, "%s: a lecture must end with a math slide" % st["sec"]


def test_every_slide_is_well_formed(deck):
    for sid, s in deck["slides"].items():
        assert s["layout"] in build_deck.LAYOUTS, (sid, s["layout"])
        assert s["level"] in build_deck.LEVELS, (sid, s["level"])
        assert s.get("title"), sid
        notes = s.get("notes", "")
        assert len(notes) > 120, "%s: notes too short" % sid
        assert "Q:" in notes and "A:" in notes, "%s: notes need an anticipated Q and its A" % sid
        if s["layout"] in ("fig", "fig-right", "fig-left"):
            assert "fig" in s, sid
        if s["layout"] == "two-figs":
            assert "fig" in s and "fig2" in s, sid
        if s["layout"] == "eq":
            assert s.get("eqs"), sid
        if s["layout"] == "table":
            t = s["table"]
            assert all(len(r) == len(t["head"]) for r in t["rows"]), sid


# ---------------------------------------------------------------- figures ---

def test_figures_are_named_by_chapter_key():
    records = list(extract_figures.catalogue(extract_figures.NOTEBOOKS))
    assert len(records) == 17, [r["file"] for r in records]
    names = sorted(r["file"] for r in records)
    assert names == ["ch01-f1.png", "ch01-f2.png", "ch01-f3.gif", "ch03-f1.png", "ch03-f2.png",
                      "ch03-f3.gif", "ch04-f1.png",
                      "ch05-f1.png", "ch05-f2.png", "ch06-f1.png", "ch06-f2.png", "ch06-f3.png",
                      "ch11-f1.png", "ch11-f2.gif", "ch12-f1.png", "ch12-f2.png", "ch12-f3.gif"]


def test_every_figure_has_the_caption_from_the_notebook():
    records = list(extract_figures.catalogue(extract_figures.NOTEBOOKS))
    for r in records:
        assert isinstance(r["figure"], int) and r["figure"] >= 1, r["file"]   # each chapter's own count, from 1
        assert len(r["caption"]) > 40, r["file"]


def test_figure_block_resolves_gif_extension():
    prov = {"fake-f1.gif": {"chapter": "x", "section": 0, "heading": "", "cell": 1,
                            "figure": 1, "caption": "a gif", "sha256": "x", "bytes": 1}}
    html = build_deck.figure_block("fake-f1", prov)
    assert 'src="figs/fake-f1.gif"' in html
    assert "a gif" in html


def test_catalogue_recognises_gif_outputs(tmp_path):
    """A cell whose output is display(Image(filename=...)) of a .gif file produces an
    image/gif MIME output in the notebook; catalogue() must recognise it exactly like image/png,
    with the same caption-pairing rule (the next HTML caption output attaches to it)."""
    import base64
    import json as _json

    gif_bytes = b"GIF89a" + b"\x00" * 20   # not a real GIF -- catalogue() only cares about the MIME key
    nb = {
        "cells": [
            {"cell_type": "code", "source": [], "outputs": [
                {"data": {"image/gif": [base64.b64encode(gif_bytes).decode()]}},
                {"data": {"text/html": ["<b>Figure 1.</b> a test animation</div>"]}},
            ]},
        ]
    }
    nb_path = tmp_path / "fake.ipynb"
    nb_path.write_text(_json.dumps(nb), encoding="utf-8")
    records = list(extract_figures.catalogue(str(nb_path)))
    assert len(records) == 1
    r = records[0]
    assert r["file"].endswith(".gif")
    assert r["figure"] == 1 and r["caption"] == "a test animation"


def test_every_figure_shown_has_notebook_provenance(deck, prov):
    figdir = os.path.join(COURSE, "deck", "figs")
    for sid, s in deck["slides"].items():
        for key in ("fig", "fig2"):
            if key not in s:
                continue
            name = next((s[key] + "." + e for e in ("png", "gif") if s[key] + "." + e in prov), s[key] + ".png")
            assert name in prov, "%s: %s has no provenance entry" % (sid, name)
            meta = prov[name]
            assert isinstance(meta["cell"], int)
            assert meta["caption"], "%s: %s has no notebook caption" % (sid, name)
            path = os.path.join(figdir, name)
            assert os.path.exists(path), path
            with open(path, "rb") as f:
                assert hashlib.sha256(f.read()).hexdigest() == meta["sha256"], "%s differs from provenance" % name


def test_figures_match_the_executed_notebook():
    """Every PNG/GIF output of the chapter notebooks is on disk, byte-identical, with no orphans."""
    records = list(extract_figures.catalogue(extract_figures.NOTEBOOKS))
    assert len(records) == 17
    problems = extract_figures.check(records, extract_figures.FIGDIR)
    assert not problems, "run course/tools/extract_figures.py: %s" % "; ".join(problems[:5])


def test_every_notebook_figure_is_used(deck, prov):
    def _resolved(key):
        return next((key + "." + e for e in ("png", "gif") if key + "." + e in prov), key + ".png")
    used = {_resolved(s[k]) for s in deck["slides"].values() for k in ("fig", "fig2") if k in s}
    assert used == set(prov), "unused notebook figures: %s" % sorted(set(prov) - used)


# --------------------------------------------------------- generated files ---

def test_generated_outputs_are_up_to_date(deck, prov):
    stale = []
    for path, text in build_deck.outputs(deck, prov).items():
        if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
            stale.append(os.path.relpath(path, COURSE))
    assert not stale, "run course/tools/build_deck.py: %s" % stale


def _resolve(deck, ref):
    slide, _, key = ref.partition(".")
    node = deck["slides"].get(slide)
    for part in key.split("."):
        if node is None:
            return None
        node = node[int(part)] if isinstance(node, list) else node.get(part)
    return node


def test_index_html_keys_resolve_and_images_exist(deck):
    html = _read("course", "deck", "index.html")
    refs = re.findall(r'data-t="([^"]+)"', html)
    assert len(refs) > 20
    missing = [r for r in refs if _resolve(deck, r) is None]      # "" is a legal empty cell
    assert not missing, missing[:10]
    for sid in re.findall(r'data-notes="([^"]+)"', html):
        assert deck["slides"][sid]["notes"]
    for src in re.findall(r'<img src="([^"]+)"', html):
        assert os.path.exists(os.path.join(COURSE, "deck", src)), src
    ids = re.findall(r'<section id="([^"]+)" data-sec="[^"]+" data-level="(intro|core|math)"', html)
    assert [i for i, _ in ids] == [s for st in deck["stacks"] for s in st["slides"]]
    for sec in re.findall(r'data-sec="([^"]+)"', html):
        assert sec in deck["sections"]
    # a divider slide opens every lecture except the opening stack
    dividers = re.findall(r'<section id="div-([^"]+)"', html)
    expected = [st["sec"] for st in deck["stacks"][1:] if deck["sections"][st["sec"]].get("lecture")]
    assert dividers == expected


def test_declared_eqs_are_actually_rendered(deck):
    """test_index_html_keys_resolve_and_images_exist only checks that every data-t reference IN
    the HTML resolves to real content -- it says nothing about whether a slide's own declared
    content made it into the HTML at all. A layout branch in render_slide() that forgets to call
    eq_block() (or bullets_block()/table_block()) would pass that test while silently dropping
    the slide's equations from the deck -- this test catches that failure mode directly."""
    html = _read("course", "deck", "index.html")
    for sid, s in deck["slides"].items():
        for i in range(len(s.get("eqs", []))):
            assert f'data-t="{sid}.eqs.{i}.math"' in html, "%s: eqs[%d] never rendered (layout %s)" % (sid, i, s["layout"])
        for i in range(len(s.get("bullets", []))):
            assert f'data-t="{sid}.bullets.{i}"' in html, "%s: bullets[%d] never rendered (layout %s)" % (sid, i, s["layout"])
        if "table" in s:
            assert f'data-t="{sid}.table.head.0"' in html, "%s: table never rendered (layout %s)" % (sid, s["layout"])


def test_handout_and_notes_cover_every_lecture_and_slide(deck):
    handout = _read("course", "handout", "handout.html")
    notes = _read("course", "notes", "LECTURER_NOTES.md")
    for sec in deck["sections"].values():
        if sec.get("lecture"):
            assert html_escape("%s · %s" % (sec["lecture"], sec["name"])) in handout, sec["name"]
    for sid in deck["slides"]:
        assert "`#%s`" % sid in notes, sid
    for term, _ in deck["glossary"]:
        assert term in handout


# ---------------------------------------------------------------- licence ---

def test_pdf_fallback_is_committed_and_complete(deck):
    """course/slides.pdf: the presentation without a browser -- one page per slide (dividers
    included), regenerated by course/tools/make_slides_pdf.py."""
    import make_slides_pdf
    path = os.path.join(COURSE, "slides.pdf")
    assert os.path.exists(path), "run course/tools/make_slides_pdf.py"
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"
    assert os.path.getsize(path) > 50_000
    n_slides = sum(len(st["slides"]) for st in deck["stacks"])
    n_div = sum(1 for i, st in enumerate(deck["stacks"])
                if i > 0 and deck["sections"][st["sec"]].get("lecture"))
    assert make_slides_pdf.page_count(path) == n_slides + n_div


def test_vendored_reveal_keeps_its_mit_licence_and_notice_names_it():
    lic = _read("course", "shared", "reveal", "LICENSE")
    assert "Permission is hereby granted, free of charge" in lic and "Hakim El Hattab" in lic
    notice = _read("NOTICE")
    assert "reveal.js" in notice and "MIT" in notice
    for f in ("dist/reset.css", "dist/reveal.css", "dist/reveal.js", "plugin/notes/notes.js"):
        assert os.path.exists(os.path.join(COURSE, "shared", "reveal", f)), f


def test_course_sources_carry_spdx_headers():
    files = glob.glob(os.path.join(COURSE, "tools", "*.py")) + [
        os.path.join(COURSE, "shared", n) for n in ("theme.css", "nav.js", "loader.js")] + [
        os.path.join(COURSE, "deck", "content.en.js")]
    missing = [f for f in files if "SPDX-License-Identifier: Apache-2.0" not in open(f, encoding="utf-8").read()[:400]]
    assert not missing, missing


def test_course_tools_print_their_version():
    version = _read("VERSION").strip()
    for tool in ("extract_figures", "build_deck", "verify_deck", "build_pptx",
                 "make_handout", "make_slides_pdf"):
        out = subprocess.run([sys.executable, os.path.join(COURSE, "tools", tool + ".py"), "--version"],
                             capture_output=True, text=True)
        assert out.returncode == 0 and version in out.stdout + out.stderr, (tool, out.stdout, out.stderr)
