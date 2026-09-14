/* SPDX-License-Identifier: Apache-2.0
   Copyright 2026 Fabio Campolim
   Content loader for the lammps-skill course (from the AILECTURE decks; nested keys added). */
/* Content injection: all prose lives in content.<lang>.js (window.DECK_CONTENT).
   Layout elements declare data-t="slideId.key"; notes asides declare data-notes="slideId".
   Swapping language = swapping the content file include. */
function applyContent(deck) {
  if (!deck || !deck.slides) { console.error("loader: DECK_CONTENT missing"); return; }
  document.title = deck.deckTitle;
  document.querySelectorAll("[data-t]").forEach(function (el) {
    var ref = el.getAttribute("data-t");
    var dot = ref.indexOf(".");
    var slide = ref.slice(0, dot), key = ref.slice(dot + 1);
    // key may be a path: "bullets.0", "eqs.1.math", "table.rows.2.0"
    var entry = deck.slides[slide];
    key.split(".").forEach(function (part) { entry = (entry === undefined || entry === null) ? undefined : entry[part]; });
    if (entry !== undefined && entry !== null) {
      el.innerHTML = entry;
    } else {
      console.error("loader: missing content for " + ref);
      el.innerHTML = "⚠ " + ref;
    }
  });
  document.querySelectorAll("aside.notes[data-notes]").forEach(function (el) {
    var slide = el.getAttribute("data-notes");
    var entry = deck.slides[slide];
    if (entry && entry.notes) { el.innerHTML = entry.notes; }
    else { console.error("loader: missing notes for " + slide); }
  });
}
document.addEventListener("DOMContentLoaded", function () { applyContent(window.DECK_CONTENT); });
