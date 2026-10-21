# jd-analyzer

What do Product Manager intern job descriptions actually ask for?

This project pulls PM intern postings from public job-board APIs, extracts the skills and
requirements each one lists, and counts and clusters them.

Status: **fetching works (Greenhouse, Lever, Ashby; ~1,000 companies discovered automatically)**.
Extraction and analysis are next.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Use the venv's `requests`, not Python's built-in `urllib`. The python.org macOS installer
ships without root certificates, so `urllib` fails with `CERTIFICATE_VERIFY_FAILED`.
`requests` bundles its own (`certifi`).

## Find companies, then fetch postings

No job board lets you search across companies, so step 1 borrows a company list:

```bash
python -m jd_analyzer.discover   # -> data/boards_discovered.txt (~1,000 boards)
```

It reads the [SimplifyJobs Summer 2027 internship list](https://github.com/SimplifyJobs/Summer2027-Internships)
and keeps every Greenhouse, Lever or Ashby board linked from it (any role, not just PM),
plus the hand-picked boards in `boards.txt`. Only company tokens come from Simplify; job
text always comes from the job boards' own APIs.

```bash
python -m jd_analyzer.fetch --boards data/boards_discovered.txt  # everything (~15 min)
python -m jd_analyzer.fetch                                      # just boards.txt
python -m jd_analyzer.fetch greenhouse:duolingo lever:spotify    # just these
```

Board format is `<job board>:<company token>`; a bare token means Greenhouse. Tokens are
checked against a strict pattern (no `/`, `%`, `?`...) before they reach a URL or filename.

Outputs (not committed, see `.gitignore`):

- `data/postings.csv`: PM-intern postings only, with columns
  `source, company, job_id, title, location, url, description, updated_at, fetched_at`
- `data/fetch_report.csv`: one row per board checked (ok / not_found / error, job count,
  PM-intern count), so you can see what was and wasn't covered
- `data/raw/<date>/<job board>/<company>.json`: the full board response, kept only for boards
  with a PM-intern match (keeping all of them would be ~1 GB)

A title counts as a PM internship when it contains "product manager" or "product management"
**and** the whole word "intern", "internship" or "MBA". See `jd_analyzer/filters.py` and
the cases in `tests/test_filters.py`, e.g. why "International" must not match.

**Coverage caveat.** On 2026-10-21, of the open PM-intern listings on Simplify, only ~9% were
on Greenhouse/Lever/Ashby; most were on Workday or company career sites, which this tool
does not read. Results describe PM internships at companies using these three job boards
(skewing toward tech startups and growth-stage companies), not all PM internships.

## Data sources (checked 2026-10-21)

| Job board | Endpoint | Auth | Results |
|---|---|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true` | none | see `data/fetch_report.csv` |
| Lever | `api.lever.co/v0/postings/<token>?mode=json` | none | see `data/fetch_report.csv` |
| Ashby | `api.ashbyhq.com/posting-api/job-board/<token>` | none | see `data/fetch_report.csv` |

Each job board is one module in `jd_analyzer/sources/` that returns `Posting` records
(`jd_analyzer/models.py`). Shared token checks and retry-on-rate-limit live in
`sources/base.py`, so adding another job board means one small file.

## Tests

```bash
python -m pytest -q
```

## Layout

```
jd_analyzer/
  models.py              Posting record + CSV column order
  filters.py             is_pm_intern(title)
  text.py                HTML -> plain text (bullets kept as "- " lines)
  boards.py              Board(source, token) + board-list files
  discover.py            find boards from the Simplify internship list
  fetch.py               command-line entry point
  sources/
    base.py              token checks, HTTP with retry, BoardNotFound
    greenhouse.py        fetch_board() (network) + parse_board() (pure)
    lever.py
    ashby.py
boards.txt               hand-picked boards, always included
tests/
```
