"""Board lists: which (job board, company token) pairs to fetch.

File format, one board per line:
    greenhouse:databricks
    lever:spotify
    ashby:ramp
    databricks          # no prefix means greenhouse
Blank lines and # comments are ignored.
"""

from pathlib import Path
from typing import NamedTuple

from jd_analyzer.sources import SOURCES
from jd_analyzer.sources.base import check_token

DEFAULT_SOURCE = "greenhouse"


class Board(NamedTuple):
    source: str
    token: str

    def __str__(self) -> str:
        return f"{self.source}:{self.token}"


def parse_board_line(text: str) -> Board:
    """Parse "source:token" (or a bare token) into a checked Board."""
    source, sep, token = text.strip().partition(":")
    if not sep:
        source, token = DEFAULT_SOURCE, source
    source, token = source.strip().lower(), token.strip().lower()
    if source not in SOURCES:
        raise ValueError(f"unknown job board {source!r} in {text!r}")
    return Board(source, check_token(token))


def read_boards(path: Path) -> list[Board]:
    """Read a board list, dropping duplicates but keeping first-seen order."""
    boards = []
    for n, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            boards.append(parse_board_line(line))
        except ValueError as e:
            raise ValueError(f"{path.name} line {n}: {e}") from None
    return list(dict.fromkeys(boards))


def write_boards(boards: list[Board], path: Path, header: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {h}" for h in header.splitlines()] + [str(b) for b in boards]
    path.write_text("\n".join(lines) + "\n")
