import pytest

from jd_analyzer.boards import Board
from jd_analyzer.discover import board_from_url, boards_from_listings


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://boards.greenhouse.io/databricks/jobs/123", Board("greenhouse", "databricks")),
        ("https://job-boards.greenhouse.io/Figma/jobs/9?gh_src=x", Board("greenhouse", "figma")),
        ("https://boards.greenhouse.io/embed/job_app?for=roblox&token=8", Board("greenhouse", "roblox")),
        ("https://jobs.lever.co/spotify/abc-123/apply", Board("lever", "spotify")),
        ("https://jobs.ashbyhq.com/Ramp/uuid", Board("ashby", "ramp")),
        ("https://jobs.ashbyhq.com/Hippocratic%20AI/uuid", Board("ashby", "hippocratic ai")),
        ("https://jobs.ashbyhq.com/mistral.ai/uuid", Board("ashby", "mistral.ai")),
    ],
)
def test_supported_links(url, expected):
    assert board_from_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://uline.wd1.myworkdayjobs.com/en-US/careers/job/123",  # Workday: unsupported
        "https://lifeattiktok.com/search/123",
        "https://jobs.eu.lever.co/acme/1",  # Lever's EU instance uses a different API
        "https://boards.greenhouse.io/",  # no token
        "https://boards.greenhouse.io/embed/job_app?token=8",  # embed without for=
        "https://evil.example/boards.greenhouse.io/x",  # host must match, not path
        "",
        "not a url",
        "http://[::1",  # urlparse raises on this
    ],
)
def test_unsupported_or_tokenless_links(url):
    assert board_from_url(url) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://jobs.ashbyhq.com/..%2F..%2Fetc/1",  # decodes to "../../etc"
        "https://jobs.lever.co/a%3Fx%3D1/1",  # decodes to "a?x=1"
        "https://boards.greenhouse.io/embed/job_app?for=../x",
    ],
)
def test_unsafe_token_in_supported_link_raises(url):
    with pytest.raises(ValueError):
        board_from_url(url)


def test_boards_from_listings_dedupes_and_reports_rejects():
    bad = "https://jobs.ashbyhq.com/..%2F..%2Fetc/1"
    listings = [
        {"url": "https://jobs.lever.co/spotify/1"},
        {"url": "https://jobs.lever.co/Spotify/2"},  # same board, different case
        {"url": bad},
        {"url": "https://uline.wd1.myworkdayjobs.com/x"},
        {},  # listing without a url
    ]
    boards, rejected = boards_from_listings(listings)
    assert boards == [Board("lever", "spotify")]
    assert rejected == [bad]
