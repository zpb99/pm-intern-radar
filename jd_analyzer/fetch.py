"""Pull PM-intern postings from job boards and save raw JSON + a clean CSV.

Usage:
    python -m jd_analyzer.fetch                                    # boards in boards.txt
    python -m jd_analyzer.fetch --boards data/boards_discovered.txt  # after discover
    python -m jd_analyzer.fetch greenhouse:duolingo lever:spotify  # just these
"""

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import requests

from jd_analyzer.boards import Board, parse_board_line, read_boards
from jd_analyzer.filters import is_pm_intern
from jd_analyzer.models import CSV_COLUMNS, Posting
from jd_analyzer.sources import SOURCES
from jd_analyzer.sources.base import BoardNotFound

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BOARDS = ROOT / "boards.txt"
DATA_DIR = ROOT / "data"
PAUSE_SECONDS = 1.0  # between requests to the same job board, to be polite
REPORT_COLUMNS = ["source", "token", "status", "jobs", "pm_intern", "error"]


_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def spreadsheet_safe(value):
    """Prefix text that Excel/Sheets would run as a formula ("- SQL", "=HYPERLINK(...)")."""
    if isinstance(value, str) and value.startswith(_FORMULA_START):
        return "'" + value
    return value


def write_csv(rows: list[dict], columns: list[str], path: Path, for_spreadsheets: bool = False) -> None:
    """Write rows to CSV. Use for_spreadsheets=True for files people open in Excel or
    Sheets; leave it off for files the pipeline reads back (it alters the text)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: spreadsheet_safe(v) for k, v in row.items()} if for_spreadsheets else row)


def fetch_one(board: Board, session, raw_dir: Path, fetched_at: str) -> tuple[list[Posting], dict]:
    """Fetch one board. Returns its PM-intern postings and a report row."""
    source = SOURCES[board.source]
    report = {"source": board.source, "token": board.token, "jobs": 0, "pm_intern": 0, "error": ""}
    try:
        raw = source.fetch_board(board.token, session)
    except BoardNotFound:
        return [], {**report, "status": "not_found"}
    except (requests.RequestException, ValueError) as e:  # ValueError: response wasn't JSON
        return [], {**report, "status": "error", "error": str(e)[:200]}

    try:
        postings = source.parse_board(board.token, raw, fetched_at)
    except (KeyError, TypeError, AttributeError) as e:  # JSON not shaped as expected
        return [], {**report, "status": "error", "error": f"parse failed: {e!r}"[:200]}
    matches = [p for p in postings if is_pm_intern(p.title)]
    if matches:  # raw JSON for every board would be ~1 GB; keep the ones we use
        (raw_dir / board.source).mkdir(parents=True, exist_ok=True)
        (raw_dir / board.source / f"{board.token}.json").write_text(json.dumps(raw, indent=2))
    return matches, {**report, "status": "ok", "jobs": len(postings), "pm_intern": len(matches)}


def fetch_source(boards: list[Board], raw_dir: Path, fetched_at: str) -> tuple[list[Posting], list[dict]]:
    """Fetch every board on one job board, one at a time with a pause between."""
    session = requests.Session()
    session.headers["User-Agent"] = "jd-analyzer (personal research project)"
    kept, reports = [], []
    for i, board in enumerate(boards, start=1):
        if i > 1:
            time.sleep(PAUSE_SECONDS)
        matches, report = fetch_one(board, session, raw_dir, fetched_at)
        kept.extend(matches)
        reports.append(report)
        if matches or report["status"] == "error":
            detail = report["error"] or f"{report['jobs']} jobs, {report['pm_intern']} PM intern"
            print(f"  {str(board):40} {detail}", flush=True)
        if i % 50 == 0 or i == len(boards):
            print(f"  [{boards[0].source}] {i}/{len(boards)} boards checked", flush=True)
    return kept, reports


def run(boards: list[Board], data_dir: Path) -> int:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    raw_dir = data_dir / "raw" / fetched_at[:10]
    by_source = {name: [b for b in boards if b.source == name] for name in SOURCES}
    by_source = {name: bs for name, bs in by_source.items() if bs}

    # One thread per job board: each board is still hit one request at a time,
    # but Greenhouse, Lever and Ashby are checked in parallel.
    with ThreadPoolExecutor(max_workers=len(by_source)) as pool:
        results = list(pool.map(lambda bs: fetch_source(bs, raw_dir, fetched_at), by_source.values()))

    kept = [p for postings, _ in results for p in postings]
    reports = [r for _, rs in results for r in rs]
    write_csv([asdict(p) for p in kept], CSV_COLUMNS, data_dir / "postings.csv")
    write_csv(reports, REPORT_COLUMNS, data_dir / "fetch_report.csv")

    print(f"\n{'job board':12} {'boards':>6} {'ok':>5} {'404':>5} {'error':>5} {'w/ PM intern':>12} {'postings':>8}")
    for name, bs in by_source.items():
        rs = [r for r in reports if r["source"] == name]
        count = lambda status: sum(r["status"] == status for r in rs)  # noqa: E731
        print(
            f"{name:12} {len(bs):6} {count('ok'):5} {count('not_found'):5} {count('error'):5} "
            f"{sum(r['pm_intern'] > 0 for r in rs):12} {sum(r['pm_intern'] for r in rs):8}"
        )
    print(f"\nSaved {len(kept)} postings to {(data_dir / 'postings.csv').relative_to(ROOT)}")
    print(f"Per-board results in {(data_dir / 'fetch_report.csv').relative_to(ROOT)}")
    errors = sum(r["status"] == "error" for r in reports)
    return 1 if errors and not kept else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("boards", nargs="*", help="boards like greenhouse:duolingo")
    parser.add_argument("--boards", dest="boards_file", type=Path, help="file with one board per line")
    args = parser.parse_args(argv)
    try:
        if args.boards:
            boards = list(dict.fromkeys(parse_board_line(b) for b in args.boards))
        else:
            boards = read_boards(args.boards_file or DEFAULT_BOARDS)
    except ValueError as e:
        parser.error(str(e))
    if not boards:
        parser.error("no boards to fetch")
    print(f"Checking {len(boards)} boards...")
    return run(boards, DATA_DIR)


if __name__ == "__main__":
    sys.exit(main())
