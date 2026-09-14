# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""lammpskill.viz: headless atom rendering (ASE + matplotlib), no display, no OVITO (pinned).
Not a visual-regression suite -- these assert the functions run headlessly and produce real,
non-trivial image/GIF bytes, not that a render looks like anything specific.

ase is an optional extra (pyproject.toml), not a core dependency -- skip like every other
optional-backend test in this suite (tests/test_io_backends.py's own convention), not error."""

import os

import numpy as np
import pytest

from lammpskill.io import backends

_NO_ASE = backends.available()["ase"] is None
_SKIP_ASE = pytest.mark.skipif(_NO_ASE, reason="ase not installed")

if not _NO_ASE:
    from lammpskill import viz

POS = np.array([[0.0, 0.0, 0.0], [1.8, 1.8, 0.0], [1.8, 0.0, 1.8], [0.0, 1.8, 1.8]])
CELL = np.array([3.6, 3.6, 3.6])


@_SKIP_ASE
def test_snapshot_with_symbols_returns_a_figure():
    fig = viz.snapshot(POS, CELL, symbols=["Cu"] * 4)
    assert fig.axes, "the figure has at least one axes with the rendered atoms"


@_SKIP_ASE
def test_snapshot_with_masses_guesses_the_element():
    fig = viz.snapshot(POS, CELL, masses=[63.546] * 4)   # Cu's real atomic mass
    assert fig.axes


@_SKIP_ASE
def test_snapshot_requires_exactly_one_of_symbols_or_masses():
    with pytest.raises(ValueError):
        viz.snapshot(POS, CELL)
    with pytest.raises(ValueError):
        viz.snapshot(POS, CELL, symbols=["Cu"] * 4, masses=[63.546] * 4)


@_SKIP_ASE
def test_snapshot_symbols_length_must_match_positions():
    with pytest.raises(ValueError):
        viz.snapshot(POS, CELL, symbols=["Cu"] * 3)


@_SKIP_ASE
def test_animate_gif_writes_a_real_gif(tmp_path):
    frames = [POS, POS + 0.1, POS + 0.2]
    out = viz.animate_gif(frames, CELL, str(tmp_path / "anim.gif"), symbols=["Ar"] * 4, fps=4)
    assert out == str(tmp_path / "anim.gif")
    with open(out, "rb") as f:
        header = f.read(6)
    assert header in (b"GIF87a", b"GIF89a")
    assert os.path.getsize(out) > 500, "a 3-frame, 4-atom GIF should be a real, non-trivial file"


def test_viz_module_import_does_not_require_ase():
    """lammpskill.viz itself must import cleanly with no ase installed -- only calling
    snapshot()/animate_gif() should need the extra (mirrors lammpskill.io.backends: importing
    the module is always safe, only using a specific backend raises)."""
    import importlib
    import lammpskill.viz as v
    importlib.reload(v)   # a fresh import, not whatever was already cached by the module above
