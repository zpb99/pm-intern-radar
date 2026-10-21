"""Weekly radar: show only PM-intern roles that are new since the last run.

Runs discover + fetch, compares against data/radar/seen.json, writes a report of
the new roles' required and preferred lines, then records what it saw.

Usage:
    python -m jd_analyzer.radar               # full run (~15 min)
    python -m jd_analyzer.radar --skip-fetch  # reuse data/postings.csv from the last fetch
"""

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import requests

from jd_analyzer import discover, fetch
from jd_analyzer.boards import read_boards
from jd_analyzer.catalog import degree_hint
from jd_analyzer.dedupe import Role, group_roles
from jd_analyzer.extract import analyze_role, read_postings
from jd_analyzer.models import Posting
from jd_analyzer.untrusted import clean_text, safe_url
from jd_analyzer.sections import PREFERRED, REQUIRED, label_lines

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RADAR_DIR = DATA_DIR / "radar"
SEEN_FILE = RADAR_DIR / "seen.json"
STORE_VERSION = 1



def posting_key(p: Posting) -> str:
    return f"{p.source}:{p.company}:{p.job_id}"


class CorruptSeenFile(Exception):
    """seen.json exists but can't be trusted. Never silently start over: that
    would report every known role as new."""


def load_seen(path: Path = SEEN_FILE) -> dict[str, dict]:
    """Return {posting key: record}. A missing file means first run: {}."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise CorruptSeenFile(f"{path} is not valid JSON ({e}). Fix or delete it.") from None
    if not isinstance(data, dict) or data.get("version") != STORE_VERSION or not isinstance(data.get("postings"), dict):
        raise CorruptSeenFile(f"{path} has an unexpected format. Fix or delete it.")
    return data["postings"]


def save_seen(seen: dict[str, dict], path: Path = SEEN_FILE) -> None:
    """Write atomically: a crash mid-write leaves the old file intact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"version": STORE_VERSION, "postings": seen}, indent=2, sort_keys=True))
    os.replace(tmp, path)


@dataclass
class RadarResult:
    first_run: bool
    new_roles: list[Role] = field(default_factory=list)
    new_locations: list[tuple[Role, list[Posting]]] = field(default_factory=list)  # known role, new copies
    gone: list[dict] = field(default_factory=list)  # seen records no longer listed


def compare(postings: list[Posting], seen: dict[str, dict], boards_checked_ok: set[tuple[str, str]]) -> RadarResult:
    """Split the current postings into new roles, new locations of known roles, and gone.

    A posting only counts as gone if its board was fetched successfully this run;
    a board that errored tells us nothing about what it still lists.
    """
    result = RadarResult(first_run=not seen)
    for role in group_roles(postings):
        fresh = [p for p in role.postings if posting_key(p) not in seen]
        if len(fresh) == len(role.postings):
            result.new_roles.append(role)
        elif fresh:
            result.new_locations.append((role, fresh))
    current = {posting_key(p) for p in postings}
    for key, record in seen.items():
        source, company, _ = key.split(":", 2)
        if key not in current and (source, company) in boards_checked_ok and not record.get("gone_since"):
            result.gone.append({"key": key, **record})
    return result


def update_seen(seen: dict[str, dict], postings: list[Posting], result: RadarResult, today: str) -> dict[str, dict]:
    updated = {k: dict(v) for k, v in seen.items()}
    for p in postings:
        record = updated.setdefault(posting_key(p), {"first_seen": today, "title": p.title, "url": p.url})
        record["last_seen"] = today
        record.pop("gone_since", None)  # reposted: listed again
    for g in result.gone:
        updated[g["key"]]["gone_since"] = today
    return updated


# Characters that can start Markdown links/images (`[`, `]`, `(`, `)`, `!`), code spans
# (backtick), raw HTML (`<`, `>`, `&`), or escapes (backslash). Everything else in job
# text can at most change formatting (bold, italics), which is harmless.
_MD_SPECIAL = re.compile(r"([\\`\[\]()!<>&])")


def _text(value: str) -> str:
    """Job-board text is untrusted: remove hidden characters, then backslash-escape the
    Markdown/HTML characters that could form a link, image, code span or tag."""
    return _MD_SPECIAL.sub(r"\\\1", clean_text(value))


def _link(url: str) -> str:
    """Only plain http(s) URLs become links; anything else is shown as escaped text."""
    if not url:
        return "not listed"
    if safe_url(url):
        return f"<{url}>"
    return f"{_text(url)} (not linked: not a plain http(s) URL)"


