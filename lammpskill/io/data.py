# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""LAMMPS data files (read_data / write_data format), written from the manual's read_data description and from
files LAMMPS wrote on this machine. Supports the atom styles listed in ATOM_STYLE_COLUMNS, optional image flags,
Masses, coefficient sections (kept as raw lines), Velocities, Bonds/Angles/Dihedrals/Impropers."""

from __future__ import annotations

import numpy as np

from .box import Box

ATOM_STYLE_COLUMNS = {
    "atomic": ("id", "type", "x", "y", "z"),
    "charge": ("id", "type", "q", "x", "y", "z"),
    "bond": ("id", "mol", "type", "x", "y", "z"),
    "angle": ("id", "mol", "type", "x", "y", "z"),
    "molecular": ("id", "mol", "type", "x", "y", "z"),
    "full": ("id", "mol", "type", "q", "x", "y", "z"),
    "sphere": ("id", "type", "diameter", "density", "x", "y", "z"),
}
_INT_COLS = {"id", "type", "mol", "ix", "iy", "iz"}
_HEADER_COUNTS = {"atoms": "natoms", "bonds": "nbonds", "angles": "nangles", "dihedrals": "ndihedrals", "impropers": "nimpropers",
                  "atom types": "ntypes", "bond types": "nbondtypes", "angle types": "nangletypes",
                  "dihedral types": "ndihedraltypes", "improper types": "nimpropertypes"}
_TOPOLOGY = {"Bonds": ("bonds", 4), "Angles": ("angles", 5), "Dihedrals": ("dihedrals", 6), "Impropers": ("impropers", 6)}
_COEFF_SECTIONS = ("Pair Coeffs", "PairIJ Coeffs", "Bond Coeffs", "Angle Coeffs", "Dihedral Coeffs", "Improper Coeffs",
                   "BondBond Coeffs", "BondAngle Coeffs", "MiddleBondTorsion Coeffs", "EndBondTorsion Coeffs",
                   "AngleTorsion Coeffs", "AngleAngleTorsion Coeffs", "BondBond13 Coeffs", "AngleAngle Coeffs")
_SECTIONS = ("Masses", "Atoms", "Velocities") + tuple(_TOPOLOGY) + _COEFF_SECTIONS


class DataFile:
    def __init__(self, comment="", atom_style="atomic", box=None, masses=None, atoms=None, velocities=None,
                 bonds=None, angles=None, dihedrals=None, impropers=None, counts=None, coeffs=None):
        self.comment = comment
        self.atom_style = atom_style
        self.box = box
        self.masses = dict(masses or {})
        self.atoms = dict(atoms or {})
        self.velocities = velocities
        self.bonds, self.angles, self.dihedrals, self.impropers = bonds, angles, dihedrals, impropers
        self.counts = dict(counts or {})
        self.coeffs = dict(coeffs or {})

    @property
    def natoms(self):
        return int(len(self.atoms["id"])) if "id" in self.atoms else int(self.counts.get("natoms", 0))

    @property
    def ntypes(self):
        if "ntypes" in self.counts:
            return int(self.counts["ntypes"])
        if self.masses:
            return int(max(self.masses))
        return int(self.atoms["type"].max()) if "type" in self.atoms else 0

    @property
    def positions(self):
        return np.column_stack([self.atoms["x"], self.atoms["y"], self.atoms["z"]])

    @property
    def types(self):
        return self.atoms["type"]

    @property
    def ids(self):
        return self.atoms["id"]

    @classmethod
    def from_arrays(cls, box, types, positions, masses, atom_style="atomic", comment="", charges=None, mol=None,
                    velocities=None, ids=None):
        n = len(types)
        cols = ATOM_STYLE_COLUMNS[atom_style]
        atoms = {"id": np.asarray(ids if ids is not None else np.arange(1, n + 1), int), "type": np.asarray(types, int)}
        pos = np.asarray(positions, float)
        atoms["x"], atoms["y"], atoms["z"] = pos[:, 0], pos[:, 1], pos[:, 2]
        if "q" in cols:
            atoms["q"] = np.asarray(charges if charges is not None else np.zeros(n), float)
        if "mol" in cols:
            atoms["mol"] = np.asarray(mol if mol is not None else np.ones(n), int)
        for extra in cols:
            if extra not in atoms:
                atoms[extra] = np.zeros(n)
        counts = {"natoms": n, "ntypes": max(masses) if masses else int(atoms["type"].max())}
        return cls(comment=comment, atom_style=atom_style, box=box, masses=masses, atoms=atoms,
                   velocities=None if velocities is None else np.asarray(velocities, float), counts=counts)


def _section_name(line):
    s = line.split("#")[0].strip()
    return s if s in _SECTIONS else None


def read_data(path, atom_style=None) -> DataFile:
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    df = DataFile(comment=lines[0].strip() if lines else "")
    i = 1
    header, box_lines = {}, []
    while i < len(lines) and _section_name(lines[i]) is None:
        s = lines[i].split("#")[0].strip()
        if s:
            parts = s.split()
            key = " ".join(parts[1:])
            if key in _HEADER_COUNTS:
                header[_HEADER_COUNTS[key]] = int(parts[0])
            elif (len(parts) >= 3 and parts[2] in ("xlo", "ylo", "zlo")) or (len(parts) >= 6 and parts[3] == "xy"):
                box_lines.append(s)
        i += 1
    df.counts = header
    df.box = Box.from_data_lines(box_lines)
    while i < len(lines):
        name = _section_name(lines[i])
        if name is None:
            i += 1
            continue
        comment = lines[i].split("#", 1)[1].strip() if "#" in lines[i] else ""
        i += 1
        body = []
        while i < len(lines) and _section_name(lines[i]) is None:
            raw = lines[i].strip()
            s = raw if (name == "Masses" or name in _COEFF_SECTIONS) else raw.split("#")[0].strip()
            if s:
                body.append(s)
            i += 1
        if name == "Masses":
            for b in body:
                p = b.split("#")[0].split()
                df.masses[int(p[0])] = float(p[1])
        elif name == "Atoms":
            style = comment or atom_style
            if not style:
                raise ValueError("Atoms section has no '# style' comment: pass atom_style=")
            if style not in ATOM_STYLE_COLUMNS:
                raise ValueError("unsupported atom_style %r (known: %s)" % (style, ", ".join(ATOM_STYLE_COLUMNS)))
            df.atom_style = style
            cols = ATOM_STYLE_COLUMNS[style]
            rows = [b.split() for b in body]
            width = len(rows[0]) if rows else len(cols)
            if width == len(cols) + 3:
                cols = cols + ("ix", "iy", "iz")
            elif width != len(cols):
                raise ValueError("Atoms # %s: expected %d or %d columns, found %d" % (style, len(cols), len(cols) + 3, width))
            arr = np.array(rows, dtype=float)
            for k, c in enumerate(cols):
                df.atoms[c] = arr[:, k].astype(int) if c in _INT_COLS else arr[:, k]
        elif name == "Velocities":
            arr = np.array([b.split()[:4] for b in body], dtype=float)
            order = np.argsort(arr[:, 0].astype(int))
            df.velocities = arr[order, 1:4]
        elif name in _TOPOLOGY:
            attr, width = _TOPOLOGY[name]
            setattr(df, attr, np.array([[int(v) for v in b.split()[:width]] for b in body], dtype=int))
        elif name in _COEFF_SECTIONS:
            df.coeffs[name] = body
    if "id" in df.atoms:
        order = np.argsort(df.atoms["id"])
        for k in df.atoms:
            df.atoms[k] = df.atoms[k][order]
    return df


def _fmt(v, col):
    return "%d" % int(v) if col in _INT_COLS else "%.16g" % float(v)


def write_data(df: DataFile, path) -> None:
    cols = list(ATOM_STYLE_COLUMNS[df.atom_style])
    if all(c in df.atoms for c in ("ix", "iy", "iz")):
        cols += ["ix", "iy", "iz"]
    out = [df.comment or "LAMMPS data file written by lammps-skill", ""]
    out.append("%d atoms" % df.natoms)
    for key, attr in (("bonds", "bonds"), ("angles", "angles"), ("dihedrals", "dihedrals"), ("impropers", "impropers")):
        arr = getattr(df, attr)
        if arr is not None and len(arr):
            out.append("%d %s" % (len(arr), key))
    out.append("%d atom types" % df.ntypes)
    for key, cnt in (("bond types", "nbondtypes"), ("angle types", "nangletypes"), ("dihedral types", "ndihedraltypes"), ("improper types", "nimpropertypes")):
        if df.counts.get(cnt):
            out.append("%d %s" % (df.counts[cnt], key))
    out.append("")
    out.extend(df.box.as_data_lines())
    if df.masses:
        out += ["", "Masses", ""] + ["%d %.16g" % (t, m) for t, m in sorted(df.masses.items())]
    for name in _COEFF_SECTIONS:
        if name in df.coeffs:
            out += ["", name, ""] + list(df.coeffs[name])
    out += ["", "Atoms # %s" % df.atom_style, ""]
    n = df.natoms
    for r in range(n):
        out.append(" ".join(_fmt(df.atoms[c][r], c) for c in cols))
    if df.velocities is not None:
        out += ["", "Velocities", ""] + ["%d %.16g %.16g %.16g" % (df.atoms["id"][r], *df.velocities[r]) for r in range(n)]
    for name, (attr, _w) in _TOPOLOGY.items():
        arr = getattr(df, attr)
        if arr is not None and len(arr):
            out += ["", name, ""] + [" ".join(str(int(v)) for v in row) for row in arr]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
