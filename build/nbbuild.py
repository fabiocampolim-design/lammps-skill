# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Notebook writer for the lammps-skill chapters.

Each chapter module in this directory defines ``CELLS = [("md", "..."), ("code", "..."), ...]``.
``assemble.py`` prepends a generated header (title + contents) and appends a generated tally cell,
then writes ``chapters/LAMMPS_NN_Slug.ipynb`` with **no outputs** -- ``execute.py`` produces those.

The chapters are generated so that a correction is made once, in Python, and re-assembled; editing
a ``.ipynb`` by hand is what the project's CLAUDE.md forbids.
"""

import hashlib
import json

KERNELSPEC = {
    "display_name": "Python 3.12 (miniconda - lammps)",
    "language": "python",
    "name": "lammps-mc",
}


def md(source):
    return ("md", source)


def code(source):
    return ("code", source)


def cell_id(kind, source, n):
    """Stable per-cell id (nbformat 4.5+ requires one). Derived from the content, so re-assembling
    an unchanged chapter produces an unchanged file and a diff means the text really changed."""
    h = hashlib.sha256(("%d:%s:%s" % (n, kind, source)).encode("utf-8")).hexdigest()
    return h[:12]


def make_cell(kind, source, n=0):
    src = source.strip("\n")
    common = {"metadata": {}, "source": src, "id": cell_id(kind, src, n)}
    if kind == "md":
        return dict(common, cell_type="markdown")
    return dict(common, cell_type="code", execution_count=None, outputs=[])


def write_notebook(cells, path):
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": dict(KERNELSPEC),
            "language_info": {"name": "python", "version": "3.12"},
        },
        "cells": [make_cell(kind, src, n) for n, (kind, src) in enumerate(cells)],
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return path


def anchor(title):
    """The GitHub/Jupyter anchor for a `## title` heading."""
    keep = [c.lower() if c.isalnum() else ("-" if c in " -_" else "") for c in title]
    return "".join(keep)
