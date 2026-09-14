# Molecular Dynamics with LAMMPS — the course

An undergraduate course in eleven lectures, locked 1:1 with the companion book of chapter
notebooks (`chapters/`) — L0 is chapter 00, L10 is chapter 10, in order. **Every figure the
notebooks generate appears in the course, in the slides and in the PDF fallback alike, under its
full notebook caption**; a test fails if a figure drifts from the notebook output or goes unused.

Every lecture runs its full intro → core → math depth (56 slides across the 11 lectures, sized to
each chapter's own material — Plan A built the mechanism, Plan B filled in the content; both are
done). A further roadmap (atom snapshots and animations per physical case, more physical cases) is
in progress one piece at a time — see
`docs/superpowers/specs/2026-09-14-lammps-skill-atom-visuals-design.md`.

```
course/
  deck/index.html         the slides (reveal.js, offline; open in a browser)   GENERATED
  deck/content.en.js      THE SOURCE: lectures, slide order, levels, figures, notes
  deck/figs/*.png,*.gif    figures + animations extracted from the notebooks + provenance.json  GENERATED
  slides.pdf              PDF fallback of the whole deck, one page per slide   GENERATED, committed
  handout/handout.html    A4 companion handout (syllabus, key ideas, glossary)
                          handout.pdf via make_handout.py                     GENERATED
  notes/LECTURER_NOTES.md every slide's notes with the anticipated question   GENERATED
  shared/                 theme.css, nav.js, loader.js + vendored reveal.js 5.2.0 (MIT)
  tools/                  extract_figures.py, build_deck.py (stdlib) · verify_deck.py,
                          build_pptx.py, make_handout.py, make_slides_pdf.py (Playwright)
```

## Syllabus

| | Lecture | Notebook |
|---|---|---|
| L0 | Orientation — LAMMPS, the two release lines, the routes measured here, record-or-run | ch00 |
| L1 | First Simulation — an LJ melt end to end through the checker's fourteen rules | ch01 |
| L2 | Forces and Integration — velocity Verlet in mdlite, forces and energy conservation vs LAMMPS | ch02 |
| L3 | Thermostats — Berendsen, Langevin, Nosé–Hoover, checked against the NIST reference | ch03 |
| L4 | Ensembles and Restarts — an NPT sketch, `fix npt`, restart continuation | ch04 |
| L5 | Potentials: EAM — copper's lattice constant and cohesive energy from a real setfl file | ch05 |
| L6 | Structure and Analysis — g(r), S(k), MSD, diffusion coefficient, VACF | ch06 |
| L7 | Minimisation — steepest descent vs FIRE, and why lost atoms happen | ch07 |
| L8 | Reading What LAMMPS Writes — data, dump, log, restart, and four pitfalls | ch08 |
| L9 | Choosing a Build — package list vs package count, from a 314-case sweep | ch09 |
| L10 | Scaling and Limits — MPI/OpenMP speed-up, and this machine's honest limits | ch10 |

The deck is **flat and linear**: one slide after another in lecture order, each lecture opened
by a divider slide (its label, summary and a level-coloured agenda). Within a lecture the
slides run *intro → core → math* — the chip at the top-right of every slide says which.

## Presenting

Open `deck/index.html` in any modern browser — no server, no network. No browser at hand?
`slides.pdf` is the same deck, one page per slide.

| Key | Action |
|---|---|
| `→` / `←`, clicker, space | next / previous slide — the only navigation there is |
| `Shift+→` / `Shift+←`, bottom-right buttons | jump to the next / previous lecture divider |
| click the progress bar | jump to that lecture |
| `S` | speaker view with the notes |
| `Esc` | overview grid |

PowerPoint: `python course/tools/build_pptx.py` writes a `.pptx` with one full-bleed screenshot
per slide and the notes as editable speaker notes.

## Rebuilding

The content file is the only thing to edit. From `lammps-skill/`:

```bash
python course/tools/extract_figures.py     # notebook outputs -> deck/figs/*.png,*.gif + provenance.json
python course/tools/build_deck.py          # content.en.js -> index.html, handout.html, LECTURER_NOTES.md
python course/tools/make_slides_pdf.py     # deck -> slides.pdf (committed; needs Playwright)
python -m pytest tests/test_course.py      # provenance fresh, outputs fresh, PDF complete, slides well-formed
```

The stdlib tools accept `--check` (exit 1 when their outputs are stale). When a chapter notebook
is re-executed (`build/execute.py`) its figures must be re-extracted and the PDF regenerated, or
`test_course.py` says what drifted.

Optional tooling (headless Chromium; `make_slides_pdf.py` needs it too):

```bash
python -m pip install -r course/tools/requirements.txt && python -m playwright install chromium
python course/tools/verify_deck.py         # walk every slide: console errors, overflow, screenshots
python course/tools/build_pptx.py          # course/build/Molecular Dynamics with LAMMPS.pptx
python course/tools/make_handout.py        # course/handout/handout.pdf (A4)
```

## Content model (`deck/content.en.js`)

Strict JSON after `window.DECK_CONTENT =`, so Python and the browser read the same file.
`sections` (name, lecture label, notebook chapter, summary), `stacks` (the linear order of
slides in each lecture), `slides` (per slide: `level` in intro/core/math, `layout` in hero ·
text · syllabus · eq · code · fig · fig-right · fig-left · two-figs · table, `title`, `lead`,
`bullets`, `eqs`, `code`, `table`, `fig`/`fig2` as provenance keys such as `ch06-f1`, `notes`
with a `Q:`/`A:` pair), `glossary`. The divider slides are generated from `sections` — they are
not content. Prose may contain HTML; math is set by hand with `<span class='math'>` (italic
serif) — no MathJax, so the deck works offline.

## Licence

Course material: Apache-2.0 (see `../LICENSE`, `../NOTICE`). `shared/reveal/` is reveal.js 5.2.0
by Hakim El Hattab and contributors, MIT (`shared/reveal/LICENSE`). LAMMPS (GPL-2.0) is used
through its input-script language and manual as documented interfaces; the figures are the
notebooks' own output.
