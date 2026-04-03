"""Tool for getting city-specific current weather."""

from datetime import datetime, timedelta
from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

from .constants import (
    CITY_LOCATIONS,
    calculate_distance,
    validate_mesonet_datatype,
    normalize_city_name,
)


class GetCityWeatherArgs(BaseModel):
    """Arguments for city-specific weather."""

    city: str = Field(
        description="City/town name in snake_case (e.g. 'honolulu', 'manoa', 'kaneohe', 'lahaina')"
    )
    datatype: str = Field(
        description="Mesonet variable: friendly name ('temperature','rainfall','humidity','wind','solar','weather') or raw var_id ('Tair_1_Avg'). Use 'weather' for a multi-variable summary (temperature + humidity + rainfall)."
    )


tool_definition = Tool(
    name="get_city_current_weather",
    description=(
        "Current weather for a named city or town. Averages nearby mesonet stations within 15km. "
        "Use datatype='weather' for a multi-variable summary (temperature, humidity, rainfall). "
        "For neighborhoods or microclimate-sensitive areas (valleys, uplands), prefer using "
        "get_mesonet_stations to find the 1-3 closest stations, then query them directly with "
        "get_mesonet_data for more accurate readings."
    ),
    inputSchema=GetCityWeatherArgs.model_json_schema(),
)


async def handle(
    client, arguments: dict
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_city_current_weather tool call."""
    args = GetCityWeatherArgs(**arguments)
    city_key = normalize_city_name(args.city)
    city_data = CITY_LOCATIONS.get(city_key)
    if not city_data:
        raise ValueError(f"Unknown city: {args.city}")

    # Resolve user-friendly datatype to mesonet variable ID(s)
    var_id = validate_mesonet_datatype(args.datatype)
    var_id_list = [v.strip() for v in var_id.split(",")]

    # 1. Get all stations
    stations = await client.get_mesonet_stations()

    # 2. Find nearby stations (within 15 km)
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
        except (ValueError, KeyError, TypeError):
            continue

    if not nearby_stations:
        return {"error": f"No weather stations found within 15km of {args.city}"}

    # 3. Query today's data; use tomorrow as end_date so the API returns
    #    records through the current moment (API returns up to end_date 00:00 UTC)
    station_ids_str = ",".join(s["station_id"] for s in nearby_stations)
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    measurements = await client.get_mesonet_data(
        station_ids=station_ids_str,
        start_date=today,
        end_date=tomorrow,
        var_ids=var_id,
        limit=1000,
    )

    # 4. Aggregate: group values by variable
    var_vals = {v: [] for v in var_id_list}
    if isinstance(measurements, list):
        for m in measurements:
            mv = m.get("variable")
            if mv in var_vals:
                try:
                    var_vals[mv].append(float(m.get("value")))
                except (ValueError, TypeError):
                    continue

    station_ids = [s["station_id"] for s in nearby_stations]

    # Build per-variable summary
    summary = {}
    for v, vals in var_vals.items():
        if vals:
            summary[v] = {
                "average": round(sum(vals) / len(vals), 2),
                "min": round(min(vals), 2),
                "max": round(max(vals), 2),
                "reading_count": len(vals),
            }

    if not summary:
        return {
            "city": args.city,
            "stations_found": len(nearby_stations),
            "message": f"Found {len(nearby_stations)} stations but no recent data for {args.datatype} ({var_id})",
            "hint": "Valid datatype names: temperature, rainfall, humidity, wind, solar, weather. Or use a raw var_id like 'Tair_1_Avg'.",
        }

    # For single-variable queries, flatten the response for backward compatibility
    if len(var_id_list) == 1:
        single_var = var_id_list[0]
        single_data = summary[single_var]
        return {
            "city": args.city,
            "date": today,
            "datatype": args.datatype,
            "var_id": single_var,
            "average": single_data["average"],
            "min": single_data["min"],
            "max": single_data["max"],
            "station_count": len(nearby_stations),
            "reading_count": single_data["reading_count"],
            "stations_used": station_ids,
        }

    # Multi-variable response
    return {
        "city": args.city,
        "date": today,
        "datatype": args.datatype,
        "variables": summary,
        "station_count": len(nearby_stations),
        "stations_used": station_ids,
    }
