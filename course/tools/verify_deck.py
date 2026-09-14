# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Walk every slide and fragment of the course deck in headless Chromium.

Collects console errors/warnings (a missing data-t key surfaces here through
loader.js), page errors, horizontal-overflow and content-taller-than-slide
flags, and writes one screenshot per state to ``--screens`` (default
course/tools/screens/, gitignored). Exit 1 on any problem.

Needs the optional tooling env (course/tools/requirements.txt: playwright +
``playwright install chromium``); the fast test-suite does not run it.

Usage (from lammps-skill/):
    python course/tools/verify_deck.py [--screens DIR] [--no-screens]
"""

import argparse
import os
import sys

__version__ = "0.1.18"

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE = os.path.abspath(os.path.join(HERE, ".."))
INDEX = os.path.join(COURSE, "deck", "index.html")
SCREENS = os.path.join(HERE, "screens")


def verify(index=INDEX, screens=SCREENS, take_screens=True, quiet=False):
    from playwright.sync_api import sync_playwright   # optional dependency

    problems = []
    if take_screens:
        os.makedirs(screens, exist_ok=True)
        for old in os.listdir(screens):
            if old.endswith(".png"):
                os.unlink(os.path.join(screens, old))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.on("console", lambda m: problems.append(f"console.{m.type}: {m.text}")
                if m.type in ("error", "warning") and "favicon" not in m.text else None)
        page.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
        page.goto("file:///" + index.replace("\\", "/"))
        page.wait_for_function("() => window.Reveal && Reveal.isReady()")
        page.evaluate("Reveal.configure({transition:'none'})")
        page.evaluate("document.querySelectorAll('.deck-divider').forEach(e => e.style.display = 'none')")

        step = 0
        while step < 1000:
            page.wait_for_timeout(150)
            sid = page.evaluate("Reveal.getCurrentSlide().id")
            info = page.evaluate("""() => {
                const s = Reveal.getCurrentSlide();
                const box = document.querySelector('.reveal .slides').getBoundingClientRect();  // fixed 1920x1080 stage
                let bottom = 0, right = 0;
                s.querySelectorAll('*').forEach(el => {
                    if (el.tagName === 'ASIDE' || el.closest('aside')) return;
                    const r = el.getBoundingClientRect();
                    if (r.width === 0 && r.height === 0) return;
                    bottom = Math.max(bottom, r.bottom); right = Math.max(right, r.right);
                });
                const sc = Reveal.getScale();
                return {over: Math.round((bottom - box.bottom) / sc), wide: Math.round((right - box.right) / sc)};
            }""")
            if info["wide"] > 0:
                problems.append(f"content {info['wide']}px wider than slide on #{sid}")
            if info["over"] > 0:
                problems.append(f"content {info['over']}px below the slide bottom on #{sid}")
            if take_screens:
                page.screenshot(path=os.path.join(screens, f"{step:03d}-{sid}.png"))
            done = page.evaluate("Reveal.isLastSlide() && Reveal.availableFragments().next !== true")
            if done:
                break
            page.evaluate("Reveal.next()")
            step += 1
        browser.close()
    if not quiet:
        print(f"{step + 1} states walked" + (f" -> {screens}" if take_screens else ""))
    return problems


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--index", default=INDEX, help="deck to verify")
    p.add_argument("--screens", default=SCREENS, help="screenshot directory")
    p.add_argument("--no-screens", action="store_true", help="walk without screenshots")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    problems = verify(a.index, a.screens, not a.no_screens, a.quiet)
    for pr in problems:
        print(f"  - {pr}")
    print("clean" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
