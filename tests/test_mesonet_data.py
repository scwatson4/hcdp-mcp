"""Tests for get_mesonet_data tool using verified March 2026 storm ground truth.

Ground truth source: rainfall_new_day_statewide_partial_station_data_2026_03.csv
Stations:
  0501 = Lyon Arboretum  (SKN 785.12, elev 151m, Manoa Valley, Oahu)
  0502 = Nuuanu Res 1    (SKN 775.11, elev 117m, Nuuanu Valley, Oahu)
"""

import asyncio
import logging
import pytest

from conftest import (
    GROUND_TRUTH_STORM_1,
    GROUND_TRUTH_STORM_2,
    STATION_NAMES,
    TOLERANCE_MM,
    fetch_daily_rainfall_hst,
    fetch_daily_rainfall_no_hst_correction,
)
from hcdp_mcp_server.client import HCDPClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Storm 1: March 11–14, 2026
# ---------------------------------------------------------------------------

STORM_1_START = "2026-03-11"
STORM_1_END = "2026-03-14"
STORM_1_STATIONS = ["0501", "0502"]

# Module-level cache: fetched once, shared by all Storm 1 tests
_storm1_cache = None


def _get_storm1_rainfall():
    """Lazy-fetch and cache Storm 1 rainfall data."""
    global _storm1_cache
    if _storm1_cache is None:
        _storm1_cache = asyncio.get_event_loop().run_until_complete(
            fetch_daily_rainfall_hst(STORM_1_STATIONS, STORM_1_START, STORM_1_END)
        )
    return _storm1_cache


@pytest.fixture
def storm1_rainfall():
    """Provide Storm 1 daily rainfall data (cached per module)."""
    return _get_storm1_rainfall()


# ---------------------------------------------------------------------------
# Storm 2: March 19–23, 2026
# ---------------------------------------------------------------------------

STORM_2_START = "2026-03-19"
STORM_2_END = "2026-03-23"
STORM_2_STATIONS = ["0501", "0502"]

_storm2_cache = None


def _get_storm2_rainfall():
    """Lazy-fetch and cache Storm 2 rainfall data."""
    global _storm2_cache
    if _storm2_cache is None:
        _storm2_cache = asyncio.get_event_loop().run_until_complete(
            fetch_daily_rainfall_hst(STORM_2_STATIONS, STORM_2_START, STORM_2_END)
        )
    return _storm2_cache


@pytest.fixture
def storm2_rainfall():
    """Provide Storm 2 daily rainfall data (cached per module)."""
    return _get_storm2_rainfall()


# ---------------------------------------------------------------------------
# Storm 1 daily totals — Lyon Arboretum (0501)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "date,expected_mm",
    [
        ("2026-03-11", GROUND_TRUTH_STORM_1["0501"]["2026-03-11"]),
        ("2026-03-12", GROUND_TRUTH_STORM_1["0501"]["2026-03-12"]),
        ("2026-03-13", GROUND_TRUTH_STORM_1["0501"]["2026-03-13"]),
        ("2026-03-14", GROUND_TRUTH_STORM_1["0501"]["2026-03-14"]),
    ],
    ids=["Mar11", "Mar12", "Mar13-peak", "Mar14"],
)
def test_storm1_daily_totals_lyon(storm1_rainfall, date, expected_mm):
    """Verify each day of Storm 1 (Mar 11–14) for Lyon Arboretum (0501).

    Compares RF_1_Tot300s 5-minute sums (HST-converted) against the
    authoritative HCDP CSV daily totals within ±5mm tolerance.
    """
    actual = storm1_rainfall.get("0501", {}).get(date, 0.0)
    assert actual == pytest.approx(
        expected_mm, abs=TOLERANCE_MM
    ), f"Lyon Arboretum {date}: got {actual}mm, expected {expected_mm}mm (±{TOLERANCE_MM}mm)"


# ---------------------------------------------------------------------------
# Storm 1 daily totals — Nuuanu Res 1 (0502)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "date,expected_mm",
    [
        ("2026-03-11", GROUND_TRUTH_STORM_1["0502"]["2026-03-11"]),
        ("2026-03-12", GROUND_TRUTH_STORM_1["0502"]["2026-03-12"]),
        ("2026-03-13", GROUND_TRUTH_STORM_1["0502"]["2026-03-13"]),
        ("2026-03-14", GROUND_TRUTH_STORM_1["0502"]["2026-03-14"]),
    ],
    ids=["Mar11", "Mar12", "Mar13-peak", "Mar14"],
)
def test_storm1_daily_totals_nuuanu(storm1_rainfall, date, expected_mm):
    """Verify each day of Storm 1 (Mar 11–14) for Nuuanu Res 1 (0502).

    Compares RF_1_Tot300s 5-minute sums (HST-converted) against the
    authoritative HCDP CSV daily totals within ±5mm tolerance.
    """
    actual = storm1_rainfall.get("0502", {}).get(date, 0.0)
    assert actual == pytest.approx(
        expected_mm, abs=TOLERANCE_MM
    ), f"Nuuanu Res 1 {date}: got {actual}mm, expected {expected_mm}mm (±{TOLERANCE_MM}mm)"


