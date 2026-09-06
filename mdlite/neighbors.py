# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Cell list and Verlet list (Allen & Tildesley 2017, ch. 5): the two ideas that make MD O(N)."""

import numpy as np


class CellList:
    def __init__(self, box, rcut):
        self.box, self.rcut = box, float(rcut)
        self.ncell = np.maximum(1, np.floor(box.lengths / rcut).astype(int))
        self._i = self._j = None

    def build(self, pos):
        pos = self.box.wrap(pos)
        n = len(pos)
        if np.any(self.ncell < 3):  # tiny boxes: every cell is its own neighbour set; fall back to all pairs
            self._i, self._j = np.triu_indices(n, 1)
            return
        frac = (pos - self.box.lo) / self.box.lengths
        c = np.minimum((frac * self.ncell).astype(int), self.ncell - 1)
        cid = np.ravel_multi_index(c.T, self.ncell)
        order = np.argsort(cid, kind="stable")
        cid_sorted = cid[order]
        starts = np.searchsorted(cid_sorted, np.arange(int(np.prod(self.ncell)) + 1))
        I, J = [], []
        nx, ny, nz = self.ncell
        offsets = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]
        for cx in range(nx):
            for cy in range(ny):
                for cz in range(nz):
                    a = np.ravel_multi_index((cx, cy, cz), self.ncell)
                    mine = order[starts[a]:starts[a + 1]]
                    if len(mine) == 0:
                        continue
                    for dx, dy, dz in offsets:
                        b = np.ravel_multi_index(((cx + dx) % nx, (cy + dy) % ny, (cz + dz) % nz), self.ncell)
                        if b < a:
                            continue
                        other = order[starts[b]:starts[b + 1]]
                        if len(other) == 0:
                            continue
                        if b == a:
                            ii, jj = np.triu_indices(len(mine), 1)
                            I.append(mine[ii])
                            J.append(mine[jj])
                        else:
                            g = np.array(np.meshgrid(mine, other, indexing="ij")).reshape(2, -1)
                            I.append(np.minimum(g[0], g[1]))
                            J.append(np.maximum(g[0], g[1]))
        i = np.concatenate(I) if I else np.zeros(0, int)
        j = np.concatenate(J) if J else np.zeros(0, int)
        key = np.unique(i * n + j)
        self._i, self._j = key // n, key % n

    def pairs(self):
        return self._i, self._j


class VerletList:
    def __init__(self, box, rcut, skin=0.3):
        self.box, self.rcut, self.skin = box, float(rcut), float(skin)
        self.cells = CellList(box, rcut + skin)
        self.pairs = (np.zeros(0, int), np.zeros(0, int))
        self._ref = None
        self.nbuilds = 0

    def update(self, pos):
        pos = np.asarray(pos, float)
        if self._ref is not None and len(self._ref) == len(pos):
            disp = self.box.minimum_image(pos - self._ref)
            if np.sqrt((disp * disp).sum(1)).max() < 0.5 * self.skin:
                return False
        self.cells.build(pos)
        i, j = self.cells.pairs()
        d = self.box.minimum_image(pos[i] - pos[j])
        keep = (d * d).sum(1) < (self.rcut + self.skin) ** 2
        self.pairs = (i[keep], j[keep])
        self._ref = pos.copy()
        self.nbuilds += 1
        return True
