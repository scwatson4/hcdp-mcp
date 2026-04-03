"""Pytest configuration and shared fixtures for HCDP MCP storm validation tests.

Ground truth source: rainfall_new_day_statewide_partial_station_data_2026_03.csv
from the HCDP data export. These are authoritative daily totals (in mm).
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from collections import defaultdict

from hcdp_mcp_server.client import HCDPClient
from hcdp_mcp_server.server import handle_call_tool


# ---------------------------------------------------------------------------
# Ground truth constants — do not modify
# ---------------------------------------------------------------------------

GROUND_TRUTH_STORM_1 = {
    "0501": {
        "2026-03-11": 63.75,
        "2026-03-12": 52.07,
        "2026-03-13": 197.61,
        "2026-03-14": 59.18,
    },
    "0502": {
        "2026-03-11": 44.73,
        "2026-03-12": 30.53,
        "2026-03-13": 177.29,
        "2026-03-14": 46.53,
    },
}

GROUND_TRUTH_STORM_2 = {
    "0501": {
        "2026-03-19": 18.54,
        "2026-03-20": 148.34,
        "2026-03-21": 40.13,
        "2026-03-22": 29.97,
        "2026-03-23": 135.89,
    },
    "0502": {
        "2026-03-19": 20.07,
        "2026-03-20": 97.28,
        "2026-03-21": 22.35,
        "2026-03-22": 27.64,
        "2026-03-23": 112.06,
    },
}

STATION_NAMES = {"0501": "Lyon Arboretum", "0502": "Nuuanu Res 1"}
TOLERANCE_MM = 5.0  # acceptable deviation from CSV ground truth

# Station reference:
# 0501 = Lyon Arboretum (SKN 785.12, elev 151m, Manoa Valley, Oahu)
# 0502 = Nuuanu Reservoir 1 (SKN 775.11, elev 117m, Nuuanu Valley, Oahu)

# Manoa coordinates for timeseries queries
MANOA_LAT = 21.3330
MANOA_LNG = -157.8025

# Maximum days per chunk to stay under 1MB API response limit
MAX_DAYS_PER_CHUNK = 2


# ---------------------------------------------------------------------------
# Shared helper: fetch and aggregate mesonet rainfall with HST conversion
# ---------------------------------------------------------------------------


async def _fetch_chunk(client, station_ids_str, start_date, end_date):
    """Fetch RF_1_Tot300s measurements for a single date chunk."""
    return await client.get_mesonet_data(
        station_ids=station_ids_str,
        start_date=start_date,
        end_date=end_date,
        var_ids="RF_1_Tot300s",
    )


async def fetch_daily_rainfall_hst(
    station_ids: list[str], start_date: str, end_date: str
) -> dict[str, dict[str, float]]:
    """Query RF_1_Tot300s from get_mesonet_data and sum 5-minute intervals
    into HST daily totals.

    CRITICAL: subtracts 10 hours from UTC timestamps before grouping by date.
    Never group on raw UTC date — this causes storm days to appear as 0mm.

    Automatically chunks requests into 2-day windows to stay under the 1MB
    API response limit.

    NOTE on API boundary behaviour: querying end_date=X returns records up to
    X 00:00:00 UTC only (not through X 23:59 UTC).  To cover the full last HST
    day (which extends 10 h into the next UTC day) we extend the query window
    by 2 extra UTC days and let adjacent chunks share their boundary timestamp,
    deduplicating by (station_id, timestamp) to avoid double-counting.

    Returns:
        {station_id: {date_str: total_mm, ...}, ...}
    """
    client = HCDPClient()
    station_ids_str = ",".join(station_ids)

    dt_start = datetime.strptime(start_date, "%Y-%m-%d")
    dt_end = datetime.strptime(end_date, "%Y-%m-%d")
    # Extend by 2 days so the last chunk covers end_date's full HST day
    # (HST = UTC-10, so end_date 23:55 HST = end_date+1 09:55 UTC; adding one
    # more day accounts for the API returning only up to end_date 00:00 UTC)
    dt_end_query = dt_end + timedelta(days=2)

    all_measurements = []
    seen: set[tuple] = set()  # dedup (station_id, timestamp) at chunk boundaries

    chunk_start = dt_start
    while chunk_start < dt_end_query:
        chunk_end = min(chunk_start + timedelta(days=MAX_DAYS_PER_CHUNK), dt_end_query)

        measurements = await _fetch_chunk(
            client,
            station_ids_str,
            chunk_start.strftime("%Y-%m-%d"),
            chunk_end.strftime("%Y-%m-%d"),
        )

        if isinstance(measurements, list):
            for m in measurements:
                key = (m.get("station_id"), m.get("timestamp"))
                if key not in seen:
                    seen.add(key)
                    all_measurements.append(m)

        # Adjacent chunks share the boundary timestamp; no +1 so there is no gap
        chunk_start = chunk_end

    # Aggregate by station and HST date
    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for record in all_measurements:
        station = record.get("station_id", "")
        if station not in station_ids:
            continue

        variable = record.get("variable", "")
        if variable != "RF_1_Tot300s":
            continue

        value_str = record.get("value")
        if value_str is None:
            continue
        try:
            value = float(value_str)
        except (ValueError, TypeError):
            continue

        # CRITICAL: convert UTC timestamp to HST (UTC-10, no DST)
        ts = record.get("timestamp", "")
        utc_dt = datetime.fromisoformat(ts.replace("Z", ""))
        hst_dt = utc_dt - timedelta(hours=10)
        day = hst_dt.strftime("%Y-%m-%d")

        totals[station][day] += value

    # Return only dates within the requested HST range; discard overflow from
    # the extended UTC query window
    return {
        station: {
            day: round(total, 2)
            for day, total in days.items()
            if start_date <= day <= end_date
        }
        for station, days in totals.items()
    }


async def fetch_daily_rainfall_no_hst_correction(
    station_ids: list[str], start_date: str, end_date: str
) -> dict[str, dict[str, float]]:
    """Same as fetch_daily_rainfall_hst but deliberately groups on raw UTC date.

    This exists solely to demonstrate the UTC offset bug: storm rainfall is
    misattributed to adjacent days when the HST correction is skipped.
    """
    client = HCDPClient()
    station_ids_str = ",".join(station_ids)

    dt_start = datetime.strptime(start_date, "%Y-%m-%d")
    dt_end = datetime.strptime(end_date, "%Y-%m-%d")

    all_measurements = []
    seen: set[tuple] = set()
    dt_end_query = dt_end + timedelta(days=2)

    chunk_start = dt_start
    while chunk_start < dt_end_query:
        chunk_end = min(chunk_start + timedelta(days=MAX_DAYS_PER_CHUNK), dt_end_query)
        measurements = await _fetch_chunk(
            client,
            station_ids_str,
            chunk_start.strftime("%Y-%m-%d"),
            chunk_end.strftime("%Y-%m-%d"),
        )
        if isinstance(measurements, list):
            for m in measurements:
                key = (m.get("station_id"), m.get("timestamp"))
                if key not in seen:
                    seen.add(key)
                    all_measurements.append(m)
        chunk_start = chunk_end

    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for record in all_measurements:
        station = record.get("station_id", "")
        if station not in station_ids:
            continue
        variable = record.get("variable", "")
        if variable != "RF_1_Tot300s":
            continue
        value_str = record.get("value")
        if value_str is None:
            continue
        try:
            value = float(value_str)
        except (ValueError, TypeError):
            continue

        # BUG: grouping on raw UTC date without HST conversion
        ts = record.get("timestamp", "")
        utc_dt = datetime.fromisoformat(ts.replace("Z", ""))
        day = utc_dt.strftime("%Y-%m-%d")

        totals[station][day] += value

    return {
        station: {day: round(total, 2) for day, total in days.items()}
        for station, days in totals.items()
    }


# ---------------------------------------------------------------------------
# Helper for calling MCP tools and parsing JSON response
# ---------------------------------------------------------------------------


async def call_tool(name: str, arguments: dict) -> dict | list:
    """Call an MCP tool via handle_call_tool and return the parsed JSON."""
    result = await handle_call_tool(name, arguments)
    assert len(result) >= 1, f"Tool {name} returned no content"
    text = result[0].text
    # If the tool returned an error string, return it as-is for assertions
    if text.startswith("Error calling HCDP API:"):
        return {"_error": text}
    return json.loads(text)
