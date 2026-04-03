"""Tool for accessing real-time mesonet weather data."""

from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field


class GetMesonetDataArgs(BaseModel):
    """Arguments for getting mesonet data."""

    station_ids: str | None = Field(
        default=None, description="Comma-separated station IDs (e.g. '0145,0141')"
    )
    start_date: str | None = Field(
        default=None, description="Start date in YYYY-MM-DD format"
    )
    end_date: str | None = Field(
        default=None, description="End date in YYYY-MM-DD format"
    )
    var_ids: str | None = Field(
        default=None,
        description="Comma-separated mesonet variable IDs (e.g. 'Tair_1_Avg,RH_1_Avg'). Use get_mesonet_variables to list valid IDs.",
    )
    location: str = Field(
        default="hawaii", description="Location ('hawaii' or 'american_samoa')"
    )
    intervals: str | None = Field(default=None, description="Time intervals")
    limit: int | None = Field(
        default=None,
        description="Max records to return. Applies across ALL stations and variables combined. For N stations with M var_ids, use limit >= N*M.",
    )
    offset: int | None = Field(default=None, description="Offset for pagination")
    join_metadata: bool = Field(default=True, description="Include metadata in results")


tool_definition = Tool(
    name="get_mesonet_data",
    description="""Fetch real-time mesonet measurements by station ID, date range, and variable. Use get_mesonet_variables to discover valid var_ids.

USAGE NOTES:
- WITHOUT end_date: results are DESCENDING (newest first). For latest reading: start_date=today, no end_date, limit=1.
- WITH end_date: results are ASCENDING (oldest first).
- Data lags real time by ~20-25 minutes.
- For recent rainfall, use RF_1_Tot300s (5-min totals), NOT RF_1_Tot86400s (daily aggregate, often empty for recent dates).
""",
    inputSchema=GetMesonetDataArgs.model_json_schema(),
)


async def handle(
    client, arguments: dict
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_mesonet_data tool call.

    Sort-order behaviour (live-tested 2026-04-01):
      - end_date provided  → ascending  (offset=0 = oldest record in window)
      - end_date omitted   → descending (offset=0 = most recent record available)

    For current conditions use: start_date=today, no end_date, limit=1, offset=0.
    Data lags real time by ~20–25 minutes.
    """
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
        join_metadata=args.join_metadata,
    )
    return result
