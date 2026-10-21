from jd_analyzer.sources import ashby, lever

LEVER_RAW = [
    {
        "id": "abc",
        "text": " Product Manager Intern ",
        "categories": {"location": "New York", "team": "Product"},
        "hostedUrl": "https://jobs.lever.co/acme/abc",
        "description": "<div>Intro paragraph</div>",
        "lists": [
            {"text": "What you'll need", "content": "<li>SQL</li><li>Curiosity</li>"},
            {"text": "", "content": ""},  # empty section is dropped
        ],
        "additional": "<div>Closing</div>",
        "createdAt": 1791566108174,
    },
    {"id": "def", "text": "Engineer"},  # bare minimum fields
]


def test_lever_joins_description_lists_and_closing():
    p = lever.parse_board("acme", LEVER_RAW, "t")[0]
    assert p.description == "Intro paragraph\nWhat you'll need\n- SQL\n- Curiosity\nClosing"
    assert (p.source, p.title, p.location, p.url) == ("lever", "Product Manager Intern", "New York", LEVER_RAW[0]["hostedUrl"])
    assert p.updated_at == "2026-10-09T17:15:08+00:00"  # checked with `date -u -r 1791566108`


def test_lever_tolerates_missing_fields():
    p = lever.parse_board("acme", LEVER_RAW, "t")[1]
    assert (p.location, p.url, p.description, p.updated_at) == ("", "", "", "")


def test_lever_empty_board():
    assert lever.parse_board("acme", [], "t") == []


ASHBY_RAW = {
    "jobs": [
        {
            "id": "u1",
            "title": "Product Management Intern",
            "location": "San Francisco",
            "jobUrl": "https://jobs.ashbyhq.com/acme/u1",
            "descriptionHtml": "<p>Requirements</p><ul><li>Ship</li></ul>",
            "descriptionPlain": "Requirements Ship",
            "publishedAt": "2026-10-01T00:00:00+00:00",
            "isListed": True,
        },
        {"id": "u2", "title": "Hidden", "isListed": False},
        {"id": "u3", "title": "Plain only", "descriptionPlain": "fallback text"},
    ]
}


def test_ashby_prefers_html_to_keep_bullets():
    p = ashby.parse_board("acme", ASHBY_RAW, "t")[0]
    assert p.description == "Requirements\n- Ship"
    assert (p.source, p.location, p.updated_at) == ("ashby", "San Francisco", "2026-10-01T00:00:00+00:00")


def test_ashby_drops_unlisted_and_falls_back_to_plain():
    postings = ashby.parse_board("acme", ASHBY_RAW, "t")
    assert [p.job_id for p in postings] == ["u1", "u3"]
    assert postings[1].description == "fallback text"


def test_ashby_empty_board():
    assert ashby.parse_board("acme", {}, "t") == []
