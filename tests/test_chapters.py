# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""The chapter notebooks are generated, never hand-edited: these tests guard the generator.

Rule 25 (size), the spec's chapter shape (TOC header, Setup cell, tally cell), the pinned kernel,
and the rule that a chapter marked "no LAMMPS" really does run without it.
"""

import json
import os
import subprocess
import sys

import pytest

from conftest import ROOT

BUILD = os.path.join(ROOT, "build")
sys.path.insert(0, BUILD)

import assemble as asm     # noqa: E402
import nbbuild             # noqa: E402

NB_MAX = 1_000_000         # rule 25: 1 MB target per notebook, with outputs


def test_every_chapter_is_registered_with_a_slug_and_a_module():
    assert len(asm.CHAPTERS) >= 1
    seen = set()
    for key, ch in asm.CHAPTERS.items():
        assert key.isdigit() and len(key) == 2, key
        assert ch["slug"] and ch["title"]
        assert ch["slug"] not in seen
        seen.add(ch["slug"])
        assert isinstance(ch["module"].CELLS, list) and ch["module"].CELLS


def test_a_cell_is_a_kind_and_a_string():
    for key, ch in asm.CHAPTERS.items():
        for kind, src in ch["module"].CELLS:
            assert kind in ("md", "code"), (key, kind)
            assert isinstance(src, str) and src.strip(), key


def test_assembled_notebook_has_the_required_shape(tmp_path):
    key = sorted(asm.CHAPTERS)[0]
    path = asm.assemble_one(key, str(tmp_path))
    nb = json.loads(open(path, encoding="utf-8").read())
    assert nb["metadata"]["kernelspec"]["name"] == nbbuild.KERNELSPEC["name"] == "lammps-mc"
    sources = ["".join(c["source"]) if isinstance(c["source"], list) else c["source"] for c in nb["cells"]]
    assert sources[0].startswith("# "), "the first cell is the title/TOC header"
    assert "## Contents" in sources[0]
    assert any("lammpskill" in s and "detect" in s for s in sources[:3]), "a Setup cell near the top"
    assert "tally" in sources[-1].lower(), "the last cell tallies what the chapter claimed"
    assert nb["cells"][-1]["cell_type"] == "code"


def test_assembled_notebooks_carry_no_outputs(tmp_path):
    """assemble writes the source; execute.py produces outputs. A committed notebook with stale
    outputs is how a chapter starts lying about what it computed."""
    for key in asm.CHAPTERS:
        nb = json.loads(open(asm.assemble_one(key, str(tmp_path)), encoding="utf-8").read())
        for c in nb["cells"]:
            if c["cell_type"] == "code":
                assert c["outputs"] == [] and c["execution_count"] is None


def test_every_notebook_is_within_the_size_cap(tmp_path):
    for key in asm.CHAPTERS:
        path = asm.assemble_one(key, str(tmp_path))
        assert os.path.getsize(path) < NB_MAX, "%s over the rule-25 cap before outputs" % key


def test_chapters_that_claim_no_lammps_do_not_call_the_runner():
    """Chapters 00, 07, 08 and 09 are the ones a reviewer can run without installing LAMMPS
    (plan 1b). If one of them reaches for the runner, that promise is broken."""
    for key, ch in asm.CHAPTERS.items():
        if ch.get("needs_lammps"):
            continue
        body = "\n".join(src for kind, src in ch["module"].CELLS if kind == "code")
        for forbidden in ("lammpskill.run.run(", "from lammpskill.run import run\n", "SubprocessBackend"):
            assert forbidden not in body, "%s claims no LAMMPS but uses %s" % (key, forbidden)


def test_every_plot_is_captioned():
    """Rule 22: every figure the notebooks generate needs its caption for the course.
    A caption() call must immediately follow every plt.show() in a chapter's code cells,
    so extract_figures.py (course/tools/) always finds one to attach."""
    for key, ch in asm.CHAPTERS.items():
        body = "\n".join(src for kind, src in ch["module"].CELLS if kind == "code")
        assert body.count("plt.show()") == body.count("caption("), (
            "%s: %d plt.show() but %d caption() calls"
            % (key, body.count("plt.show()"), body.count("caption(")))


def test_setup_cell_defines_caption():
    assert "def caption(" in asm.SETUP and "_FIG = {" in asm.SETUP


def test_assemble_cli_lists_without_writing(tmp_path):
    p = subprocess.run([sys.executable, os.path.join(BUILD, "assemble.py"), "--list"],
                       capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
    for key in asm.CHAPTERS:
        assert key in p.stdout
    assert not list(tmp_path.glob("*.ipynb"))


def test_build_parser_flags_are_documented():
    flags = set()
    for a in asm.build_parser()._actions:
        flags.update(a.option_strings)
    agents = open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8").read()
    manual = open(os.path.join(ROOT, "docs", "USER_MANUAL.md"), encoding="utf-8").read()
    for f in flags:
        if f in ("-h", "--help"):
            continue
        assert f in agents, "build/assemble.py %s missing from AGENTS.md" % f
        assert f in manual, "build/assemble.py %s missing from docs/USER_MANUAL.md" % f


@pytest.mark.parametrize("key", sorted(asm.CHAPTERS))
def test_chapter_title_and_toc_agree(key, tmp_path):
    ch = asm.CHAPTERS[key]
    nb = json.loads(open(asm.assemble_one(key, str(tmp_path)), encoding="utf-8").read())
    header = "".join(nb["cells"][0]["source"]) if isinstance(nb["cells"][0]["source"], list) else nb["cells"][0]["source"]
    assert ch["title"] in header
    # every "## " section in the body appears in the header's contents list
    body_sections = [src.splitlines()[0][3:].strip()
                     for kind, src in ch["module"].CELLS
                     if kind == "md" and src.lstrip().startswith("## ")]
    for sec in body_sections:
        assert sec in header, "%s: section %r missing from the contents" % (key, sec)
