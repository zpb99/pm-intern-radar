import json
import re

import pytest

from jd_analyzer import radar
from jd_analyzer.catalog import degree_hint
from jd_analyzer.models import Posting
from jd_analyzer.radar import (
    CorruptSeenFile,
    compare,
    load_seen,
    posting_key,
    render_report,
    save_seen,
    update_seen,
)

ROLE_A = "Basic Qualifications\n- Currently pursuing an MBA\n- Strong communication\n" + " ".join(f"a{i}" for i in range(80))
ROLE_B = "Requirements\n- Pursuing a bachelor's degree\n- SQL\n" + " ".join(f"b{i}" for i in range(80))


def posting(company, job_id, description, location="NYC", title="Product Manager Intern"):
    return Posting("greenhouse", company, job_id, title, location, f"https://x/{job_id}", description, "", "")


A1 = posting("acme", "1", ROLE_A)
A2 = posting("acme", "2", ROLE_A, location="Paris")  # same role, second location
B1 = posting("beta", "9", ROLE_B)
ALL_OK = {("greenhouse", "acme"), ("greenhouse", "beta")}


def seen_of(*postings, today="2026-10-21"):
    return {posting_key(p): {"first_seen": today, "last_seen": today, "title": p.title, "url": p.url} for p in postings}


# --- the seen store ---------------------------------------------------------


def test_missing_store_is_first_run(tmp_path):
    assert load_seen(tmp_path / "seen.json") == {}


def test_store_round_trips(tmp_path):
    seen = seen_of(A1, B1)
    save_seen(seen, tmp_path / "seen.json")
    assert load_seen(tmp_path / "seen.json") == seen
    assert not (tmp_path / "seen.json.tmp").exists()  # temp file renamed away


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        "[]",
        json.dumps({"postings": {}}),  # no version
        json.dumps({"version": 99, "postings": {}}),
        json.dumps({"version": 1, "postings": []}),
    ],
)
def test_corrupt_store_raises_instead_of_starting_over(tmp_path, content):
    (tmp_path / "seen.json").write_text(content)
    with pytest.raises(CorruptSeenFile):
        load_seen(tmp_path / "seen.json")


# --- comparing a run against the store ----------------------------------------


def test_first_run_everything_is_new():
    result = compare([A1, A2, B1], {}, ALL_OK)
    assert result.first_run
    assert len(result.new_roles) == 2  # A1 and A2 are one role
    assert result.new_locations == [] and result.gone == []


def test_nothing_changed_reports_nothing():
    result = compare([A1, A2, B1], seen_of(A1, A2, B1), ALL_OK)
    assert (result.new_roles, result.new_locations, result.gone) == ([], [], [])
    assert not result.first_run


def test_new_role_is_reported():
    result = compare([A1, B1], seen_of(A1), ALL_OK)
    assert [r.postings[0].job_id for r in result.new_roles] == ["9"]


def test_new_location_of_known_role_is_not_a_new_role():
    result = compare([A1, A2], seen_of(A1), ALL_OK)
    assert result.new_roles == []
    (role, fresh), = result.new_locations
    assert [p.job_id for p in fresh] == ["2"]


def test_missing_posting_on_a_healthy_board_is_gone():
    result = compare([A1], seen_of(A1, B1), ALL_OK)
    assert [g["key"] for g in result.gone] == ["greenhouse:beta:9"]


def test_missing_posting_on_a_failed_board_is_not_gone():
    result = compare([A1], seen_of(A1, B1), {("greenhouse", "acme")})  # beta errored this run
    assert result.gone == []


def test_gone_is_reported_once_and_cleared_when_reposted():
    seen = seen_of(A1, B1)
    week2 = compare([A1], seen, ALL_OK)
    seen = update_seen(seen, [A1], week2, "2026-10-28")
    assert seen["greenhouse:beta:9"]["gone_since"] == "2026-10-28"
    assert compare([A1], seen, ALL_OK).gone == []  # not reported again
    week4 = compare([A1, B1], seen, ALL_OK)
    assert week4.new_roles == []  # a repost of something seen is not new
    seen = update_seen(seen, [A1, B1], week4, "2026-11-11")
    assert "gone_since" not in seen["greenhouse:beta:9"]


def test_update_keeps_first_seen_and_bumps_last_seen():
    seen = update_seen(seen_of(A1), [A1, B1], compare([A1, B1], seen_of(A1), ALL_OK), "2026-10-28")
    assert seen["greenhouse:acme:1"]["first_seen"] == "2026-10-21"
    assert seen["greenhouse:acme:1"]["last_seen"] == "2026-10-28"
    assert seen["greenhouse:beta:9"]["first_seen"] == "2026-10-28"


# --- the report -------------------------------------------------------------


def test_report_lists_requirements_and_puts_mba_roles_first():
    report = render_report(compare([B1, A1], {}, ALL_OK), "2026-10-21", boards_ok=2, boards_failed=0)
    assert "First run" in report
    assert report.index("beta") > report.index("acme")  # the MBA role comes first
    assert "- Currently pursuing an MBA" in report
    assert "MBA named in the requirements" in report
    assert "bachelor's only" in report


@pytest.mark.parametrize(
    "required, expected",
    [
        ({"MBA", "Master's / graduate degree"}, (0, "MBA named")),
        ({"Master's / graduate degree", "Bachelor's degree"}, (1, "MBA not named")),  # Appian: Master's in CS
        ({"Bachelor's degree"}, (2, "bachelor's only")),
        (set(), (1, "no degree requirement")),
    ],
)
def test_eligibility_does_not_treat_masters_as_mba(required, expected):
    rank, text = degree_hint(required, set())
    assert rank == expected[0] and expected[1] in text


