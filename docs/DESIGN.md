# DESIGN.md — why lammps-skill looks the way it does

## Purpose

An AI-agent skill, a verified Python toolkit, a clean-room teaching engine and (from plan 1b) chapter
notebooks and an undergraduate course for molecular dynamics with LAMMPS. Three things the toolkit
does: **install, detect and drive** LAMMPS through every route a user may have (one contract per
route, measured); **analyse** results independently of the binary with our own readers; **teach** the
method with `mdlite`, a numpy engine written from the textbooks and cross-checked at stated precision.

## Constraints that shaped it

- LAMMPS is GPL-2.0; the product is Apache-2.0 and contains no LAMMPS code, example, potential file or
  manual text. File formats and the input language are documented interfaces; readers are validated
  against files LAMMPS wrote, not transcribed from its source.
- LAMMPS has many distributions (apt, source, conda-forge, a third-party wheel, Windows installers,
  containers, clusters). The owner asked for all of them to be understood and exposed, so
  `lammpskill.install` is a set of route modules with one `Installation` dataclass, and the runner has
  two backends (subprocess for any executable, in-process for the python module) returning one `Result`.
- The reference machine is Windows with WSL2; every child process is started hidden and with a
  timeout inside WSL, because a console popping up is a defect.
- Numbers are trusted only with provenance: benchmarks cite a source, records store the measured
  residue with the route/version/date, and tests read tolerances from the records (never a literal).

## Trade-offs

- Own parsers instead of ASE/MDAnalysis: keeps the core Apache-only and lets the tests pin every
  format detail LAMMPS actually writes; the ecosystem is bridged optionally instead.
- A spec-based script builder with a checker instead of a full input-language model: `Spec` covers
  what the chapters need and renders in the manual's order; commands outside it go in `pre`/`post` or
  are inserted after the command they modify — simpler than a grammar, honest about its limits.
- `mdlite` is deliberately small (orthogonal boxes, LJ, EAM, harmonic bonds, three thermostats, two
  minimisers) so a reader can hold it in mind; it is not an MD code.
- Docker and remote routes are contracts tested with fakes: designed now so nothing changes when the
  owner enables them, refused by the runner until then.
