"""Tool for comparing current weather to historical averages."""

from datetime import datetime, timedelta
from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

from .constants import CITY_LOCATIONS, ISLAND_EXTENTS, calculate_distance


class CompareHistoryArgs(BaseModel):
    """Arguments for comparing current vs historical weather."""
    city: str = Field(description="City name: 'honolulu', 'hilo', 'kona', 'kahului', 'lihue', 'pago_pago'")
    datatype: str = Field(description="Variable to compare (e.g., 'temperature', 'rainfall')")


tool_definition = Tool(
    name="compare_current_vs_historical",
    description="""Compare current weather to historical averages.

    Compares today's Mesonet data (city average) vs. historical Timeseries data (previous year, same month).
    returns the difference (e.g., "+1.5C warmer than normal").
    """,
    inputSchema=CompareHistoryArgs.model_json_schema(),
)


async def handle(client, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle compare_current_vs_historical tool call."""
    args = CompareHistoryArgs(**arguments)
    city_data = CITY_LOCATIONS.get(args.city.lower())
    if not city_data:
        raise ValueError(f"Unknown city: {args.city}")

    # 1. Get Current Data
    stations = await client.get_mesonet_stations()
    nearby_stations = []
    for station in stations:
        try:
            dist = calculate_distance(
                city_data["lat"], city_data["lng"],
                float(station["lat"]), float(station["lng"])
            )
            if dist <= 15:
                nearby_stations.append(station)
        except:
            continue

    current_val = None
    if nearby_stations:
        station_ids = [s["station_id"] for s in nearby_stations]
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
        if vals:
            current_val = sum(vals) / len(vals)

    # 2. Get Historical Data (Timeseries for same month, previous year)
    last_year = datetime.now().replace(year=datetime.now().year - 1)
    start_date = last_year.replace(day=1).strftime("%Y-%m-%d")
    next_month = last_year.replace(day=28) + timedelta(days=4)
    end_date = (next_month - timedelta(days=next_month.day)).strftime("%Y-%m-%d")

    ts_datatype = args.datatype
    if args.datatype == "temperature": ts_datatype = "temp_mean"
    if args.datatype == "precipitation": ts_datatype = "rainfall"

    historical_val = None
    try:
        island_code = ISLAND_EXTENTS.get(city_data["island"], "statewide")
        ts_data = await client.get_timeseries_data(
            datatype=ts_datatype,
            start=start_date,
            end=end_date,
            lat=city_data["lat"],
            lng=city_data["lng"],
            extent=island_code,
            production="new" if ts_datatype == "rainfall" else None,
            aggregation="month" if ts_datatype != "rainfall" else None,
            period="month" if ts_datatype == "rainfall" else None
        )

        if ts_data and len(ts_data) > 0:
            ts_vals = list(ts_data.values())
            historical_val = sum(ts_vals) / len(ts_vals)
    except Exception as e:
        print(f"Historical fetch failed: {e}")

    # 3. Compare
    result = {
        "city": args.city,
        "datatype": args.datatype,
        "current_value": round(current_val, 2) if current_val is not None else "No data",
        "historical_avg": round(historical_val, 2) if historical_val is not None else "No data",
        "historical_period": f"{start_date} to {end_date}",
        "comparison": "N/A"
    }

    if current_val is not None and historical_val is not None:
        diff = current_val - historical_val
        sign = "+" if diff > 0 else ""
        result["comparison"] = f"{sign}{diff:.2f} difference from historical average"
        result["details"] = f"Current ({round(current_val, 1)}) is {'higher' if diff > 0 else 'lower'} than historical ({round(historical_val, 1)})"

    return result
