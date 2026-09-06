# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Binary restart files: only the magic string, endianness check and the version string are read — the manual states
the format is not portable and not documented, so everything else goes through LAMMPS itself
(`read_restart` + `write_data` via lammpskill.run)."""

import struct

MAGIC = b"LammpS RestartT"   # written as a 16-byte NUL-terminated string (observed 2026-09-06, 10 Dec 2025 build)


def read_restart_header(path) -> dict:
    with open(path, "rb") as f:
        head = f.read(len(MAGIC) + 1)
        if head[:len(MAGIC)] != MAGIC:
            raise ValueError("%s is not a LAMMPS restart file (magic %r)" % (path, head[:16]))
        endian = struct.unpack("<i", f.read(4))[0]
        endian_ok = endian == 0x0001
        _revision = struct.unpack("<i", f.read(4))[0]
        # the first record is the version string: int flag (0), int length, bytes
        flag, length = struct.unpack("<ii", f.read(8))
        version = f.read(length).rstrip(b"\x00").decode("utf-8", errors="replace") if flag == 0 and 0 < length < 256 else ""
    return {"magic": MAGIC.decode(), "endian_ok": endian_ok, "version": version, "revision": _revision}
