"""Lever public postings API (no auth required).

Docs: https://github.com/lever/postings-api
"""

from datetime import datetime, timezone

import requests

from jd_analyzer.models import Posting
from jd_analyzer.sources.base import board_url, get_json
from jd_analyzer.text import html_to_text

SOURCE = "lever"
BOARD_URL = "https://api.lever.co/v0/postings/{token}"


def fetch_board(company: str, session: requests.Session | None = None) -> list:
    """Return the raw JSON (a list of postings) for one company."""
    return get_json(board_url(BOARD_URL, company), session, params={"mode": "json"})


def parse_board(company: str, raw: list, fetched_at: str) -> list[Posting]:
    postings = []
    for job in raw or []:
        categories = job.get("categories") or {}
        postings.append(
            Posting(
                source=SOURCE,
                company=company,
                job_id=str(job["id"]),
                title=job.get("text", "").strip(),
                location=categories.get("location", "") or "",
                url=job.get("hostedUrl", ""),
                description=_description(job),
                updated_at=_ms_to_iso(job.get("createdAt")),  # Lever has no updated time
                fetched_at=fetched_at,
            )
        )
    return postings


def _description(job: dict) -> str:
    """Lever splits a posting into an intro, titled lists, and a closing section.

    The requirements usually live in the lists ("What you'll need"), so all
    three parts are joined, with each list title on its own line.
    """
    parts = [html_to_text(job.get("description", ""))]
    for section in job.get("lists") or []:
        parts.append(section.get("text", "").strip())
        parts.append(html_to_text(section.get("content", "")))
    parts.append(html_to_text(job.get("additional", "")))
    return "\n".join(p for p in parts if p)


def _ms_to_iso(ms) -> str:
    if not isinstance(ms, (int, float)):
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat(timespec="seconds")
