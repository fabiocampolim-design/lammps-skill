# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""lammpskill.viz: headless atom rendering (ASE + matplotlib), no display, no OVITO (pinned).
Not a visual-regression suite -- these assert the functions run headlessly and produce real,
non-trivial image/GIF bytes, not that a render looks like anything specific."""

import os

import numpy as np
import pytest

from lammpskill import viz

POS = np.array([[0.0, 0.0, 0.0], [1.8, 1.8, 0.0], [1.8, 0.0, 1.8], [0.0, 1.8, 1.8]])
CELL = np.array([3.6, 3.6, 3.6])


def test_snapshot_with_symbols_returns_a_figure():
    fig = viz.snapshot(POS, CELL, symbols=["Cu"] * 4)
    assert fig.axes, "the figure has at least one axes with the rendered atoms"


def test_snapshot_with_masses_guesses_the_element():
    fig = viz.snapshot(POS, CELL, masses=[63.546] * 4)   # Cu's real atomic mass
    assert fig.axes


def test_snapshot_requires_exactly_one_of_symbols_or_masses():
    with pytest.raises(ValueError):
        viz.snapshot(POS, CELL)
    with pytest.raises(ValueError):
        viz.snapshot(POS, CELL, symbols=["Cu"] * 4, masses=[63.546] * 4)


def test_snapshot_symbols_length_must_match_positions():
    with pytest.raises(ValueError):
        viz.snapshot(POS, CELL, symbols=["Cu"] * 3)


def test_animate_gif_writes_a_real_gif(tmp_path):
    frames = [POS, POS + 0.1, POS + 0.2]
    out = viz.animate_gif(frames, CELL, str(tmp_path / "anim.gif"), symbols=["Ar"] * 4, fps=4)
    assert out == str(tmp_path / "anim.gif")
    with open(out, "rb") as f:
        header = f.read(6)
    assert header in (b"GIF87a", b"GIF89a")
    assert os.path.getsize(out) > 500, "a 3-frame, 4-atom GIF should be a real, non-trivial file"
