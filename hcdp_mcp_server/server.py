"""HCDP MCP Server - Main server implementation."""

import asyncio
import json
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from pydantic import BaseModel, Field
from .client import HCDPClient


class GetClimateRasterArgs(BaseModel):
    """Arguments for getting climate raster data."""
    datatype: str = Field(description="Climate data type (e.g., 'rainfall', 'temp_mean', 'temp_min', 'temp_max', 'rh')")
    date: str = Field(description="Date in YYYY-MM-DD format")
    extent: str = Field(description="Spatial extent (e.g., 'statewide', 'oahu', 'big_island')")
    location: str = Field(default="hawaii", description="Location ('hawaii' or 'american_samoa')")
    production: str | None = Field(default=None, description="Production level (for rainfall data)")
    aggregation: str | None = Field(default=None, description="Temporal aggregation (for temperature data)")
    timescale: str | None = Field(default=None, description="Timescale (for SPI data)")
    period: str | None = Field(default=None, description="Period specification")


class GetTimeseriesArgs(BaseModel):
    """Arguments for getting time series data."""
    datatype: str = Field(description="Climate data type")
    start: str = Field(description="Start date in YYYY-MM-DD format")
    end: str = Field(description="End date in YYYY-MM-DD format")
    extent: str = Field(description="Spatial extent")
    lat: float | None = Field(default=None, description="Latitude coordinate (optional)")
    lng: float | None = Field(default=None, description="Longitude coordinate (optional)")
    location: str = Field(default="hawaii", description="Location ('hawaii' or 'american_samoa')")
    production: str | None = Field(default=None, description="Production level (optional)")
    aggregation: str | None = Field(default=None, description="Temporal aggregation (optional)")
    timescale: str | None = Field(default=None, description="Timescale (optional)")
    period: str | None = Field(default=None, description="Period specification (optional)")


class GetStationDataArgs(BaseModel):
    """Arguments for getting station data."""
    q: str = Field(description="Query parameter for station search")
    limit: int | None = Field(default=None, description="Limit number of results (optional)")
    offset: int | None = Field(default=None, description="Offset for pagination (optional)")


class GetMesonetDataArgs(BaseModel):
    """Arguments for getting mesonet data."""
    station_ids: str | None = Field(default=None, description="Comma-separated station IDs (optional)")
    start_date: str | None = Field(default=None, description="Start date in YYYY-MM-DD format (optional)")
    end_date: str | None = Field(default=None, description="End date in YYYY-MM-DD format (optional)")
    var_ids: str | None = Field(default=None, description="Comma-separated variable IDs (optional)")
    location: str = Field(default="hawaii", description="Location")
    intervals: str | None = Field(default=None, description="Time intervals (optional)")
    limit: int | None = Field(default=None, description="Limit number of results (optional)")
    offset: int | None = Field(default=None, description="Offset for pagination (optional)")
    join_metadata: bool = Field(default=True, description="Include metadata in results")


class GenerateDataPackageArgs(BaseModel):
    """Arguments for generating data packages."""
    email: str = Field(description="Email address for package delivery")
    datatype: str = Field(description="Climate data type")
    production: str | None = Field(default=None, description="Production level (optional)")
    period: str | None = Field(default=None, description="Period specification (optional)")
    extent: str | None = Field(default=None, description="Spatial extent (optional)")
    start_date: str | None = Field(default=None, description="Start date (optional)")
    end_date: str | None = Field(default=None, description="End date (optional)")
    files: str | None = Field(default=None, description="Specific files to include (optional)")
    zipName: str | None = Field(default=None, description="Custom zip file name (optional)")


app = Server("hcdp-mcp-server")


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_climate_raster",
            description="Retrieve climate data maps (GeoTIFF files) for specified variables, dates, and locations from HCDP",
            inputSchema=GetClimateRasterArgs.model_json_schema(),
        ),
        Tool(
            name="get_timeseries_data", 
            description="Get time series climate data for a specific latitude/longitude coordinate",
            inputSchema=GetTimeseriesArgs.model_json_schema(),
        ),
        Tool(
            name="get_station_data",
            description="Retrieve station-specific climate measurements and metadata",
            inputSchema=GetStationDataArgs.model_json_schema(),
        ),
        Tool(
            name="get_mesonet_data",
            description="Access real-time weather station (mesonet) measurements",
            inputSchema=GetMesonetDataArgs.model_json_schema(),
        ),
        Tool(
            name="generate_data_package",
            description="Generate downloadable zip packages of climate data with email or instant download options",
            inputSchema=GenerateDataPackageArgs.model_json_schema(),
        ),
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls."""
    client = HCDPClient()
    
    try:
        if name == "get_climate_raster":
            args = GetClimateRasterArgs(**arguments)
            result = await client.get_raster_data(
                datatype=args.datatype,
                date=args.date,
                extent=args.extent,
                location=args.location,
                production=args.production,
                aggregation=args.aggregation,
                timescale=args.timescale,
                period=args.period
            )
            
        elif name == "get_timeseries_data":
            args = GetTimeseriesArgs(**arguments)
            result = await client.get_timeseries_data(
                datatype=args.datatype,
                start=args.start,
                end=args.end,
                extent=args.extent,
                lat=args.lat,
                lng=args.lng,
                location=args.location,
                production=args.production,
                aggregation=args.aggregation,
                timescale=args.timescale,
                period=args.period
            )
            
        elif name == "get_station_data":
            args = GetStationDataArgs(**arguments)
            result = await client.get_station_data(
                q=args.q,
                limit=args.limit,
                offset=args.offset
            )
            
        elif name == "get_mesonet_data":
            args = GetMesonetDataArgs(**arguments)
            result = await client.get_mesonet_data(
                station_ids=args.station_ids,
                start_date=args.start_date,
                end_date=args.end_date,
                var_ids=args.var_ids,
                location=args.location,
                intervals=args.intervals,
                limit=args.limit,
                offset=args.offset,
                join_metadata=args.join_metadata
            )
            
        elif name == "generate_data_package":
            args = GenerateDataPackageArgs(**arguments)
            result = await client.generate_data_package(
                email=args.email,
                datatype=args.datatype,
                production=args.production,
                period=args.period,
                extent=args.extent,
                start_date=args.start_date,
                end_date=args.end_date,
                files=args.files,
                zipName=args.zipName
            )
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
        
    except Exception as e:
        return [TextContent(
            type="text", 
            text=f"Error calling HCDP API: {str(e)}"
        )]


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
                    experimental_capabilities={}
                ),
            ),
        )


def cli_main():
    """Entry point for the CLI script."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()