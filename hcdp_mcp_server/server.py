"""HCDP MCP Server - Main server implementation."""

import asyncio
import base64
import json
from typing import Sequence
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from .client import HCDPClient
from .tools import get_all_tool_definitions, dispatch_tool

# Re-export constants and arg models for backward compatibility with tests
from .tools.constants import (  # noqa: F401
    ISLAND_EXTENTS,
    CITY_LOCATIONS,
    ISLAND_REPRESENTATIVE_POINTS,
    MESONET_DATATYPE_MAP,
    ISLAND_BOUNDS,
    CITY_ALIASES,
    calculate_distance,
    resolve_mesonet_datatype,
    normalize_city_name,
    resolve_extent_from_coords,
)
from .tools.timeseries import GetTimeseriesArgs  # noqa: F401
from .tools.station_data import GetStationDataArgs  # noqa: F401
from .tools.mesonet_data import GetMesonetDataArgs  # noqa: F401
from .tools.mesonet_stations import GetMesonetStationsArgs  # noqa: F401
from .tools.mesonet_variables import GetMesonetVariablesArgs  # noqa: F401
from .tools.island_summary import GetIslandSummaryArgs  # noqa: F401
from .tools.city_weather import GetCityWeatherArgs  # noqa: F401
from .tools.compare_historical import CompareHistoryArgs  # noqa: F401
from .tools.island_history import GetIslandHistoryArgs  # noqa: F401

SERVER_INSTRUCTIONS = """HCDP (Hawaii Climate Data Portal) - Tool Routing Guide

CURRENT/REAL-TIME WEATHER (mesonet stations, updated every 15 min):
  Weather for a city/town -> get_city_current_weather
  Weather summary for an island -> get_island_current_summary
  Raw measurements by station ID -> get_mesonet_data

HISTORICAL/GRIDDED DATA (processed climate maps, days-months lag):
  Time series at a lat/lng point -> get_timeseries_data
  Island-wide annual patterns -> get_island_history_summary
  Compare today vs last year -> compare_current_vs_historical

DISCOVERY (use these first when unsure):
  List weather stations -> get_mesonet_stations
  List available variable IDs -> get_mesonet_variables
  Search station metadata by name -> get_station_data

TIPS:
- City names use snake_case: honolulu, manoa, kaneohe, lahaina, lanai_city
- Friendly datatype names accepted for current weather: 'temperature', 'rainfall', 'humidity', 'wind', 'solar'
- For raw mesonet var_ids (e.g. Tair_1_Avg), call get_mesonet_variables first
- Dates: YYYY-MM-DD for mesonet/station tools, YYYY-MM-DD for timeseries start/end
- Historical/gridded datatypes: 'rainfall', 'temperature' (with aggregation), 'relative_humidity', 'spi', 'ndvi_modis', 'ignition_probability'
- Production values for rainfall: 'new' (1990-present) or 'legacy' (1920-2012)
"""

app = Server("hcdp-mcp-server", instructions=SERVER_INSTRUCTIONS)


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    return get_all_tool_definitions()


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls."""
    client = HCDPClient()

    try:
        result = await dispatch_tool(name, client, arguments)

        # Process the result to handle binary data
        processed_result = result
        if isinstance(result, dict) and "data" in result:
            data_content = result["data"]
            # Check if it's bytes
            if isinstance(data_content, bytes):
                # Base64 encode binary data
                processed_result["data"] = base64.b64encode(data_content).decode(
                    "utf-8"
                )
                processed_result["encoding"] = "base64"
                processed_result["media_type"] = (
                    "application/octet-stream"  # Generic binary
                )

                # Try to guess specific type based on tool name
                if "raster" in name:
                    processed_result["media_type"] = "image/tiff"
                elif "zip" in str(arguments.get("zipName", "")):
                    processed_result["media_type"] = "application/zip"

        return [
            TextContent(
                type="text",
                text=json.dumps(processed_result, indent=2, default=str),
            )
        ]

    except Exception as e:
        return [TextContent(type="text", text=f"Error calling HCDP API: {str(e)}")]


async def main():
    """Main entry point for the server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="hcdp-mcp-server",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def cli_main():
    """Entry point for the CLI script."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
