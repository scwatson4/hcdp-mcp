"""Tool for getting historical weather patterns for an island."""

import asyncio
from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

from .constants import ISLAND_EXTENTS, ISLAND_REPRESENTATIVE_POINTS


class GetIslandHistoryArgs(BaseModel):
    """Arguments for island history summary."""
    island: str = Field(description="Island name: 'oahu', 'big_island', 'maui', 'kauai', 'molokai', 'lanai'")
    datatype: str = Field(description="Variable: 'rainfall', 'temperature'")
    year: str = Field(description="Year to summarize, e.g. '2024'")


tool_definition = Tool(
    name="get_island_history_summary",
    description="""Get historical weather patterns for an entire island (Parallelized).

    Fetches history for ~5 representative locations (Windward, Leeward, Mauka, Makai) simultaneously.
    Use this for: "Rainfall patterns for Oahu in 2024" or "Where was it hottest on Maui last year?"
    """,
    inputSchema=GetIslandHistoryArgs.model_json_schema(),
)


async def handle(client, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_island_history_summary tool call."""
    args = GetIslandHistoryArgs(**arguments)
    target_island = args.island.lower()
    points = ISLAND_REPRESENTATIVE_POINTS.get(target_island)

    if not points:
        raise ValueError(f"Unknown island or no representative points for: {args.island}")

    # Prepare arguments for parallel fetching
    ts_datatype = args.datatype
    production = "new" if ts_datatype == "rainfall" else None
    aggregation = "month" if ts_datatype != "rainfall" else None
    period = "month" if ts_datatype == "rainfall" else None
    if ts_datatype == "temperature": ts_datatype = "temp_mean"
    if ts_datatype == "precipitation": ts_datatype = "rainfall"

    start_date = f"{args.year}-01-01"
    end_date = f"{args.year}-12-31"
    island_code = ISLAND_EXTENTS.get(target_island, "statewide")

    # Create tasks (Parallel Fetching!)
    tasks = []
    location_names = []

    for loc_name, coords in points.items():
        location_names.append(loc_name)
        tasks.append(client.get_timeseries_data(
            datatype=ts_datatype,
            start=start_date,
            end=end_date,
            lat=coords["lat"],
            lng=coords["lng"],
            extent=island_code,
            production=production,
            aggregation=aggregation,
            period=period
        ))

    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    point_summaries = []
    all_vals = []

    for i, res in enumerate(results):
        loc_name = location_names[i]
        if isinstance(res, Exception):
            point_summaries.append({
                "location": loc_name,
                "error": str(res)
            })
            continue

        if res and isinstance(res, dict) and len(res) > 0:
            try:
                vals = list(res.values())
                valid_vals = [v for v in vals if v is not None and v != -9999]
                if valid_vals:
                    avg = sum(valid_vals) / len(valid_vals)
                    point_summaries.append({
                        "location": loc_name,
                        "average": round(avg, 2),
                        "min": min(valid_vals),
                        "max": max(valid_vals),
                        "data_points": len(valid_vals)
                    })
                    all_vals.extend(valid_vals)
                else:
                    point_summaries.append({"location": loc_name, "message": "No valid data"})
            except Exception as e:
                point_summaries.append({"location": loc_name, "error": str(e)})
        else:
            point_summaries.append({"location": loc_name, "message": "No data returned"})

    # Island-wide aggregation
    island_avg = None
    if all_vals:
        island_avg = sum(all_vals) / len(all_vals)

    return {
        "island": args.island,
        "year": args.year,
        "datatype": args.datatype,
        "island_wide_average": round(island_avg, 2) if island_avg else "N/A",
        "regional_breakdown": point_summaries
    }
