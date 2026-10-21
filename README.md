# jd-analyzer

What do Product Manager intern job descriptions actually ask for?

This project pulls PM intern postings from public job-board APIs, extracts the skills and
requirements each one lists, and counts and clusters them.

Status: **fetching works (Greenhouse)**. Extraction and analysis are next.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Use the venv's `requests`, not Python's built-in `urllib`. The python.org macOS installer
ships without root certificates, so `urllib` fails with `CERTIFICATE_VERIFY_FAILED`.
`requests` bundles its own (`certifi`).

## Fetch postings

```bash
python -m jd_analyzer.fetch                      # every board in companies.txt
python -m jd_analyzer.fetch databricks duolingo  # just these
```

Outputs (not committed, see `.gitignore`):

- `data/raw/greenhouse/<date>/<company>.json`: the full board, untouched, so you can re-parse
  without re-fetching
- `data/postings.csv`: PM-intern postings only, with columns
  `source, company, job_id, title, location, url, description, updated_at, fetched_at`

A title counts as a PM internship when it contains "product manager" or "product management"
**and** the whole word "intern", "internship" or "MBA". See `jd_analyzer/filters.py` and
the cases in `tests/test_filters.py`, e.g. why "International" must not match.

## Data sources (checked 2026-10-21)

| Board | Endpoint | Auth | PM-intern titles found |
|---|---|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true` | none | Databricks, Datadog, Coinbase, Duolingo, Roblox |
| Lever | `api.lever.co/v0/postings/<token>?mode=json` | none | none on boards tested |
| Ashby | `api.ashbyhq.com/posting-api/job-board/<token>` | none | none on boards tested |

Only Greenhouse is implemented. Each board is one module in `jd_analyzer/sources/` that
returns `Posting` records (`jd_analyzer/models.py`). Adding Lever or Ashby means adding one
file. Nothing else changes.

## Tests

```bash
python -m pytest -q
```

## Layout

```
jd_analyzer/
  models.py            Posting record + CSV column order
  filters.py           is_pm_intern(title)
  text.py              HTML -> plain text (bullets kept as "- " lines)
  sources/greenhouse.py  fetch_board() (network) + parse_board() (pure)
  fetch.py             command-line entry point
companies.txt          board tokens to pull
tests/
```
