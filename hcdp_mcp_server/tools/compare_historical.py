"""Tool for comparing current weather to historical averages."""

from datetime import datetime, timedelta
from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

from .constants import (
    CITY_LOCATIONS,
    MAJOR_CITIES,
    ISLAND_EXTENTS,
    calculate_distance,
    validate_mesonet_datatype,
    normalize_city_name,
)


class CompareHistoryArgs(BaseModel):
    """Arguments for comparing current vs historical weather."""

    city: str = Field(
        description=(
            "Major city name in snake_case. Supported: "
            "honolulu, hilo, kona, kahului, lihue, kapolei, kaunakakai, pago_pago."
        )
    )
    datatype: str = Field(
        description="Variable: 'temperature', 'rainfall', or 'humidity'. Mapped to API names internally."
    )


tool_definition = Tool(
    name="compare_current_vs_historical",
    description="Compare today's city weather to the same month last year. Returns the difference from historical average.",
    inputSchema=CompareHistoryArgs.model_json_schema(),
)


async def handle(
    client, arguments: dict
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle compare_current_vs_historical tool call."""
    args = CompareHistoryArgs(**arguments)
    city_key = normalize_city_name(args.city)
    city_data = CITY_LOCATIONS.get(city_key)
    if not city_data:
        raise ValueError(f"Unknown location: {args.city}")

    if city_key not in MAJOR_CITIES:
        raise ValueError(
            f"'{args.city}' is a neighborhood/small town. "
            f"compare_current_vs_historical only supports major cities: "
            f"{', '.join(sorted(MAJOR_CITIES))}."
        )

    resolved_var = validate_mesonet_datatype(args.datatype)

    # 1. Get Current Data
    stations = await client.get_mesonet_stations()
    nearby_stations = []
    for station in stations:
        try:
            dist = calculate_distance(
                city_data["lat"],
                city_data["lng"],
                float(station["lat"]),
                float(station["lng"]),
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
            var_ids=[resolved_var],
            limit=100,
        )
        vals = []
        for m in measurements:
            if resolved_var in m:
                try:
                    vals.append(float(m[resolved_var]))
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
    if args.datatype == "temperature":
        ts_datatype = "temp_mean"
    if args.datatype == "precipitation":
        ts_datatype = "rainfall"

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
            period="month" if ts_datatype == "rainfall" else None,
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
        "current_value": (
            round(current_val, 2) if current_val is not None else "No data"
        ),
        "historical_avg": (
            round(historical_val, 2) if historical_val is not None else "No data"
        ),
        "historical_period": f"{start_date} to {end_date}",
        "comparison": "N/A",
    }

    if current_val is not None and historical_val is not None:
        diff = current_val - historical_val
        sign = "+" if diff > 0 else ""
        result["comparison"] = f"{sign}{diff:.2f} difference from historical average"
        result["details"] = (
            f"Current ({round(current_val, 1)}) is "
            f"{'higher' if diff > 0 else 'lower'} than historical ({round(historical_val, 1)})"
        )

    return result
