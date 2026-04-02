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
    description="""Access real-time weather station (mesonet) measurements.

USAGE NOTES (discovered during live testing):

1. SORT ORDER DEPENDS ON end_date
   - WITH end_date:    results are ASCENDING  (oldest first). offset=0 = earliest record.
   - WITHOUT end_date: results are DESCENDING (newest first). offset=0 = most recent record.
   Omit end_date when you want the latest reading.

2. PATTERN FOR MOST RECENT READING
   To get the latest value for a station/variable, use:
     start_date = today's date, end_date = (omit), limit = 1, offset = 0
   This returns the single most recent 5-minute reading (~20–25 min behind real time).

3. DATA LAG ~20–25 MINUTES
   Mesonet data is near-real-time, not live. Expect the most recent record to be
   approximately 20–30 minutes behind the current clock time.

4. MICROCLIMATE ACCURACY
   get_city_current_weather averages stations within ~15 km of a city centre.
   For valleys or microclimates (e.g., Mānoa), use get_mesonet_stations to find
   the nearest individual station and query it directly with get_mesonet_data.
   Example: Lyon Arboretum (station_id=0501) is the closest station to Mānoa valley.
""",
    inputSchema=GetMesonetDataArgs.model_json_schema(),
)


async def handle(client, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
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
        join_metadata=args.join_metadata
    )
    return result
