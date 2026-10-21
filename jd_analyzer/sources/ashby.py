"""Ashby public job board API (no auth required).

Docs: https://developers.ashbyhq.com/docs/public-job-posting-api
"""

import requests

from jd_analyzer.models import Posting
from jd_analyzer.sources.base import board_url, get_json
from jd_analyzer.text import html_to_text

SOURCE = "ashby"
BOARD_URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"


def fetch_board(company: str, session: requests.Session | None = None) -> dict:
    return get_json(board_url(BOARD_URL, company), session)


def parse_board(company: str, raw: dict, fetched_at: str) -> list[Posting]:
    postings = []
    for job in raw.get("jobs", []):
        if job.get("isListed") is False:  # hidden from the public board
            continue
        description = html_to_text(job.get("descriptionHtml", "")) or job.get("descriptionPlain", "")
        postings.append(
            Posting(
                source=SOURCE,
                company=company,
                job_id=str(job["id"]),
                title=job.get("title", "").strip(),
                location=job.get("location", "") or "",
                url=job.get("jobUrl", ""),
                description=description,
                updated_at=job.get("publishedAt", ""),  # Ashby has no updated time
                fetched_at=fetched_at,
            )
        )
    return postings