# ---------------------------------------------------------------------------
# Storm 2 daily totals — Lyon Arboretum (0501)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "date,expected_mm",
    [
        ("2026-03-19", GROUND_TRUTH_STORM_2["0501"]["2026-03-19"]),
        ("2026-03-20", GROUND_TRUTH_STORM_2["0501"]["2026-03-20"]),
        ("2026-03-21", GROUND_TRUTH_STORM_2["0501"]["2026-03-21"]),
        ("2026-03-22", GROUND_TRUTH_STORM_2["0501"]["2026-03-22"]),
        ("2026-03-23", GROUND_TRUTH_STORM_2["0501"]["2026-03-23"]),
    ],
    ids=["Mar19", "Mar20-peak1", "Mar21", "Mar22", "Mar23-peak2"],
)
def test_storm2_daily_totals_lyon(storm2_rainfall, date, expected_mm):
    """Verify each day of Storm 2 (Mar 19–23) for Lyon Arboretum (0501).

    Compares RF_1_Tot300s 5-minute sums (HST-converted) against the
    authoritative HCDP CSV daily totals within ±5mm tolerance.
    """
    actual = storm2_rainfall.get("0501", {}).get(date, 0.0)
    assert actual == pytest.approx(
        expected_mm, abs=TOLERANCE_MM
    ), f"Lyon Arboretum {date}: got {actual}mm, expected {expected_mm}mm (±{TOLERANCE_MM}mm)"


# ---------------------------------------------------------------------------
# Storm 2 daily totals — Nuuanu Res 1 (0502)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "date,expected_mm",
    [
        ("2026-03-19", GROUND_TRUTH_STORM_2["0502"]["2026-03-19"]),
        ("2026-03-20", GROUND_TRUTH_STORM_2["0502"]["2026-03-20"]),
        ("2026-03-21", GROUND_TRUTH_STORM_2["0502"]["2026-03-21"]),
        ("2026-03-22", GROUND_TRUTH_STORM_2["0502"]["2026-03-22"]),
        ("2026-03-23", GROUND_TRUTH_STORM_2["0502"]["2026-03-23"]),
    ],
    ids=["Mar19", "Mar20-peak1", "Mar21", "Mar22", "Mar23-peak2"],
)
def test_storm2_daily_totals_nuuanu(storm2_rainfall, date, expected_mm):
    """Verify each day of Storm 2 (Mar 19–23) for Nuuanu Res 1 (0502).

    Compares RF_1_Tot300s 5-minute sums (HST-converted) against the
    authoritative HCDP CSV daily totals within ±5mm tolerance.
    """
    actual = storm2_rainfall.get("0502", {}).get(date, 0.0)
    assert actual == pytest.approx(
        expected_mm, abs=TOLERANCE_MM
    ), f"Nuuanu Res 1 {date}: got {actual}mm, expected {expected_mm}mm (±{TOLERANCE_MM}mm)"


# ---------------------------------------------------------------------------
# Peak-day assertions
# ---------------------------------------------------------------------------


def test_storm1_peak_day(storm1_rainfall):
    """Assert March 13 is the single largest rainfall day in the Storm 1
    window (Mar 11–14) for both Lyon Arboretum and Nuuanu Res 1.

    Ground truth confirms Mar 13 received 197.61mm (0501) and 177.29mm
    (0502), far exceeding all other days in the window.
    """
    for station_id in ["0501", "0502"]:
        station_data = storm1_rainfall.get(station_id, {})
        storm_days = {
            d: station_data.get(d, 0.0) for d in GROUND_TRUTH_STORM_1[station_id]
        }
        peak_day = max(storm_days, key=storm_days.get)
        assert peak_day == "2026-03-13", (
            f"Station {station_id} ({STATION_NAMES[station_id]}): "
            f"expected peak on 2026-03-13 but got {peak_day} "
            f"({storm_days[peak_day]:.1f}mm)"
        )


def test_storm2_peak_day(storm2_rainfall):
    """Assert March 20 and March 23 are the two largest rainfall days in the
    Storm 2 window (Mar 19–23) for both stations.

    Ground truth shows a double-peak pattern: Mar 20 (148.34/97.28mm) and
    Mar 23 (135.89/112.06mm).
    """
    for station_id in ["0501", "0502"]:
        station_data = storm2_rainfall.get(station_id, {})
        storm_days = {
            d: station_data.get(d, 0.0) for d in GROUND_TRUTH_STORM_2[station_id]
        }
        sorted_days = sorted(storm_days, key=storm_days.get, reverse=True)
        top_two = set(sorted_days[:2])
        assert top_two == {"2026-03-20", "2026-03-23"}, (
            f"Station {station_id} ({STATION_NAMES[station_id]}): "
            f"expected top-2 days {{2026-03-20, 2026-03-23}} but got {top_two}"
        )


