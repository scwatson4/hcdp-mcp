"""Tests for get_nearby_stations tool.

Validates that the nearby stations tool correctly finds and sorts
mesonet stations by Haversine distance from a target coordinate.
"""

import pytest

from conftest import MANOA_LAT, MANOA_LNG, call_tool


@pytest.mark.asyncio
async def test_nearby_manoa_finds_lyon():
    """Call get_nearby_stations near Manoa and assert station 0501
    (Lyon Arboretum) appears in the results.

    Lyon Arboretum (lat=21.333, lng=-157.8025) is located in upper
    Manoa Valley and should be < 1km from the Manoa test coordinates.
    """
    result = await call_tool(
        "get_nearby_stations",
        {"lat": MANOA_LAT, "lng": MANOA_LNG, "limit": 5},
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "stations" in result, f"Missing 'stations' key. Keys: {list(result.keys())}"

    station_ids = [s["station_id"] for s in result["stations"]]
    assert "0501" in station_ids, (
        f"Station 0501 (Lyon Arboretum) not found near Manoa coordinates. "
        f"Returned stations: {station_ids}"
    )


@pytest.mark.asyncio
async def test_nearby_returns_correct_limit():
    """Assert get_nearby_stations respects the limit parameter."""
    for limit in [1, 2, 3]:
        result = await call_tool(
            "get_nearby_stations",
            {"lat": MANOA_LAT, "lng": MANOA_LNG, "limit": limit},
        )
        stations = result["stations"]
        assert len(stations) == limit, f"Expected {limit} stations, got {len(stations)}"


@pytest.mark.asyncio
async def test_nearby_distances_sorted():
    """Assert returned stations are sorted by distance_km ascending."""
    result = await call_tool(
        "get_nearby_stations",
        {"lat": MANOA_LAT, "lng": MANOA_LNG, "limit": 5},
    )
    stations = result["stations"]
    distances = [s["distance_km"] for s in stations]
    assert distances == sorted(
        distances
    ), f"Stations not sorted by distance: {distances}"


@pytest.mark.asyncio
async def test_nearby_response_structure():
    """Assert response has the expected keys and station fields."""
    result = await call_tool(
        "get_nearby_stations",
        {"lat": MANOA_LAT, "lng": MANOA_LNG, "limit": 3},
    )

    # Top-level keys
    assert "location" in result
    assert "stations" in result
    assert "note" in result

    # Location echoes back the query coordinates
    assert result["location"]["lat"] == MANOA_LAT
    assert result["location"]["lng"] == MANOA_LNG

    # Each station has required fields
    for station in result["stations"]:
        for field in ["station_id", "name", "distance_km", "lat", "lng"]:
            assert field in station, f"Station missing field '{field}': {station}"
        # distance should be non-negative
        assert station["distance_km"] >= 0


@pytest.mark.asyncio
async def test_nearby_lyon_distance_under_1km():
    """Assert Lyon Arboretum is within 1km of the Manoa test coordinates.

    The Manoa test coordinates (21.3330, -157.8025) are essentially at
    Lyon Arboretum, so the distance should be very small.
    """
    result = await call_tool(
        "get_nearby_stations",
        {"lat": MANOA_LAT, "lng": MANOA_LNG, "limit": 5},
    )
    lyon = next((s for s in result["stations"] if s["station_id"] == "0501"), None)
    assert lyon is not None, "Station 0501 (Lyon Arboretum) not found"
    assert lyon["distance_km"] < 1.0, (
        f"Lyon Arboretum distance {lyon['distance_km']}km should be < 1km "
        f"from Manoa coordinates"
    )
