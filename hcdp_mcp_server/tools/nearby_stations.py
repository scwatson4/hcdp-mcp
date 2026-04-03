"""Tool for finding the nearest mesonet stations to a location."""

from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

from .constants import calculate_distance


class GetNearbyStationsArgs(BaseModel):
    """Arguments for finding nearby stations."""

    lat: float = Field(description="Latitude of the target location")
    lng: float = Field(description="Longitude of the target location")
    limit: int = Field(
        default=3,
        description="Number of nearest stations to return (default 3)",
    )


tool_definition = Tool(
    name="get_nearby_stations",
    description=(
        "Find the nearest mesonet weather stations to a lat/lng coordinate. "
        "Returns stations sorted by distance with station_ids ready for use with get_mesonet_data."
    ),
    inputSchema=GetNearbyStationsArgs.model_json_schema(),
)


async def handle(
    client, arguments: dict
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_nearby_stations tool call."""
    args = GetNearbyStationsArgs(**arguments)

    stations = await client.get_mesonet_stations()

    # Calculate distance to each station and sort
    station_distances = []
    for station in stations:
        try:
            slat = float(station["lat"])
            slng = float(station["lng"])
            dist = calculate_distance(args.lat, args.lng, slat, slng)
            station_distances.append(
                {
                    "station_id": station["station_id"],
                    "name": station.get("name", ""),
                    "distance_km": round(dist, 2),
                    "lat": station["lat"],
                    "lng": station["lng"],
                    "elevation": station.get("elevation", ""),
                    "status": station.get("status", ""),
                }
            )
        except (ValueError, KeyError, TypeError):
            continue

    # Sort by distance and take the closest N
    station_distances.sort(key=lambda s: s["distance_km"])
    nearest = station_distances[: args.limit]

    return {
        "location": {"lat": args.lat, "lng": args.lng},
        "stations": nearest,
        "note": (
            "Stations beyond 5km may not be representative of the target location. "
            "Prefer using only the closest 1-2 stations for neighborhood-level accuracy."
        ),
    }
