"""Tool for getting city-specific current weather."""

from datetime import datetime, timedelta
from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

from .constants import CITY_LOCATIONS, calculate_distance

# Map user-friendly datatype names to mesonet variable IDs
DATATYPE_TO_VAR_ID = {
    "temperature": "Tair_1_Avg",
    "rainfall": "RF_1_Tot300s",
}


class GetCityWeatherArgs(BaseModel):
    """Arguments for city-specific weather."""
    city: str = Field(description="City name: 'honolulu', 'hilo', 'kona', 'kahului', 'lihue', 'pago_pago'")
    datatype: str = Field(description="Variable to retrieve (e.g., 'temperature', 'rainfall')")


tool_definition = Tool(
    name="get_city_current_weather",
    description="""Get aggregated current weather for a specific city.

    Finds stations within ~15km of the city centre and averages their readings.
    Supported cities: Honolulu, Hilo, Kona, Kahului, Lihue, Kaunakakai, Lanai City, Pago Pago.

    LIMITATION — MICROCLIMATE ACCURACY:
    The 15 km radius average can obscure local microclimates. For precise readings
    in valleys or upland areas (e.g., Mānoa, Nuuanu), call get_mesonet_stations,
    filter to the nearest station by coordinates, and query it directly with
    get_mesonet_data (omit end_date, limit=1 for the most recent reading).
    Example: Lyon Arboretum (station_id=0501, lat=21.333, lng=-157.8025) gives
    a far more accurate reading for Mānoa valley than the Honolulu city average.
    """,
    inputSchema=GetCityWeatherArgs.model_json_schema(),
)


async def handle(client, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_city_current_weather tool call."""
    args = GetCityWeatherArgs(**arguments)
    city_data = CITY_LOCATIONS.get(args.city.lower())
    if not city_data:
        raise ValueError(f"Unknown city: {args.city}")

    # Resolve user-friendly datatype to mesonet variable ID
    var_id = DATATYPE_TO_VAR_ID.get(args.datatype.lower(), args.datatype)

    # 1. Get all stations
    stations = await client.get_mesonet_stations()

    # 2. Find nearby stations (within 15 km)
    nearby_stations = []
    for station in stations:
        try:
            dist = calculate_distance(
                city_data["lat"], city_data["lng"],
                float(station["lat"]), float(station["lng"])
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
            "message": f"Found {len(nearby_stations)} stations but no recent data for {args.datatype} ({var_id})"
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
