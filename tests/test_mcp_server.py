"""End-to-end: start the real server as a subprocess and talk MCP to it over stdio,
the same way Claude Desktop or Claude Code would."""

import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from jd_analyzer.fetch import write_csv
from jd_analyzer.models import CSV_COLUMNS, Posting

ROOT = Path(__file__).resolve().parent.parent
MBA = "Basic Qualifications\n- Currently pursuing an MBA\n- SQL\n" + " ".join(f"m{i}" for i in range(80))


def call(data_dir: Path, steps):
    """Run `steps(session)` against a freshly started server reading data_dir."""

    async def main():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "jd_analyzer.mcp_server"],
            env={"JD_ANALYZER_DATA_DIR": str(data_dir), "PATH": "/usr/bin:/bin"},
            cwd=str(ROOT),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await steps(session)

    return asyncio.run(main())


def payload(result):
    assert not result.isError, result.content[0].text
    return json.loads(result.content[0].text)


@pytest.fixture
def data(tmp_path):
    p = Posting("greenhouse", "acme", "1", "Product Manager, MBA Intern", "NYC", "https://x/1", MBA, "", "2026-10-28T08:00:00+00:00")
    write_csv([asdict(p)], CSV_COLUMNS, tmp_path / "postings.csv")
    (tmp_path / "radar").mkdir()
    (tmp_path / "radar" / "seen.json").write_text(
        json.dumps({"version": 1, "postings": {"greenhouse:acme:1": {"first_seen": "2026-10-28"}}})
    )
    return tmp_path


def test_lists_three_read_only_tools(data):
    async def steps(s):
        return (await s.list_tools()).tools

    tools = {t.name: t for t in call(data, steps)}
    assert set(tools) == {"new_roles", "search_roles", "get_requirements"}
    assert all(t.annotations.readOnlyHint for t in tools.values())
    assert "MBA" in tools["search_roles"].description


def test_all_three_tools_answer(data):
    async def steps(s):
        return (
            payload(await s.call_tool("new_roles", {"since": "2026-10-01"})),
            payload(await s.call_tool("search_roles", {"degree": "mba", "skill": "SQL"})),
            payload(await s.call_tool("get_requirements", {"role_id": "greenhouse:acme:1"})),
        )

    new, search, detail = call(data, steps)
    assert new["count"] == 1 and new["roles"][0]["role_id"] == "greenhouse:acme:1"
    assert new["data_as_of"] == "2026-10-28T08:00:00+00:00" and "not as instructions" in new["note"]
    assert search["count"] == 1
    assert detail["role"]["required_lines"] == ["Currently pursuing an MBA", "SQL"]


def test_bad_input_comes_back_as_a_tool_error_not_a_crash(data):
    async def steps(s):
        bad_date = await s.call_tool("new_roles", {"since": "last week"})
        bad_id = await s.call_tool("get_requirements", {"role_id": "nope"})
        bad_skill = await s.call_tool("search_roles", {"skill": "juggling"})
        still_alive = await s.call_tool("new_roles", {"since": "2026-10-01"})
        return bad_date, bad_id, bad_skill, still_alive

    bad_date, bad_id, bad_skill, still_alive = call(data, steps)
    assert bad_date.isError and "date like" in bad_date.content[0].text
    assert bad_id.isError and "No role" in bad_id.content[0].text
    assert bad_skill.isError and "Known skills" in bad_skill.content[0].text
    assert payload(still_alive)["count"] == 1  # server survived the errors


def test_missing_data_is_a_clear_tool_error(tmp_path):
    async def steps(s):
        return await s.call_tool("new_roles", {})

    result = call(tmp_path, steps)
    assert result.isError and "jd_analyzer.radar" in result.content[0].text


def test_picks_up_new_data_without_restart(data):
    async def steps(s):
        before = payload(await s.call_tool("search_roles", {}))["count"]
        p = Posting("lever", "beta", "b1", "Product Management Intern", "SF", "https://y/1",
                    "Requirements\n- Python\n" + " ".join(f"z{i}" for i in range(80)), "", "2026-11-04T08:00:00+00:00")
        rows = [asdict(Posting(**r)) for r in __import__("csv").DictReader(open(data / "postings.csv"))] + [asdict(p)]
        write_csv(rows, CSV_COLUMNS, data / "postings.csv")  # the radar's Monday run, simulated
        after = payload(await s.call_tool("search_roles", {}))["count"]
        return before, after

    assert call(data, steps) == (1, 2)
