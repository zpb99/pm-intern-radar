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
    assert report == {"source": "greenhouse", "token": "acme", "status": "ok", "jobs": 3, "pm_intern": 1, "error": ""}
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