def render_role(role: Role) -> str:
    analyzed = analyze_role(role)
    lines_by_label = {REQUIRED: [], PREFERRED: []}
    for label, line in label_lines(role.postings[0].description):
        if label in lines_by_label:
            lines_by_label[label].append(line.removeprefix("- "))
    first = role.postings[0]
    out = [
        f"### {_text(first.title)}: {', '.join(role.companies)}",
        f"- **Where:** {_text(' | '.join(sorted({p.location for p in role.postings if p.location}))) or 'not listed'}",
        f"- **Link:** {_link(first.url)}",
        f"- **Degree:** {degree_hint(analyzed.required, analyzed.preferred)[1]}",
    ]
    if analyzed.required:
        out.append(f"- **Required skills:** {', '.join(sorted(analyzed.required))}")
    if not analyzed.has_sections:
        out.append("\n_No requirements section detected. Read the posting._")
    for label, heading in ((REQUIRED, "Required"), (PREFERRED, "Preferred")):
        if lines_by_label[label]:
            out.append(f"\n**{heading}:**")
            out.extend(f"- {_text(line)}" for line in lines_by_label[label])
    return "\n".join(out)


def render_report(result: RadarResult, today: str, boards_ok: int, boards_failed: int) -> str:
    def mba_first(role: Role):
        a = analyze_role(role)
        return (degree_hint(a.required, a.preferred)[0], role.companies[0])

    head = f"# PM intern radar: {today}\n\n"
    if result.first_run:
        head += "_First run: everything below is the baseline. Next runs show only what's new._\n\n"
    head += (
        f"**{len(result.new_roles)} new roles**, {len(result.new_locations)} known roles with new locations, "
        f"{len(result.gone)} postings no longer listed. Checked {boards_ok} boards"
        + (f" ({boards_failed} failed, see data/fetch_report.csv)" if boards_failed else "")
        + ".\n\nRoles naming the MBA are listed first; bachelor's-only roles last. Degree and skill tags are "
        "keyword matches: read the posting before relying on them.\n"
    )
    parts = [head]
    if result.new_roles:
        parts.append("## New roles\n")
        parts.extend(render_role(r) + "\n" for r in sorted(result.new_roles, key=mba_first))
    if result.new_locations:
        parts.append("## Known roles, new locations\n")
        parts.extend(
            f"- {_text(r.title)} ({', '.join(r.companies)}): {_text(', '.join(p.location or '?' for p in fresh))}"
            for r, fresh in result.new_locations
        )
        parts.append("")
    if result.gone:
        parts.append("## No longer listed\n")
        parts.extend(f"- {_text(g['title'])}: {g['key'].split(':')[1]}" for g in result.gone)
    return "\n".join(parts).rstrip() + "\n"


def _unused_path(path: Path) -> Path:
    """report-2026-10-21.md, or report-2026-10-21-2.md if that exists, and so on."""
    candidate, n = path, 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
        n += 1
    return candidate


def _refresh_boards() -> list:
    """Re-run discovery; if Simplify is unreachable, reuse last week's board list."""
    try:
        discover.main()
    except (requests.RequestException, ValueError) as e:
        if not discover.OUTPUT.exists():
            raise
        print(f"Discovery failed ({e}); reusing {discover.OUTPUT.name}")
    return read_boards(discover.OUTPUT)


def run(skip_fetch: bool = False, today: str | None = None) -> int:
    today = today or date.today().isoformat()
    seen = load_seen(SEEN_FILE)  # fail before the 15-minute fetch, not after
    if not skip_fetch:
        fetch.run(_refresh_boards(), DATA_DIR)

    postings = read_postings(DATA_DIR / "postings.csv")
    with (DATA_DIR / "fetch_report.csv").open(newline="") as f:
        reports = list(csv.DictReader(f))
    boards_ok = {(r["source"], r["token"]) for r in reports if r["status"] == "ok"}
    boards_failed = sum(r["status"] == "error" for r in reports)
    if not boards_ok:
        print("No board was fetched successfully; not updating the radar.", file=sys.stderr)
        return 1

    result = compare(postings, seen, boards_ok)
    report = render_report(result, today, len(boards_ok), boards_failed)
    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    _unused_path(RADAR_DIR / f"report-{today}.md").write_text(report)  # never overwrite an earlier run
    (RADAR_DIR / "latest.md").write_text(report)
    save_seen(update_seen(seen, postings, result, today), SEEN_FILE)

    print(f"\n{len(result.new_roles)} new roles, {len(result.new_locations)} known roles with new locations, "
          f"{len(result.gone)} gone")
    print(f"Report: {RADAR_DIR / 'latest.md'}")
    (RADAR_DIR / "last_summary.txt").write_text(f"{len(result.new_roles)}\n")  # read by the scheduler script
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-fetch", action="store_true", help="reuse the last fetch's data/postings.csv")
    args = parser.parse_args(argv)
    try:
        return run(skip_fetch=args.skip_fetch)
    except CorruptSeenFile as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
