# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Optional bridges to the ecosystem. Every import is local to the function that needs it; nothing here is required
by the rest of lammpskill. Licences: lammps GPL-2.0, ase LGPL-2.1, pymatgen MIT, MDAnalysis GPL-2.0, ovito GPL-3.0/MIT."""

from __future__ import annotations

import importlib

import numpy as np

from .box import Box
from .data import DataFile

_HINTS = {
    "lammps": ("pip install lammps  (third-party wheel, GPL-2.0) or the python module of your LAMMPS build", "GPL-2.0"),
    "ase": ("pip install ase", "LGPL-2.1"),
    "pymatgen": ("pip install pymatgen", "MIT"),
    "MDAnalysis": ("pip install MDAnalysis", "GPL-2.0"),
    "ovito": ("conda install -c conda-forge ovito  (or pip install ovito)", "GPL-3.0 / MIT modules"),
}


class BackendUnavailable(ImportError):
    pass


def _import(name):
    return importlib.import_module(name)


def _need(name):
    try:
        return _import(name)
    except ImportError as e:
        hint, lic = _HINTS[name]
        raise BackendUnavailable("%s is not installed: %s (licence %s). It is optional; lammpskill works without it." % (name, hint, lic)) from e


def available() -> dict:
    out = {}
    for name in _HINTS:
        try:
            mod = _import(name)
            out[name] = str(getattr(mod, "__version__", "installed"))
        except Exception:
            out[name] = None
    return out


def _mass_to_symbol(mass):
    try:
        ase_data = _need("ase.data")
        diffs = np.abs(np.array(ase_data.atomic_masses[1:]) - mass)
        return ase_data.chemical_symbols[int(np.argmin(diffs)) + 1]
    except (BackendUnavailable, KeyError):
        return "X"


def to_ase(obj):
    ase = _need("ase")
    if isinstance(obj, DataFile):
        pos, types, box = obj.positions, obj.types, obj.box
        symbols = [_mass_to_symbol(obj.masses.get(int(t), 1.0)) for t in types]
        masses = [obj.masses.get(int(t)) for t in types]
    else:  # Frame
        pos, types, box = obj.positions, obj.types, obj.box
        symbols, masses = ["X"] * len(types), None
    atoms = ase.Atoms(symbols=symbols, positions=pos - box.lo, cell=box.matrix, pbc=True)
    atoms.set_tags(types)
    if masses and all(m is not None for m in masses):
        atoms.set_masses(masses)
    return atoms


def from_ase(atoms, masses=None) -> DataFile:
    _need("ase")
    cell = np.asarray(atoms.cell)
    box = Box(0, cell[0, 0], 0, cell[1, 1], 0, cell[2, 2], cell[1, 0], cell[2, 0], cell[2, 1])
    tags = np.asarray(atoms.get_tags())
    if tags.max() == 0:
        symbols = list(dict.fromkeys(atoms.get_chemical_symbols()))
        types = np.array([symbols.index(s) + 1 for s in atoms.get_chemical_symbols()])
    else:
        types = tags.astype(int)
    m = dict(masses or {})
    for t, mass in zip(types, atoms.get_masses()):
        m.setdefault(int(t), float(mass))
    return DataFile.from_arrays(box=box, types=types, positions=np.asarray(atoms.positions), masses=m, atom_style="atomic")


def to_pymatgen(obj):
    _need("pymatgen")
    from pymatgen.core import Lattice, Structure
    pos, types, box = obj.positions, obj.types, obj.box
    species = [_mass_to_symbol(obj.masses.get(int(t), 1.0)) if isinstance(obj, DataFile) else "H" for t in types]
    return Structure(Lattice(box.matrix), species, pos - box.lo, coords_are_cartesian=True)


def mdanalysis_universe(data_path, dump_path=None, atom_style=None):
    mda = _need("MDAnalysis")
    kw = {"atom_style": atom_style} if atom_style else {}
    if dump_path:
        return mda.Universe(data_path, dump_path, format="LAMMPSDUMP", topology_format="DATA", **kw)
    return mda.Universe(data_path, topology_format="DATA", **kw)


def ovito_pipeline(path):
    _need("ovito")
    from ovito.io import import_file
    return import_file(path)
