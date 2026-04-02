"""Tests for get_city_current_weather tool.

Validates real-time temperature data for Honolulu by comparing HCDP mesonet
readings against Open-Meteo, a free public weather API that requires no key
and provides current temperature from NWP analysis grids.

Open-Meteo endpoint used:
  GET https://api.open-meteo.com/v1/forecast
  Params: latitude, longitude, current=temperature_2m, timezone=Pacific/Honolulu
  Docs:   https://open-meteo.com/en/docs

Tolerance rationale:
  HCDP reports an average of physical station sensors within 15 km of
  Honolulu city centre; Open-Meteo interpolates from NWP model grids.
  Urban heat effects, elevation differences between stations, and the
  ~5-minute reporting lag of mesonet sensors can produce discrepancies
  of several degrees.  We use ±5 °C as the sanity-check threshold —
  tight enough to catch a unit mismatch (°C vs °F would be ~17 °C off)
  or a completely wrong station, but loose enough to tolerate normal
  micro-climate variation across the Honolulu metro area.
"""

import logging

import httpx
import pytest

from conftest import call_tool
from hcdp_mcp_server.tools.constants import CITY_LOCATIONS

logger = logging.getLogger(__name__)

HONOLULU = CITY_LOCATIONS["honolulu"]
TEMPERATURE_TOLERANCE_C = 5.0  # ±°C acceptable deviation from reference


async def _fetch_open_meteo_temperature(lat: float, lng: float) -> float:
    """Return current 2-metre air temperature (°C) from Open-Meteo."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lng,
                "current": "temperature_2m",
                "timezone": "Pacific/Honolulu",
            },
        )
        r.raise_for_status()
        data = r.json()
    return float(data["current"]["temperature_2m"])


@pytest.mark.asyncio
async def test_city_weather_temperature_honolulu():
    """Call get_city_current_weather for honolulu/temperature and assert the
    result is within ±5 °C of the current Open-Meteo analysis temperature.

    This test exercises the full tool pipeline:
      1. Fetch mesonet station list
      2. Spatial filter: stations within 15 km of Honolulu (21.31°N, 157.86°W)
      3. Query Tair_1_Avg for today via /mesonet/db/measurements
      4. Average readings across all reporting stations

    If no stations have reported temperature today the tool returns a
    'message' key instead of 'average'; the test skips in that case since
    the data gap is an API/sensor availability issue, not a tool bug.
    """
    hcdp_result = await call_tool(
        "get_city_current_weather",
        {"city": "honolulu", "datatype": "temperature"},
    )

    # Propagate any hard API errors
    if isinstance(hcdp_result, dict) and "_error" in hcdp_result:
        pytest.fail(
            f"get_city_current_weather returned an error: {hcdp_result['_error']}"
        )

    assert isinstance(hcdp_result, dict), (
        f"Expected dict response, got {type(hcdp_result)}: {hcdp_result}"
    )

    # Skip gracefully if no stations have reported data today
    if "message" in hcdp_result:
        pytest.skip(
            f"No temperature data available from HCDP today: "
            f"{hcdp_result['message']}. Skipping comparison — this is "
            f"expected if stations have not yet reported Tair_1_Avg today."
        )

    hcdp_temp = hcdp_result["average"]
    assert isinstance(hcdp_temp, (int, float)), (
        f"'average' should be numeric, got {type(hcdp_temp)}: {hcdp_temp}"
    )

    # Sanity check: Honolulu temperatures are roughly 18–35 °C year-round
    assert 10.0 <= hcdp_temp <= 40.0, (
        f"HCDP average temperature {hcdp_temp} °C is outside the plausible "
        f"Honolulu range (10–40 °C). Likely a unit error or wrong station."
    )

    # Fetch reference temperature from Open-Meteo
    try:
        ref_temp = await _fetch_open_meteo_temperature(
            HONOLULU["lat"], HONOLULU["lng"]
        )
    except Exception as exc:
        pytest.skip(
            f"Open-Meteo reference fetch failed ({exc}). Cannot compare — "
            f"HCDP reported {hcdp_temp} °C from "
            f"{hcdp_result.get('station_count', '?')} stations."
        )

    logger.info(
        "Honolulu temperature — HCDP: %.1f °C (avg of %d stations, %d readings), "
        "Open-Meteo: %.1f °C, diff: %.1f °C",
        hcdp_temp,
        hcdp_result.get("station_count", 0),
        hcdp_result.get("reading_count", 0),
        ref_temp,
        abs(hcdp_temp - ref_temp),
    )

    assert abs(hcdp_temp - ref_temp) <= TEMPERATURE_TOLERANCE_C, (
        f"Honolulu temperature mismatch: HCDP={hcdp_temp:.1f} °C vs "
        f"Open-Meteo={ref_temp:.1f} °C "
        f"(diff={abs(hcdp_temp - ref_temp):.1f} °C, tolerance=±{TEMPERATURE_TOLERANCE_C} °C). "
        f"Stations used: {hcdp_result.get('stations_used', [])}."
    )


@pytest.mark.asyncio
async def test_city_weather_response_structure():
    """Assert get_city_current_weather returns the expected response shape.

    This structural test does not depend on real-time data being available —
    it verifies that when the tool has data it returns the correct keys, and
    when it has no data it returns the expected 'message' key.
    """
    result = await call_tool(
        "get_city_current_weather",
        {"city": "honolulu", "datatype": "temperature"},
    )

    if isinstance(result, dict) and "_error" in result:
        pytest.fail(f"Tool returned API error: {result['_error']}")

    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "city" in result, f"Missing 'city' key. Keys: {list(result.keys())}"
    assert result["city"] == "honolulu"

    if "message" in result:
        # No data path: tool should still report stations_found
        assert "stations_found" in result, (
            "No-data response must include 'stations_found'"
        )
        assert result["stations_found"] > 0, (
            "Expected at least one station within 15 km of Honolulu"
        )
    else:
        # Data path: verify all expected numeric fields
        for key in ("average", "min", "max", "station_count", "reading_count"):
            assert key in result, (
                f"Missing '{key}' in data response. Keys: {list(result.keys())}"
            )
        assert result["min"] <= result["average"] <= result["max"], (
            f"min/avg/max ordering violated: "
            f"min={result['min']}, avg={result['average']}, max={result['max']}"
        )
        assert result["station_count"] > 0
        assert result["reading_count"] > 0
        assert isinstance(result.get("stations_used"), list)


@pytest.mark.asyncio
async def test_city_weather_unknown_city():
    """Assert that requesting an unknown city raises an error rather than
    returning empty data silently."""
    result = await call_tool(
        "get_city_current_weather",
        {"city": "atlantis", "datatype": "temperature"},
    )
    # The tool raises ValueError for unknown cities, which the server wraps
    # as an error string
    assert isinstance(result, dict) and "_error" in result, (
        f"Expected an error for unknown city 'atlantis', got: {result}"
    )
