"""HCDP MCP Server tools package.

Each tool is defined in its own module with:
- An args model (Pydantic BaseModel)
- A tool_definition (mcp.types.Tool)
- A handle(client, arguments) async function
"""

from . import (
    timeseries,
    station_data,
    mesonet_data,
    mesonet_stations,
    mesonet_variables,
    island_summary,
    city_weather,
    compare_historical,
    island_history,
)

# Registry of all active tools: maps tool name -> module
TOOL_REGISTRY = {
    timeseries.tool_definition.name: timeseries,
    station_data.tool_definition.name: station_data,
    mesonet_data.tool_definition.name: mesonet_data,
    mesonet_stations.tool_definition.name: mesonet_stations,
    mesonet_variables.tool_definition.name: mesonet_variables,
    island_summary.tool_definition.name: island_summary,
    city_weather.tool_definition.name: city_weather,
    compare_historical.tool_definition.name: compare_historical,
    island_history.tool_definition.name: island_history,
}


def get_all_tool_definitions():
    """Return a list of all tool definitions."""
    return [module.tool_definition for module in TOOL_REGISTRY.values()]


async def dispatch_tool(name, client, arguments):
    """Dispatch a tool call to the appropriate handler."""
    module = TOOL_REGISTRY.get(name)
    if module is None:
        raise ValueError(f"Unknown tool: {name}")
    return await module.handle(client, arguments)
