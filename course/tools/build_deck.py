# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Generate the course deliverables from one content file.

``course/deck/content.en.js`` (strict JSON after ``window.DECK_CONTENT =``)
is the single source of truth: sections (lectures), the order of slides in
each lecture, each slide's level (intro -> core -> math), layout, figure keys
and lecturer notes. This script writes

    course/deck/index.html          FLAT reveal.js deck: one slide after another
                                    (single-level arrow navigation), with a
                                    generated divider slide opening each lecture
    course/handout/handout.html     A4 companion handout (syllabus, key ideas, glossary)
    course/notes/LECTURER_NOTES.md  every slide's notes with its anticipated question

Figures are referenced by provenance key (``ch06-f1``) and resolved against
``course/deck/figs/provenance.json`` written by ``extract_figures.py``; every
figure carries the notebook's own full caption plus its figure number,
section and cell. The committed PDF fallback (``course/slides.pdf``) is
rendered from index.html by ``make_slides_pdf.py``.

Usage (from lammps-skill/):
    python course/tools/build_deck.py             # write all three
    python course/tools/build_deck.py --check     # exit 1 if any output is stale
"""

import argparse
import html
import json
import os
import re
import sys

__version__ = "0.1.29"

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE = os.path.abspath(os.path.join(HERE, ".."))
CONTENT = os.path.join(COURSE, "deck", "content.en.js")
PROVENANCE = os.path.join(COURSE, "deck", "figs", "provenance.json")
INDEX = os.path.join(COURSE, "deck", "index.html")
HANDOUT = os.path.join(COURSE, "handout", "handout.html")
NOTES = os.path.join(COURSE, "notes", "LECTURER_NOTES.md")

LEVELS = ("intro", "core", "math")
LAYOUTS = ("hero", "text", "syllabus", "eq", "code", "fig", "fig-right", "fig-left",
           "two-figs", "table")


# ---------------------------------------------------------------- content ---

def load_content(path=CONTENT):
    """Parse the JS content file as JSON (everything after the assignment)."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    marker = "window.DECK_CONTENT ="
    body = src[src.index(marker) + len(marker):].strip()
    if body.endswith(";"):
        body = body[:-1]
    return json.loads(body)


