# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Render the course deck to the committed PDF fallback (course/slides.pdf).

Loads ``deck/index.html?print-pdf`` (reveal.js print layout: one page per
slide, 1920x1080) in headless Chromium and prints it. The PDF carries every
slide of the deck — all notebook figures with their full captions — so the
course can be read or presented without a browser.

Needs the optional tooling env (course/tools/requirements.txt: playwright +
``playwright install chromium``); the fast test-suite only checks that the
committed PDF exists, is a PDF and has one page per slide.

Usage (from pythtb-skill/):
    python course/tools/make_slides_pdf.py [--out FILE.pdf]
"""

import argparse
import os
import re
import sys

__version__ = "0.1.13"

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE = os.path.abspath(os.path.join(HERE, ".."))
INDEX = os.path.join(COURSE, "deck", "index.html")
OUT = os.path.join(COURSE, "slides.pdf")


def page_count(path):
    """Number of pages of a PDF (the /Type /Page objects Chromium writes)."""
    with open(path, "rb") as f:
        data = f.read()
    n = len(re.findall(rb"/Type\s*/Page[^s]", data))
    if n:
        return n
    m = re.search(rb"/Count\s+(\d+)", data)
    return int(m.group(1)) if m else 0


def make(index=INDEX, out=OUT, quiet=False):
    from playwright.sync_api import sync_playwright   # optional dependency
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto("file:///" + index.replace("\\", "/") + "?print-pdf")
        page.wait_for_function("() => window.Reveal && Reveal.isReady()")
        page.wait_for_timeout(1500)                    # let images decode
        page.pdf(path=out, width="20in", height="11.25in", print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()
    n = page_count(out)
    if not quiet:
        print(f"ok: {out} ({os.path.getsize(out)} bytes, {n} pages)")
    return n


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--index", default=INDEX, help="deck to render")
    p.add_argument("--out", default=OUT, help="output PDF (course/slides.pdf)")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    make(a.index, a.out, a.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
