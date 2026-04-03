"""Tool for getting time series climate data."""

from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field, field_validator

from .constants import resolve_extent_from_coords


class GetTimeseriesArgs(BaseModel):
    """Arguments for getting time series data."""

    datatype: str = Field(
        description="Climate variable: 'rainfall', 'temperature', 'relative_humidity', 'spi', 'ndvi_modis', or 'ignition_probability'. Use aggregation for temperature min/max/mean."
    )
    start: str = Field(description="Start date in YYYY-MM-DD format")
    end: str = Field(description="End date in YYYY-MM-DD format")
    extent: str | None = Field(
        default=None,
        description="Island extent code ('bi','oa','ka','mn','statewide'). Auto-resolved from lat/lng if omitted.",
    )
    lat: float | str | None = Field(default=None, description="Latitude coordinate")
    lng: float | str | None = Field(default=None, description="Longitude coordinate")
    location: str = Field(
        default="hawaii", description="Location ('hawaii' or 'american_samoa')"
    )
    production: str | None = Field(
        default=None,
        description="For rainfall only: 'new' (1990-present) or 'legacy' (1920-2012)",
    )
    aggregation: str | None = Field(
        default=None,
        description="For temperature only: 'min', 'max', or 'mean'",
    )
    timescale: str | None = Field(
        default=None,
        description="For SPI only: e.g. 'timescale001', 'timescale003', 'timescale012'",
    )
    period: str | None = Field(
        default=None, description="Time period: 'month' or 'day'"
    )

    @field_validator("lat", "lng", mode="before")
    @classmethod
    def convert_to_float(cls, v):
        """Convert string coordinates to floats."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return float(v)
        return v


tool_definition = Tool(
    name="get_timeseries_data",
    description="Historical gridded climate data at a specific point. Requires lat and lng coordinates. Returns values over a date range.",
    inputSchema=GetTimeseriesArgs.model_json_schema(),
)


async def handle(
    client, arguments: dict
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_timeseries_data tool call."""
    args = GetTimeseriesArgs(**arguments)

    # Auto-resolve extent from coordinates if not provided
    if args.extent is None and args.lat is not None and args.lng is not None:
        args.extent = resolve_extent_from_coords(float(args.lat), float(args.lng))
    elif args.extent is None:
        args.extent = "statewide"

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
        period=args.period,
    )
    return result
