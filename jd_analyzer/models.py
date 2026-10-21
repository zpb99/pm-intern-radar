"""The one record type every job-board source returns."""

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Posting:
    source: str  # which job board, e.g. "greenhouse"
    company: str  # the board token, e.g. "duolingo"
    job_id: str
    title: str
    location: str
    url: str
    description: str  # plain text, HTML already stripped
    updated_at: str  # as reported by the job board
    fetched_at: str  # when we pulled it (UTC, ISO 8601)


CSV_COLUMNS = [f.name for f in fields(Posting)]
