"""Tests for get_island_history_summary tool.

Validates historical rainfall patterns for Oahu using the parallelized
multi-point timeseries approach.
"""

import pytest

from conftest import call_tool


@pytest.mark.asyncio
async def test_history_summary_2026_oahu():
    """Call get_island_history_summary for oahu/rainfall/2026 and assert
    the response contains regional breakdown entries with a positive
    island-wide average.

    This tool fetches timeseries data for ~5 representative locations
    on the island in parallel. The response should contain a regional
    breakdown list and an island-wide average.
    """
    result = await call_tool(
        "get_island_history_summary",
        {"island": "oahu", "datatype": "rainfall", "year": "2026"},
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    assert "regional_breakdown" in result, (
        f"Missing 'regional_breakdown'. Keys: {list(result.keys())}"
    )
    breakdown = result["regional_breakdown"]
    assert isinstance(breakdown, list), "regional_breakdown should be a list"
    assert len(breakdown) > 0, "regional_breakdown is empty"

    # At least some locations should have data
    locations_with_data = [
        entry for entry in breakdown if "average" in entry
    ]
    assert len(locations_with_data) > 0, (
        f"No locations returned data. All entries: {breakdown}"
    )

    # Island-wide average should be a positive number (it rains in Hawaii)
    avg = result.get("island_wide_average")
    if avg != "N/A":
        assert isinstance(avg, (int, float)), f"island_wide_average should be numeric, got {type(avg)}"
        assert avg > 0, f"island_wide_average should be positive for Oahu rainfall, got {avg}"


@pytest.mark.asyncio
async def test_history_summary_windward_wetter():
    """Assert that the Windward/Kaneohe region receives more rainfall than
    the Leeward/Kapolei region for Oahu in 2026.

    This is a physical sanity check: the windward (northeast) side of Oahu
    consistently receives more orographic rainfall than the leeward
    (southwest) side due to prevailing trade winds hitting the Koolau range.
    """
    result = await call_tool(
        "get_island_history_summary",
        {"island": "oahu", "datatype": "rainfall", "year": "2026"},
    )

    breakdown = result.get("regional_breakdown", [])
    location_map = {entry.get("location", ""): entry for entry in breakdown}

    # Find windward and leeward entries
    windward = location_map.get("Kaneohe (Windward)", {})
    leeward = location_map.get("Kapolei (Leeward)", {})

    windward_avg = windward.get("average")
    leeward_avg = leeward.get("average")

    if windward_avg is None or leeward_avg is None:
        pytest.skip(
            "Missing data for Windward or Leeward locations. "
            f"Windward: {windward}, Leeward: {leeward}"
        )

    assert windward_avg > leeward_avg, (
        f"Physical sanity check failed: Windward/Kaneohe ({windward_avg}mm) "
        f"should receive more rainfall than Leeward/Kapolei ({leeward_avg}mm) "
        f"due to orographic effects from trade winds."
    )
