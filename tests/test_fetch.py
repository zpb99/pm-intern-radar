import json

import pytest
import requests

from jd_analyzer import fetch
from jd_analyzer.boards import Board
from jd_analyzer.sources import greenhouse
from jd_analyzer.sources.base import BoardNotFound

BOARD = Board("greenhouse", "acme")
RAW = {
    "jobs": [
        {"id": 1, "title": "Product Manager, MBA Intern", "content": "&lt;p&gt;Hi&lt;/p&gt;"},
        {"id": 2, "title": "Product Manager | International"},
        {"id": 3, "title": "Software Engineer"},
    ]
}


def fake_fetch(result):
    def _fetch(token, session=None):
        if isinstance(result, Exception):
            raise result
        return result

    return _fetch


def test_fetch_one_keeps_only_pm_interns_and_saves_raw(monkeypatch, tmp_path):
    monkeypatch.setattr(greenhouse, "fetch_board", fake_fetch(RAW))
    matches, report = fetch.fetch_one(BOARD, None, tmp_path, "t")
    assert [p.job_id for p in matches] == ["1"]
    assert report == {"source": "greenhouse", "token": "acme", "status": "ok", "jobs": 3, "matches": 1, "error": ""}
    assert json.loads((tmp_path / "greenhouse" / "acme.json").read_text()) == RAW


def test_fetch_one_skips_raw_file_when_no_matches(monkeypatch, tmp_path):
    monkeypatch.setattr(greenhouse, "fetch_board", fake_fetch({"jobs": [RAW["jobs"][2]]}))
    matches, report = fetch.fetch_one(BOARD, None, tmp_path, "t")
    assert matches == [] and report["status"] == "ok"
    assert not (tmp_path / "greenhouse").exists()


@pytest.mark.parametrize(
    "result, status",
    [
        (BoardNotFound("u"), "not_found"),
        (requests.HTTPError("HTTP 500"), "error"),
        (requests.ConnectionError("down"), "error"),
        (ValueError("not JSON"), "error"),
        ({"jobs": [{"title": "no id field"}]}, "error"),  # malformed JSON shape
        ({"jobs": "not a list"}, "error"),
    ],
)
def test_fetch_one_turns_failures_into_report_rows(monkeypatch, tmp_path, result, status):
    monkeypatch.setattr(greenhouse, "fetch_board", fake_fetch(result))
    matches, report = fetch.fetch_one(BOARD, None, tmp_path, "t")
    assert matches == [] and report["status"] == status


@pytest.mark.parametrize(
    "value, expected",
    [
        ("- SQL", "'- SQL"),
        ("=HYPERLINK(\"http://x\")", "'=HYPERLINK(\"http://x\")"),
        ("+1", "'+1"),
        ("@cmd", "'@cmd"),
        ("Strong SQL", "Strong SQL"),  # ordinary text untouched
        ("", ""),
        (3, 3),  # non-strings untouched
    ],
)
def test_spreadsheet_safe(value, expected):
    assert fetch.spreadsheet_safe(value) == expected


def test_write_csv_escapes_only_when_asked(tmp_path):
    rows = [{"line": "- SQL"}]
    fetch.write_csv(rows, ["line"], tmp_path / "raw.csv")
    fetch.write_csv(rows, ["line"], tmp_path / "people.csv", for_spreadsheets=True)
    assert (tmp_path / "raw.csv").read_text().splitlines()[1] == "- SQL"
    assert (tmp_path / "people.csv").read_text().splitlines()[1] == "'- SQL"


def test_fetch_one_uses_the_given_role_filter(monkeypatch, tmp_path):
    from jd_analyzer.filters import RoleFilter

    monkeypatch.setattr(greenhouse, "fetch_board", fake_fetch(RAW))
    swe = RoleFilter.from_patterns(name="SWE", title=r"\bsoftware\s+engineer\b")
    matches, report = fetch.fetch_one(BOARD, None, tmp_path, "t", swe)
    assert [p.job_id for p in matches] == ["3"] and report["matches"] == 1


def test_fetch_cli_rejects_a_bad_roles_file(tmp_path, capsys):
    bad = tmp_path / "roles.toml"
    bad.write_text("[filter]\ntitle = '(unclosed'\n")
    with pytest.raises(SystemExit) as exit_info:
        fetch.main(["greenhouse:acme", "--roles", str(bad)])
    assert exit_info.value.code == 2 and "not a valid regex" in capsys.readouterr().err


def test_run_works_with_a_data_dir_outside_the_repo(monkeypatch, tmp_path, capsys):
    # Regression: run() printed paths relative to the repo and crashed for any other folder.
    monkeypatch.setattr(greenhouse, "fetch_board", fake_fetch(RAW))
    assert fetch.run([BOARD], tmp_path) == 0
    assert (tmp_path / "postings.csv").exists() and (tmp_path / "fetch_report.csv").exists()
    assert "Saved 1 postings" in capsys.readouterr().out
