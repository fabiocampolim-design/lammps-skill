# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""EAM potential files in the DYNAMO setfl (`eam/alloy`) and funcfl (`eam`) layouts, from the manual's pair_eam page.
`synthetic_setfl` builds our own smooth test potential so no upstream potential file is ever tracked."""

from __future__ import annotations

import numpy as np


class EAMSetfl:
    def __init__(self, comments, elements, nrho, drho, nr, dr, cutoff, atomic_number, mass, lattice_constant, lattice, F, rho, rphi):
        c = list(comments)[:3]
        self.comments = c + [""] * (3 - len(c))
        self.elements = list(elements)
        self.nrho, self.drho, self.nr, self.dr, self.cutoff = int(nrho), float(drho), int(nr), float(dr), float(cutoff)
        self.atomic_number, self.mass = list(atomic_number), list(mass)
        self.lattice_constant, self.lattice = list(lattice_constant), list(lattice)
        self.F, self.rho, self.rphi = np.asarray(F, float), np.asarray(rho, float), np.asarray(rphi, float)

    @property
    def r(self):
        return np.arange(self.nr) * self.dr

    @property
    def rhogrid(self):
        return np.arange(self.nrho) * self.drho

    def pair_index(self, i, j):
        """setfl order: for i in elements, for j <= i: phi_ij — so (0,0), (1,0), (1,1), (2,0), (2,1), (2,2) …"""
        a, b = max(i, j), min(i, j)
        return a * (a + 1) // 2 + b


def _values(tokens, n, pos):
    return np.array(tokens[pos:pos + n], dtype=float), pos + n


def read_eam_setfl(path) -> EAMSetfl:
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    comments = lines[:3]
    hdr = lines[3].split()
    nel = int(hdr[0])
    elements = hdr[1:1 + nel]
    h5 = lines[4].split()
    nrho, drho, nr, dr, cutoff = int(h5[0]), float(h5[1]), int(h5[2]), float(h5[3]), float(h5[4])
    tokens = " ".join(lines[5:]).split()
    pos = 0
    Z, M, A, L, F, rho = [], [], [], [], [], []
    for _ in range(nel):
        Z.append(int(float(tokens[pos])))
        M.append(float(tokens[pos + 1]))
        A.append(float(tokens[pos + 2]))
        L.append(tokens[pos + 3])
        pos += 4
        fi, pos = _values(tokens, nrho, pos)
        ri, pos = _values(tokens, nr, pos)
        F.append(fi)
        rho.append(ri)
    npairs = nel * (nel + 1) // 2
    rphi = []
    for _ in range(npairs):
        p, pos = _values(tokens, nr, pos)
        rphi.append(p)
    return EAMSetfl(comments, elements, nrho, drho, nr, dr, cutoff, Z, M, A, L, np.array(F), np.array(rho), np.array(rphi))


def write_eam_setfl(s: EAMSetfl, path) -> None:
    out = list(s.comments)
    out.append("%d %s" % (len(s.elements), " ".join(s.elements)))
    out.append("%d %.16e %d %.16e %.16e" % (s.nrho, s.drho, s.nr, s.dr, s.cutoff))
    for k in range(len(s.elements)):
        out.append("%d %.10g %.10g %s" % (s.atomic_number[k], s.mass[k], s.lattice_constant[k], s.lattice[k]))
        out += ["%.16e" % v for v in s.F[k]]
        out += ["%.16e" % v for v in s.rho[k]]
    for p in range(len(s.rphi)):
        out += ["%.16e" % v for v in s.rphi[p]]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")


def read_eam_funcfl(path) -> EAMSetfl:
    """Single-element funcfl: comment, `Z mass a0 lattice`, `nrho drho nr dr cutoff`, F(rho), Z(r) (effective charge), rho(r).
    Converted to setfl: r*phi = Z(r)^2 * 27.2 * 0.529 (Hartree*Bohr, the manual's convention)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    z, m, a, lat = lines[1].split()[:4]
    nrho, drho, nr, dr, cutoff = lines[2].split()[:5]
    nrho, nr = int(nrho), int(nr)
    tokens = " ".join(lines[3:]).split()
    F = np.array(tokens[:nrho], float)
    Zr = np.array(tokens[nrho:nrho + nr], float)
    rho = np.array(tokens[nrho + nr:nrho + 2 * nr], float)
    rphi = Zr * Zr * 27.2 * 0.529
    return EAMSetfl([lines[0], "", ""], ["X"], nrho, float(drho), nr, float(dr), float(cutoff), [int(float(z))], [float(m)], [float(a)], [lat],
                    F[None, :], rho[None, :], rphi[None, :])


def synthetic_setfl(element="Xx", nr=500, nrho=500, cutoff=5.0, rhomax=20.0) -> EAMSetfl:
    """A smooth made-up EAM: rho(r) = exp(-2(r-2)) cut at rc, F(rho) = -sqrt(rho), phi(r) = Morse (D=0.5, a=1.5, r0=2.5) shifted to 0 at rc."""
    dr = cutoff / (nr - 1)
    r = np.arange(nr) * dr
    drho = rhomax / (nrho - 1)
    rhog = np.arange(nrho) * drho
    dens = np.exp(-2.0 * (r - 2.0)) * (1 - (r / cutoff) ** 2) ** 2
    dens[r > cutoff] = 0.0
    D, a, r0 = 0.5, 1.5, 2.5
    morse = D * (np.exp(-2 * a * (r - r0)) - 2 * np.exp(-a * (r - r0)))
    morse -= D * (np.exp(-2 * a * (cutoff - r0)) - 2 * np.exp(-a * (cutoff - r0)))
    morse[0] = morse[1]
    F = -np.sqrt(rhog)
    return EAMSetfl(["synthetic EAM for lammps-skill tests (our own)", "not a real material", ""], [element], nrho, drho, nr, dr, cutoff,
                    [1], [1.0], [4.0], ["fcc"], F[None, :], dens[None, :], (r * morse)[None, :])
