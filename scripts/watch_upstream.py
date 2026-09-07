#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""Weekly upstream watch for LAMMPS and its ecosystem (playbook S8 / rule 23).

All sources anonymous, one request per second, descriptive User-Agent. Every source is wrapped:
one that is unreachable is recorded in the report, never raised -- a watch that dies because a
forum is down stops being a watch.

- GitHub API, `lammps/lammps`: head of the default branch, releases (never `/tags`: GitHub does
  not date-order them, so a new tag can fall outside the window), and the most recently
  updated open issues and pull requests. `docs/07` measured ~46 open issues and ~30 open PRs, so
  the counts themselves are a signal when they move.
- Web pages by visible-text hash: lammps.org, the manual's front page and its version, the
  download page, the Windows installer directory (the route we cannot measure -- Q-1/N-2), and the
  manual's *Python_install* page, because P-1's draft depends on what that page says.
- matsci.org: the LAMMPS category's `latest.json`. Release announcements appear there the same day
  as the tags (`docs/08`), so it doubles as a release signal.
- PyPI: `lammps` and the packages this toolkit optionally bridges to.
- `--pull`: `git fetch` / `git pull --ff-only` for every clone under `--upstream-dir`, with the
  count of new commits per clone. A directory without `.git` is reported and left alone.

    python scripts/watch_upstream.py --snapshot                 # baseline, writes no report
    python scripts/watch_upstream.py --weekly --pull            # delta vs the last snapshot,
                                                                # writes docs/watch/YYYY-WW.md
Idempotent within a week, and the week's report is never emptied: a second run compares against the
first run's snapshot, so it rewrites the report only when something actually moved since.
A watched page that hashes to fewer than MIN_PAGE_WORDS visible words is reported as a warning:
a sensor pointed at a redirect stub never fires, which is what www.lammps.org/download.html was.
Audit log under <state-dir>/logs/. Exit 0 ok, 1 a source was unreachable, 2 usage error.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
STUDY = os.path.normpath(os.path.join(ROOT, ".."))
sys.path.insert(0, ROOT)
from lammpskill import __version__  # noqa: E402

UA = "lammps-skill/%s upstream watch (study project; anonymous, 1 req/s)" % __version__
PAUSE = 1.0
GITHUB_REPOS = ["lammps/lammps"]
FIRST_CAP = 15
PAGES = {
    "lammps_org_home": "https://www.lammps.org/",
    "manual_home": "https://docs.lammps.org/",
    "manual_python_install": "https://docs.lammps.org/Python_install.html",
    "manual_build_package": "https://docs.lammps.org/Build_package.html",
    "download": "https://www.lammps.org/download/",
    "windows_installers": "https://rpm.lammps.org/windows/",
}
# A watched page below this many visible words is a redirect stub or an error page,
# not a sensor: www.lammps.org/download.html hashed to ONE word (2026-09-07).
MIN_PAGE_WORDS = 50
FORUM_LATEST = "https://matsci.org/c/lammps/40/l/latest.json"
PYPI_PACKAGES = ["lammps", "lammpsio", "pylammpsmpi", "ase", "pymatgen", "MDAnalysis"]


def _get(url, accept=None, timeout=60):
    """(bytes, headers dict). Tests monkeypatch this; nothing else here opens a socket."""
    headers = {"User-Agent": UA}
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), {k.lower(): v for k, v in r.headers.items()}


def _get_json(url, accept="application/json"):
    body, h = _get(url, accept)
    time.sleep(PAUSE)
    return json.loads(body.decode("utf-8")), h


def _get_text(url):
    body, h = _get(url)
    time.sleep(PAUSE)
    return body.decode("utf-8", "replace"), h


def visible_text_hash(page_html):
    """Hash of what a reader sees: markup, scripts and styles removed, whitespace collapsed."""
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page_html, flags=re.S | re.I)
    t = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16], len(t.split())


