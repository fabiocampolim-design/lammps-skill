# Analysis — `lammpskill.post`

Every function is numpy only and independent of LAMMPS; inputs come from `lammpskill.io` objects
(`ThermoRun`, `Frame`, `Trajectory`, `Box`) or plain arrays. Formulas follow Allen & Tildesley (2017)
and Frenkel & Smit (2002); the pitfalls are the ones the chapters demonstrate.

| function | formula / estimator | pitfalls |
|---|---|---|
| `block_average(x, nblocks)` | mean of block means; error = std(block means, ddof=1)/√nblocks | blocks must be longer than the correlation time — halve `nblocks` until the error stops growing |
| `rdf(positions, box, nbins, rmax, types, pair)` | histogram of minimum-image pair distances normalised by N ρ_b × shell volume; chunked O(N²) | `rmax` must stay below half the smallest box length (default); for `pair=(a,b)` with a≠b the self-pair exclusion is off |
| `rdf_trajectory(traj, …)` | average of `rdf` over frames | frames must be uncorrelated enough for the error you want |
| `unwrap_positions(traj)` / `msd(traj, dt, unwrap=True)` | ⟨|r(t) − r(0)|²⟩ over atoms; unwrap by minimum-image steps between consecutive frames | dumps must be frequent enough that no atom moves more than half a box between frames — otherwise write `xu yu zu` and pass `unwrap=False` |
| `diffusion_coefficient(t, msd, fit_from, dim)` | D = slope/(2·dim) of a linear fit over the last (1 − fit_from) fraction | the early ballistic part must be excluded; the error is the fit's, not the sampling's — repeat over origins for a real error |
| `vacf(velocities, dt, max_lag)` | ⟨v(0)·v(t)⟩/⟨v²⟩ averaged over atoms and time origins | lags beyond ~a third of the run are noisy |
| `structure_factor(r, g, rho, kmax, nk)` | S(k) = 1 + 4πρ ∫ r² (g − 1) sin(kr)/(kr) dr | the truncation of g(r) at rmax rings at small k; window or extend g → 1 |
| `energy_drift(thermo, col)` | linear fit of the total energy vs step; relative drift end − start | judge NVE integration quality; a stable temperature says nothing about drift |
| `elastic_from_stress(strains, stresses)` | C11, C12 from uniaxial strains, C44 from a shear; stress = −pressure tensor | use ± strains around zero and relax internal coordinates for non-Bravais cells |
| `load_benchmark(name)` / `compare(value, entry, tolerance)` | tolerance default 2σ of the entry's stated error, else 1 % | a benchmark without provenance is refused |

Units are whatever the inputs carry: reduced (lj) or the LAMMPS unit system of the run. `dt` in
`msd` / `vacf` converts dump frames to time.
