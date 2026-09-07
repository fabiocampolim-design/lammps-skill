# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Fabio Campolim
"""watch_upstream with every fetch faked: snapshot shape, deltas, the weekly report, idempotency.

No test here touches the network. The point of the fakes is that the weekly watch must keep working
when a source is down -- an unreachable source is recorded, never raised (rule 23 / S8).
"""

import json

import pytest

import watch_upstream as wu

GH_REPO = {"default_branch": "develop", "pushed_at": "2026-09-04T22:28:29Z",
           "open_issues_count": 76, "stargazers_count": 2400, "forks_count": 1800}
GH_HEAD = {"sha": "3214c5b1a0deadbeef", "commit": {"committer": {"date": "2026-09-04T22:28:29Z"}}}
GH_TAGS = [{"name": "stable_22Jul2025_update6"}, {"name": "patch_2Sep2026"}]
GH_RELEASES = [{"tag_name": "stable_22Jul2025_update6", "published_at": "2026-09-03T00:00:00Z",
                "name": "Stable release update 6"}]
GH_ISSUES = [{"number": 5178, "title": "Feature Proposal: mesomem pair style", "state": "open",
              "updated_at": "2026-09-03T09:41:44Z", "html_url": "https://github.com/lammps/lammps/issues/5178"}]
GH_PULLS = [{"number": 5179, "title": "Update bundled linalg library", "state": "open",
             "updated_at": "2026-09-05T16:33:22Z", "html_url": "https://github.com/lammps/lammps/pull/5179"}]
PAGE = ("<html><head><title>LAMMPS Molecular Dynamics Simulator</title></head>"
        "<body><script>x=1</script><h1>LAMMPS</h1> Download the stable release.</body></html>")
LATEST = {"topic_list": {"topics": [
    {"id": 61234, "title": "Sixth and final update to the 22 July 2025 stable release posted",
     "created_at": "2026-09-03T12:00:00Z", "posts_count": 3, "views": 85},
    {"id": 61200, "title": "Optimizing LAMMPS for dipole interaction in large system",
     "created_at": "2026-09-01T08:00:00Z", "posts_count": 8, "views": 38}]}}
PYPI = {"info": {"version": "2025.7.22.4.0"},
        "releases": {"2025.7.22.4.0": [{"upload_time": "2025-08-01T00:00:00"}]}}


def fake_get_factory(state):
    def fake_get(url, accept=None, timeout=60):
        state["calls"].append(url)
        if "api.github.com/repos/" in url:
            if "/releases" in url:
                return json.dumps(GH_RELEASES).encode(), {}
            if "/tags" in url:
                return json.dumps(GH_TAGS).encode(), {}
            if "/pulls" in url:
                return json.dumps(GH_PULLS).encode(), {}
            if "/issues" in url:
                return json.dumps(GH_ISSUES).encode(), {}
            if "/commits/" in url:
                return json.dumps(dict(GH_HEAD, sha=state.get("sha", GH_HEAD["sha"]))).encode(), {}
            return json.dumps(GH_REPO).encode(), {}
        if "matsci.org" in url:
            return json.dumps(LATEST).encode(), {}
        if "pypi.org" in url:
            return json.dumps(PYPI).encode(), {}
        return PAGE.encode(), {}
    return fake_get


@pytest.fixture
def faked(monkeypatch):
    state = {"calls": []}
    monkeypatch.setattr(wu, "_get", fake_get_factory(state))
    monkeypatch.setattr(wu, "PAUSE", 0)
    return state


def test_snapshot_records_every_source_and_never_raises(faked):
    snap = wu.snapshot()
    assert snap["errors"] == {}
    gh = snap["github"]["lammps/lammps"]
    assert gh["default_branch"] == "develop" and gh["head"]["sha"].startswith("3214c5b1a0")
    assert "stable_22Jul2025_update6" in [r["tag_name"] for r in gh["releases"]]
    assert gh["open_issues"] == 76
    assert snap["forum"]["topics"][0]["title"].startswith("Sixth and final update")
    assert snap["pypi"]["lammps"]["version"] == "2025.7.22.4.0"
    for name in wu.PAGES:
        assert len(snap["pages"][name]["hash"]) == 16


def test_a_source_that_fails_is_recorded_not_raised(monkeypatch):
    def boom(url, accept=None, timeout=60):
        if "matsci.org" in url:
            raise OSError("connection reset")
        return fake_get_factory({"calls": []})(url, accept, timeout)
    monkeypatch.setattr(wu, "_get", boom)
    monkeypatch.setattr(wu, "PAUSE", 0)
    snap = wu.snapshot()
    assert "forum" in snap["errors"] and "connection reset" in snap["errors"]["forum"]
    assert snap["github"]           # the rest of the snapshot still happened


