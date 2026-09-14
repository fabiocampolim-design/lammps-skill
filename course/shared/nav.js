/* SPDX-License-Identifier: Apache-2.0
   Copyright 2026 Fabio Campolim
   DeckNav for the lammps-skill course — single-level navigation aids.

   The deck is FLAT: the arrow keys / clicker simply go to the next or
   previous slide, handled entirely by reveal.js — nothing here intercepts
   them, so navigation is never cut by an animation. DeckNav only adds:
     - a bottom-right label: current lecture, position in it, global position;
     - a clickable segmented progress bar (one segment per lecture);
     - two mouse buttons + Shift+arrow to jump between lecture dividers. */
window.DeckNav = (function () {
  "use strict";

  function init(R) {
    var deck = window.DECK_CONTENT || { sections: {} };
    var slides = R.getSlides();                       // flat: one entry per slide
    var total = slides.length;

    // lecture boundaries: first slide index of each data-sec run
    var runs = [];                                    // [{sec, name, start, count}]
    slides.forEach(function (s, i) {
      var sec = s.getAttribute("data-sec") || "";
      if (!runs.length || runs[runs.length - 1].sec !== sec) {
        var entry = deck.sections[sec] || {};
        var label = entry.lecture ? entry.lecture + " · " : "";
        runs.push({ sec: sec, name: label + (entry.name || sec), start: i, count: 0 });
      }
      runs[runs.length - 1].count += 1;
    });
    function runOf(i) {
      for (var r = runs.length - 1; r >= 0; r--) if (i >= runs[r].start) return r;
      return 0;
    }
    function indexOfCurrent() { return R.getIndices().h; }

    // ---- label (bottom right) --------------------------------------------
    var el = document.createElement("div");
    el.className = "deck-nav";
    el.innerHTML =
      '<button id="dn-prev" title="previous lecture (Shift+←)">‹</button>' +
      '<span id="dn-label"></span>' +
      '<button id="dn-next" title="next lecture (Shift+→)">›</button>';
    document.body.appendChild(el);

    function jump(delta) {
      var r = runOf(indexOfCurrent()) + delta;
      if (r >= 0 && r < runs.length) R.slide(runs[r].start);
    }
    document.getElementById("dn-prev").addEventListener("click", function () { jump(-1); });
    document.getElementById("dn-next").addEventListener("click", function () { jump(1); });
    // Shift+arrows only; plain arrows stay 100% reveal's own
    document.addEventListener("keydown", function (e) {
      if (!e.shiftKey) return;
      if (e.key === "ArrowRight") { e.preventDefault(); jump(1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); jump(-1); }
    });

    // ---- segmented progress bar (one segment per lecture, clickable) -----
    var prog = document.createElement("div");
    prog.className = "deck-progress";
    var fills = runs.map(function (run) {
      var seg = document.createElement("div");
      seg.className = "dp-seg";
      seg.style.flexGrow = String(run.count);
      seg.title = run.name;
      var fill = document.createElement("div");
      fill.className = "dp-fill";
      seg.appendChild(fill);
      seg.addEventListener("click", function () { R.slide(run.start); });
      prog.appendChild(seg);
      return fill;
    });
    document.body.appendChild(prog);

    function update() {
      var i = indexOfCurrent();
      var r = runOf(i);
      document.getElementById("dn-label").textContent =
        runs[r].name + "  " + (i - runs[r].start + 1) + "/" + runs[r].count +
        "  ·  " + (i + 1) + "/" + total;
      document.getElementById("dn-prev").disabled = r === 0;
      document.getElementById("dn-next").disabled = r === runs.length - 1;
      fills.forEach(function (fill, k) {
        var w = k < r ? 100 : k > r ? 0
              : Math.round((i - runs[k].start + 1) / runs[k].count * 100);
        fill.style.width = w + "%";
      });
    }
    R.on("slidechanged", update);
    R.on("overviewshown", function () { el.style.display = "none"; });
    R.on("overviewhidden", function () { el.style.display = ""; });
    if (R.isReady()) update(); else R.on("ready", update);
  }

  return { init: init };
})();
