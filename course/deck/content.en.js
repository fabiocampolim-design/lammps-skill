/* SPDX-License-Identifier: Apache-2.0
   Copyright 2026 Fabio Campolim
   lammps-skill course content, English. Strict JSON after the assignment:
   course/tools/build_deck.py, the handout, the lecturer notes and the tests all
   parse it. Figures are named by their provenance key (course/deck/figs).
   Plan A (docs/superpowers/plans/2026-09-13-lammps-skill-course-infra.md) ships one slide per
   lecture; Plan B adds the intro -> core -> math depth. */
window.DECK_CONTENT = {
  "lang": "en",
  "deckTitle": "Molecular Dynamics with LAMMPS",
  "deckSubtitle": "An undergraduate course in eleven lectures",
  "author": "Fabio Campolim",
  "edition": "2026",
  "sections": {
    "orientation": {"name": "Orientation", "lecture": "L0", "notebook": "ch00",
      "summary": "What LAMMPS is, its two release lines, the install routes this project measured, and how record-or-run lets every chapter run with or without LAMMPS installed."},
    "first-sim": {"name": "First Simulation", "lecture": "L1", "notebook": "ch01",
      "summary": "A Lennard-Jones melt end to end -- Spec, check, run, read the log, plot -- through the checker's fourteen rules, one at a time."},
    "forces": {"name": "Forces and Integration", "lecture": "L2", "notebook": "ch02",
      "summary": "Velocity Verlet in mdlite, forces checked against a numerical derivative, and energy conservation against the timestep, cross-checked with LAMMPS at 3e-13."},
    "thermostats": {"name": "Thermostats", "lecture": "L3", "notebook": "ch03",
      "summary": "Berendsen, Langevin and a Nose-Hoover chain: what each one conserves, what each distorts, and NVT checked against the NIST reference within 3 sigma."},
    "ensembles": {"name": "Ensembles and Restarts", "lecture": "L4", "notebook": "ch04",
      "summary": "An NPT sketch with its limits stated, LAMMPS's own fix npt, and restarting a run through write_restart / read_restart."},
    "eam": {"name": "Potentials: EAM", "lecture": "L5", "notebook": "ch05",
      "summary": "An embedded-atom potential read from a real setfl file: copper's lattice constant and cohesive energy against the recorded 3e-5 -- and why the potential file is never shipped."},
    "structure": {"name": "Structure and Analysis", "lecture": "L6", "notebook": "ch06",
      "summary": "Radial distribution function, structure factor, mean-squared displacement, diffusion coefficient and velocity autocorrelation, computed from one trajectory."},
    "minimisation": {"name": "Minimisation", "lecture": "L7", "notebook": "ch07",
      "summary": "Steepest descent against FIRE on an LJ wall -- and the lesson that gives lost atoms their name: an uncapped step explodes at fmax 2.6e14."},
    "reading": {"name": "Reading What LAMMPS Writes", "lecture": "L8", "notebook": "ch08",
      "summary": "Data, dump, log and restart formats, and four pitfalls this project hit first: thermo normalisation, dump precision, the restart magic number, multi-format logs."},
    "build": {"name": "Choosing a Build", "lecture": "L9", "notebook": "ch09",
      "summary": "What a 314-case sweep of the examples says: package list beats package count, and how to read Installation.packages before choosing styles."},
    "scaling": {"name": "Scaling and Limits", "lecture": "L10", "notebook": "ch10",
      "summary": "MPI and OpenMP speed-up on eight cores, where it stops, and what this machine honestly cannot do -- no GPU, no -partition methods."}
  },
  "stacks": [
    {"sec": "orientation", "slides": ["orientation-intro", "orientation-releases", "orientation-toolkit", "orientation-pylj", "orientation-packages", "orientation-validation"]},
    {"sec": "first-sim", "slides": ["first-sim-intro", "first-sim-checker", "first-sim-checker-result", "first-sim-script", "first-sim-recordrun"]},
    {"sec": "forces", "slides": ["forces-intro"]},
    {"sec": "thermostats", "slides": ["thermostats-intro"]},
    {"sec": "ensembles", "slides": ["ensembles-intro"]},
    {"sec": "eam", "slides": ["eam-intro"]},
    {"sec": "structure", "slides": ["structure-intro", "structure-msd-vacf"]},
    {"sec": "minimisation", "slides": ["minimisation-intro"]},
    {"sec": "reading", "slides": ["reading-intro"]},
    {"sec": "build", "slides": ["build-intro"]},
    {"sec": "scaling", "slides": ["scaling-intro"]}
  ],
  "slides": {
    "orientation-intro": {
      "level": "intro", "layout": "text",
      "title": "What is LAMMPS, and what is this course?",
      "lead": "LAMMPS is a classical molecular dynamics engine maintained by Sandia/NTESS: you write an <em>input script</em>, it integrates Newton's equations for a box of particles under a chosen potential.",
      "bullets": [
        "Two release lines track upstream: <span class='math'>develop</span> (daily) and one <strong>stable</strong> release a year with periodic updates.",
        "This course sits on top of <code>lammpskill</code> (a verified toolkit: script builder, checker, parsers, runner) and <code>mdlite</code> (a small teaching engine that reproduces LAMMPS's numbers from scratch).",
        "Every chapter follows <strong>record-or-run</strong>: with LAMMPS installed, the computation runs live; without it, a stored result loads instead -- the figures never lie about which happened."
      ],
      "notes": "Open by naming the two audiences this course actually has: someone with LAMMPS installed who will run every cell, and someone without it who still sees real numbers and real figures. Q: \"Do I need to install LAMMPS to follow this course?\" A: No -- every chapter runs and renders its figures either way; record-or-run loads a stored, provenance-checked result when no installation is detected."
    },
    "orientation-releases": {
      "level": "core", "layout": "text",
      "title": "Two release lines, and why the difference matters",
      "lead": "LAMMPS ships two lines from the same repository, and a distribution package usually tracks one without saying so.",
      "bullets": [
        "A <strong>stable</strong> release is cut once a year and then <em>updated</em> for a long time -- <code>stable_22Jul2025</code> was still receiving updates fourteen months later, update 6, September 2026.",
        "<strong>Feature</strong> (patch) releases follow every six to eight weeks, alongside the stable updates.",
        "The Ubuntu 26.04 package is <code>20251210</code> -- the 10 December 2025 <em>feature</em> release, not the stable one it might be assumed to track."
      ],
      "notes": "Make the point concrete before naming any policy: ask the room what \"I installed LAMMPS\" tells you, then show that it doesn't even say which of two active lines you are running. Q: \"Which line should I use?\" A: Stable for anything you plan to keep running for months (fewer surprises between runs); develop or the newest feature release if you need a capability that only landed recently -- this project pins stable as primary and watches develop."
    },
    "orientation-toolkit": {
      "level": "core", "layout": "text",
      "title": "What lammpskill adds on top of LAMMPS itself",
      "lead": "lammpskill is the part of this project that talks to LAMMPS -- five pieces behind one import.",
      "bullets": [
        "<code>install</code>: seven routes behind one contract, each measured on this machine rather than assumed to work.",
        "<code>script</code>: build an input from a <code>Spec</code>, then a checker with fourteen rules, each pointing at the manual page it comes from.",
        "<code>io</code>: read what LAMMPS writes -- data files, dumps, three log thermo styles, the restart header, EAM potential files.",
        "<code>run</code>: a subprocess backend for any host, an in-process backend through the official python module -- both return the same <code>Result</code>.",
        "<code>post</code>: RDF, MSD, diffusion, VACF, structure factor, block averages, checked against reference tables that carry their own provenance."
      ],
      "notes": "This is the map the rest of the course keeps referring back to -- naming the five pieces once here means later lectures can say \"the checker\" or \"post\" without re-explaining. Q: \"Is any of this required to use LAMMPS?\" A: No -- lammpskill drives a LAMMPS you already have; every optional bridge (ASE, pymatgen, MDAnalysis, OVITO) is exactly that, optional, and the core depends on numpy and scipy only."
    },
    "orientation-pylj": {
      "level": "core", "layout": "text",
      "title": "mdlite's closest neighbour, and how it differs",
      "lead": "mdlite is a small molecular-dynamics engine written from scratch in numpy -- a teaching object, not an MD code; nobody should run research on it.",
      "bullets": [
        "Its closest relative is <strong>pylj</strong> (McCluskey, Morgan, Edler and Parker, <em>JOSE</em> 1, 19, 2018, MIT): a Lennard-Jones teaching engine in Jupyter, written for undergraduate exercises, with Monte Carlo as well as dynamics.",
        "mdlite differs in two ways: it sits <em>next to</em> a toolkit that drives the production code, so a chapter can compute something in twenty lines of numpy and then compute the same thing in LAMMPS and subtract.",
        "And its numbers are cross-checked against that production code, with the residues recorded -- not asserted, read from a file."
      ],
      "notes": "If anyone in the room already knows pylj, say so directly rather than let the comparison go unstated -- positioning against a known neighbour is more convincing than a comparison nobody in the room can check. Q: \"Why not just use pylj?\" A: pylj is the gentler first contact and a fine choice for that; mdlite trades some of that gentleness for living inside a project that also drives real LAMMPS, so every number it teaches has an independent check."
    },
    "orientation-packages": {
      "level": "core", "layout": "table",
      "title": "Package list, never package count",
      "lead": "The most common way to be wrong about a LAMMPS build is to assume a bigger package set is a superset.",
      "table": {
        "head": ["Build", "Packages", "Examples cases that started (of 314)"],
        "rows": [
          ["Ubuntu package, 10 Dec 2025", "52", "184"],
          ["This project's source build, core preset", "11", "137"]
        ]
      },
      "notes": "Land the surprise before the explanation: the bigger build starts more cases overall, and still cannot run ten that the smaller one can (EXTRA-FIX, which the Ubuntu build omits). Q: \"So which build should I use?\" A: Neither dominates -- ask Installation.packages (read from lmp -h) for the specific style you need, never trust the package count alone; L9 (Choosing a Build) measures this in full."
    },
    "orientation-validation": {
      "level": "math", "layout": "table",
      "title": "What 'cross-checked against LAMMPS' actually means, in numbers",
      "lead": "mdlite's claim is not that it is fast or complete -- it is that where it teaches a number, that number has been checked against the code it is teaching you to use.",
      "table": {
        "head": ["Quantity", "mdlite vs LAMMPS", "Where"],
        "rows": [
          ["Lennard-Jones forces, 256 atoms", "agree to 3×10<sup>-13</sup>", "L2, Forces and Integration"],
          ["Copper lattice constant a<sub>0</sub> and cohesive energy", "agree to 3×10<sup>-5</sup>", "L5, Potentials: EAM"],
          ["NVT state point (T*=0.85, ρ*=0.776)", "agrees with the NIST reference within 3σ", "L3, Thermostats"]
        ]
      },
      "notes": "This is the slide to return to if anyone doubts a number mdlite reports later in the course -- every one of these three checks is a JSON file under data/records/, not a claim in a slide. Q: \"Couldn't these numbers have been chosen to make mdlite look good?\" A: They're read by the test suite from the record files, and the record files are regenerated by scripts this project's own local runs execute -- a session cannot quietly rewrite the tolerance without the test that reads it also changing."
    },
    "first-sim-intro": {
      "level": "intro", "layout": "fig-right", "fig": "ch01-f1",
      "title": "One simulation, start to finish",
      "lead": "<code>Spec</code> describes the case in Python; <code>check</code> applies fourteen rules against the manual before anything runs; <code>run</code> calls LAMMPS; the log comes back as a typed <code>ThermoRun</code>.",
      "bullets": [
        "The case: an fcc Lennard-Jones lattice heated until it melts, in reduced (LJ) units.",
        "Nothing here is a hand-typed input script -- the checker exists so a beginner's script fails before LAMMPS ever sees it.",
        "The same four steps -- build, check, run, read -- reappear in every later chapter."
      ],
      "notes": "This is the one lecture to slow down on if the audience has never seen a molecular dynamics input before: walk the four steps as a loop they will use for the rest of the course. Q: \"Why not just write the LAMMPS script directly?\" A: You can -- Spec generates exactly the script the manual describes; the checker is what catches the mistakes (wrong units, a missing pair_coeff, an unset timestep) before a run silently does the wrong thing."
    },
    "first-sim-checker": {
      "level": "core", "layout": "table",
      "title": "Fourteen rules, each pointing at a manual page",
      "lead": "lammpskill.script.check() does not trust a description of what a mistake looks like -- each rule is confirmed against one minimal snippet built to trigger exactly it.",
      "table": {
        "head": ["Rule", "What it catches"],
        "rows": [
          ["C01", "no <code>units</code> command"],
          ["C02", "<code>coul/long</code> in the pair style with no <code>kspace_style</code>"],
          ["C05", "<code>run</code> before a <code>pair_style</code> is set"],
          ["C07", "a fix ID reused without <code>unfix</code>"],
          ["C11", "<code>velocity create</code> before <code>mass</code> is set"],
          ["C14", "<code>read_data</code> naming a file that does not exist"]
        ]
      },
      "notes": "Six of fourteen is enough to show the range -- from a missing keyword to a file that will not be there when LAMMPS looks for it. Q: \"Does the checker run LAMMPS to find these?\" A: No -- it is a static check of the rendered script text against rules read from the manual; that is why it also works with no LAMMPS installed."
    },
    "first-sim-checker-result": {
      "level": "core", "layout": "code",
      "title": "All fourteen, confirmed at once",
      "lead": "The chapter does not just list the rules -- it runs all fourteen deliberately-broken snippets through the checker and confirms every one is caught.",
      "code": "triggered, missed = [], []\nfor code_, snippet in SNIPPETS.items():\n    findings = check(snippet, workdir=...)\n    codes = [f.code for f in findings]\n    (triggered if code_ in codes else missed).append(code_)\n\nprint(len(triggered), \"/\", len(SNIPPETS), \"rules triggered by their own minimal snippet\")\n# 14 / 14 rules triggered by their own minimal snippet",
      "notes": "This is the difference between documenting fourteen rules and demonstrating them -- the assertion the chapter's tally cell checks is exactly len(missed) == 0. Q: \"What happens if a fifteenth rule is added later?\" A: It needs its own deliberately-broken snippet in this same dictionary, or this cell's count silently stays at fourteen while the checker knows fifteen -- the chapter's own discipline applies to itself."
    },
    "first-sim-script": {
      "level": "core", "layout": "code",
      "title": "A Spec, rendered -- not a script typed by hand",
      "lead": "lammpskill.script.lj_melt() is a preset Spec: reduced units, an FCC lattice at the melt density rho=0.8442, 4000 atoms by default. render() turns it into the actual input text, in the order the manual's Commands_structure page prescribes.",
      "code": "from lammpskill.script import lj_melt, render\n\nspec = lj_melt()          # rho=0.8442, T=3.0, steps=250\ntext = render(spec)       # the real LAMMPS input, in manual order",
      "notes": "Contrast this with copying an example script -- nothing here is text a human typed and might have gotten subtly wrong; it is generated from the same Spec object the checker and the runner also see. Q: \"Could I edit the rendered text directly?\" A: You could, but then the checker and the runner are checking and running text that no longer corresponds to any Spec -- the pattern this course teaches is to change the Spec and re-render, the same discipline as never hand-editing a generated notebook."
    },
    "first-sim-recordrun": {
      "level": "math", "layout": "code",
      "title": "run_or_load: the pattern every later lecture uses",
      "lead": "The one call that makes a chapter work whether or not LAMMPS is installed.",
      "code": "def compute():\n    result = run(spec, workdir, time_limit=300)\n    return {...}          # only plain, JSON-safe data\n\nrec = run_or_load(\"lj_melt_ch01\", compute, records_dir=\"../data/records\")\n# with LAMMPS: compute() runs, its result is written to the record\n# without LAMMPS: the record is loaded, compute() never runs\n# with neither: rec[\"source\"] == \"skip\", visibly",
      "notes": "This is worth stating precisely because it is the single mechanism that makes the whole course reviewable without installing anything -- every later lecture's run_or_load call is exactly this shape. Q: \"What stops a stale record from silently going unnoticed?\" A: Nothing inside run_or_load itself -- the discipline is that compute() is also what regenerates the record when it needs to change, and the notebook's tally cell asserts on the record's own numbers, so a record that quietly went wrong fails a visible assertion, not a silent one."
    },
    "forces-intro": {
      "level": "intro", "layout": "text",
      "title": "Integration is the part that must not be approximate",
      "lead": "<code>mdlite</code> implements velocity Verlet from the same equations LAMMPS integrates, so its forces can be checked against a numerical derivative and against LAMMPS itself.",
      "bullets": [
        "Forces from <code>mdlite</code>'s Lennard-Jones match a central-difference numerical derivative to machine precision.",
        "Against a real LAMMPS run of the identical case, the two energies agree to <span class='math'>3×10<sup>-13</sup></span> -- there is no approximation hiding in either implementation.",
        "Energy conservation versus timestep is the practical version of the same idea: too large a step and the trajectory drifts, long before it visibly explodes."
      ],
      "notes": "This slide's job is to establish trust in mdlite before it is used as a comparison tool for the rest of the course. Q: \"If mdlite already gets the right answer, why use LAMMPS at all?\" A: mdlite is a teaching engine, deliberately limited (one thermostat family, no parallelism, no accelerated neighbour lists at scale) -- LAMMPS is the production tool; the agreement is what licenses using mdlite to explain what LAMMPS is doing."
    },
    "thermostats-intro": {
      "level": "intro", "layout": "fig-right", "fig": "ch03-f1",
      "title": "Three ways to hold a temperature",
      "lead": "A thermostat couples the system to an external bath; which one you choose changes what else it disturbs.",
      "bullets": [
        "Berendsen: fast, simple, but does not sample the correct canonical ensemble -- fine for equilibration, not for production statistics.",
        "Langevin: adds friction and noise per atom; correct ensemble, but its own set of fluctuations to tune.",
        "Nose-Hoover chain: an extra dynamical variable keeps the total (system + thermostat) energy conserved -- checked here directly."
      ],
      "notes": "Beginners on the LAMMPS forum ask 'which thermostat, for how long' more than almost anything else (docs/08) -- this slide is where that question gets a real answer instead of a rule of thumb. Q: \"Which one should I actually use?\" A: Berendsen or Langevin to equilibrate quickly, then Nose-Hoover (LAMMPS's fix nvt) once you are measuring an ensemble average that has to be exactly canonical."
    },
    "ensembles-intro": {
      "level": "intro", "layout": "fig-right", "fig": "ch04-f1",
      "title": "Beyond NVT: pressure, and picking a run back up",
      "lead": "NPT couples a barostat to the thermostat so the box itself relaxes toward a target pressure; restarting means LAMMPS can continue a run exactly, not merely resume from the last log line.",
      "bullets": [
        "The <code>mdlite</code> NPT here is a stated sketch (Berendsen barostat only) -- good enough to show the mechanism, not a substitute for LAMMPS's <code>fix npt</code>.",
        "<code>write_restart</code> / <code>read_restart</code> carry the box and every atom's state; a restart script cannot redeclare <code>units</code>, <code>dimension</code> or <code>boundary</code> once the box exists.",
        "This is the pattern for a run too long to finish in one session: checkpoint, then continue."
      ],
      "notes": "Flag directly that mdlite's NPT is intentionally the least complete piece of the teaching engine -- that honesty is itself part of what this course teaches about the difference between a teaching model and a production one. Q: \"What happens if I put `units lj` back into a restart-continuation script?\" A: LAMMPS refuses -- units, dimension and boundary are fixed the moment the box is read from the restart file; lammpskill's Spec(units=None) is how you build a script that respects that."
    },
    "eam-intro": {
      "level": "intro", "layout": "text",
      "title": "A real potential, from a real file",
      "lead": "The embedded-atom method adds a density-dependent term to a pairwise potential -- realistic enough for metals, and never something this project ships.",
      "bullets": [
        "The setfl file is fetched by the installer from the official source, never tracked in this repository (rule 7).",
        "From it, LAMMPS and <code>mdlite</code> both reproduce copper's lattice constant <span class='math'>a<sub>0</sub></span> and cohesive energy <span class='math'>E<sub>coh</sub></span>, agreeing to <span class='math'>3×10<sup>-5</sup></span>.",
        "This is the forum's other recurring beginner question -- wrong pair_coeff, a potential file that silently does not match the element -- answered by a case built the same checked way as chapter 1."
      ],
      "notes": "Tie this explicitly back to the licensing rule: the potential file is data the user's installer downloads, and that boundary matters for what this project is legally and practically allowed to redistribute. Q: \"Can I just copy a potential file from a tutorial into my project?\" A: You can use it (potential files are typically separately licensed for redistribution), but this project specifically never tracks one -- it is fetched fresh by the installer every time, so the source of truth is always the upstream file, not a possibly-stale copy."
    },
    "structure-intro": {
      "level": "intro", "layout": "fig-right", "fig": "ch06-f1",
      "title": "Turning a trajectory into physics",
      "lead": "A dump file is a sequence of raw coordinates; <code>lammpskill.post</code> turns it into the quantities a paper would actually report.",
      "bullets": [
        "g(r) and S(k) describe the same structure in real and reciprocal space -- one computed from the other, not measured independently.",
        "MSD's late-time slope gives a diffusion coefficient by the Einstein relation; block averages give it an honest error bar.",
        "The velocity autocorrelation function distinguishes a liquid (decays monotonically) from a solid (oscillates, atoms caged) -- itself a check that the case behaved as intended."
      ],
      "notes": "This lecture is the payoff for chapters 1-5: everything computed so far becomes a real analysis pipeline here. Q: \"Why fit the diffusion coefficient from only the second half of the MSD curve?\" A: The early part is ballistic, not diffusive -- Einstein's relation only holds in the diffusive regime, so fitting the whole curve would systematically bias D."
    },
    "structure-msd-vacf": {
      "level": "math", "layout": "two-figs", "fig": "ch06-f2", "fig2": "ch06-f3",
      "title": "From a trajectory to a diffusion coefficient",
      "lead": "The same run, seen two more ways: how far particles have moved (MSD) and how quickly they forget their own velocity (VACF) -- both routes to the same physics.",
      "eqs": [
        {"label": "Einstein relation (3D)", "math": "<span class='math'>D = lim<sub>t→∞</sub> MSD(t) / 6t</span>"}
      ],
      "bullets": [
        "<span class='math'>lammpskill.post.diffusion_coefficient</span> fits the slope over the second half of MSD(t), where the motion is genuinely diffusive.",
        "The VACF's decay to zero and the MSD's crossover from ballistic to diffusive are two views of the same relaxation time."
      ],
      "notes": "This is the slide where the course states the Einstein relation as an equation rather than only as code -- worth writing it out even for an audience that will mostly use the function. Q: \"Could I get D directly from the VACF instead of the MSD?\" A: Yes -- its time integral gives the same D by the Green-Kubo relation; lammpskill.post currently only implements the Einstein (MSD) route, which is why this slide shows VACF as a qualitative check rather than a second D estimate."
    },
    "minimisation-intro": {
      "level": "intro", "layout": "text",
      "title": "Why atoms get \"lost\"",
      "lead": "The single largest category of beginner questions on the LAMMPS forum is lost atoms and nan energies (docs/08) -- this chapter reproduces the mechanism directly.",
      "bullets": [
        "A fixed-size steepest-descent step on an LJ wall explodes: the recorded force reaches <span class='math'>f<sub>max</sub></span> = 2.6×10<sup>14</sup> before the run gives up (finding N-7).",
        "FIRE (adaptive step, velocity-aware) converges the same case without blowing up.",
        "The fix that matters in practice is not a better algorithm but a <strong>displacement cap</strong> -- bound how far one step is allowed to move an atom, whichever minimiser you use."
      ],
      "notes": "This is the slide to point back to every time a later chapter's run looks like it is about to fail -- the mechanism here is the same one behind almost every 'lost atoms' report. Q: \"Is a displacement cap a real LAMMPS feature or just a mdlite fix?\" A: Both -- LAMMPS's own min_style and fix nve/limit apply the identical idea; mdlite's minimiser demonstrates why it is needed, not a LAMMPS-specific workaround."
    },
    "reading-intro": {
      "level": "intro", "layout": "table",
      "title": "Four formats, four pitfalls",
      "lead": "Every format LAMMPS writes has one behaviour that looks like a bug the first time you meet it.",
      "table": {
        "head": ["Format", "The pitfall this project hit"],
        "rows": [
          ["log (thermo)", "<code>thermo_modify norm</code> defaults to per-atom in lj units -- an energy column can look off by the atom count until you know that"],
          ["dump", "float precision is truncated by default; a coordinate that looks identical to the data file may not be, bit for bit"],
          ["restart", "carries an undocumented 16-byte magic number this project had to observe directly rather than find in the manual"],
          ["log (multi style)", "the <code>multi</code> thermo style's block layout parses differently from the default one-line-per-step style"]
        ]
      },
      "notes": "Every row here is a finding this project recorded the hard way (N-4, N-5, N-6, N-18) -- tell the class that up front, it is more convincing than presenting them as textbook facts. Q: \"Where is this documented?\" A: Some of it is in the LAMMPS manual if you know to look; the restart magic number specifically was not documented anywhere this project found and had to be read directly from a hex dump."
    },
    "build-intro": {
      "level": "intro", "layout": "text",
      "title": "The build you have decides what you can run",
      "lead": "A 314-case sweep of LAMMPS's own example scripts, run on this project's two installed builds, is the evidence behind this lecture.",
      "bullets": [
        "Package <em>list</em> beats package <em>count</em>: an 11-package build ran cases a 52-package build could not, because the specific packages differed.",
        "<code>lammpskill.install.Installation.packages</code> is read from <code>lmp -h</code>, not assumed from the build recipe -- the same question (\"is the package actually in my build?\") the MOLFILE forum thread asked once, answered by measurement.",
        "The Windows installer is the single most-viewed installation thread of the year on the LAMMPS forum -- and the one route this project cannot yet speak to from its own measurements (open question Q-1)."
      ],
      "notes": "Be candid about the open question here rather than skipping it -- it is a real, stated gap in this project's coverage, not a rhetorical one. Q: \"How do I know if a package I need is in my build?\" A: Run `lmp -h` and read the package list it prints, or use `lammpskill.install.detect_all()` -- never assume from the build's name or from how many packages were compiled in."
    },
    "scaling-intro": {
      "level": "intro", "layout": "text",
      "title": "Where speed-up stops, and what this machine cannot do",
      "lead": "Measured on this project's 8-core, no-GPU machine: 2 MPI ranks gave 1.73x, 2 OpenMP threads gave 2.09x -- both honestly short of ideal.",
      "bullets": [
        "Parallel efficiency drops as communication overhead grows relative to the per-rank workload -- expected, and worth showing rather than assuming.",
        "This machine has no GPU and no <code>-partition</code> support, so KOKKOS/GPU acceleration and multi-replica methods (NEB, TAD) are out of scope here by design, not by oversight.",
        "The honest version of a scaling claim states the hardware it was measured on -- these numbers are this machine's, not a general LAMMPS property."
      ],
      "notes": "Close the course on the same note it opened on: every number here came from a real, named, bounded run -- that is the whole method of this project, applied one last time to the toolkit's own performance. Q: \"Would a GPU change this a lot?\" A: For pair-style-dominated cases, often yes -- but this project has none to measure, so the honest answer is a citation to LAMMPS's own KOKKOS/GPU documentation rather than a number this machine cannot produce."
    }
  },
  "glossary": [
    ["LJ units", "LAMMPS's reduced (Lennard-Jones) unit system: energy, length and mass are in units of the potential's own epsilon, sigma and particle mass, so every quantity is dimensionless."],
    ["record-or-run", "This project's pattern for a chapter cell that needs LAMMPS: with an installation detected, it runs and records the result; without one, it loads a previously recorded result instead."],
    ["thermostat", "A method that couples a simulated system to an external heat bath so it samples a chosen temperature instead of drifting under its own dynamics."],
    ["ensemble", "The statistical set a simulation samples from -- NVE (fixed energy), NVT (fixed temperature), NPT (fixed temperature and pressure) -- named by what is held fixed."],
    ["EAM", "Embedded-atom method: a potential for metals that adds an energy depending on the local electron density, on top of a pairwise term."],
    ["RDF / g(r)", "Radial distribution function: the probability of finding another particle at distance r, relative to a uniform (ideal-gas) density."],
    ["MSD", "Mean-squared displacement: the average squared distance particles have moved after time t; its late-time slope gives the diffusion coefficient."],
    ["checker", "lammpskill's fourteen-rule static check of a generated input script against the LAMMPS manual, run before any script reaches LAMMPS."]
  ]
};