def test_compare_reports_a_moved_head_a_new_release_and_a_new_topic(faked):
    prev = wu.snapshot()
    faked["sha"] = "ffffffffff000000"
    cur = wu.snapshot()
    cur["github"]["lammps/lammps"]["releases"].insert(
        0, {"tag_name": "patch_1Oct2026", "published_at": "2026-10-01T00:00:00Z", "name": "Feature release"})
    cur["forum"]["topics"].insert(0, {"id": 61999, "title": "New feature release posted",
                                      "created_at": "2026-10-01T00:00:00Z", "posts_count": 1, "views": 4})
    deltas = wu.compare(prev, cur)
    flat = " ".join(ln for lines in deltas.values() for ln in lines)
    assert "ffffffffff000000" in flat
    assert "patch_1Oct2026" in flat
    assert "New feature release posted" in flat


def test_compare_against_no_previous_snapshot_is_a_baseline(faked):
    deltas = wu.compare(None, wu.snapshot())
    assert any("baseline" in ln for lines in deltas.values() for ln in lines)


def test_nothing_moved_says_so(faked):
    snap = wu.snapshot()
    deltas = wu.compare(snap, snap)
    report = wu.render_weekly("2026-W37", snap, deltas)
    assert "nothing moved" in report


def test_weekly_writes_one_report_per_week_and_snapshots(tmp_path, faked):
    out, state = tmp_path / "watch", tmp_path / "state"
    rc = wu.main(["--weekly", "--outdir", str(out), "--state-dir", str(state), "--week", "2026-W37", "-q"])
    assert rc == 0
    report = out / "2026-W37.md"
    assert report.exists() and "Upstream watch" in report.read_text(encoding="utf-8")
    assert (state / "snapshot.json").exists()


def test_weekly_is_idempotent_within_a_week(tmp_path, faked):
    out, state = tmp_path / "watch", tmp_path / "state"
    args = ["--weekly", "--outdir", str(out), "--state-dir", str(state), "--week", "2026-W37", "-q"]
    wu.main(args)
    first = (out / "2026-W37.md").read_text(encoding="utf-8")
    wu.main(args)                     # nothing moved in between
    assert (out / "2026-W37.md").read_text(encoding="utf-8") == first


def test_snapshot_mode_writes_state_but_no_report(tmp_path, faked):
    out, state = tmp_path / "watch", tmp_path / "state"
    assert wu.main(["--snapshot", "--outdir", str(out), "--state-dir", str(state), "-q"]) == 0
    assert (state / "snapshot.json").exists()
    assert not out.exists() or not list(out.glob("*.md"))


def test_pull_reports_a_directory_that_is_not_a_clone(tmp_path):
    (tmp_path / "notaclone").mkdir()
    lines = wu.pull_all(str(tmp_path))
    assert any("not a clone" in ln for ln in lines)


def test_visible_text_hash_ignores_markup_and_scripts():
    a, _ = wu.visible_text_hash("<p>LAMMPS <script>var v=1</script>release</p>")
    b, _ = wu.visible_text_hash("<div>LAMMPS   release</div><script>var v=2</script>")
    assert a == b


def test_build_parser_exposes_every_documented_flag():
    flags = set()
    for a in wu.build_parser()._actions:
        flags.update(a.option_strings)
    for f in ("--snapshot", "--weekly", "--pull", "--state-dir", "--outdir", "--week", "--version"):
        assert f in flags


def test_a_page_that_is_only_a_redirect_stub_is_flagged(monkeypatch):
    """A page-hash sensor pointed at a redirect stub never fires. www.lammps.org/download.html is
    exactly that -- 252 bytes of meta-refresh to /download/ -- and it hashed to ONE word, which
    looks like a working sensor until you count (2026-09-07). Too-short pages are reported."""
    stub = ('<!doctype html><html><head><title>https://www.lammps.org/download/</title>'
            '<meta http-equiv=refresh content="0; url=https://www.lammps.org/download/"></head></html>')

    def fake_get(url, accept=None, timeout=60):
        if url in wu.PAGES.values():
            return stub.encode(), {}
        return fake_get_factory({"calls": []})(url, accept, timeout)

    monkeypatch.setattr(wu, "_get", fake_get)
    monkeypatch.setattr(wu, "PAUSE", 0)
    snap = wu.snapshot()
    assert snap["warnings"], "a one-word page must be reported, not silently watched"
    assert any("too short" in w for w in snap["warnings"].values())


def test_releases_not_tags_are_the_release_signal(faked):
    """GitHub's /tags is not date-ordered: the live call returned stable_31Mar2017 first, so a new
    tag can fall outside the window entirely. /releases IS date-ordered and LAMMPS publishes one
    per tag we care about, so that is the signal (checked 2026-09-07)."""
    snap = wu.snapshot()
    gh = snap["github"]["lammps/lammps"]
    assert "tags" not in gh
    assert gh["releases"][0]["tag_name"] == "stable_22Jul2025_update6"
    assert not any("/tags" in c for c in faked["calls"])
