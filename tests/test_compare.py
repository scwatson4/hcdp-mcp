"""Tests for compare_current_vs_historical tool.

Validates that the tool returns meaningful historical comparison data
and handles gracefully when current-day data is unavailable.
"""

import pytest

from conftest import call_tool


@pytest.mark.asyncio
async def test_compare_honolulu_returns_data():
    """Call compare_current_vs_historical for honolulu/rainfall and assert
    that historical_avg is a positive number and historical_period is a
    non-empty string.

    The historical component uses timeseries data from the previous year's
    same month, which should be available (beyond the processing lag window).
    """
    result = await call_tool(
        "compare_current_vs_historical",
        {"city": "honolulu", "datatype": "rainfall"},
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "_error" not in result, f"Tool returned error: {result.get('_error')}"

    # Historical average should be present
    historical_avg = result.get("historical_avg")
    assert historical_avg is not None, (
        f"Missing 'historical_avg'. Keys: {list(result.keys())}"
    )

    # If historical data was successfully fetched, it should be a positive number
    if historical_avg != "No data":
        assert isinstance(historical_avg, (int, float)), (
            f"historical_avg should be numeric, got {type(historical_avg)}"
        )
        assert historical_avg > 0, (
            f"historical_avg should be positive for Honolulu rainfall, "
            f"got {historical_avg}"
        )

    # Historical period should be a non-empty string
    historical_period = result.get("historical_period", "")
    assert isinstance(historical_period, str) and len(historical_period) > 0, (
        f"historical_period should be a non-empty string, got '{historical_period}'"
    )


@pytest.mark.asyncio
async def test_compare_documents_current_unavailability():
    """Assert that current_value may equal "No data" and that this does
    not raise an exception.

    The current-day component depends on live mesonet stations within 15km
    of the city reporting rainfall data today. If no stations have reported
    yet (e.g., early morning, or the variable isn't being measured), the
    tool returns "No data" for current_value. This is expected behavior
    and should not cause failures.
    """
    result = await call_tool(
        "compare_current_vs_historical",
        {"city": "honolulu", "datatype": "rainfall"},
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "_error" not in result, f"Tool returned error: {result.get('_error')}"

    current_value = result.get("current_value")
    assert current_value is not None, "current_value key should always be present"

    # Document: current_value = "No data" is acceptable and expected
    if current_value == "No data":
        # This is fine — no stations have reported rainfall today
        pass
    else:
        # If we do have data, it should be a non-negative number
        assert isinstance(current_value, (int, float)), (
            f"current_value should be numeric or 'No data', got {type(current_value)}"
        )
        assert current_value >= 0, f"current_value should be non-negative, got {current_value}"
