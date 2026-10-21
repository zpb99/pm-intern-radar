"""Plumbing shared by every job-board source: token checks and polite HTTP."""

import re
import time
from urllib.parse import quote

import requests

# Board tokens are slugs like "databricks", "mistral.ai" or (Ashby) "hippocratic ai".
# Inner dots and spaces are fine; slashes, "%", "?", control characters, and a
# leading or trailing dot/space are rejected before a token can reach a URL or a
# filename. With no "/" and no leading ".", a token can't climb out of a folder.
_TOKEN = re.compile(r"\A[a-z0-9](?:[a-z0-9_. -]{0,62}[a-z0-9_-])?\Z")

RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 5.0


class BoardNotFound(Exception):
    """The company has no board under that token on this job board (HTTP 404)."""


class InvalidToken(ValueError):
    """The token is not a plain slug, so it is unsafe to put in a URL or path."""


def check_token(token: str) -> str:
    """Return the token unchanged if it is a safe slug, else raise InvalidToken."""
    if not isinstance(token, str) or not _TOKEN.match(token):
        raise InvalidToken(f"invalid board token: {token!r}")
    return token


def board_url(template: str, token: str) -> str:
    """Fill a URL template with a checked, URL-encoded token."""
    return template.format(token=quote(check_token(token), safe=""))


def get_json(url: str, session: requests.Session | None = None, params: dict | None = None):
    """GET a URL and return parsed JSON.

    404 raises BoardNotFound. Rate limits and server errors are retried with
    backoff (honoring Retry-After); if they persist, the HTTP error is raised.
    """
    http = session or requests
    for attempt in range(1, MAX_ATTEMPTS + 1):
        resp = http.get(url, params=params, timeout=30)
        if resp.status_code == 404:
            raise BoardNotFound(url)
        if resp.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
            time.sleep(_retry_delay(resp, attempt))
            continue
        resp.raise_for_status()
        return resp.json()


def _retry_delay(resp, attempt: int) -> float:
    retry_after = resp.headers.get("Retry-After", "")
    if retry_after.isdigit():
        return min(float(retry_after), 60.0)
    return BACKOFF_SECONDS * attempt
