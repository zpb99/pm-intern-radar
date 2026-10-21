"""Job-board sources. Each module exposes SOURCE, fetch_board() and parse_board()."""

from jd_analyzer.sources import ashby, greenhouse, lever

SOURCES = {m.SOURCE: m for m in (greenhouse, lever, ashby)}
