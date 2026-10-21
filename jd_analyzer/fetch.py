"""Pull PM-intern postings from Greenhouse boards and save raw JSON + a clean CSV.

Usage:
    python -m jd_analyzer.fetch                      # companies from companies.txt
    python -m jd_analyzer.fetch databricks duolingo  # just these
"""

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import requests

from jd_analyzer.filters import is_pm_intern
from jd_analyzer.models import CSV_COLUMNS, Posting
from jd_analyzer.sources import greenhouse

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COMPANIES = ROOT / "companies.txt"
DATA_DIR = ROOT / "data"
PAUSE_SECONDS = 1.0  # be polite to a free public API


def read_companies(path: Path) -> list[str]:
    """One board token per line; blank lines and # comments ignored."""
    lines = (line.split("#", 1)[0].strip() for line in path.read_text().splitlines())
    return [line for line in lines if line]


def write_csv(postings: list[Posting], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for p in postings:
            writer.writerow(asdict(p))


def run(companies: list[str], data_dir: Path) -> int:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    raw_dir = data_dir / "raw" / greenhouse.SOURCE / fetched_at[:10]
    raw_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = "jd-analyzer (personal research project)"

    kept: list[Posting] = []
    failures: list[str] = []
    for i, company in enumerate(companies):
        if i:
            time.sleep(PAUSE_SECONDS)
        try:
            raw = greenhouse.fetch_board(company, session)
        except greenhouse.BoardNotFound:
            print(f"  {company:14} no Greenhouse board (404), skipped")
            failures.append(company)
            continue
        except requests.RequestException as e:
            print(f"  {company:14} FAILED: {e}")
            failures.append(company)
            continue

        (raw_dir / f"{company}.json").write_text(json.dumps(raw, indent=2))
        postings = greenhouse.parse_board(company, raw, fetched_at)
        matches = [p for p in postings if is_pm_intern(p.title)]
        kept.extend(matches)
        print(f"  {company:14} {len(postings):4} jobs, {len(matches)} PM intern")

    csv_path = data_dir / "postings.csv"
    write_csv(kept, csv_path)
    print(f"\nSaved {len(kept)} postings to {csv_path.relative_to(ROOT)}")
    print(f"Raw JSON in {raw_dir.relative_to(ROOT)}/")
    if failures:
        print(f"Failed or missing boards: {', '.join(failures)}")
    return 1 if failures and not kept else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("companies", nargs="*", help="Greenhouse board tokens")
    args = parser.parse_args(argv)
    companies = args.companies or read_companies(DEFAULT_COMPANIES)
    if not companies:
        parser.error("no companies given and companies.txt is empty")
    print(f"Fetching {len(companies)} Greenhouse boards...")
    return run(companies, DATA_DIR)


if __name__ == "__main__":
    sys.exit(main())
