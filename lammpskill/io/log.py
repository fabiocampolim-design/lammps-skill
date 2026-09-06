# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""LAMMPS log/screen parser: thermo blocks (`one` and `yaml` styles), warnings, errors, loop lines.
Written from the manual's description of thermo output and from logs LAMMPS wrote on this machine."""

from __future__ import annotations

import re

import numpy as np

_NUM = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$|^[-+]?(inf|nan)$", re.I)
_LOOP = re.compile(r"Loop time of ([\d.eE+-]+) on (\d+) procs for (\d+) steps with (\d+) atoms")
_VERSION = re.compile(r"^LAMMPS \((.+?)\)")
_CREATED = re.compile(r"Created (\d+) atoms")


class ThermoRun:
    def __init__(self, columns, rows, loop_time=None, nprocs=None, nsteps=None, natoms=None):
        self.columns = list(columns)
        self.data = np.array(rows, dtype=float).reshape(-1, len(self.columns)) if rows else np.zeros((0, len(self.columns)))
        self.loop_time, self.nprocs, self.nsteps, self.natoms = loop_time, nprocs, nsteps, natoms

    def get(self, col):
        if col not in self.columns:
            raise KeyError("column %r not in %s" % (col, self.columns))
        return self.data[:, self.columns.index(col)]

    def as_dict(self):
        return {c: self.get(c) for c in self.columns}

    @property
    def last(self):
        if self.data.shape[0] == 0:
            return {}
        return {c: float(v) for c, v in zip(self.columns, self.data[-1])}

    def __repr__(self):
        return "ThermoRun(%d rows x %s)" % (self.data.shape[0], self.columns)


class LogFile:
    def __init__(self):
        self.version = None
        self.runs = []
        self.warnings = []
        self.errors = []
        self.natoms = None

    @property
    def thermo(self):
        if not self.runs:
            raise ValueError("no thermo output in this log")
        return self.runs[-1]


def _is_numeric_row(parts):
    return bool(parts) and all(_NUM.match(p) for p in parts)


def _yaml_block(lines, i):
    """Parse a thermo YAML block starting at lines[i] == '---'. Returns (columns, rows, next_index)."""
    cols, rows = [], []
    j = i + 1
    while j < len(lines):
        s = lines[j].strip()
        if s == "...":
            return cols, rows, j + 1
        if s.startswith("keywords:"):
            inner = s[len("keywords:"):].strip().strip("[]")
            cols = [c.strip().strip("'\"") for c in inner.split(",") if c.strip()]
        elif s.startswith("- ["):
            inner = s[3:].rstrip("]").strip()
            rows.append([float(v) for v in inner.split(",") if v.strip()])
        j += 1
    return cols, rows, j


def parse_log(text: str) -> LogFile:
    lf = LogFile()
    lines = text.splitlines()
    i = 0
    current = None  # (columns, rows) of an open thermo block
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        m = _VERSION.match(s)
        if m and lf.version is None:
            lf.version = m.group(1)
        m = _CREATED.search(s)
        if m:
            lf.natoms = int(m.group(1))
        if s.startswith("WARNING:"):
            lf.warnings.append(s)
        elif s.startswith("ERROR:") or s.startswith("ERROR on proc"):
            lf.errors.append(s)
        elif s == "---":
            cols, rows, i = _yaml_block(lines, i)
            if cols:
                current = (cols, rows)
            continue
        m = _LOOP.search(s)
        if m:
            cols, rows = current if current else ([], [])
            if cols:
                lf.runs.append(ThermoRun(cols, rows, loop_time=float(m.group(1)), nprocs=int(m.group(2)),
                                         nsteps=int(m.group(3)), natoms=int(m.group(4))))
            lf.natoms = int(m.group(4))
            current = None
            i += 1
            continue
        parts = s.split()
        if parts and parts[0] == "Step" and not _is_numeric_row(parts):
            current = (parts, [])
        elif current is not None and _is_numeric_row(parts) and len(parts) == len(current[0]):
            current[1].append([float(p) for p in parts])
        i += 1
    if current is not None and current[1]:  # a run cut off before its Loop line (killed job) still counts
        lf.runs.append(ThermoRun(current[0], current[1]))
    return lf


def read_log(path) -> LogFile:
    with open(path, encoding="utf-8", errors="replace") as f:
        return parse_log(f.read())
