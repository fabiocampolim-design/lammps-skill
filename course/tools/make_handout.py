# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Print course/handout/handout.html to an A4 PDF (course/handout/handout.pdf,
gitignored like docs/USER_MANUAL.pdf).

Needs the optional tooling env (course/tools/requirements.txt: playwright).

Usage (from lammps-skill/):
    python course/tools/make_handout.py [--out FILE.pdf]
"""

import argparse
import os
import sys

__version__ = "0.1.22"

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE = os.path.abspath(os.path.join(HERE, ".."))
HANDOUT = os.path.join(COURSE, "handout", "handout.html")
OUT = os.path.join(COURSE, "handout", "handout.pdf")


def make(src=HANDOUT, out=OUT, quiet=False):
    from playwright.sync_api import sync_playwright   # optional dependency
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("file:///" + src.replace("\\", "/"))
        page.pdf(path=out, format="A4", print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()
    if not quiet:
        print(f"ok: {out} ({os.path.getsize(out)} bytes)")


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--src", default=HANDOUT, help="handout HTML")
    p.add_argument("--out", default=OUT, help="output PDF")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    make(a.src, a.out, a.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
