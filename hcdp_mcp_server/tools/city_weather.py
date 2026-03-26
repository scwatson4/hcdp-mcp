"""Tool for getting city-specific current weather."""

from datetime import datetime
from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

from .constants import CITY_LOCATIONS, calculate_distance


class GetCityWeatherArgs(BaseModel):
    """Arguments for city-specific weather."""
    city: str = Field(description="City name: 'honolulu', 'hilo', 'kona', 'kahului', 'lihue', 'pago_pago'")
    datatype: str = Field(description="Variable to retrieve (e.g., 'temperature', 'rainfall')")


tool_definition = Tool(
    name="get_city_current_weather",
    description="""Get aggregated current weather for a specific city.

    Finds stations within ~15km of the city and averages their data.
    Supported cities: Honolulu, Hilo, Kona, Kahului, Lihue, Kaunakakai, Lanai City, Pago Pago.
    """,
    inputSchema=GetCityWeatherArgs.model_json_schema(),
)


async def handle(client, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_city_current_weather tool call."""
    args = GetCityWeatherArgs(**arguments)
    city_data = CITY_LOCATIONS.get(args.city.lower())
    if not city_data:
        raise ValueError(f"Unknown city: {args.city}")

    # 1. Get all stations
    stations = await client.get_mesonet_stations()

    # 2. Find nearby stations
    nearby_stations = []
    for station in stations:
        try:
            dist = calculate_distance(
                city_data["lat"], city_data["lng"],
                float(station["lat"]), float(station["lng"])
            )
            if dist <= 15:  # within 15km
                nearby_stations.append(station)
        except (ValueError, KeyError, TypeError):
            continue

    if not nearby_stations:
        return {"error": f"No weather stations found within 15km of {args.city}"}

    # 3. Get data for these stations
    station_ids = [s["station_id"] for s in nearby_stations]
    today = datetime.now().strftime("%Y-%m-%d")

    measurements = await client.get_mesonet_data(
        station_ids=station_ids,
        start_date=today,
        end_date=today,
        var_ids=[args.datatype],
        limit=100
    )

    # 4. Aggregation
    vals = []
    for m in measurements:
        if args.datatype in m:
            try:
                vals.append(float(m[args.datatype]))
            except:
                continue

    if not vals:
        return {
            "city": args.city,
            "stations_found": len(nearby_stations),
            "message": f"Found {len(nearby_stations)} stations but no recent data for {args.datatype}"
        }

    avg_val = sum(vals) / len(vals)
    return {
        "city": args.city,
        "date": today,
        "datatype": args.datatype,
        "average": round(avg_val, 2),
        "min": min(vals),
        "max": max(vals),
        "station_count": len(vals),
        "stations_used": station_ids
    }
