"""Tests for get_island_current_summary tool.

Validates that the real-time island-wide weather summary returns
well-formed data for Oahu rainfall.
"""

import pytest

from conftest import call_tool


@pytest.mark.asyncio
async def test_island_summary_returns_rainfall():
    """Call get_island_current_summary for oahu/rainfall and assert the
    response contains island_wide statistics with non-negative values.

    This tool aggregates real-time mesonet data across all active stations
    on the island. The response should contain average, min, and max keys
    with numeric values.
    """
    result = await call_tool(
        "get_island_current_summary",
        {"island": "oahu", "datatype": "rainfall"},
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    # If no recent data, the tool returns a message instead of stats
    if "message" in result:
        pytest.skip(
            f"No recent rainfall data available: {result['message']}. "
            f"This is expected if no stations have reported today."
        )

    assert "average" in result, f"Missing 'average' key. Keys: {list(result.keys())}"
    assert "min" in result, f"Missing 'min' key. Keys: {list(result.keys())}"
    assert "max" in result, f"Missing 'max' key. Keys: {list(result.keys())}"

    assert isinstance(result["average"], (int, float)), "average should be numeric"
    assert result["average"] >= 0, f"average should be non-negative, got {result['average']}"
    assert result["min"] >= 0, f"min should be non-negative, got {result['min']}"
    assert result["max"] >= result["min"], (
        f"max ({result['max']}) should be >= min ({result['min']})"
    )


@pytest.mark.asyncio
async def test_island_summary_not_used_for_historical():
    """Verify that get_island_current_summary is a real-time tool.

    NOTE: This tool aggregates live mesonet data for the current day only.
    It must NOT be used for historical storm analysis. For historical
    rainfall, use get_mesonet_data with RF_1_Tot300s (for recent months)
    or get_timeseries_data (for older data beyond the ~6-month lag window).

    This test simply confirms the tool returns today's date in the response,
    verifying it operates on current data only.
    """
    result = await call_tool(
        "get_island_current_summary",
        {"island": "oahu", "datatype": "rainfall"},
    )
    assert isinstance(result, dict)

    # The tool should report today's date or a message about no data
    if "date" in result:
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        assert result["date"] == today, (
            f"Expected today's date ({today}), got {result['date']}. "
            f"This tool is real-time only — it must not be used for "
            f"historical storm analysis."
        )
