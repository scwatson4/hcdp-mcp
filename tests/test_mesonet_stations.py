"""Tests for get_mesonet_stations tool.

Validates that the mesonet station listing includes the two ground-truth
stations (Lyon Arboretum and Nuuanu Res 1) with correct metadata.
"""

import pytest

from conftest import STATION_NAMES, call_tool


@pytest.mark.asyncio
async def test_stations_exist():
    """Call get_mesonet_stations and assert stations 0501 (Lyon Arboretum) and
    0502 (Nuuanu Res 1) are present with correct names.

    These stations are the ground-truth reference for the March 2026 storm
    validation suite. Their presence and correct naming confirms the API
    station inventory is consistent with the HCDP CSV export.
    """
    result = await call_tool("get_mesonet_stations", {"location": "hawaii"})
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Station list is empty"

    station_map = {s["station_id"]: s for s in result}

    for station_id, expected_name in STATION_NAMES.items():
        assert station_id in station_map, (
            f"Station {station_id} ({expected_name}) not found in mesonet "
            f"station listing. Available IDs: "
            f"{sorted(station_map.keys())[:20]}..."
        )
        station = station_map[station_id]
        assert expected_name.lower() in station.get("name", "").lower(), (
            f"Station {station_id} name mismatch: expected '{expected_name}', "
            f"got '{station.get('name')}'"
        )


@pytest.mark.asyncio
async def test_stations_have_rf_metadata():
    """Assert that both ground-truth stations have non-null elevation, lat,
    and lng fields.

    These metadata fields are required for geographic filtering (e.g., the
    island_summary tool uses bounding boxes) and for validating station
    identity. Null values would break downstream tools.
    """
    result = await call_tool("get_mesonet_stations", {"location": "hawaii"})
    station_map = {s["station_id"]: s for s in result}

    for station_id in STATION_NAMES:
        station = station_map[station_id]

        assert station.get("lat") is not None, (
            f"Station {station_id} has null latitude"
        )
        assert station.get("lng") is not None, (
            f"Station {station_id} has null longitude"
        )
        assert station.get("elevation") is not None, (
            f"Station {station_id} has null elevation"
        )

        # Sanity check: stations should be on Oahu
        lat = float(station["lat"])
        lng = float(station["lng"])
        assert 21.2 < lat < 21.8, f"Station {station_id} lat {lat} not on Oahu"
        assert -158.3 < lng < -157.6, f"Station {station_id} lng {lng} not on Oahu"
