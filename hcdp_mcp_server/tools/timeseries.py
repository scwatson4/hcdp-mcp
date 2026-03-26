"""Tool for getting time series climate data."""

from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field, field_validator


class GetTimeseriesArgs(BaseModel):
    """Arguments for getting time series data."""
    datatype: str = Field(description="Climate data type")
    start: str = Field(description="Start date in YYYY-MM-DD format")
    end: str = Field(description="End date in YYYY-MM-DD format")
    extent: str = Field(description="Spatial extent code: 'bi' (Big Island/Hawaii County), 'oa' (Oahu/Honolulu County), 'ka' (Kauai County), 'mn' (Maui County), or 'statewide' (all islands)")
    lat: float | str | None = Field(default=None, description="Latitude coordinate (optional)")
    lng: float | str | None = Field(default=None, description="Longitude coordinate (optional)")
    location: str = Field(default="hawaii", description="Location ('hawaii' or 'american_samoa')")
    production: str | None = Field(default=None, description="Production level (optional)")
    aggregation: str | None = Field(default=None, description="Temporal aggregation (optional)")
    timescale: str | None = Field(default=None, description="Timescale (optional)")
    period: str | None = Field(default=None, description="Period specification (optional)")

    @field_validator('lat', 'lng', mode='before')
    @classmethod
    def convert_to_float(cls, v):
        """Convert string coordinates to floats."""
        if v is None or v == '':
            return None
        if isinstance(v, str):
            return float(v)
        return v


tool_definition = Tool(
    name="get_timeseries_data",
    description="""Get time series climate data for specific coordinates.

    REQUIRED: You MUST provide 'lat' and 'lng' arguments.
    DO NOT provide 'extent' (e.g., 'oa', 'bi') - this tool works on specific points only.

    Use this for: "History for Hilo", "Trends at 21.3, -157.8", "Temperature for Honolulu".
    """,
    inputSchema=GetTimeseriesArgs.model_json_schema(),
)


async def handle(client, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_timeseries_data tool call."""
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
    return result
