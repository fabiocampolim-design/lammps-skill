# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Orthogonal periodic box for mdlite (independent of lammpskill.io on purpose: the engine teaches, the toolkit drives)."""

import numpy as np


class Box:
    def __init__(self, lengths, lo=(0.0, 0.0, 0.0)):
        self.lengths = np.asarray(lengths, float)
        self.lo = np.asarray(lo, float)
        if np.any(self.lengths <= 0):
            raise ValueError("box lengths must be positive")

    @property
    def hi(self):
        return self.lo + self.lengths

    @property
    def volume(self):
        return float(np.prod(self.lengths))

    def wrap(self, x):
        return self.lo + np.mod(np.asarray(x, float) - self.lo, self.lengths)

    def minimum_image(self, d):
        d = np.asarray(d, float)
        return d - self.lengths * np.round(d / self.lengths)