def test_report_flags_roles_without_sections_and_failed_boards():
    role = posting("gamma", "5", "We want a great PM intern. " + " ".join(f"g{i}" for i in range(80)))
    report = render_report(compare([role], seen_of(A1), {("greenhouse", "gamma")}), "d", 1, boards_failed=3)
    assert "No requirements section detected" in report
    assert "3 failed" in report


# --- the whole run, without the network ----------------------------------------


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(radar, "DATA_DIR", tmp_path)
    monkeypatch.setattr(radar, "RADAR_DIR", tmp_path / "radar")
    monkeypatch.setattr(radar, "SEEN_FILE", tmp_path / "radar" / "seen.json")
    return tmp_path


def write_inputs(data_dir, postings, reports):
    from dataclasses import asdict

    from jd_analyzer.fetch import REPORT_COLUMNS, write_csv
    from jd_analyzer.models import CSV_COLUMNS

    write_csv([asdict(p) for p in postings], CSV_COLUMNS, data_dir / "postings.csv")
    write_csv(reports, REPORT_COLUMNS, data_dir / "fetch_report.csv")


def ok(company):
    return {"source": "greenhouse", "token": company, "status": "ok", "jobs": 1, "pm_intern": 1, "error": ""}


def test_run_twice_second_run_shows_only_the_new_role(data_dir, monkeypatch):
    write_inputs(data_dir, [A1], [ok("acme"), ok("beta")])
    assert radar.run(skip_fetch=True, today="2026-10-21") == 0
    write_inputs(data_dir, [A1, B1], [ok("acme"), ok("beta")])
    assert radar.run(skip_fetch=True, today="2026-10-28") == 0
    latest = (data_dir / "radar" / "latest.md").read_text()
    assert "**1 new roles**" in latest and "beta" in latest and "acme" not in latest
    assert (data_dir / "radar" / "report-2026-10-21.md").exists()
    assert (data_dir / "radar" / "last_summary.txt").read_text() == "1\n"


def test_run_refuses_to_update_when_every_board_failed(data_dir, monkeypatch):
    saved = []
    monkeypatch.setattr(radar, "save_seen", lambda seen, path: saved.append(seen))
    write_inputs(data_dir, [], [{**ok("acme"), "status": "error", "error": "down"}])
    assert radar.run(skip_fetch=True, today="d") == 1
    assert saved == []  # seen store untouched


def test_main_exits_2_on_corrupt_store(data_dir, monkeypatch, capsys):
    def boom(path):
        raise CorruptSeenFile("bad file")

    monkeypatch.setattr(radar, "load_seen", boom)
    assert radar.main(["--skip-fetch"]) == 2
    assert "bad file" in capsys.readouterr().err


def test_same_day_reruns_keep_earlier_reports(data_dir):
    write_inputs(data_dir, [A1], [ok("acme")])
    assert radar.run(skip_fetch=True, today="2026-10-21") == 0
    assert radar.run(skip_fetch=True, today="2026-10-21") == 0
    first = (data_dir / "radar" / "report-2026-10-21.md").read_text()
    second = (data_dir / "radar" / "report-2026-10-21-2.md").read_text()
    assert "**1 new roles**" in first and "**0 new roles**" in second
    assert (data_dir / "radar" / "latest.md").read_text() == second


def test_report_neutralizes_untrusted_html_and_links():
    evil = Posting("greenhouse", "evil", "1", "PM Intern <img src=x onerror=alert(1)>", "<b>NYC</b>",
                   "javascript:alert(1)",
                   "Requirements\n- [Apply here](javascript:alert(1)) and ![x](http://track/p.png) `code` SQL "
                   + " ".join(f"e{i}" for i in range(80)), "", "")
    report = render_report(compare([evil], {}, {("greenhouse", "evil")}), "d", 1, 0)
    assert re.search(r"(?<!\\)<(img|b)", report) is None  # every < from the posting is backslash-escaped
    assert r"\<img src=x onerror=alert\(1\)\>" in report
    assert "](javascript" not in report and "![x](" not in report  # no Markdown link or image survives
    assert r"\[Apply here\]\(javascript:alert\(1\)\)" in report
    assert "javascript:alert\\(1\\) (not linked" in report


@pytest.mark.parametrize(
    "url, linked",
    [
        ("https://job-boards.greenhouse.io/acme/jobs/1?gh_jid=1", True),
        ("http://x.com/a", True),
        ("javascript:alert(1)", False),
        ("data:text/html,hi", False),
        ("https://x.com/a b", False),
        ("https://x.com/<script>", False),
        ("https://x.com/a`b", False),  # backtick can't end a code span if it isn't in one
        ("https://x.com/\x01a", False),  # control char urlparse would silently drop
        ("https://x.com/a\nb", False),
        ("https://x.com/(paren)", False),  # parens could close a Markdown link
        ("https://", False),  # no host
    ],
)
def test_link_only_allows_plain_http(url, linked):
    out = radar._link(url)
    assert out.startswith("<http") == linked
    if not linked:
        assert "\n" not in out and "\x01" not in out and "`" not in out.replace("\\`", "")


def test_link_empty():
    assert radar._link("") == "not listed"


@pytest.mark.parametrize(
    "raw, escaped",
    [
        ("[a](b)", r"\[a\]\(b\)"),
        ("![img](x)", r"\!\[img\]\(x\)"),
        ("`tick`", r"\`tick\`"),
        ("a\\b", r"a\\b"),
        ("<b>&", r"\<b\>\&"),
        ("line\nbreak\ttab", "line break tab"),
        ("Strong SQL, **bold** ok", "Strong SQL, **bold** ok"),  # harmless formatting kept
    ],
)
def test_text_escapes_markdown_that_could_link_or_embed(raw, escaped):
    assert radar._text(raw) == escaped
