#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
# Install LAMMPS on Ubuntu (WSL2 or native).
#   apt route (default):  lammps lammps-data lammps-examples liblammps-dev python3-lammps from the Ubuntu archive
#   source route:         --source [--tag stable_22Jul2025_update6] [--preset core|molecular|metals|reactive|ml|all-cpu]
#                         CMake build in $HOME/src/lammps-<tag> (ext4, never /mnt), shared lib + python module,
#                         installed to $HOME/.local (lmp_<preset> on ~/.local/bin, python module for the user's python3)
# Must run as root for apt (from Windows:  wsl -d Ubuntu -u root -- bash /mnt/c/<path>/install_lammps_wsl.sh);
# the source route runs as the user (its deps step needs root: run it once as root with --source --deps-only).
# Usage: install_lammps_wsl.sh [--dry-run] [--source] [--tag T] [--preset P] [--deps-only] [--jobs N]
DRY=0; SOURCE=0; TAG="stable_22Jul2025_update6"; PRESET="core"; DEPS_ONLY=0; JOBS="$(nproc 2>/dev/null || echo 4)"
while [ $# -gt 0 ]; do case "$1" in
  --dry-run) DRY=1;; --source) SOURCE=1;; --tag) TAG="$2"; shift;; --preset) PRESET="$2"; shift;;
  --deps-only) DEPS_ONLY=1;; --jobs) JOBS="$2"; shift;; *) echo "unknown arg $1"; exit 2;; esac; shift; done
UID_NOW="${LAMMPSKILL_FAKE_UID:-$(id -u)}"
export DEBIAN_FRONTEND=noninteractive
status=()
step() { echo "== $1"; echo "   $2"; if [ $DRY = 1 ]; then status+=("$1 : DRY-RUN"); return; fi
         if bash -c "$2"; then status+=("$1 : OK"); else status+=("$1 : FAIL"); printf '%s\n' "${status[@]}"; exit 1; fi; }
need_root() { if [ $DRY = 0 ] && [ "$UID_NOW" != "0" ]; then
  echo "REFUSED: this step needs root and has no terminal for sudo."
  echo "Run it as:   wsl -d Ubuntu -u root -- bash $(realpath "$0" 2>/dev/null || echo "$0") $*"
  exit 2; fi; }
case "$PRESET" in
  core)      PKGS="MOLECULE KSPACE MANYBODY RIGID OPENMP PYTHON EXTRA-COMPUTE EXTRA-DUMP EXTRA-FIX EXTRA-MOLECULE EXTRA-PAIR";;
  molecular) PKGS="MOLECULE KSPACE MANYBODY RIGID OPENMP PYTHON EXTRA-COMPUTE EXTRA-DUMP EXTRA-FIX EXTRA-MOLECULE EXTRA-PAIR MC MISC QEQ SHOCK";;
  metals)    PKGS="MOLECULE KSPACE MANYBODY RIGID OPENMP PYTHON EXTRA-COMPUTE EXTRA-DUMP EXTRA-FIX EXTRA-PAIR MEAM PHONON REPLICA";;
  reactive)  PKGS="MOLECULE KSPACE MANYBODY RIGID OPENMP PYTHON EXTRA-COMPUTE EXTRA-DUMP EXTRA-FIX EXTRA-PAIR QEQ REAXFF";;
  ml)        PKGS="MOLECULE KSPACE MANYBODY RIGID OPENMP PYTHON EXTRA-COMPUTE EXTRA-DUMP EXTRA-FIX EXTRA-PAIR ML-SNAP ML-PACE ML-IAP";;
  all-cpu)   PKGS="__ALL_CPU__";;
  *) echo "unknown preset $PRESET"; exit 2;; esac
if [ $SOURCE = 0 ]; then
  need_root
  step update  "apt-get update -y"
  step install "apt-get install -y lammps lammps-data lammps-examples liblammps-dev python3-lammps"
  step verify  "lmp -h | head -1 && python3 -c 'import lammps; print(\"python module\", lammps.__version__ if hasattr(lammps, \"__version__\") else \"ok\")'"
  printf '%s\n' "${status[@]}"
  echo "Potentials: /usr/share/lammps/potentials   Examples: check with dpkg -L lammps-examples"
  exit 0
fi
# ---- source route ----
if [ $DRY = 1 ] || [ "$UID_NOW" = "0" ] || [ $DEPS_ONLY = 1 ]; then
  need_root
  step deps "apt-get update -y && apt-get install -y build-essential cmake git libopenmpi-dev openmpi-bin python3-dev python3-pip python3-venv libfftw3-dev libjpeg-dev libpng-dev zlib1g-dev"
  [ $DEPS_ONLY = 1 ] && { printf '%s\n' "${status[@]}"; exit 0; }
else
  status+=("deps : SKIP (run once as root with --source --deps-only)")
fi
SRC="$HOME/src/lammps-$TAG"; BUILD="$SRC/build"; PREFIX="$HOME/.local"
if [ "$PKGS" = "__ALL_CPU__" ]; then
  CMAKE_PKGS="-C ../cmake/presets/most.cmake -D PKG_PYTHON=yes"
else
  CMAKE_PKGS=""; for p in $PKGS; do CMAKE_PKGS="$CMAKE_PKGS -D PKG_$p=yes"; done
fi
step fetch     "mkdir -p '$HOME/src' && { [ -d '$SRC/.git' ] || git clone --depth 1 --branch '$TAG' https://github.com/lammps/lammps.git '$SRC'; }"
step configure "mkdir -p '$BUILD' && cd '$BUILD' && cmake -D CMAKE_BUILD_TYPE=Release -D CMAKE_INSTALL_PREFIX='$PREFIX' -D BUILD_MPI=yes -D BUILD_OMP=yes -D BUILD_SHARED_LIBS=yes -D LAMMPS_MACHINE=$PRESET $CMAKE_PKGS ../cmake"
step build     "cd '$BUILD' && cmake --build . --parallel $JOBS"
step install   "cd '$BUILD' && cmake --install . && cmake --build . --target install-python"
step verify    "'$PREFIX/bin/lmp_$PRESET' -h | head -1 && python3 -c 'import lammps; l = lammps.lammps(cmdargs=[\"-log\",\"none\",\"-screen\",\"none\"]); print(\"python module\", l.version()); l.close()'"
printf '%s\n' "${status[@]}"
echo "Executable: $PREFIX/bin/lmp_$PRESET   Library: $PREFIX/lib/liblammps_$PRESET.so   Source: $SRC"
