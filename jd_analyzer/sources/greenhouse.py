"""Greenhouse public job board API (no auth required).

Docs: https://developers.greenhouse.io/job-board.html
"""

import requests

from jd_analyzer.models import Posting
from jd_analyzer.sources.base import board_url, get_json
from jd_analyzer.text import html_to_text

SOURCE = "greenhouse"
BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def fetch_board(company: str, session: requests.Session | None = None) -> dict:
    """Return the raw JSON for one company's board, descriptions included."""
    return get_json(board_url(BOARD_URL, company), session, params={"content": "true"})


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
