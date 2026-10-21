# jd-analyzer

What do Product Manager intern job descriptions actually ask for?

This project pulls PM intern postings from public job-board APIs, extracts the skills and
requirements each one lists, and counts and clusters them.

Status: **fetching, skill extraction, a weekly new-postings radar, and an MCP server work.**

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

## Extract skills

```bash
python -m jd_analyzer.extract
```

1. **Merge cross-posts into roles** (`dedupe.py`). One internship posted per country, or on
   two of a company's boards, is one role. Postings whose descriptions share at least 40% of
   their 5-word phrases are merged. On 2026-10-21, same-company copies scored 0.45–1.00 and no
   cross-company pair scored above 0.2.
2. **Label lines** required / preferred / other (`sections.py`) from headings like "Basic
   Qualifications", "Who You Are", "Bonus Points", and inline "...is a plus".
3. **Match skills** (`skills.py`): a hand-written list of regexes, built from the requirement
   lines in real postings. Each skill counts at most once per role.

Outputs: `data/skill_counts.csv` (per skill: roles mentioning it anywhere, requiring it,
preferring it), `data/roles.csv`, and `data/skill_evidence.csv`, which lists every match with
the line it came from. **Read the evidence before quoting a number.** "Mentioned anywhere"
includes company intros and job duties ("drive features through launch"), so the *required*
column is the one that means "asked of the candidate."

## Weekly radar: only what's new

```bash
python -m jd_analyzer.radar               # discover + fetch + compare (~15 min)
python -m jd_analyzer.radar --skip-fetch  # compare the last fetch only
```

The radar remembers every posting it has seen (`data/radar/seen.json`) and writes
`data/radar/latest.md` (plus a dated copy) listing only:

- **New roles**: no copy of the role was seen before. Each comes with its link, its required and
  preferred lines, and a degree hint. Roles that name the MBA come first; bachelor's-only last.
- **Known roles, new locations**: a role you've seen got another location or board.
- **No longer listed**: only counted when that company's board was fetched successfully,
  so a board that errored this week doesn't look like it closed its roles.

A corrupt `seen.json` stops the run instead of starting over, since starting over would report
every known role as new.

**Schedule (macOS):** `bash scripts/install_schedule.sh` installs a launchd job that runs
`scripts/run_radar.sh` every Monday at 08:00 (or at the next wake if the Mac was asleep),
then shows a notification with the count of new roles, or that the run failed. Logs go to
`data/radar/logs/`. Remove it with `bash scripts/uninstall_schedule.sh`.

## Ask Claude about the roles (MCP server)

`jd_analyzer/mcp_server.py` is a local [MCP](https://modelcontextprotocol.io) server over the
radar's data. It never fetches anything itself: it reads `data/postings.csv` and
`data/radar/seen.json` on every call, so Monday's radar run shows up without a restart.

| Tool | What it answers |
|---|---|
| `new_roles(since)` | Roles first seen on or after a date (default: last 7 days). `in_baseline: true` marks roles that were already open when tracking began. |
| `search_roles(text, skill, skill_in, degree, company)` | e.g. `degree="mba"`, `skill="SQL", skill_in="anywhere"`. Unknown skills return the list of valid ones. |
| `get_requirements(role_id)` | The role's required and preferred lines quoted from the posting, plus every copy's location and link. |

Every response includes `data_as_of` and a note that posting text is third-party data, not
instructions.

**Untrusted text.** Posting text is written by whoever controls a job board. Before it
reaches Claude or the report, invisible and text-reordering characters (zero-width spaces,
right-to-left overrides, U+2028 line separators) are removed (`untrusted.py`), and links
that aren't plain http(s) URLs are withheld. That doesn't make prompt injection impossible:
a posting can still contain plain-English instructions. The tools only read data, so the
worst case is a misleading answer, not an action. Check anything important at the
posting's link.

**Claude Code:**

```bash
claude mcp add pm-intern-radar -- /path/to/jd-analyzer/.venv/bin/python -m jd_analyzer.mcp_server
```

Run it from the repo folder, or add `--env JD_ANALYZER_DATA_DIR=/path/to/jd-analyzer/data`.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pm-intern-radar": {
      "command": "/path/to/jd-analyzer/.venv/bin/python",
      "args": ["-m", "jd_analyzer.mcp_server"],
      "env": {"JD_ANALYZER_DATA_DIR": "/path/to/jd-analyzer/data"}
    }
  }
}
```

**Related work, and how this differs (checked 2026-10-21):**
[ats-jobs-mcp](https://pypi.org/project/ats-jobs-mcp) already exposes Greenhouse, Ashby, Lever
and Workable boards per company, with careful salary parsing. This server instead covers one
kind of role across ~1,000 companies: what's new each week, cross-posts merged, and each
posting's required vs preferred lines.

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
  fetch.py               command-line entry point: fetch
  dedupe.py              merge cross-posted copies into roles
  sections.py            label lines required / preferred / other
  skills.py              the skill list (edit this to add skills)
  extract.py             command-line entry point: extract
  radar.py               command-line entry point: weekly new-roles report
  catalog.py             read-only queries over tracked roles (used by the MCP server)
  mcp_server.py          MCP server: new_roles, search_roles, get_requirements
  sources/
    base.py              token checks, HTTP with retry, BoardNotFound
    greenhouse.py        fetch_board() (network) + parse_board() (pure)
    lever.py
    ashby.py
boards.txt               hand-picked boards, always included
scripts/                 run_radar.sh, install_schedule.sh, uninstall_schedule.sh
tests/
```
