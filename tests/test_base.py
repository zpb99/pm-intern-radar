import pytest
import requests

from jd_analyzer.sources import base
from jd_analyzer.sources.base import BoardNotFound, InvalidToken, board_url, check_token, get_json


@pytest.mark.parametrize(
    "token",
    ["databricks", "ramp-network", "a", "co_2027", "x" * 64, "mistral.ai", "hippocratic ai", "a..b"],
)
def test_accepts_slugs(token):
    assert check_token(token) == token


@pytest.mark.parametrize(
    "token",
    [
        "",
        "../../etc",  # path traversal into the raw-JSON filename
        "a/b",
        "a/../b",
        "..",
        ".hidden",
        "trailing.",
        "trailing ",
        "foo?x=1",  # query injection into the API URL
        "foo#bar",
        "a%2fb",  # still-encoded text
        "a\tb",
        "-leading-dash",
        "_leading",
        "Databricks",  # callers must lowercase first
        "x" * 65,
        "café",
        "a\nb",
        None,
    ],
)
def test_rejects_unsafe_tokens(token):
    with pytest.raises(InvalidToken):
        check_token(token)


def test_board_url_checks_token():
    assert board_url("https://h/{token}/jobs", "duolingo") == "https://h/duolingo/jobs"
    with pytest.raises(InvalidToken):
        board_url("https://h/{token}/jobs", "../x")


class FakeResponse:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    """Returns the queued responses in order and records each call."""

    def __init__(self, *responses):
        self.responses, self.calls = list(responses), 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(base.time, "sleep", sleeps.append)
    return sleeps


def test_get_json_ok():
    assert get_json("u", FakeSession(FakeResponse(200, {"jobs": []}))) == {"jobs": []}


def test_get_json_404_is_board_not_found():
    with pytest.raises(BoardNotFound):
        get_json("u", FakeSession(FakeResponse(404)))


def test_get_json_retries_rate_limit_then_succeeds(no_sleep):
    s = FakeSession(FakeResponse(429, headers={"Retry-After": "7"}), FakeResponse(200, [1]))
    assert get_json("u", s) == [1]
    assert s.calls == 2 and no_sleep == [7.0]


def test_get_json_gives_up_after_max_attempts():
    s = FakeSession(*[FakeResponse(503) for _ in range(base.MAX_ATTEMPTS)])
    with pytest.raises(requests.HTTPError):
        get_json("u", s)
    assert s.calls == base.MAX_ATTEMPTS


def test_get_json_does_not_retry_client_errors():
    s = FakeSession(FakeResponse(403), FakeResponse(200, {}))
    with pytest.raises(requests.HTTPError):
        get_json("u", s)
    assert s.calls == 1
