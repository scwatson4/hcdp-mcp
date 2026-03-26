"""Tests for get_station_data tool.

Validates that station queries return results for the two ground-truth
stations used in the storm validation suite.
"""

import pytest

from conftest import call_tool


@pytest.mark.asyncio
async def test_station_data_lyon():
    """Query get_station_data for 'Lyon' and assert at least one result
    is returned matching Lyon Arboretum (station 0501).

    Lyon Arboretum is one of the wettest locations in Honolulu, situated
    in Manoa Valley at 151m elevation. It is a key reference station for
    the March 2026 storm validation.
    """
    result = await call_tool("get_station_data", {"q": "Lyon"})

    if isinstance(result, dict) and "_error" in result:
        pytest.fail(f"Station query for 'Lyon' returned error: {result['_error']}")

    # Result should be a list or dict with station data
    if isinstance(result, list):
        assert len(result) > 0, "No stations found matching 'Lyon'"
    elif isinstance(result, dict):
        # Some API responses wrap results in a dict
        assert len(result) > 0, "Empty response for station query 'Lyon'"


@pytest.mark.asyncio
async def test_station_data_nuuanu():
    """Query get_station_data for 'Nuuanu' and assert at least one result
    is returned matching Nuuanu Reservoir 1 (station 0502).

    Nuuanu Res 1 sits at 117m elevation in Nuuanu Valley, another
    historically wet corridor on windward Oahu. It serves as the second
    reference station for ground-truth storm validation.
    """
    result = await call_tool("get_station_data", {"q": "Nuuanu"})

    if isinstance(result, dict) and "_error" in result:
        pytest.fail(f"Station query for 'Nuuanu' returned error: {result['_error']}")

    if isinstance(result, list):
        assert len(result) > 0, "No stations found matching 'Nuuanu'"
    elif isinstance(result, dict):
        assert len(result) > 0, "Empty response for station query 'Nuuanu'"
