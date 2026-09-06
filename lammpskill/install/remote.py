# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Route remote: LAMMPS on another machine over SSH (later Slurm). CONTRACT ONLY (pinned): no machine exists yet."""

import os

from .base import Installation

NAME = "remote"


def describe():
    return ("LAMMPS on a remote host reached over SSH, later through a Slurm queue: LAMMPSKILL_REMOTE=user@host:/path/to/lmp. "
            "PINNED (owner: implement when the machine exists). The runner interface is fixed here so chapters and the "
            "CLI need no change when it lands: submit / poll / fetch, with the case directory synced under ~/runs.")


def detect(env=None, run=None):
    env = os.environ if env is None else env
    spec = env.get("LAMMPSKILL_REMOTE")
    if not spec or "@" not in spec or ":" not in spec:
        return None
    userhost, exe = spec.split(":", 1)
    return Installation(route=NAME, host="remote", executable=exe, version="unknown (remote %s)" % userhost, packages=(),
                        mpi=True, omp=False, library=None, python_module=False, launch=("ssh", userhost), distro=None,
                        python=None, extra={"pinned": True, "userhost": userhost, "note": "remote route pinned"})
