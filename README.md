# lammps-skill

An AI-agent skill, verified Python toolkit, clean-room teaching engine (`mdlite`) and undergraduate
course for molecular dynamics with LAMMPS (latest stable release primary; `develop` watched).
Version 0.1.0 — foundation; see `CHANGELOG.md`.

## What it does

- `lammpskill`: detects and drives every way LAMMPS can be installed (WSL apt, source build, conda-forge,
  the PyPI wheel, the Windows installer; Docker and a remote cluster designed and pinned), builds and
  checks input scripts, reads and writes data / dump / log / restart-header / EAM files, runs LAMMPS
  through a subprocess or in-process through the official python module, and analyses the results.
- `mdlite`: a numpy molecular-dynamics engine (Lennard-Jones, EAM, velocity Verlet, thermostats,
  minimisers) validated against NIST reference data and cross-checked against LAMMPS.
- `SKILL.md`: the agent workflows. `references/`: what the agent must know. `docs/USER_MANUAL.md`: the manual.

## Licence

Apache-2.0 — see `LICENSE` and `NOTICE`. LAMMPS itself is GPL-2.0 and is **not** included: install it
yourself (`scripts/install_lammps_wsl.sh` on WSL, or any other route in `references/install-routes.md`)
and this toolkit drives it. The optional `lammps` python module, ASE, pymatgen, MDAnalysis and OVITO
backends are separate packages under their own licences; they are never required.

### Disclaimer

This software is provided "as is", without warranties or conditions of any kind, express or implied,
including, without limitation, any warranties of merchantability, fitness for a particular purpose,
title or non-infringement. In no event shall the authors or copyright holders be liable for any
damages of any character (direct, indirect, incidental, special, consequential or otherwise) arising
from, out of or in connection with the software or its use, even if advised of the possibility of
such damages. A simulation result is only as good as its force field, its sampling and its user:
verify every number before it leaves your desk.

This project is independent and not affiliated with or endorsed by Sandia National Laboratories,
National Technology & Engineering Solutions of Sandia, LLC (NTESS), Temple University or the LAMMPS
developers.
