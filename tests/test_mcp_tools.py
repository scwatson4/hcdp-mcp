"""Test MCP server tool registration.

Validates that all 10 expected tools are registered with the MCP server
and that no tools are missing or unexpectedly added.
"""

import pytest

from hcdp_mcp_server.server import handle_list_tools

EXPECTED_TOOL_NAMES = [
    "get_timeseries_data",
    "get_station_data",
    "get_mesonet_data",
    "get_mesonet_stations",
    "get_mesonet_variables",
    "get_nearby_stations",
    "get_island_current_summary",
    "get_city_current_weather",
    "compare_current_vs_historical",
    "get_island_history_summary",
]


@pytest.mark.asyncio
async def test_all_tools_registered():
    """Assert all 10 expected tools are registered with the MCP server."""
    tools = await handle_list_tools()
    registered = [tool.name for tool in tools]

    assert len(tools) == len(EXPECTED_TOOL_NAMES), (
        f"Expected {len(EXPECTED_TOOL_NAMES)} tools, got {len(tools)}. "
        f"Registered: {registered}"
    )

    for name in EXPECTED_TOOL_NAMES:
        assert name in registered, f"Tool '{name}' not registered"


@pytest.mark.asyncio
async def test_no_extra_tools():
    """Assert no unexpected tools are registered."""
    tools = await handle_list_tools()
    registered = {tool.name for tool in tools}
    expected = set(EXPECTED_TOOL_NAMES)
    extra = registered - expected
    assert len(extra) == 0, f"Unexpected tools: {extra}"


@pytest.mark.asyncio
async def test_tools_have_descriptions():
    """Assert every registered tool has a non-empty description."""
    tools = await handle_list_tools()
    for tool in tools:
        assert tool.description, f"Tool '{tool.name}' has no description"
        assert (
            len(tool.description) > 10
        ), f"Tool '{tool.name}' description too short: {tool.description}"


@pytest.mark.asyncio
async def test_tools_have_input_schemas():
    """Assert every registered tool has an inputSchema."""
    tools = await handle_list_tools()
    for tool in tools:
        assert tool.inputSchema is not None, f"Tool '{tool.name}' has no inputSchema"
        assert (
            "properties" in tool.inputSchema or "type" in tool.inputSchema
        ), f"Tool '{tool.name}' inputSchema missing properties or type"
