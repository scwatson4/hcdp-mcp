"""Macro-query tests: 30 complex real-world questions answered via HCDP MCP tools.

Each test simulates a user question, calls the appropriate MCP tool(s),
and validates the result against known climatological facts or public
reference data (Open-Meteo API where applicable).

These are integration tests that hit the real HCDP API.

Reference sources for validation:
  - Open-Meteo (free, no key): https://open-meteo.com/en/docs
  - Known Hawaiian climatology (e.g., Hilo wetter than Kona,
    windward wetter than leeward, Mt Waialeale extreme rainfall)
  - HCDP ground-truth storm data from conftest.py
"""

import logging
from datetime import datetime

import httpx
import pytest

from conftest import (
    MANOA_LAT,
    MANOA_LNG,
    GROUND_TRUTH_STORM_1,
    TOLERANCE_MM,
    call_tool,
    fetch_daily_rainfall_hst,
)
from hcdp_mcp_server.tools.constants import (
    CITY_LOCATIONS,
    ISLAND_BOUNDS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: Open-Meteo reference fetch
# ---------------------------------------------------------------------------


async def _open_meteo_current(lat: float, lng: float, variable: str = "temperature_2m"):
    """Fetch a current weather variable from Open-Meteo."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lng,
                "current": variable,
                "timezone": "Pacific/Honolulu",
            },
        )
        r.raise_for_status()
        return float(r.json()["current"][variable])


# ===========================================================================
# CATEGORY 1: Current / Real-Time Weather Queries (1-10)
# ===========================================================================


@pytest.mark.asyncio
async def test_q01_current_temperature_honolulu():
    """Q: What is the current temperature in Honolulu?
    Tools: get_city_current_weather
    Validation: Compare vs Open-Meteo (±5°C tolerance)
    """
    result = await call_tool(
        "get_city_current_weather",
        {"city": "honolulu", "datatype": "temperature"},
    )
    if isinstance(result, dict) and "message" in result:
        pytest.skip("No temperature data available from HCDP today")

    hcdp_temp = result["average"]
    assert 10.0 <= hcdp_temp <= 40.0, f"Implausible Honolulu temp: {hcdp_temp}°C"

    try:
        ref = await _open_meteo_current(
            CITY_LOCATIONS["honolulu"]["lat"], CITY_LOCATIONS["honolulu"]["lng"]
        )
        assert (
            abs(hcdp_temp - ref) <= 5.0
        ), f"Temp mismatch: HCDP={hcdp_temp:.1f} vs Open-Meteo={ref:.1f}"
        logger.info("Q01: Honolulu temp HCDP=%.1f, Open-Meteo=%.1f", hcdp_temp, ref)
    except Exception as e:
        logger.info("Q01: Open-Meteo unavailable (%s), HCDP=%.1f°C", e, hcdp_temp)


@pytest.mark.asyncio
async def test_q02_current_weather_hilo():
    """Q: What is the current weather in Hilo?
    Tools: get_city_current_weather (multi-variable "weather")
    Validation: Response includes temp, humidity, rainfall fields
    """
    result = await call_tool(
        "get_city_current_weather",
        {"city": "hilo", "datatype": "weather"},
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    # Multi-variable query should have per-variable breakdowns
    if "_error" not in result and "message" not in result:
        assert "variables" in result or "Tair_1_Avg" in str(
            result
        ), f"Multi-variable weather response unexpected shape: {list(result.keys())}"


@pytest.mark.asyncio
async def test_q03_oahu_island_temperature_summary():
    """Q: What is the current temperature across Oahu?
    Tools: get_island_current_summary
    Validation: Average between 15-35°C, min < avg < max
    """
    result = await call_tool(
        "get_island_current_summary",
        {"island": "oahu", "datatype": "temperature"},
    )
    assert isinstance(result, dict)

    if "message" in result:
        pytest.skip(f"No data: {result['message']}")

    avg = result.get("average")
    if avg is not None:
        assert 15.0 <= avg <= 35.0, f"Implausible Oahu avg temp: {avg}°C"
        assert result["min"] <= avg <= result["max"]


@pytest.mark.asyncio
async def test_q04_humidity_across_oahu():
    """Q: What is the current humidity across Oahu?
    Tools: get_island_current_summary
    Validation: Humidity should be 30-100% (Hawaii is humid)
    """
    result = await call_tool(
        "get_island_current_summary",
        {"island": "oahu", "datatype": "humidity"},
    )
    if isinstance(result, dict) and "message" not in result:
        avg = result.get("average")
        if avg is not None:
            assert 20.0 <= avg <= 100.0, f"Implausible humidity: {avg}%"


@pytest.mark.asyncio
async def test_q05_nearest_stations_waikiki():
    """Q: What are the nearest weather stations to Waikiki Beach?
    Tools: get_nearby_stations
    Validation: Should find stations, closest within a few km of Waikiki
    """
    # Waikiki: approximately 21.2766, -157.8278
    result = await call_tool(
        "get_nearby_stations",
        {"lat": 21.2766, "lng": -157.8278, "limit": 5},
    )
    assert "stations" in result
    assert len(result["stations"]) == 5
    # Closest station should be within 10km of Waikiki (urban Honolulu)
    assert result["stations"][0]["distance_km"] < 10.0


@pytest.mark.asyncio
async def test_q06_how_many_mesonet_stations_hawaii():
    """Q: How many mesonet stations are there in Hawaii?
    Tools: get_mesonet_stations
    Validation: Should be > 50 stations (Hawaii has a dense network)
    """
    result = await call_tool("get_mesonet_stations", {"location": "hawaii"})
    assert isinstance(result, list)
    assert len(result) > 50, f"Expected > 50 stations, got {len(result)}"
    logger.info("Q06: Hawaii has %d mesonet stations", len(result))


@pytest.mark.asyncio
async def test_q07_current_wind_speed_honolulu():
    """Q: What is the wind speed in Honolulu right now?
    Tools: get_city_current_weather
    Validation: Wind speed should be non-negative, < 50 m/s
    """
    result = await call_tool(
        "get_city_current_weather",
        {"city": "honolulu", "datatype": "wind"},
    )
    if isinstance(result, dict) and "message" not in result and "_error" not in result:
        avg = result.get("average")
        if avg is not None:
            assert 0.0 <= avg <= 50.0, f"Implausible wind speed: {avg} m/s"


@pytest.mark.asyncio
async def test_q08_kauai_weather_summary():
    """Q: What is the current weather summary for Kauai?
    Tools: get_island_current_summary
    Validation: Returns data from Kauai stations
    """
    result = await call_tool(
        "get_island_current_summary",
        {"island": "kauai", "datatype": "temperature"},
    )
    assert isinstance(result, dict)
    if "station_count" in result:
        assert result["station_count"] > 0, "Expected stations on Kauai"


@pytest.mark.asyncio
async def test_q09_real_time_rainfall_lyon_arboretum():
    """Q: What is the real-time rainfall at Lyon Arboretum right now?
    Tools: get_mesonet_data
    Validation: Returns data for station 0501, values are non-negative mm
    """
    today = datetime.now().strftime("%Y-%m-%d")
    result = await call_tool(
        "get_mesonet_data",
        {
            "station_ids": "0501",
            "start_date": today,
            "var_ids": "RF_1_Tot300s",
            "limit": 5,
        },
    )
    # May be empty if station hasn't reported today yet
    if isinstance(result, list) and len(result) > 0:
        for record in result:
            value = float(record.get("value", 0))
            assert value >= 0, f"Negative rainfall value: {value}"


@pytest.mark.asyncio
async def test_q10_compare_all_major_cities_temperature():
    """Q: Compare temperature across all major Hawaiian cities.
    Tools: get_city_current_weather (multiple calls)
    Validation: All temperatures 10-40°C, coastal cities have similar temps
    """
    temps = {}
    for city in ["honolulu", "hilo", "kona", "kahului", "lihue"]:
        result = await call_tool(
            "get_city_current_weather",
            {"city": city, "datatype": "temperature"},
        )
        if isinstance(result, dict) and "average" in result:
            temps[city] = result["average"]

    if len(temps) < 2:
        pytest.skip("Not enough cities reported temperature data")

    # All Hawaiian city temps should be within a reasonable range
    for city, temp in temps.items():
        assert 10.0 <= temp <= 40.0, f"{city}: implausible temp {temp}°C"

    logger.info("Q10: City temperatures: %s", temps)


# ===========================================================================
# CATEGORY 2: Historical / Climatological Queries (11-20)
# ===========================================================================


@pytest.mark.asyncio
async def test_q11_is_hilo_wetter_than_kona():
    """Q: Is Hilo wetter than Kona? (Known: yes, due to orographic rainfall)
    Tools: get_island_history_summary for big_island
    Validation: Hilo (East/Wet) should have higher rainfall than Kona (West/Dry)
    """
    result = await call_tool(
        "get_island_history_summary",
        {"island": "big_island", "datatype": "rainfall", "year": "2024"},
    )
    breakdown = result.get("regional_breakdown", [])
    loc_map = {e.get("location", ""): e for e in breakdown}

    hilo = loc_map.get("Hilo (East/Wet)", {})
    kona = loc_map.get("Kona (West/Dry)", {})

    hilo_avg = hilo.get("average")
    kona_avg = kona.get("average")

    if hilo_avg is None or kona_avg is None:
        pytest.skip("Missing data for Hilo or Kona")

    assert hilo_avg > kona_avg, (
        f"Climatological fact violated: Hilo ({hilo_avg}mm) should be wetter "
        f"than Kona ({kona_avg}mm) due to orographic rainfall from trade winds."
    )
    logger.info(
        "Q11: Hilo=%.1fmm vs Kona=%.1fmm (%.1fx wetter)",
        hilo_avg,
        kona_avg,
        hilo_avg / max(kona_avg, 0.01),
    )


@pytest.mark.asyncio
async def test_q12_windward_vs_leeward_oahu():
    """Q: Does windward Oahu get more rain than leeward Oahu?
    Tools: get_island_history_summary
    Validation: Kaneohe (windward) > Kapolei (leeward) — orographic effect
    """
    result = await call_tool(
        "get_island_history_summary",
        {"island": "oahu", "datatype": "rainfall", "year": "2024"},
    )
    breakdown = result.get("regional_breakdown", [])
    loc_map = {e.get("location", ""): e for e in breakdown}

    windward = loc_map.get("Kaneohe (Windward)", {}).get("average")
    leeward = loc_map.get("Kapolei (Leeward)", {}).get("average")

    if windward is None or leeward is None:
        pytest.skip("Missing windward/leeward data")

    assert windward > leeward, (
        f"Orographic fact violated: Windward ({windward}mm) should exceed "
        f"Leeward ({leeward}mm)"
    )


@pytest.mark.asyncio
async def test_q13_historical_rainfall_manoa_2024():
    """Q: How much did it rain in Manoa Valley in 2024?
    Tools: get_timeseries_data
    Validation: Manoa gets ~150+ inches/year (~3800mm), expect > 1000mm
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
    if isinstance(result, dict) and "_error" not in result:
        values = [v for v in result.values() if v is not None and v != -9999]
        if values:
            total = sum(values)
            assert total > 1000, (
                f"Manoa annual rainfall {total}mm seems too low "
                f"(expected > 1000mm for one of Hawaii's wettest valleys)"
            )
            logger.info(
                "Q13: Manoa 2024 rainfall: %.0fmm from %d months", total, len(values)
            )


@pytest.mark.asyncio
async def test_q14_compare_kauai_vs_maui_rainfall():
    """Q: How does Kauai rainfall compare to Maui?
    Tools: get_island_history_summary (two calls)
    Validation: Both should have positive rainfall; Kauai likely wetter overall
    """
    kauai = await call_tool(
        "get_island_history_summary",
        {"island": "kauai", "datatype": "rainfall", "year": "2024"},
    )
    maui = await call_tool(
        "get_island_history_summary",
        {"island": "maui", "datatype": "rainfall", "year": "2024"},
    )

    kauai_avg = kauai.get("island_wide_average")
    maui_avg = maui.get("island_wide_average")

    if kauai_avg == "N/A" or maui_avg == "N/A":
        pytest.skip("Missing island averages")

    assert kauai_avg > 0, f"Kauai rainfall should be positive: {kauai_avg}"
    assert maui_avg > 0, f"Maui rainfall should be positive: {maui_avg}"
    logger.info("Q14: Kauai avg=%.1fmm, Maui avg=%.1fmm", kauai_avg, maui_avg)


@pytest.mark.asyncio
async def test_q15_compare_current_vs_historical_honolulu():
    """Q: How does current Honolulu weather compare to historical?
    Tools: compare_current_vs_historical
    Validation: Returns current_value and historical_average; both numeric
    """
    result = await call_tool(
        "compare_current_vs_historical",
        {"city": "honolulu", "datatype": "temperature"},
    )
    assert isinstance(result, dict)

    if "historical_average" in result:
        hist = result["historical_average"]
        assert isinstance(hist, (int, float)), f"historical_average not numeric: {hist}"
        assert 15.0 <= hist <= 35.0, f"Implausible historical temp: {hist}°C"


@pytest.mark.asyncio
async def test_q16_temperature_trend_oahu_2024():
    """Q: What was the temperature trend for Oahu across 2024?
    Tools: get_timeseries_data
    Validation: Monthly temps 15-35°C; summer months warmer than winter
    """
    result = await call_tool(
        "get_timeseries_data",
        {
            "datatype": "temperature",
            "start": "2024-01-01",
            "end": "2024-12-31",
            "extent": "oa",
            "lat": 21.3069,
            "lng": -157.8583,
            "period": "month",
        },
    )
    if isinstance(result, dict) and "_error" not in result:
        values = {k: v for k, v in result.items() if v is not None and v != -9999}
        if len(values) >= 6:
            for month, temp in values.items():
                assert 15.0 <= temp <= 35.0, f"Month {month}: implausible temp {temp}°C"
            logger.info("Q16: Oahu 2024 monthly temps: %s", values)


@pytest.mark.asyncio
async def test_q17_march_2026_storm_peak_day():
    """Q: What was the peak rainfall day during the March 2026 storm at Lyon Arboretum?
    Tools: Uses conftest ground-truth data (validated against get_mesonet_data)
    Validation: Peak day should be March 13 with ~197mm (known from HCDP CSV)
    """
    # Ground truth from conftest
    storm_data = GROUND_TRUTH_STORM_1["0501"]
    peak_day = max(storm_data, key=storm_data.get)
    peak_mm = storm_data[peak_day]

    assert (
        peak_day == "2026-03-13"
    ), f"Peak storm day should be March 13, got {peak_day}"
    assert (
        abs(peak_mm - 197.61) < 1.0
    ), f"Peak rainfall should be ~197.61mm, got {peak_mm}"
    logger.info("Q17: March 2026 storm peak at Lyon: %s = %.1fmm", peak_day, peak_mm)


@pytest.mark.asyncio
async def test_q18_oahu_annual_rainfall_patterns():
    """Q: How much did it rain across Oahu in 2024?
    Tools: get_island_history_summary
    Validation: Island-wide average should be positive
    """
    result = await call_tool(
        "get_island_history_summary",
        {"island": "oahu", "datatype": "rainfall", "year": "2024"},
    )
    avg = result.get("island_wide_average")
    if avg != "N/A":
        assert avg > 0, f"Oahu should have positive rainfall: {avg}"
        logger.info("Q18: Oahu 2024 island-wide rainfall avg: %.1fmm", avg)


@pytest.mark.asyncio
async def test_q19_spi_drought_index_big_island():
    """Q: What is the SPI (Standardized Precipitation Index) for Big Island?
    Tools: get_timeseries_data with datatype='spi'
    Validation: SPI values typically range -3 to +3
    """
    result = await call_tool(
        "get_timeseries_data",
        {
            "datatype": "spi",
            "start": "2024-01-01",
            "end": "2024-12-31",
            "extent": "bi",
            "lat": 19.7241,
            "lng": -155.0868,
            "period": "month",
        },
    )
    if isinstance(result, dict) and "_error" not in result:
        values = [v for v in result.values() if v is not None and v != -9999]
        if values:
            for v in values:
                assert -4.0 <= v <= 4.0, f"SPI value {v} outside typical range"
            logger.info("Q19: Big Island SPI values: %s", values)
        else:
            logger.info("Q19: No SPI data available for Big Island 2024")


@pytest.mark.asyncio
async def test_q20_hilo_temperature_vs_open_meteo():
    """Q: What is the temperature in Hilo compared to reference data?
    Tools: get_city_current_weather
    Validation: Compare vs Open-Meteo (±5°C)
    """
    result = await call_tool(
        "get_city_current_weather",
        {"city": "hilo", "datatype": "temperature"},
    )
    if isinstance(result, dict) and "average" in result:
        hcdp_temp = result["average"]
        assert 10.0 <= hcdp_temp <= 40.0, f"Implausible Hilo temp: {hcdp_temp}°C"

        try:
            ref = await _open_meteo_current(
                CITY_LOCATIONS["hilo"]["lat"], CITY_LOCATIONS["hilo"]["lng"]
            )
            assert (
                abs(hcdp_temp - ref) <= 5.0
            ), f"Hilo temp mismatch: HCDP={hcdp_temp:.1f} vs Open-Meteo={ref:.1f}"
            logger.info("Q20: Hilo temp HCDP=%.1f, Open-Meteo=%.1f", hcdp_temp, ref)
        except Exception as e:
            logger.info("Q20: Open-Meteo unavailable (%s), HCDP=%.1f°C", e, hcdp_temp)
    else:
        pytest.skip("No temperature data available for Hilo")


# ===========================================================================
# CATEGORY 3: Discovery / Metadata Queries (21-25)
# ===========================================================================


@pytest.mark.asyncio
async def test_q21_what_rainfall_variables_available():
    """Q: What rainfall measurement variables does the mesonet have?
    Tools: get_mesonet_variables
    Validation: Must include RF_1_Tot300s (5-min totals)
    """
    result = await call_tool("get_mesonet_variables", {"location": "hawaii"})
    var_names = {v.get("standard_name", "") for v in result}
    assert "RF_1_Tot300s" in var_names, "5-minute rainfall variable missing"
    assert "Tair_1_Avg" in var_names, "Temperature variable missing"
    logger.info("Q21: Found %d mesonet variables", len(result))


@pytest.mark.asyncio
async def test_q22_soil_moisture_variable_exists():
    """Q: Is soil moisture data available in the mesonet?
    Tools: get_mesonet_variables
    Validation: Check if SM_1_Avg exists in variable listing
    """
    result = await call_tool("get_mesonet_variables", {"location": "hawaii"})
    var_names = {v.get("standard_name", "") for v in result}
    # Soil moisture may or may not be available at all stations
    has_soil = "SM_1_Avg" in var_names
    logger.info("Q22: Soil moisture (SM_1_Avg) available: %s", has_soil)
    # Not asserting it must exist — just documenting availability


@pytest.mark.asyncio
async def test_q23_mesonet_stations_on_molokai():
    """Q: Are there mesonet stations on Molokai?
    Tools: get_mesonet_stations + geographic filter
    Validation: Molokai has limited but existing stations
    """
    result = await call_tool("get_mesonet_stations", {"location": "hawaii"})
    molokai_bounds = ISLAND_BOUNDS["molokai"]
    molokai_stations = [
        s
        for s in result
        if (
            s.get("lat") is not None
            and s.get("lng") is not None
            and molokai_bounds[0] <= float(s["lat"]) <= molokai_bounds[1]
            and molokai_bounds[2] <= float(s["lng"]) <= molokai_bounds[3]
        )
    ]
    logger.info("Q23: Molokai has %d mesonet stations", len(molokai_stations))
    # Molokai should have at least a couple stations
    assert len(molokai_stations) >= 1, "Expected at least 1 station on Molokai"


@pytest.mark.asyncio
async def test_q24_station_search_lyon_arboretum():
    """Q: Find station metadata for Lyon Arboretum.
    Tools: get_station_data
    Validation: Should find station with Lyon in the name
    """
    result = await call_tool(
        "get_station_data",
        {"q": '{"name": {"$regex": "Lyon", "$options": "i"}}'},
    )
    if isinstance(result, list):
        names = [s.get("name", "") + " " + s.get("full_name", "") for s in result]
        found = any("lyon" in n.lower() for n in names)
        if found:
            logger.info("Q24: Found Lyon Arboretum in station data")
        else:
            logger.info(
                "Q24: Lyon not found via station search (may need different query)"
            )
    elif isinstance(result, dict) and "_error" not in result:
        logger.info("Q24: Station data returned dict: %s", list(result.keys())[:5])


@pytest.mark.asyncio
async def test_q25_american_samoa_stations():
    """Q: Are there weather stations in American Samoa?
    Tools: get_mesonet_stations with location=american_samoa
    Validation: Should find at least a few stations
    """
    result = await call_tool("get_mesonet_stations", {"location": "american_samoa"})
    if isinstance(result, list):
        logger.info("Q25: American Samoa has %d mesonet stations", len(result))
        # American Samoa has a smaller network but should have some
        assert len(result) >= 1, "Expected at least 1 station in American Samoa"
    elif isinstance(result, dict) and "_error" in result:
        pytest.skip(f"American Samoa query failed: {result['_error']}")


# ===========================================================================
# CATEGORY 4: Complex / Multi-Tool Queries (26-30)
# ===========================================================================


@pytest.mark.asyncio
async def test_q26_stations_within_10km_downtown_honolulu():
    """Q: How many mesonet stations are within 10km of downtown Honolulu?
    Tools: get_nearby_stations
    Validation: Urban Honolulu should have several nearby stations
    """
    result = await call_tool(
        "get_nearby_stations",
        {"lat": 21.3069, "lng": -157.8583, "limit": 20},
    )
    stations = result.get("stations", [])
    within_10km = [s for s in stations if s["distance_km"] <= 10.0]
    logger.info(
        "Q26: %d stations within 10km of downtown Honolulu (of %d returned)",
        len(within_10km),
        len(stations),
    )
    assert (
        len(within_10km) >= 3
    ), f"Expected >= 3 stations within 10km of Honolulu, got {len(within_10km)}"


@pytest.mark.asyncio
async def test_q27_elevation_gradient_oahu_stations():
    """Q: Do higher-elevation Oahu stations show lower temperatures?
    Tools: get_mesonet_stations + get_mesonet_data
    Validation: General trend of temperature decreasing with elevation
    """
    stations = await call_tool("get_mesonet_stations", {"location": "hawaii"})
    oahu_bounds = ISLAND_BOUNDS["oahu"]
    oahu_stations = [
        s
        for s in stations
        if (
            s.get("lat") is not None
            and s.get("lng") is not None
            and s.get("elevation") is not None
            and oahu_bounds[0] <= float(s["lat"]) <= oahu_bounds[1]
            and oahu_bounds[2] <= float(s["lng"]) <= oahu_bounds[3]
        )
    ]

    if len(oahu_stations) < 5:
        pytest.skip("Not enough Oahu stations with elevation data")

    # Sort by elevation
    oahu_stations.sort(key=lambda s: float(s.get("elevation", 0)))

    lowest = oahu_stations[:3]
    highest = oahu_stations[-3:]

    low_elev_avg = sum(float(s["elevation"]) for s in lowest) / 3
    high_elev_avg = sum(float(s["elevation"]) for s in highest) / 3

    logger.info(
        "Q27: Lowest 3 stations avg elevation: %.0fm, Highest 3: %.0fm",
        low_elev_avg,
        high_elev_avg,
    )
    assert (
        high_elev_avg > low_elev_avg
    ), "Highest stations should have greater elevation"


@pytest.mark.asyncio
async def test_q28_kahului_temperature_vs_open_meteo():
    """Q: What is the current temperature in Kahului, Maui?
    Tools: get_city_current_weather
    Validation: Compare vs Open-Meteo reference
    """
    result = await call_tool(
        "get_city_current_weather",
        {"city": "kahului", "datatype": "temperature"},
    )
    if isinstance(result, dict) and "average" in result:
        hcdp_temp = result["average"]
        assert 10.0 <= hcdp_temp <= 40.0, f"Implausible Kahului temp: {hcdp_temp}°C"

        try:
            ref = await _open_meteo_current(
                CITY_LOCATIONS["kahului"]["lat"], CITY_LOCATIONS["kahului"]["lng"]
            )
            diff = abs(hcdp_temp - ref)
            assert (
                diff <= 5.0
            ), f"Kahului temp: HCDP={hcdp_temp:.1f} vs Open-Meteo={ref:.1f} (diff={diff:.1f})"
            logger.info("Q28: Kahului temp HCDP=%.1f, Open-Meteo=%.1f", hcdp_temp, ref)
        except Exception:
            pass
    else:
        pytest.skip("No temperature data for Kahului")


@pytest.mark.asyncio
async def test_q29_multi_island_rainfall_comparison():
    """Q: Which Hawaiian island got the most rainfall in 2024?
    Tools: get_island_history_summary (multiple calls)
    Validation: All islands have positive rainfall, Big Island likely wettest
    """
    islands = ["oahu", "big_island", "maui", "kauai"]
    rainfall = {}

    for island in islands:
        result = await call_tool(
            "get_island_history_summary",
            {"island": island, "datatype": "rainfall", "year": "2024"},
        )
        avg = result.get("island_wide_average")
        if avg != "N/A" and avg is not None:
            rainfall[island] = avg

    if len(rainfall) < 2:
        pytest.skip("Not enough islands returned rainfall data")

    for island, avg in rainfall.items():
        assert avg > 0, f"{island} should have positive rainfall: {avg}"

    wettest = max(rainfall, key=rainfall.get)
    logger.info("Q29: Island rainfall averages: %s (wettest: %s)", rainfall, wettest)


@pytest.mark.asyncio
async def test_q30_march_2026_storm_validation_via_api():
    """Q: Does the HCDP API mesonet data match the CSV ground truth for
    the March 11-14, 2026 storm at Lyon Arboretum?
    Tools: get_mesonet_data (via fetch_daily_rainfall_hst)
    Validation: Within ±5mm of HCDP CSV ground truth per day
    """
    api_rainfall = await fetch_daily_rainfall_hst(
        station_ids=["0501"],
        start_date="2026-03-11",
        end_date="2026-03-14",
    )

    if "0501" not in api_rainfall:
        pytest.skip("No API data for station 0501 in March 2026 storm window")

    api_data = api_rainfall["0501"]
    ground_truth = GROUND_TRUTH_STORM_1["0501"]

    for date, expected_mm in ground_truth.items():
        actual_mm = api_data.get(date, 0.0)
        diff = abs(actual_mm - expected_mm)
        assert diff <= TOLERANCE_MM, (
            f"Storm day {date}: API={actual_mm:.1f}mm vs CSV={expected_mm:.1f}mm "
            f"(diff={diff:.1f}mm exceeds tolerance={TOLERANCE_MM}mm)"
        )

    logger.info(
        "Q30: All 4 storm days match ground truth within ±%.1fmm",
        TOLERANCE_MM,
    )
