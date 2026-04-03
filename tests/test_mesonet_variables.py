"""Tests for get_mesonet_variables tool.

Validates that the rainfall measurement variables needed for the storm
validation tests are available and have correct units.
"""

import pytest

from conftest import call_tool

RF_VARIABLE_NAMES = ["RF_1_Tot300s", "RF_1_Tot3600s", "RF_1_Tot86400s"]


@pytest.mark.asyncio
async def test_rf_variables_available():
    """Assert RF_1_Tot300s (5-min), RF_1_Tot3600s (hourly), and
    RF_1_Tot86400s (daily) are all listed in the mesonet variables response.

    RF_1_Tot300s is the primary variable used for rainfall aggregation.
    RF_1_Tot3600s and RF_1_Tot86400s are documented here even though they
    are unreliable for recent data (see test_daily_aggregate_unavailable).
    """
    result = await call_tool("get_mesonet_variables", {"location": "hawaii"})
    assert isinstance(result, list), f"Expected list, got {type(result)}"

    available_names = {v.get("standard_name", "") for v in result}

    for var_name in RF_VARIABLE_NAMES:
        assert var_name in available_names, (
            f"Variable '{var_name}' not found in mesonet variables listing. "
            f"Sample available: {sorted(list(available_names))[:10]}..."
        )


@pytest.mark.asyncio
async def test_rf_units_are_mm():
    """Assert all three RF rainfall variables report units of 'mm'.

    Correct units are critical because the ground-truth storm totals from
    the HCDP CSV export are in millimeters. A unit mismatch (e.g., inches
    vs mm) would cause all tolerance-based assertions to fail.
    """
    result = await call_tool("get_mesonet_variables", {"location": "hawaii"})

    var_map = {v.get("standard_name", ""): v for v in result}

    for var_name in RF_VARIABLE_NAMES:
        assert var_name in var_map, f"Variable '{var_name}' not found"
        units = var_map[var_name].get("units", "")
        assert units == "mm", (
            f"Variable '{var_name}' has units '{units}', expected 'mm'. "
            f"Ground truth totals are in mm — a unit mismatch will cause "
            f"all rainfall comparisons to fail."
        )
