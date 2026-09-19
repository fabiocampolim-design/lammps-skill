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


def test_pdf_env_prefers_tex_lives_own_fontconfig(tmp_path, monkeypatch):
    """Regression: TeX Live's xelatex on Windows failed with 'Fontconfig error: Cannot load
    default config file' even with the requested fonts installed system-wide, and even with NO
    conda environment active -- this is the exact condition the first version of this fix
    (conda-only) left untested and unfixed, caught by an independent /code-review the same
    session and cross-referenced to a prior, more general diagnosis of the same root cause
    (KEEP rules/07, 2026-09-02): TeX Live ships its own fontconfig config, findable relative to
    wherever the engine binary itself is, with no dependency on conda at all."""
    import build_manual
    engine_path = tmp_path / "texlive" / "2026" / "bin" / "windows" / "xelatex.exe"
    engine_path.parent.mkdir(parents=True)
    engine_path.write_text("", encoding="utf-8")
    fonts_conf = tmp_path / "texlive" / "2026" / "tlpkg" / "tlpostcode" / "xetex" / "conf" / "fonts.conf"
    fonts_conf.parent.mkdir(parents=True)
    fonts_conf.write_text("<fontconfig/>", encoding="utf-8")
    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    monkeypatch.delenv("FONTCONFIG_PATH", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.setattr(build_manual.shutil, "which", lambda name: str(engine_path))
    assert build_manual._pdf_env("xelatex")["FONTCONFIG_FILE"] == str(fonts_conf)


def test_pdf_env_falls_back_to_conda_when_tex_lives_own_layout_is_absent(tmp_path, monkeypatch):
    """The conda fallback still matters when the engine isn't laid out like a normal TeX Live
    install (a case shutil.which can't distinguish from the real one without checking)."""
    import build_manual
    fonts_conf = tmp_path / "Library" / "etc" / "fonts" / "fonts.conf"
    fonts_conf.parent.mkdir(parents=True)
    fonts_conf.write_text("<fontconfig/>", encoding="utf-8")
    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    monkeypatch.delenv("FONTCONFIG_PATH", raising=False)
    monkeypatch.setenv("CONDA_PREFIX", str(tmp_path))
    monkeypatch.setattr(build_manual.shutil, "which", lambda name: None)
    assert build_manual._pdf_env("xelatex")["FONTCONFIG_FILE"] == str(fonts_conf)


def test_pdf_env_leaves_an_existing_fontconfig_setting_alone(monkeypatch):
    import build_manual
    monkeypatch.setenv("FONTCONFIG_FILE", "/already/set.conf")
    assert build_manual._pdf_env()["FONTCONFIG_FILE"] == "/already/set.conf"


def test_pdf_env_is_a_harmless_noop_when_neither_layout_is_found(monkeypatch):
    """Neither fix applies (no TeX Live layout, no conda fonts.conf): _pdf_env() must not crash
    or fabricate a path -- the caller's own subprocess call will then fail exactly as before,
    which is honest, not a silent wrong answer."""
    import build_manual
    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    monkeypatch.delenv("FONTCONFIG_PATH", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.setattr(build_manual.shutil, "which", lambda name: None)
    env = build_manual._pdf_env("xelatex")
    assert "FONTCONFIG_FILE" not in env


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
