"""Tool for getting city-specific current weather."""

from datetime import datetime, timedelta
from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

from .constants import (
    CITY_LOCATIONS,
    calculate_distance,
    resolve_mesonet_datatype,
    normalize_city_name,
)


class GetCityWeatherArgs(BaseModel):
    """Arguments for city-specific weather."""

    city: str = Field(
        description="City/town name in snake_case (e.g. 'honolulu', 'manoa', 'kaneohe', 'lahaina')"
    )
    datatype: str = Field(
        description="Mesonet variable: friendly name ('temperature','rainfall','humidity','wind','solar') or raw var_id ('Tair_1_Avg')"
    )


tool_definition = Tool(
    name="get_city_current_weather",
    description=(
        "Current weather for a named city or town. Averages nearby mesonet stations within 15km. "
        "For microclimate accuracy (valleys, uplands), use get_mesonet_stations to find the nearest "
        "station and query it directly with get_mesonet_data."
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

    # Resolve user-friendly datatype to mesonet variable ID
    var_id = resolve_mesonet_datatype(args.datatype)

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

    # 4. Aggregate: filter records matching var_id and collect numeric values
    vals = []
    if isinstance(measurements, list):
        for m in measurements:
            if m.get("variable") != var_id:
                continue
            try:
                vals.append(float(m.get("value")))
            except (ValueError, TypeError):
                continue

    station_ids = [s["station_id"] for s in nearby_stations]

    if not vals:
        return {
            "city": args.city,
            "stations_found": len(nearby_stations),
            "message": f"Found {len(nearby_stations)} stations but no recent data for {args.datatype} ({var_id})",
        }

    avg_val = sum(vals) / len(vals)
    return {
        "city": args.city,
        "date": today,
        "datatype": args.datatype,
        "var_id": var_id,
        "average": round(avg_val, 2),
        "min": round(min(vals), 2),
        "max": round(max(vals), 2),
        "station_count": len(nearby_stations),
        "reading_count": len(vals),
        "stations_used": station_ids,
    }
