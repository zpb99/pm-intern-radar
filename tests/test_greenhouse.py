from jd_analyzer.sources.greenhouse import parse_board

RAW = {
    "jobs": [
        {
            "id": 123,
            "title": " Product Manager, MBA Intern ",
            "location": {"name": "Pittsburgh, PA"},
            "absolute_url": "https://example.com/jobs/123",
            "content": "&lt;p&gt;Ship things&lt;/p&gt;",
            "updated_at": "2026-10-15T15:00:01-04:00",
        },
        # Missing optional fields must not crash parsing.
        {"id": 456, "title": "Engineer", "location": None},
    ]
}


def test_parse_board_maps_fields():
    p = parse_board("duolingo", RAW, "2026-10-21T00:00:00+00:00")[0]
    assert p.source == "greenhouse"
    assert p.company == "duolingo"
    assert p.job_id == "123"
    assert p.title == "Product Manager, MBA Intern"
    assert p.location == "Pittsburgh, PA"
    assert p.description == "Ship things"
    assert p.fetched_at == "2026-10-21T00:00:00+00:00"


def test_parse_board_tolerates_missing_fields():
    p = parse_board("x", RAW, "t")[1]
    assert (p.location, p.url, p.description, p.updated_at) == ("", "", "", "")


def test_parse_board_empty():
    assert parse_board("x", {}, "t") == []
