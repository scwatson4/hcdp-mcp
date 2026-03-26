"""Tool for accessing real-time mesonet weather data."""

from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field


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


tool_definition = Tool(
    name="get_mesonet_data",
    description="Access real-time weather station (mesonet) measurements",
    inputSchema=GetMesonetDataArgs.model_json_schema(),
)


async def handle(client, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_mesonet_data tool call."""
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
    return result