def _short(items, keys, cap=FIRST_CAP):
    return [{k: x.get(k) for k in keys} for x in (items or [])[:cap]]


# ------------------------------------------------------------------------------- snapshot

def snapshot():
    """The current upstream state. Every source is wrapped: failures are recorded, not raised."""
    snap = {"taken": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "errors": {}, "warnings": {}, "github": {}, "pages": {}, "forum": {}, "pypi": {}}

    for repo in GITHUB_REPOS:
        try:
            api = "https://api.github.com/repos/" + repo
            info, _ = _get_json(api)
            branch = info.get("default_branch", "develop")
            head, _ = _get_json("%s/commits/%s" % (api, branch))
            # /releases, never /tags: GitHub does not date-order tags (the live call
            # returned stable_31Mar2017 first), so a new tag can fall outside the window.
            rels, _ = _get_json(api + "/releases?per_page=15")
            issues, _ = _get_json(api + "/issues?state=open&sort=updated&per_page=15")
            pulls, _ = _get_json(api + "/pulls?state=open&sort=updated&per_page=15")
            # /issues returns PRs too; the `pull_request` key is how GitHub distinguishes them.
            issues = [i for i in issues if "pull_request" not in i]
            snap["github"][repo] = {
                "default_branch": branch,
                "head": {"sha": (head.get("sha") or "")[:16],
                         "date": head.get("commit", {}).get("committer", {}).get("date", "")},
                "releases": _short(rels, ("tag_name", "published_at", "name")),
                "open_issues": info.get("open_issues_count"),
                "issues": _short(issues, ("number", "title", "state", "updated_at", "html_url")),
                "pulls": _short(pulls, ("number", "title", "state", "updated_at", "html_url")),
                "stars": info.get("stargazers_count"), "forks": info.get("forks_count"),
            }
        except Exception as e:                                   # noqa: BLE001 - any failure is data
            snap["errors"]["github:" + repo] = "%s: %s" % (type(e).__name__, e)

    for name, url in PAGES.items():
        try:
            text, _ = _get_text(url)
            h, words = visible_text_hash(text)
            snap["pages"][name] = {"hash": h, "words": words, "url": url}
            if words < MIN_PAGE_WORDS:
                snap["warnings"]["page:" + name] = (
                    "%s: only %d visible word(s) -- too short to be a sensor "
                    "(redirect stub or error page?)" % (url, words))
        except Exception as e:                                   # noqa: BLE001
            snap["errors"]["page:" + name] = "%s: %s" % (type(e).__name__, e)

    try:
        data, _ = _get_json(FORUM_LATEST)
        topics = (data.get("topic_list") or {}).get("topics") or []
        snap["forum"] = {"topics": _short(topics, ("id", "title", "created_at", "posts_count", "views"))}
    except Exception as e:                                       # noqa: BLE001
        snap["errors"]["forum"] = "%s: %s" % (type(e).__name__, e)

    for pkg in PYPI_PACKAGES:
        try:
            data, _ = _get_json("https://pypi.org/pypi/%s/json" % pkg)
            ver = (data.get("info") or {}).get("version")
            files = (data.get("releases") or {}).get(ver) or []
            snap["pypi"][pkg] = {"version": ver,
                                 "uploaded": (files[0].get("upload_time") if files else "")}
        except Exception as e:                                   # noqa: BLE001
            snap["errors"]["pypi:" + pkg] = "%s: %s" % (type(e).__name__, e)

    return snap


# -------------------------------------------------------------------------------- compare

def _index(items, key):
    return {str(x.get(key)): x for x in items or []}


def delta_list(old, new, key, fields=("state", "updated_at")):
    """New items, and items whose watched fields changed, between two lists keyed by `key`."""
    o, n = _index(old, key), _index(new, key)
    added = [n[k] for k in n if k not in o]
    changed = [n[k] for k in n if k in o and any(o[k].get(f) != n[k].get(f) for f in fields)]
    return added, changed


