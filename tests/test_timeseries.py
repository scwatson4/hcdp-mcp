"""Tests for get_timeseries_data tool.

Validates that the HCDP processed timeseries data is unavailable for
recent dates (within ~6 months) but available for historical periods.
"""

import logging
import pytest

from conftest import MANOA_LAT, MANOA_LNG, call_tool

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_timeseries_unavailable_for_recent():
    """Call get_timeseries_data for rainfall at Manoa coordinates spanning
    March 2026 and assert the result is empty or returns gracefully.

    HCDP processed timeseries and gridded rainfall products lag by
    approximately 6–12 months. For recent dates, the API returns empty
    results. This is expected behavior — for recent rainfall, always use
    get_mesonet_data with RF_1_Tot300s and sum manually.
    """
    result = await call_tool(
        "get_timeseries_data",
        {
            "datatype": "rainfall",
            "start": "2026-03-01",
            "end": "2026-03-31",
            "extent": "oa",
            "lat": MANOA_LAT,
            "lng": MANOA_LNG,
            "production": "new",
            "period": "month",
        },
    )

    # The result may be an empty dict, an empty list, or an error dict.
    # Any of these is acceptable — the key point is no exception was raised.
    if isinstance(result, dict):
        if "_error" in result:
            logger.info(
                "Timeseries for March 2026 returned error (expected): %s",
                result["_error"],
            )
        else:
            # If it's a data dict, it should be empty or have no values
            data_values = [
                v for v in result.values()
                if v is not None and v != -9999
            ]
            logger.info(
                "Timeseries for March 2026 returned %d values (expected 0 "
                "due to ~6-12 month processing lag).",
                len(data_values),
            )
            assert len(data_values) == 0, (
                f"Expected empty timeseries for March 2026 (data lags by "
                f"~6-12 months), but got {len(data_values)} values. If this "
                f"test fails, the processed data may have caught up."
            )
    elif isinstance(result, list):
        assert len(result) == 0, (
            f"Expected empty timeseries for March 2026, got {len(result)} items"
        )


@pytest.mark.asyncio
async def test_timeseries_available_for_historical():
    """Call get_timeseries_data for rainfall at Manoa coordinates for 2024
    and assert a non-empty result is returned.

    Unlike recent dates, historical timeseries data (beyond the processing
    lag window) should be available and return actual rainfall values.
    """
    result = await call_tool(
        "get_timeseries_data",
        {
            "datatype": "rainfall",
            "start": "2024-01-01",
            "end": "2024-12-31",
            "extent": "oa",
            "lat": MANOA_LAT,
            "lng": MANOA_LNG,
            "production": "new",
            "period": "month",
        },
    )

    assert not isinstance(result, list) or len(result) > 0, (
        "Expected non-empty timeseries for 2024"
    )
    if isinstance(result, dict):
        assert "_error" not in result, (
            f"Timeseries query for 2024 returned error: {result.get('_error')}"
        )
        # Should have at least some monthly values
        data_values = [
            v for v in result.values() if v is not None and v != -9999
        ]
        assert len(data_values) > 0, (
            f"Expected non-empty timeseries data for 2024 at Manoa. "
            f"Got dict with keys: {list(result.keys())[:10]}"
        )
        logger.info(
            "Historical timeseries for 2024 returned %d values.", len(data_values)
        )
