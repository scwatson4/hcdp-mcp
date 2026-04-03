"""Tests for get_station_data tool.

Validates that station queries return results for the two ground-truth
stations used in the storm validation suite.

NOTE on /stations query format:
  The HCDP /stations endpoint requires a Python-dict-style (single-quoted)
  MongoDB query, NOT standard JSON.  There are exactly two valid document
  type names:
    {'name': 'hcdp_station_metadata'} — all station metadata (filter client-side)
    {'name': 'hcdp_station_value', ...} — measurement records filtered by value.*

  Server-side name search is not supported; the caller must fetch all metadata
  and filter locally.
"""

import pytest

from conftest import call_tool


def _find_by_name(stations: list, substring: str) -> list:
    """Return stations where any string field contains substring (case-insensitive)."""
    sub = substring.lower()
    return [
        s for s in stations
        if any(sub in str(v).lower() for v in s.values() if v is not None)
    ]


@pytest.mark.asyncio
async def test_station_data_lyon():
    """Fetch all station metadata and assert at least one record matches
    Lyon Arboretum (station 0501).

    The /stations endpoint does not support server-side text search; we query
    all metadata with {'name': 'hcdp_station_metadata'} and filter locally.

    Lyon Arboretum is one of the wettest locations in Honolulu, situated
    in Manoa Valley at 151m elevation. It is a key reference station for
    the March 2026 storm validation.
    """
    result = await call_tool(
        "get_station_data", {"q": "{'name': 'hcdp_station_metadata'}"}
    )

    if isinstance(result, dict) and "_error" in result:
        pytest.fail(f"Station metadata query returned error: {result['_error']}")

    stations = result.get("result", result) if isinstance(result, dict) else result
    assert isinstance(stations, list) and len(stations) > 0, (
        f"Station metadata returned no results. Raw: {str(result)[:200]}"
    )

    lyon_stations = _find_by_name(stations, "lyon")
    assert len(lyon_stations) > 0, (
        f"No station matching 'Lyon' found in {len(stations)} metadata records"
    )


@pytest.mark.asyncio
async def test_station_data_nuuanu():
    """Fetch all station metadata and assert at least one record matches
    Nuuanu Reservoir 1 (station 0502).

    Nuuanu Res 1 sits at 117m elevation in Nuuanu Valley, another
    historically wet corridor on windward Oahu. It serves as the second
    reference station for ground-truth storm validation.
    """
    result = await call_tool(
        "get_station_data", {"q": "{'name': 'hcdp_station_metadata'}"}
    )

    if isinstance(result, dict) and "_error" in result:
        pytest.fail(f"Station metadata query returned error: {result['_error']}")

    stations = result.get("result", result) if isinstance(result, dict) else result
    assert isinstance(stations, list) and len(stations) > 0, (
        f"Station metadata returned no results. Raw: {str(result)[:200]}"
    )

    nuuanu_stations = _find_by_name(stations, "nuuanu")
    assert len(nuuanu_stations) > 0, (
        f"No station matching 'Nuuanu' found in {len(stations)} metadata records"
    )