# ---------------------------------------------------------------------------
# UTC offset bug demonstration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_utc_offset_bug():
    """Deliberately query WITHOUT the HST correction and assert that the
    peak storm day (Mar 13 HST) shows dramatically wrong values.

    Because Hawaii is UTC-10, rainfall from ~14:00–23:59 HST on Mar 13
    falls on Mar 14 UTC. Grouping by raw UTC date therefore splits the
    storm across two calendar days, causing the HST peak day to appear
    near-zero or dramatically reduced.

    This test proves the UTC offset bug exists and validates that
    fetch_daily_rainfall_hst correctly guards against it.
    """
    # Get correct HST-converted totals
    correct = await fetch_daily_rainfall_hst(
        ["0501"], STORM_1_START, STORM_1_END
    )
    correct_mar13 = correct.get("0501", {}).get("2026-03-13", 0.0)

    # Get buggy UTC-grouped totals
    buggy = await fetch_daily_rainfall_no_hst_correction(
        ["0501"], STORM_1_START, STORM_1_END
    )
    buggy_mar13 = buggy.get("0501", {}).get("2026-03-13", 0.0)

    # The correct value should be ~197.61mm (ground truth)
    assert correct_mar13 == pytest.approx(
        GROUND_TRUTH_STORM_1["0501"]["2026-03-13"], abs=TOLERANCE_MM
    ), "HST-corrected value should match ground truth"

    # The buggy value should differ significantly from ground truth
    # (rainfall is redistributed to adjacent UTC days)
    difference = abs(correct_mar13 - buggy_mar13)
    assert difference > 10.0, (
        f"Expected significant difference between HST and UTC grouping for "
        f"Mar 13, but HST={correct_mar13:.1f}mm vs UTC={buggy_mar13:.1f}mm "
        f"(diff={difference:.1f}mm). The UTC offset bug should cause >10mm "
        f"discrepancy on the peak storm day."
    )
    logger.info(
        "UTC offset bug confirmed: Mar 13 HST=%.1fmm vs UTC=%.1fmm (diff=%.1fmm)",
        correct_mar13,
        buggy_mar13,
        difference,
    )


# ---------------------------------------------------------------------------
# Chunked vs full-range consistency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chunked_vs_full_range():
    """Query Storm 1 in two 2-day chunks, sum results, and compare to
    querying all 4 days at once. Assert totals match within rounding error.

    This validates that the chunking strategy (required to stay under the
    1MB API response limit) does not lose or duplicate data.
    """
    stations = ["0501", "0502"]

    # Full range query (internally chunked by fetch_daily_rainfall_hst)
    full = await fetch_daily_rainfall_hst(stations, STORM_1_START, STORM_1_END)

    # Manually chunk: Mar 11-12 + Mar 13-14
    chunk_a = await fetch_daily_rainfall_hst(stations, "2026-03-11", "2026-03-12")
    chunk_b = await fetch_daily_rainfall_hst(stations, "2026-03-13", "2026-03-14")

    for station_id in stations:
        full_total = sum(
            full.get(station_id, {}).get(d, 0.0)
            for d in GROUND_TRUTH_STORM_1[station_id]
        )
        chunk_total = sum(
            chunk_a.get(station_id, {}).get(d, 0.0)
            for d in ["2026-03-11", "2026-03-12"]
        ) + sum(
            chunk_b.get(station_id, {}).get(d, 0.0)
            for d in ["2026-03-13", "2026-03-14"]
        )

        assert full_total == pytest.approx(chunk_total, abs=0.1), (
            f"Station {station_id}: full-range total ({full_total:.2f}mm) != "
            f"chunked total ({chunk_total:.2f}mm)"
        )


# ---------------------------------------------------------------------------
# Daily aggregate variable unavailability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_daily_aggregate_unavailable():
    """Query RF_1_Tot86400s (daily aggregate) for the storm dates and assert
    the result is empty or contains no usable data.

    This documents the known limitation that daily aggregate variables are
    unreliable for recent data. The fallback to RF_1_Tot300s (5-minute
    totals) is therefore required.
    """
    client = HCDPClient()

    measurements = await client.get_mesonet_data(
        station_ids="0501,0502",
        start_date=STORM_1_START,
        end_date=STORM_1_END,
        var_ids="RF_1_Tot86400s",
    )

    # Count records that actually have RF_1_Tot86400s data
    rf_daily_records = []
    if isinstance(measurements, list):
        rf_daily_records = [
            m
            for m in measurements
            if m.get("variable") == "RF_1_Tot86400s"
            and m.get("value") is not None
        ]

    logger.warning(
        "RF_1_Tot86400s returned %d records for storm dates %s to %s. "
        "This variable is unreliable for recent data — always use "
        "RF_1_Tot300s with manual HST-converted summation.",
        len(rf_daily_records),
        STORM_1_START,
        STORM_1_END,
    )

    # The daily aggregate should be empty or have very few records
    # for dates this recent
    assert len(rf_daily_records) == 0, (
        f"Expected RF_1_Tot86400s to be unavailable for recent dates, but "
        f"got {len(rf_daily_records)} records. If this test fails, the daily "
        f"aggregate may have become available — verify values match ground "
        f"truth before relying on them."
    )
