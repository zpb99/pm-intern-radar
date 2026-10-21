"""MCP server: ask Claude about tracked Product Manager intern roles.

Reads the data the weekly radar writes (data/postings.csv, data/radar/seen.json);
it never fetches anything itself, so every call is fast and offline. Data is
re-read on each call, so Monday's radar run shows up without a restart.

Run (stdio):
    python -m jd_analyzer.mcp_server
Set JD_ANALYZER_DATA_DIR to read data from somewhere other than ./data.
"""

from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from jd_analyzer import catalog
from jd_analyzer.catalog import CatalogError

mcp = FastMCP(
    "pm-intern-radar",
    instructions=(
        "Tracks Product Manager internship postings from public Greenhouse, Lever and Ashby job boards "
        "(about 1,000 companies, found via the SimplifyJobs internship list), refreshed weekly. Coverage "
        "skews to tech startups and growth-stage companies; Workday and custom career sites are not covered. "
        "Degree and skill tags are keyword matches; quote required_lines when precision matters. "
        + catalog.UNTRUSTED_NOTE
    ),
)
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)


def _envelope(cat: catalog.Catalog, **payload) -> dict:
    return {"data_as_of": cat.data_as_of, "tracking_since": cat.baseline_date, "note": catalog.UNTRUSTED_NOTE, **payload}


def _load() -> catalog.Catalog:
    try:
        return catalog.load()
    except CatalogError as e:
        raise ToolError(str(e)) from None


@mcp.tool(annotations=READ_ONLY)
def new_roles(since: str | None = None) -> dict:
    """List PM intern roles first seen on or after a date (YYYY-MM-DD; default: 7 days ago).

    A "role" merges copies of one job posted in several locations or on several boards.
    Roles with in_baseline=true were already open when tracking started, so first_seen
    is not their posting date. Results list roles naming the MBA first. Use
    get_requirements(role_id) for the full requirement lines.
    """
    cat = _load()
    since = since or (date.today() - timedelta(days=7)).isoformat()
    try:
        rows = catalog.new_roles(cat, since)
    except CatalogError as e:
        raise ToolError(str(e)) from None
    return _envelope(cat, since=since, count=len(rows), roles=rows)


@mcp.tool(annotations=READ_ONLY)
def search_roles(
    text: str = "",
    skill: str = "",
    skill_in: str = "required",
    degree: str = "any",
    company: str = "",
) -> dict:
    """Search all currently open PM intern roles. Filters are optional and combine with AND.

    - text: case-insensitive substring of the title, company or posting text.
    - skill: a skill name or unique part of one, e.g. "SQL", "MBA", "AI tools", "A/B testing".
      An unknown name returns the list of valid skills.
    - skill_in: "required" (default), "preferred", or "anywhere" (includes job duties
      and company blurbs, so it is noisier).
    - degree: "any" (default), "mba" (MBA named), "graduate" (MBA or master's mentioned),
      or "bachelors_only".
    - company: substring of the company's board name, e.g. "duolingo".
    """
    cat = _load()
    try:
        rows = catalog.search_roles(cat, text=text, skill=skill, skill_in=skill_in, degree=degree, company=company)
    except CatalogError as e:
        raise ToolError(str(e)) from None
    return _envelope(cat, count=len(rows), roles=rows)


@mcp.tool(annotations=READ_ONLY)
def get_requirements(role_id: str) -> dict:
    """Full detail for one role: its required and preferred lines quoted from the posting,
    matched skills, degree hint, and every copy's location and link.

    role_id comes from new_roles or search_roles; any posting key in the role also works.
    If has_requirements_section is false, the posting had no recognizable requirements
    heading: read it at the url.
    """
    cat = _load()
    try:
        role = catalog.get_requirements(cat, role_id)
    except CatalogError as e:
        raise ToolError(str(e)) from None
    return _envelope(cat, role=role)


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