def compare(prev, cur):
    """The weekly delta: {section: [line, ...]}. Empty lists mean nothing moved."""
    d = {}
    if prev is None:
        d["Baseline"] = ["no previous snapshot: this run is the baseline, nothing to compare against"]

    for repo, g in cur.get("github", {}).items():
        lines = []
        pg = (prev or {}).get("github", {}).get(repo, {})
        if prev is not None and pg.get("head", {}).get("sha") != g["head"]["sha"]:
            lines.append("`%s` moved to `%s` (%s)" % (g["default_branch"], g["head"]["sha"], g["head"]["date"]))
        new_rel, _ = delta_list(pg.get("releases"), g.get("releases"), "tag_name", ("published_at",)) if prev else ([], [])
        for r in new_rel:
            lines.append("**release `%s`** (%s) %s" % (r.get("tag_name"), r.get("published_at", "")[:10], r.get("name") or ""))
        if prev is not None and pg.get("open_issues") != g.get("open_issues"):
            lines.append("open issue count %s -> %s" % (pg.get("open_issues"), g.get("open_issues")))
        for label, key in (("issue", "issues"), ("PR", "pulls")):
            added, changed = delta_list(pg.get(key), g.get(key), "number") if prev else ([], [])
            for x in added:
                lines.append("new %s #%s %s" % (label, x.get("number"), (x.get("title") or "")[:90]))
            for x in changed:
                lines.append("%s #%s updated (%s) %s" % (label, x.get("number"), x.get("state"),
                                                         (x.get("title") or "")[:70]))
        d["GitHub " + repo] = lines

    lines = []
    for name, p in cur.get("pages", {}).items():
        pp = ((prev or {}).get("pages", {}) or {}).get(name)
        if prev is not None and pp and pp.get("hash") != p["hash"]:
            lines.append("**%s changed** (%s words -> %s) %s" % (name, pp.get("words"), p["words"], p["url"]))
    d["Pages"] = lines

    added, _ = delta_list((prev or {}).get("forum", {}).get("topics"),
                          cur.get("forum", {}).get("topics"), "id", ("posts_count",)) if prev else ([], [])
    d["Forum (matsci.org)"] = ["new topic: %s (%s)" % ((t.get("title") or "")[:100], (t.get("created_at") or "")[:10])
                               for t in added]

    lines = []
    for pkg, info in cur.get("pypi", {}).items():
        pv = ((prev or {}).get("pypi", {}) or {}).get(pkg, {}).get("version")
        if prev is not None and pv and pv != info.get("version"):
            lines.append("PyPI `%s` %s -> %s (%s)" % (pkg, pv, info.get("version"), (info.get("uploaded") or "")[:10]))
    d["PyPI"] = lines
    return d


def render_weekly(week, cur, deltas, pulls=None):
    n = sum(len(v) for v in deltas.values())
    out = ["# Upstream watch — %s" % week, "",
           "Snapshot %s by `scripts/watch_upstream.py` (lammps-skill %s). "
           "%d change line(s); sources unreachable: %d." % (cur["taken"], __version__, n, len(cur.get("errors", {}))),
           ""]
    for sec, lines in deltas.items():
        out.append("## %s" % sec)
        out += ["- %s" % ln for ln in lines] or ["- nothing moved"]
        out.append("")
    if pulls is not None:
        out.append("## Mirror clones (`--pull`)")
        out += ["- %s" % ln for ln in pulls] or ["- no clones under --upstream-dir"]
        out.append("")
    out.append("## Unreachable")
    out += ["- %s: %s" % (k, v) for k, v in sorted(cur.get("errors", {}).items())] or ["- none"]
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------------- clones

def _git(cwd, *args, timeout=900):
    p = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout + p.stderr).strip()


