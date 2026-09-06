# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Route docker: a LAMMPS container image. CONTRACT ONLY (pinned): Docker Desktop is not installed on the reference
machine (2026-09-06); the executor never installs it. Detection needs LAMMPSKILL_DOCKER_IMAGE and a docker CLI."""

import os
import shutil
import subprocess

from .base import Installation

NAME = "docker"


def describe():
    return ("A LAMMPS container image run with `docker run --rm -v <case>:/work -w /work <image> lmp -in in.x`. "
            "PINNED until the owner installs Docker Desktop: the route detects only when LAMMPSKILL_DOCKER_IMAGE names an "
            "image the local docker CLI lists; which public images exist is recorded in docs/10 from a real check.")


def detect(env=None, run=None):
    env = os.environ if env is None else env
    image = env.get("LAMMPSKILL_DOCKER_IMAGE")
    if not image:
        return None
    if run is None:
        if shutil.which("docker") is None:
            return None

        def run(cmd):
            return subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    try:
        p = run(["docker", "image", "ls", "--format", "{{.Repository}}:{{.Tag}}"])
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0 or image not in p.stdout.split():
        return None
    return Installation(route=NAME, host="docker", executable="lmp", version="unknown (image %s)" % image, packages=(),
                        mpi=False, omp=False, library=None, python_module=False,
                        launch=("docker", "run", "--rm", "-v", "{cwd}:/work", "-w", "/work", image), distro=None, python=None,
                        extra={"pinned": True, "image": image, "note": "docker route pinned; run.SubprocessBackend refuses until unpinned"})
