# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
import numpy as np
import pytest

from lammpskill import post
from lammpskill.io.box import Box
from lammpskill.io.dump import Frame, Trajectory
from lammpskill.io.log import ThermoRun


def test_block_average_of_white_noise():
    rng = np.random.default_rng(1)
    x = rng.normal(0.0, 1.0, 10000)
    m, e = post.block_average(x, nblocks=10)
    assert abs(m) < 0.05 and 0.005 < e < 0.02


def test_rdf_of_a_simple_cubic_lattice_has_a_peak_at_the_spacing():
    n = 6
    a = 1.0
    g = np.array([[i, j, k] for i in range(n) for j in range(n) for k in range(n)], float) * a
    box = Box(0, n * a, 0, n * a, 0, n * a)
    r, gr = post.rdf(g, box, nbins=60, rmax=2.5)
    # 6 neighbours at a, 12 at sqrt(2) a, 8 at sqrt(3) a; nothing below a; g(r) integrates to the coordination numbers
    assert gr[r < 0.95].max() == 0.0
    first = (r > 0.95) & (r < 1.05)
    assert gr[first].max() > 5.0
    dr = r[1] - r[0]
    rho = len(g) / box.volume
    n_first = (4 * np.pi * rho * (r[first] ** 2) * gr[first] * dr).sum()
    assert abs(n_first - 6.0) < 0.05


def test_msd_and_diffusion_of_a_random_walk():
    rng = np.random.default_rng(2)
    nframes, natoms, L = 200, 50, 100.0
    steps = rng.normal(0, 0.1, (nframes, natoms, 3)).cumsum(axis=0) + L / 2
    box = Box(0, L, 0, L, 0, L)
    frames = [Frame(t, natoms, box, ("pp",) * 3, ["id", "type", "x", "y", "z"],
                    np.column_stack([np.arange(1, natoms + 1), np.ones(natoms), box.wrap(steps[t])])) for t in range(nframes)]
    t, m = post.msd(Trajectory(frames), dt=1.0)
    assert m[0] == 0 and m[-1] > m[10]
    D, err = post.diffusion_coefficient(t, m)
    assert abs(D - 3 * 0.01 / 6) < 0.002      # <r^2> = 3 sigma^2 t -> D = sigma^2/2 = 0.005


def test_vacf_starts_at_one_and_decays():
    rng = np.random.default_rng(3)
    v = rng.normal(size=(300, 20, 3))
    for i in range(1, 300):
        v[i] = 0.9 * v[i - 1] + 0.1 * v[i]
    t, c = post.vacf(v, dt=1.0, max_lag=50)
    assert c[0] == pytest.approx(1.0) and c[20] < 0.5 and len(t) == 51


def test_structure_factor_of_ideal_gas_is_one():
    r = np.linspace(0.01, 10, 500)
    k, S = post.structure_factor(r, np.ones_like(r), rho=0.5)
    np.testing.assert_allclose(S, 1.0, atol=1e-6)


def test_energy_drift_and_elastic_constants():
    run = ThermoRun(["Step", "TotEng"], [[i, 1.0 + 1e-6 * i] for i in range(100)])
    d = post.energy_drift(run)
    assert d["slope_per_step"] == pytest.approx(1e-6) and d["rel_drift"] == pytest.approx(99e-6, rel=1e-3)
    C11, C12, C44 = 170.0, 120.0, 75.0
    strains, stresses = [], []
    for e in (-0.01, -0.005, 0.005, 0.01):
        eps = np.diag([e, 0, 0])
        strains.append(eps)
        stresses.append(-np.diag([C11 * e, C12 * e, C12 * e]))
        gam = np.zeros((3, 3))
        gam[1, 2] = gam[2, 1] = e / 2
        strains.append(gam)
        s = np.zeros((3, 3))
        s[1, 2] = s[2, 1] = -C44 * e
        stresses.append(s)
    c = post.elastic_from_stress(strains, stresses)
    assert c["C11"] == pytest.approx(C11) and c["C12"] == pytest.approx(C12) and c["C44"] == pytest.approx(C44)


def test_benchmarks_load_with_provenance_and_compare():
    for name in ("nist_lj", "eam_cu"):
        b = post.load_benchmark(name)
        assert b["provenance"]["url"] and b["provenance"]["retrieved"] and b["entries"]
        for k, e in b["entries"].items():
            assert {"value", "units"} <= set(e), (name, k)
    e = {"value": 1.0, "error": 0.1, "units": "x"}
    assert post.compare(1.05, e).within and not post.compare(1.5, e).within
    assert post.compare(1.5, e, tolerance=1.0).within


def test_nist_entries_cover_a_chapter_state_point():
    b = post.load_benchmark("nist_lj")
    keys = set(b["entries"])
    assert any(k.endswith("_P") for k in keys) and any(k.endswith("_U") for k in keys), keys