def pull_all(upstream_dir):
    """Fetch every clone under `upstream_dir`; report new commits. Never touches a non-clone."""
    lines = []
    if not os.path.isdir(upstream_dir):
        return ["%s does not exist" % upstream_dir]
    for name in sorted(os.listdir(upstream_dir)):
        d = os.path.join(upstream_dir, name)
        if not os.path.isdir(d):
            continue
        if not os.path.isdir(os.path.join(d, ".git")):
            lines.append("%s: not a clone, left alone" % name)
            continue
        rc, before = _git(d, "rev-parse", "HEAD")
        rc2, out = _git(d, "fetch", "--all", "--tags", "--prune")
        if rc2 != 0:
            lines.append("%s: fetch failed: %s" % (name, out.splitlines()[-1] if out else "?"))
            continue
        _, count = _git(d, "rev-list", "--count", "HEAD..@{u}")
        lines.append("%s: %s new commit(s) upstream of %s" % (name, count.strip() or "?", before[:10]))
    return lines


# ----------------------------------------------------------------------------------- state

def load_state(state_dir):
    p = os.path.join(state_dir, "snapshot.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_state(state_dir, snap):
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, "snapshot.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(snap, f, indent=1, ensure_ascii=False, sort_keys=True)


def week_label(day=None):
    day = day or dt.date.today()
    y, w, _ = day.isocalendar()
    return "%d-W%02d" % (y, w)


def _log(log_dir, line):
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "watch_upstream.log"), "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def build_parser():
    ap = argparse.ArgumentParser(prog="watch_upstream", description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", action="store_true", help="record the current state, write no report")
    g.add_argument("--weekly", action="store_true",
                   help="compare with the previous snapshot, write the week's report, then snapshot")
    ap.add_argument("--pull", action="store_true",
                    help="fetch the clones under --upstream-dir and report new commits")
    ap.add_argument("--state-dir", default=os.path.join(STUDY, "runs", "watch"),
                    help="where snapshot.json and logs/ live (gitignored)")
    ap.add_argument("--outdir", default=os.path.join(STUDY, "docs", "watch"),
                    help="where YYYY-WW.md reports go")
    ap.add_argument("--log-dir", default=None, help="audit log directory (default <state-dir>/logs)")
    ap.add_argument("--upstream-dir", default=os.path.join(STUDY, "mirror"),
                    help="directory of upstream clones for --pull")
    ap.add_argument("--week", default=None, help="override the ISO week label (tests)")
    ap.add_argument("-q", "--quiet", action="store_true")
    ap.add_argument("--version", action="version", version="lammps-skill %s" % __version__)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    log_dir = a.log_dir or os.path.join(a.state_dir, "logs")
    cur = snapshot()
    if a.snapshot:
        save_state(a.state_dir, cur)
        _log(log_dir, "%s snapshot errors=%d" % (cur["taken"], len(cur["errors"])))
        if not a.quiet:
            print("snapshot %s (%d source(s) unreachable)" % (cur["taken"], len(cur["errors"])))
        return 1 if cur["errors"] else 0

    prev = load_state(a.state_dir)
    deltas = compare(prev, cur)
    pulls = pull_all(a.upstream_dir) if a.pull else None
    week = a.week or week_label()
    report = render_weekly(week, cur, deltas, pulls)
    os.makedirs(a.outdir, exist_ok=True)
    path = os.path.join(a.outdir, week + ".md")
    n = sum(len(v) for v in deltas.values())
    # Idempotent within a week, and the week's report is never emptied. A second run in the same
    # week compares against the first run's snapshot, so its delta covers only what moved since --
    # rewriting the file with that would discard what the week already recorded. So: write when
    # there is no report yet, or when something actually moved.
    if n or not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(report)
    save_state(a.state_dir, cur)
    _log(log_dir, "%s weekly %s changes=%d errors=%d" % (cur["taken"], week, n, len(cur["errors"])))
    if not a.quiet:
        print("%s: %d change line(s), %d source(s) unreachable -> %s" % (week, n, len(cur["errors"]), path))
    return 1 if cur["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
