"""Greenhouse public job board API (no auth required).

Docs: https://developers.greenhouse.io/job-board.html
"""

import requests

from jd_analyzer.models import Posting
from jd_analyzer.text import html_to_text

SOURCE = "greenhouse"
BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"


class BoardNotFound(Exception):
    """The company has no Greenhouse board under that token (HTTP 404)."""


def fetch_board(company: str, session: requests.Session | None = None) -> dict:
    """Return the raw JSON for one company's board, descriptions included."""
    http = session or requests
    resp = http.get(BOARD_URL.format(company=company), params={"content": "true"}, timeout=30)
    if resp.status_code == 404:
        raise BoardNotFound(company)
    resp.raise_for_status()  # any other error (429, 500...) stops loudly
    return resp.json()


def parse_board(company: str, raw: dict, fetched_at: str) -> list[Posting]:
    """Convert raw board JSON into Posting records (all jobs, unfiltered)."""
    postings = []
    for job in raw.get("jobs", []):
        postings.append(
            Posting(
                source=SOURCE,
                company=company,
                job_id=str(job["id"]),
                title=job["title"].strip(),
                location=(job.get("location") or {}).get("name", ""),
                url=job.get("absolute_url", ""),
                description=html_to_text(job.get("content", "")),
                updated_at=job.get("updated_at", ""),
                fetched_at=fetched_at,
            )
        )
    return postings
