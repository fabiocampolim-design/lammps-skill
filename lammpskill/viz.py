# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Headless atom rendering: a static snapshot and an animated GIF, both from plain numpy arrays
-- never mdlite.box.Box or lammpskill.io.box.Box directly (this project's own recorded pitfall is
mixing those two incompatible classes; a caller with either one converts once, at the call site,
via its own `.lengths`/`.matrix` attribute).

Built on ASE's plot_atoms (ase.visualize.plot) on a matplotlib Agg-backend figure, and
matplotlib.animation.PillowWriter for the GIF -- both confirmed working headless, no display, no
ffmpeg (2026-09-14). OVITO is not used here; it remains an optional bridge
(lammpskill.io.backends.ovito_pipeline) pinned for a future, separate pass.

Every call needs exactly one of `symbols` (explicit chemical symbols -- required for a reduced
Lennard-Jones system, which has no real element: pass a conventional stand-in like "Ar", never a
reduced mass value) or `masses` (real atomic mass in amu, for a system where every atom really is
a physical element -- the symbol is then guessed the same way
lammpskill.io.backends.to_ase() already guesses it).
"""

from __future__ import annotations

import numpy as np


def _require_ase():
    try:
        import ase           # noqa: F401
        import matplotlib
    except ImportError as e:
        raise ImportError("lammpskill.viz needs the 'ase' extra: pip install lammps-skill[ase] "
                          "(or: pip install ase)") from e
    return ase, matplotlib


def _symbols_from(positions, symbols, masses):
    n = len(positions)
    if (symbols is None) == (masses is None):
        raise ValueError("pass exactly one of symbols= or masses=")
    if symbols is not None:
        if len(symbols) != n:
            raise ValueError("symbols must have one entry per atom (%d != %d)" % (len(symbols), n))
        return list(symbols)
    from .io.backends import _mass_to_symbol
    if len(masses) != n:
        raise ValueError("masses must have one entry per atom (%d != %d)" % (len(masses), n))
    return [_mass_to_symbol(m) for m in masses]


def _cell_matrix(cell):
    cell = np.asarray(cell, float)
    if cell.shape == (3,):
        return np.diag(cell)
    if cell.shape == (3, 3):
        return cell
    raise ValueError("cell must be a (3,) box-length vector or a (3,3) matrix, got shape %s" % (cell.shape,))


def _make_atoms(positions, cell, symbols):
    ase, _ = _require_ase()
    return ase.Atoms(symbols=symbols, positions=np.asarray(positions, float),
                     cell=_cell_matrix(cell), pbc=True)


def snapshot(positions, cell, symbols=None, masses=None, rotation="15x,-15y,0z",
             figsize=(4, 4), ax=None):
    """One static render of `positions` ((N,3) array) in a box `cell` ((3,) lengths or (3,3)
    matrix). Returns the Figure; the caller decides whether to plt.show()+caption() it (the
    chapter convention) -- this function never calls plt.show or savefig itself."""
    _, matplotlib = _require_ase()
    import matplotlib.pyplot as plt
    from ase.visualize.plot import plot_atoms

    syms = _symbols_from(positions, symbols, masses)
    atoms = _make_atoms(positions, cell, syms)
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure
    plot_atoms(atoms, ax, radii=0.5, rotation=rotation)
    ax.set_axis_off()
    return fig


def animate_gif(frames_positions, cell, path, symbols=None, masses=None, fps=8,
                rotation="15x,-15y,0z", figsize=(4, 4)):
    """One animated GIF, one rendered frame per entry of `frames_positions` (list of (N,3)
    arrays, same N throughout), written to `path`. Returns `path`. The caller embeds it in a
    notebook cell via `IPython.display.Image(filename=path)` -- this function never displays
    anything itself, matching snapshot()'s convention."""
    _, matplotlib = _require_ase()
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    from ase.visualize.plot import plot_atoms

    syms = _symbols_from(frames_positions[0], symbols, masses)
    fig, ax = plt.subplots(figsize=figsize)

    def draw(i):
        ax.clear()
        ax.set_axis_off()
        atoms = _make_atoms(frames_positions[i], cell, syms)
        plot_atoms(atoms, ax, radii=0.5, rotation=rotation)
        return ()

    anim = animation.FuncAnimation(fig, draw, frames=len(frames_positions))
    anim.save(path, writer=animation.PillowWriter(fps=fps))
    plt.close(fig)
    return path
