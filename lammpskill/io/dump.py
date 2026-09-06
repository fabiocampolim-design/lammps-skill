# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""LAMMPS text dump files (`dump atom` / `dump custom`), written from the manual's dump description and from files
LAMMPS wrote here. Frames are ordered by atom id; scaled (xs) and unwrapped (xu) coordinates are recognised."""

from __future__ import annotations

import gzip

import numpy as np

from .box import Box


class Frame:
    def __init__(self, timestep, natoms, box, boundary, columns, data):
        self.timestep, self.natoms, self.box, self.boundary = int(timestep), int(natoms), box, tuple(boundary)
        self.columns, self.data = list(columns), np.asarray(data, float)

    def get(self, col):
        return self.data[:, self.columns.index(col)]

    @property
    def ids(self):
        return self.get("id").astype(int)

    @property
    def types(self):
        return self.get("type").astype(int)

    @property
    def positions(self):
        c = self.columns
        if all(k in c for k in ("x", "y", "z")):
            return np.column_stack([self.get("x"), self.get("y"), self.get("z")])
        if all(k in c for k in ("xu", "yu", "zu")):
            return np.column_stack([self.get("xu"), self.get("yu"), self.get("zu")])
        if all(k in c for k in ("xs", "ys", "zs")):
            return self.box.cartesian(np.column_stack([self.get("xs"), self.get("ys"), self.get("zs")]))
        raise KeyError("no x/y/z, xu/yu/zu or xs/ys/zs columns in %s" % c)

    def sorted_by_id(self):
        order = np.argsort(self.ids)
        return Frame(self.timestep, self.natoms, self.box, self.boundary, self.columns, self.data[order])


class Trajectory:
    def __init__(self, frames):
        self.frames = list(frames)

    @property
    def timesteps(self):
        return [f.timestep for f in self.frames]

    @property
    def box(self):
        return self.frames[0].box

    @property
    def positions(self):
        return np.stack([f.positions for f in self.frames])

    def __len__(self):
        return len(self.frames)


def _open(path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, encoding="utf-8", errors="replace")


def _box_from_bounds(header, rows):
    parts = header.split()
    tilt = "xy" in parts
    boundary = tuple(parts[-3:])
    vals = [[float(v) for v in r.split()] for r in rows]
    if tilt:
        (xlo_b, xhi_b, xy), (ylo_b, yhi_b, xz), (zlo_b, zhi_b, yz) = vals
        # manual (Howto_triclinic): the bounds include the tilt; recover the box
        xlo = xlo_b - min(0.0, xy, xz, xy + xz)
        xhi = xhi_b - max(0.0, xy, xz, xy + xz)
        ylo = ylo_b - min(0.0, yz)
        yhi = yhi_b - max(0.0, yz)
        return Box(xlo, xhi, ylo, yhi, zlo_b, zhi_b, xy, xz, yz), boundary
    (xlo, xhi), (ylo, yhi), (zlo, zhi) = vals
    return Box(xlo, xhi, ylo, yhi, zlo, zhi), boundary


def iter_dump(path):
    with _open(path) as f:
        line = f.readline()
        while line:
            if not line.startswith("ITEM: TIMESTEP"):
                line = f.readline()
                continue
            timestep = int(f.readline().split()[0])
            assert f.readline().startswith("ITEM: NUMBER OF ATOMS")
            natoms = int(f.readline().split()[0])
            bh = f.readline()
            assert bh.startswith("ITEM: BOX BOUNDS")
            box, boundary = _box_from_bounds(bh, [f.readline() for _ in range(3)])
            ah = f.readline()
            assert ah.startswith("ITEM: ATOMS")
            columns = ah.split()[2:]
            rows = [f.readline().split() for _ in range(natoms)]
            data = np.array(rows, dtype=float) if rows else np.zeros((0, len(columns)))
            fr = Frame(timestep, natoms, box, boundary, columns, data)
            yield fr.sorted_by_id() if "id" in columns else fr
            line = f.readline()


def read_dump(path, every=1, max_frames=None) -> Trajectory:
    frames = []
    for k, fr in enumerate(iter_dump(path)):
        if k % every:
            continue
        frames.append(fr)
        if max_frames is not None and len(frames) >= max_frames:
            break
    return Trajectory(frames)


def write_dump(frames, path) -> None:
    out = []
    for fr in frames:
        out += ["ITEM: TIMESTEP", str(fr.timestep), "ITEM: NUMBER OF ATOMS", str(fr.natoms)]
        b = fr.box
        if b.is_triclinic:
            out.append("ITEM: BOX BOUNDS xy xz yz %s" % " ".join(fr.boundary))
            out += ["%.16g %.16g %.16g" % (b.xlo + min(0.0, b.xy, b.xz, b.xy + b.xz), b.xhi + max(0.0, b.xy, b.xz, b.xy + b.xz), b.xy),
                    "%.16g %.16g %.16g" % (b.ylo + min(0.0, b.yz), b.yhi + max(0.0, b.yz), b.xz),
                    "%.16g %.16g %.16g" % (b.zlo, b.zhi, b.yz)]
        else:
            out.append("ITEM: BOX BOUNDS %s" % " ".join(fr.boundary))
            out += ["%.16g %.16g" % (b.xlo, b.xhi), "%.16g %.16g" % (b.ylo, b.yhi), "%.16g %.16g" % (b.zlo, b.zhi)]
        out.append("ITEM: ATOMS " + " ".join(fr.columns))
        for row in fr.data:
            out.append(" ".join(("%d" % v) if c in ("id", "type", "mol", "ix", "iy", "iz") else ("%.16g" % v) for c, v in zip(fr.columns, row)))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
