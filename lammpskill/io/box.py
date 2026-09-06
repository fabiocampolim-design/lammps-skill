# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Simulation box in LAMMPS conventions (bounds + tilt factors xy xz yz), orthogonal or triclinic."""

from __future__ import annotations

import numpy as np


class Box:
    def __init__(self, xlo, xhi, ylo, yhi, zlo, zhi, xy=0.0, xz=0.0, yz=0.0):
        self.xlo, self.xhi, self.ylo, self.yhi, self.zlo, self.zhi = map(float, (xlo, xhi, ylo, yhi, zlo, zhi))
        self.xy, self.xz, self.yz = map(float, (xy, xz, yz))
        if not (self.xhi > self.xlo and self.yhi > self.ylo and self.zhi > self.zlo):
            raise ValueError("box bounds must satisfy lo < hi")

    @property
    def lo(self):
        return np.array([self.xlo, self.ylo, self.zlo])

    @property
    def hi(self):
        return np.array([self.xhi, self.yhi, self.zhi])

    @property
    def lengths(self):
        return self.hi - self.lo

    @property
    def is_triclinic(self):
        return any(abs(t) > 0 for t in (self.xy, self.xz, self.yz))

    @property
    def matrix(self):
        """Cell vectors as rows: a = (lx,0,0), b = (xy,ly,0), c = (xz,yz,lz)."""
        lx, ly, lz = self.lengths
        return np.array([[lx, 0.0, 0.0], [self.xy, ly, 0.0], [self.xz, self.yz, lz]])

    @property
    def volume(self):
        return float(np.prod(self.lengths))

    def fractional(self, xyz):
        return np.linalg.solve(self.matrix.T, (np.asarray(xyz, float) - self.lo).T).T

    def cartesian(self, frac):
        return np.asarray(frac, float) @ self.matrix + self.lo

    def wrap(self, xyz):
        xyz = np.asarray(xyz, float)
        if not self.is_triclinic:
            return self.lo + np.mod(xyz - self.lo, self.lengths)
        f = self.fractional(xyz)
        return self.cartesian(f - np.floor(f))

    def minimum_image(self, d):
        d = np.asarray(d, float)
        if not self.is_triclinic:
            L = self.lengths
            return d - L * np.round(d / L)
        f = np.linalg.solve(self.matrix.T, d.T).T
        return (f - np.round(f)) @ self.matrix

    def as_data_lines(self):
        lines = ["%.16g %.16g xlo xhi" % (self.xlo, self.xhi), "%.16g %.16g ylo yhi" % (self.ylo, self.yhi),
                 "%.16g %.16g zlo zhi" % (self.zlo, self.zhi)]
        if self.is_triclinic:
            lines.append("%.16g %.16g %.16g xy xz yz" % (self.xy, self.xz, self.yz))
        return lines

    @classmethod
    def from_data_lines(cls, lines):
        vals = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 4 and parts[2] == "xlo":
                vals["x"] = (float(parts[0]), float(parts[1]))
            elif len(parts) >= 4 and parts[2] == "ylo":
                vals["y"] = (float(parts[0]), float(parts[1]))
            elif len(parts) >= 4 and parts[2] == "zlo":
                vals["z"] = (float(parts[0]), float(parts[1]))
            elif len(parts) >= 6 and parts[3] == "xy":
                vals["tilt"] = tuple(float(v) for v in parts[:3])
        if not all(k in vals for k in "xyz"):
            raise ValueError("box lines incomplete: need xlo xhi, ylo yhi, zlo zhi")
        t = vals.get("tilt", (0.0, 0.0, 0.0))
        return cls(*vals["x"], *vals["y"], *vals["z"], *t)

    def __repr__(self):
        return "Box(%s)" % ", ".join(self.as_data_lines())