def load_provenance(path=PROVENANCE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["figures"]


def lectures(deck):
    """Stacks that are lectures (sections with a lecture label); the closing
    stack has none and stays out of the syllabus and the handout."""
    return [s for s in deck["stacks"] if deck["sections"][s["sec"]].get("lecture")]


def ordered_slides(deck):
    for stack in deck["stacks"]:
        for sid in stack["slides"]:
            yield stack["sec"], sid, deck["slides"][sid]


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


# ------------------------------------------------------------------- deck ---

def _chapter_label(meta):
    """'chapter 4, ' from the provenance's notebook file name (empty if unknown)."""
    m = re.match(r"LAMMPS_(\d+)_", meta.get("chapter", ""))
    return f"chapter {int(m.group(1))}, " if m else ""


def _resolve_figure(key, prov):
    """(ext, meta) for a provenance key, whichever extension it actually has (.png for a static
    plot, .gif for an animation) -- the one place that knows figures aren't always .png."""
    ext = next((e for e in ("png", "gif") if key + "." + e in prov), None)
    if ext is None:
        raise KeyError(key)
    return ext, prov[key + "." + ext]


def figure_block(key, prov, extra_class=""):
    """<figure> for a provenance key; the full notebook caption travels with it."""
    ext, meta = _resolve_figure(key, prov)
    cap = html.escape(meta["caption"])
    fig = f'Figure {meta["figure"]} · ' if meta.get("figure") else ""
    return (f'<figure class="fig {extra_class}">'
            f'<img src="figs/{key}.{ext}" alt="{cap}">'
            f'<figcaption class="caption">{cap}'
            f' <span class="src">— {fig}notebook §{meta["section"]} · '
            f'{_chapter_label(meta)}cell {meta["cell"]}</span>'
            f'</figcaption>'
            f'</figure>')


def bullets_block(sid, slide, cls=""):
    if not slide.get("bullets"):
        return ""
    items = "".join(f'<li data-t="{sid}.bullets.{i}"></li>' for i in range(len(slide["bullets"])))
    return f'<ul class="{cls}">{items}</ul>'


def eq_block(sid, slide):
    out = []
    for i, _ in enumerate(slide.get("eqs", [])):
        out.append(f'<div class="eq-box"><div class="kicker" data-t="{sid}.eqs.{i}.label"></div>'
                   f'<div class="eq-hero" data-t="{sid}.eqs.{i}.math"></div></div>')
    return "".join(out)


def table_block(sid, slide):
    t = slide["table"]
    head = "".join(f'<th data-t="{sid}.table.head.{j}"></th>' for j in range(len(t["head"])))
    rows = "".join(
        "<tr>" + "".join(f'<td data-t="{sid}.table.rows.{i}.{j}"></td>' for j in range(len(row))) + "</tr>"
        for i, row in enumerate(t["rows"]))
    return f'<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'


def syllabus_block(deck):
    items = []
    for stack in lectures(deck):
        sec = deck["sections"][stack["sec"]]
        items.append(f'<li><b>{html.escape(sec["lecture"])}</b>{html.escape(sec["name"])}'
                     f' <span class="c-muted">· {html.escape(sec["notebook"])}</span></li>')
    return '<ul class="syllabus">' + "".join(items) + "</ul>"


def render_slide(deck, sec, sid, slide, prov):
    lay = slide["layout"]
    level = slide["level"]
    assert lay in LAYOUTS, (sid, lay)
    assert level in LEVELS, (sid, level)
    T = f'<h2 data-t="{sid}.title"></h2>'
    lead = f'<p data-t="{sid}.lead"></p>' if slide.get("lead") else ""
    body = ""
    if lay == "hero":
        kicker = f'<p class="kicker" data-t="{sid}.kicker"></p>' if slide.get("kicker") else ""
        body = (f'<div class="hero-wrap">{kicker}<h1 data-t="{sid}.title"></h1>'
                f'<p class="hero-sub" data-t="{sid}.sub"></p></div>')
    elif lay == "text":
        body = T + lead + bullets_block(sid, slide)
    elif lay == "syllabus":
        body = T + lead + syllabus_block(deck)
    elif lay == "eq":
        body = T + lead + eq_block(sid, slide) + bullets_block(sid, slide, "small")
    elif lay == "code":
        body = (T + lead + f'<div class="panel code" data-t="{sid}.code"></div>'
                + bullets_block(sid, slide, "small"))
    elif lay == "fig":
        body = T + lead + figure_block(slide["fig"], prov, "fig-tall")
    elif lay == "fig-right":
        body = (T + '<div class="grid-2">' + f'<div>{lead}{bullets_block(sid, slide)}</div>'
                + figure_block(slide["fig"], prov) + "</div>")
    elif lay == "fig-left":
        body = (T + '<div class="grid-2">' + figure_block(slide["fig"], prov)
                + f'<div>{lead}{bullets_block(sid, slide)}</div></div>')
    elif lay == "two-figs":
        body = (T + lead + eq_block(sid, slide) + '<div class="grid-2 two-figs">' + figure_block(slide["fig"], prov)
                + figure_block(slide["fig2"], prov) + "</div>" + bullets_block(sid, slide, "small"))
    elif lay == "table":
        body = T + lead + table_block(sid, slide) + bullets_block(sid, slide, "small")
    return (f'      <section id="{sid}" data-sec="{sec}" data-level="{level}">\n'
            f'        {body}\n'
            f'        <aside class="notes" data-notes="{sid}"></aside>\n      </section>\n')


def render_divider(deck, stack):
    """A real slide that opens a lecture: label, name, summary, agenda.

    Dividers replace the old overlay flash — they are ordinary slides, so
    navigation is never interrupted by an animation."""
    sec = deck["sections"][stack["sec"]]
    agenda = "".join(
        f'<li class="lv-{deck["slides"][sid]["level"]}">'
        f'{html.escape(strip_tags(deck["slides"][sid]["title"]))}</li>'
        for sid in stack["slides"])
    return (f'      <section id="div-{stack["sec"]}" data-sec="{stack["sec"]}" class="divider-slide">\n'
            f'        <p class="kicker">{html.escape(sec["lecture"])} · notebook {html.escape(sec["notebook"])}</p>\n'
            f'        <h1>{html.escape(sec["name"])}</h1>\n'
            f'        <p class="hero-sub">{html.escape(sec["summary"])}</p>\n'
            f'        <ol class="agenda">{agenda}</ol>\n'
            f'        <aside class="notes">Divider — one breath: say in a sentence where the '
            f'previous lecture ended and what this one adds. The list mirrors the slide order; '
            f'colours mark intro / core / math.</aside>\n'
            f'      </section>\n')


def render_index(deck, prov):
    out = []
    for i, stack in enumerate(deck["stacks"]):
        if i > 0 and deck["sections"][stack["sec"]].get("lecture"):
            out.append(render_divider(deck, stack))
        for sid in stack["slides"]:
            out.append(render_slide(deck, stack["sec"], sid, deck["slides"][sid], prov))
    title = html.escape(deck["deckTitle"])
    return f"""<!doctype html>
<!-- SPDX-License-Identifier: Apache-2.0 | Copyright 2026 Fabio Campolim
     GENERATED by course/tools/build_deck.py from deck/content.en.js -- do not edit. -->
<html lang="{deck["lang"]}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="stylesheet" href="../shared/reveal/dist/reset.css">
  <link rel="stylesheet" href="../shared/reveal/dist/reveal.css">
  <link rel="stylesheet" href="../shared/theme.css">
</head>
<body>
  <div class="reveal">
    <div class="slides">
{"".join(out)}    </div>
  </div>
  <script src="../shared/reveal/dist/reveal.js"></script>
  <script src="../shared/reveal/plugin/notes/notes.js"></script>
  <script src="content.en.js"></script>
  <script src="../shared/loader.js"></script>
  <script src="../shared/nav.js"></script>
  <script>
    Reveal.initialize({{
      width: 1920, height: 1080, margin: 0.02,
      hash: true, progress: false, center: false, controls: false,
      transition: "fade", transitionSpeed: "fast",
      plugins: [RevealNotes]
    }}).then(function () {{ DeckNav.init(Reveal); }});
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------- handout ---

def render_handout(deck, prov):
    secs = []
    for stack in lectures(deck):
        sec = deck["sections"][stack["sec"]]
        slides = [deck["slides"][s] for s in stack["slides"]]
        ideas = "".join(f"<li>{s['lead']}</li>" for s in slides if s.get("lead") and s["level"] != "math")
        eqs = "".join(f"<li><span class='eq'>{e['math']}</span> <span class='lab'>— {html.escape(e['label'])}</span></li>"
                      for s in slides for e in s.get("eqs", []))
        figs = sorted({s[k] for s in slides for k in ("fig", "fig2") if k in s})
        figlist = ", ".join(f"§{_resolve_figure(f, prov)[1]['section']} cell {_resolve_figure(f, prov)[1]['cell']}" for f in figs)
        secs.append(f"""
<section class="lecture">
  <h2>{html.escape(sec['lecture'])} · {html.escape(sec['name'])}
      <span class="nb">notebook {html.escape(sec['notebook'])}</span></h2>
  <p class="summary">{html.escape(sec['summary'])}</p>
  <h3>Key ideas</h3><ul>{ideas}</ul>
  {'<h3>Equations</h3><ul class="eqs">' + eqs + '</ul>' if eqs else ''}
  <p class="figs">Figures shown: {figlist or 'none'} (all generated by the notebook).</p>
</section>""")
    gloss = "".join(f'<div class="term"><dt>{html.escape(t)}</dt> <dd>{html.escape(d)}</dd></div>'
                    for t, d in deck["glossary"])
    return f"""<!doctype html>
<!-- SPDX-License-Identifier: Apache-2.0 | Copyright 2026 Fabio Campolim
     GENERATED by course/tools/build_deck.py from deck/content.en.js -- do not edit. -->
<html lang="{deck["lang"]}">
<head>
<meta charset="utf-8">
<title>{html.escape(deck["deckTitle"])} — Companion Handout</title>
<style>
  @page {{ size: A4; margin: 16mm 15mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "Segoe UI", system-ui, sans-serif; color: #1c2128; font-size: 10.5pt; line-height: 1.45;
         max-width: 190mm; margin: 0 auto; padding: 10mm 0; }}
  h1 {{ font-size: 20pt; letter-spacing: -0.01em; }}
  h2 {{ font-size: 13pt; margin: 14pt 0 6pt 0; color: #0d419d; border-bottom: 2px solid #d0d7de; padding-bottom: 3pt; }}
  h2 .nb {{ float: right; font-size: 9pt; color: #57606a; font-weight: 500; margin-top: 4pt; }}
  h3 {{ font-size: 10.5pt; margin: 8pt 0 3pt 0; color: #3d444d; }}
  p {{ margin: 4pt 0; }}
  .sub {{ color: #57606a; font-size: 10pt; }}
  .summary {{ font-style: italic; color: #3d444d; }}
  .lecture {{ break-inside: avoid-page; page-break-inside: avoid; margin-bottom: 8pt; }}
  ul {{ margin: 3pt 0 3pt 14pt; }}
  li {{ margin: 2pt 0; }}
  .eqs li {{ list-style: none; margin-left: -14pt; }}
  .eq {{ font-family: Georgia, serif; font-style: italic; }}
  .eq .fn, .eq .op, .eq .num {{ font-style: normal; }}
  .lab {{ color: #57606a; font-size: 9pt; }}
  .figs {{ color: #57606a; font-size: 9pt; }}
  code {{ font-family: Consolas, monospace; font-size: 9pt; background: #f6f8fa; padding: 0 3pt; border-radius: 3pt; }}
  strong {{ color: #0d419d; }} em {{ font-style: normal; color: #0d419d; }}
  table.syl {{ width: 100%; border-collapse: collapse; margin: 6pt 0 10pt 0; font-size: 9.5pt; }}
  table.syl th {{ text-align: left; color: #57606a; font-weight: 600; padding: 3pt 6pt; border-bottom: 1.5px solid #d0d7de; }}
  table.syl td {{ padding: 3pt 6pt; border-bottom: 1px solid #eaeef2; vertical-align: top; }}
  .cols2 {{ column-count: 2; column-gap: 18pt; }}
  dl {{ font-size: 9.3pt; }} dt {{ font-weight: 600; display: inline; }} dd {{ display: inline; margin: 0; color: #3d444d; }}
  .term {{ break-inside: avoid; margin-bottom: 4pt; }}
  .foot {{ color: #8c959f; font-size: 8.5pt; margin-top: 12pt; border-top: 1px solid #d0d7de; padding-top: 4pt; }}
  sup, sub {{ font-size: 0.7em; }}
</style>
</head>
<body>
<h1>{html.escape(deck["deckTitle"])}</h1>
<p class="sub">{html.escape(deck["deckSubtitle"])} · companion handout · {html.escape(deck["author"])} · {html.escape(deck["edition"])}</p>
<p>Every figure in the lectures is produced by a cell of the companion chapter notebooks
(<code>chapters/</code> in lammps-skill; the caption names the chapter and cell). Each lecture runs from
a picture (intro) through the physics (core) to the equations (math); stop where your course stops. The slides are
<code>course/deck/index.html</code> (any browser, offline) with a PDF fallback at <code>course/slides.pdf</code>.</p>
<h2>Syllabus</h2>
<table class="syl"><tr><th>Lecture</th><th>Title</th><th>Notebook</th><th>Summary</th></tr>
{"".join(f"<tr><td>{html.escape(deck['sections'][s['sec']]['lecture'])}</td><td>{html.escape(deck['sections'][s['sec']]['name'])}</td><td>{html.escape(deck['sections'][s['sec']]['notebook'])}</td><td>{html.escape(deck['sections'][s['sec']]['summary'])}</td></tr>" for s in lectures(deck))}
</table>
{"".join(secs)}
<h2>Glossary</h2>
<div class="cols2"><dl>{gloss}</dl></div>
<p class="foot">lammps-skill course · Apache-2.0 · LAMMPS is GPL-2.0 by Sandia National Laboratories / NTESS and
the LAMMPS developers; this course uses it through its input script and manual as documented interfaces, and
contains no LAMMPS source. Slides: <code>course/deck/index.html</code>. Generated by <code>course/tools/build_deck.py</code>.</p>
</body>
</html>
"""


# ------------------------------------------------------------------ notes ---

def render_notes(deck, prov):
    out = [f"# {deck['deckTitle']} — lecturer notes\n",
           "<!-- GENERATED by course/tools/build_deck.py from deck/content.en.js; do not edit. -->\n",
           f"{deck['deckSubtitle']}. One entry per slide, in presentation order; each ends with the "
           "anticipated question (Q) and its answer (A). Level: intro → core → math within every lecture.\n"]
    for stack in deck["stacks"]:
        sec = deck["sections"][stack["sec"]]
        head = (f"{sec['lecture']} · {sec['name']} (notebook {sec['notebook']})"
                if sec.get("lecture") else sec["name"])
        out.append(f"\n## {head}\n")
        out.append(f"_{sec['summary']}_\n")
        for sid in stack["slides"]:
            s = deck["slides"][sid]
            figs = [s[k] for k in ("fig", "fig2") if k in s]
            figtxt = ("; figures " + ", ".join(f"`{f}` (§{_resolve_figure(f, prov)[1]['section']} cell {_resolve_figure(f, prov)[1]['cell']})"
                                              for f in figs)) if figs else ""
            out.append(f"\n### {strip_tags(s['title'])}  `[{s['level']}]`\n")
            out.append(f"Slide `#{sid}`{figtxt}.\n\n{strip_tags(s['notes'])}\n")
    return "".join(out)


# ------------------------------------------------------------------- main ---

def outputs(deck, prov):
    return {INDEX: render_index(deck, prov),
            HANDOUT: render_handout(deck, prov),
            NOTES: render_notes(deck, prov)}


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--content", default=CONTENT, help="content file (deck/content.en.js)")
    p.add_argument("--check", action="store_true",
                   help="do not write; exit 1 if index.html, handout or notes differ from the content")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    deck = load_content(a.content)
    prov = load_provenance()
    stale = []
    for path, text in outputs(deck, prov).items():
        if a.check:
            try:
                with open(path, encoding="utf-8") as f:
                    current = f.read()
            except FileNotFoundError:
                current = None
            if current != text:
                stale.append(os.path.relpath(path, COURSE))
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        if not a.quiet:
            print(f"wrote {os.path.relpath(path, COURSE)}")
    if a.check:
        for s in stale:
            print(f"stale: {s} -- run build_deck.py", file=sys.stderr)
        if not a.quiet:
            print(f"{len(stale)} stale output(s)")
        return 1 if stale else 0
    if not a.quiet:
        n = sum(len(s["slides"]) for s in deck["stacks"])
        d = sum(1 for i, s in enumerate(deck["stacks"])
                if i > 0 and deck["sections"][s["sec"]].get("lecture"))
        print(f"ok: {len(lectures(deck))} lectures, {n} slides + {d} dividers (flat, linear)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
