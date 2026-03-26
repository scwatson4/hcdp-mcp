"""Tool for getting island-wide weather summaries."""

from datetime import datetime
from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

from .constants import ISLAND_EXTENTS, ISLAND_BOUNDS


class GetIslandSummaryArgs(BaseModel):
    """Arguments for island-wide weather summary."""
    island: str = Field(description="Island name: 'oahu', 'big_island', 'maui', 'kauai', 'molokai', 'lanai'")
    datatype: str = Field(description="Variable to summarize (e.g., 'temperature', 'rainfall', 'humidity')")


tool_definition = Tool(
    name="get_island_current_summary",
    description="""Get a weather summary for an entire island (Average/Min/Max).

    Aggregates real-time data from all active Mesonet stations on the island.
    Use this for: "What's the average temperature on Oahu?" or "How much rain on Big Island?"
    """,
    inputSchema=GetIslandSummaryArgs.model_json_schema(),
)


async def handle(client, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_island_current_summary tool call."""
    args = GetIslandSummaryArgs(**arguments)
    # 1. Get all stations
    stations = await client.get_mesonet_stations()
    if "error" in stations:
        raise ValueError(f"Failed to fetch stations: {stations['error']}")

    # 2. Filter by island
    target_island = args.island.lower()
    if target_island not in ISLAND_EXTENTS:
        raise ValueError(f"Unknown island: {target_island}")

    # 3. Get list of station IDs filtered by bounding box
    station_ids = []
    bounds = ISLAND_BOUNDS.get(target_island)
    if not bounds:
        # Fallback: Just take first 20 stations if bounds unknown (e.g. statewide)
        station_ids = [s["station_id"] for s in stations[:20]]
    else:
        lat_min, lat_max, lng_min, lng_max = bounds
        for s in stations:
            try:
                slat, slng = float(s["lat"]), float(s["lng"])
                if lat_min <= slat <= lat_max and lng_min <= slng <= lng_max:
                    station_ids.append(s["station_id"])
            except:
                continue

    if not station_ids:
        return {"error": f"No stations found on {args.island}"}

    # Limit to 50 to avoid timeouts
    station_ids = station_ids[:50]

    # 4. Fetch data
    today = datetime.now().strftime("%Y-%m-%d")
    measurements = await client.get_mesonet_data(
        station_ids=station_ids,
        start_date=today,
        end_date=today,
        var_ids=[args.datatype],
        limit=100
    )

    vals = []
    for m in measurements:
        if args.datatype in m:
            try:
                vals.append(float(m[args.datatype]))
            except:
                continue

    if not vals:
        return {
            "island": args.island,
            "stations_checked": len(station_ids),
            "message": f"No recent data for {args.datatype} found"
        }

    avg_val = sum(vals) / len(vals)
    return {
        "island": args.island,
        "date": today,
        "datatype": args.datatype,
        "average": round(avg_val, 2),
        "min": min(vals),
        "max": max(vals),
        "station_count": len(vals),
        "note": "Averaged from active mesonet stations"
    }
