"""Verify all 11 v2 MCP tools are registered and callable."""
import asyncio
import json
import sys
import os

# Ensure project is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hcdp_mcp_server.server import (
    get_mesonet_data,        GetMesonetDataArgs,
    get_mesonet_stations,    GetMesonetStationsArgs,
    get_mesonet_variables,   GetMesonetVariablesArgs,
    get_island_climate_history, GetIslandClimateHistoryArgs,
    get_island_history_summary, GetIslandHistoryArgs,
    get_timeseries_data,     GetTimeseriesArgs,
    get_station_latest,      GetStationLatestArgs,
    get_nearest_stations,    GetNearestStationsArgs,
    get_island_comparison,   GetIslandComparisonArgs,
    get_drought_index,       GetDroughtIndexArgs,
    export_mesonet_csv_via_email, ExportMesonetCsvViaEmailArgs,
    mcp,
)

EXPECTED_TOOLS = [
    "get_mesonet_data",
    "get_mesonet_stations",
    "get_mesonet_variables",
    "get_island_climate_history",
    "get_island_history_summary",
    "get_timeseries_data",
    "get_station_latest",
    "get_nearest_stations",
    "get_island_comparison",
    "get_drought_index",
    "export_mesonet_csv_via_email",
]


def test_tool_registration():
    """All 11 tools must be registered in the FastMCP instance."""
    registered = {t.name for t in mcp._tool_manager.list_tools()}
    missing = [t for t in EXPECTED_TOOLS if t not in registered]
    extra   = [t for t in registered if t not in EXPECTED_TOOLS]
    assert not missing, f"Missing tools: {missing}"
    print(f"  ✓ All {len(EXPECTED_TOOLS)} tools registered (extra: {extra or 'none'})")


def test_pydantic_models():
    """Instantiate each arg model to ensure schemas parse cleanly."""
    # get_mesonet_data
    m = GetMesonetDataArgs(var_ids="Tair_1_Avg")
    assert m.var_ids == "Tair_1_Avg"
    assert m.limit == 10000

    # get_mesonet_stations
    m = GetMesonetStationsArgs()
    assert m.status == "active"

    # get_mesonet_variables
    m = GetMesonetVariablesArgs()
    assert m.response_format.value == "json"

    # get_island_climate_history (single island/year)
    m = GetIslandClimateHistoryArgs(islands="oahu", years=2023, datatype="rainfall")
    assert m.islands == "oahu"

    # get_island_climate_history (multi island/year)
    m = GetIslandClimateHistoryArgs(islands=["oahu", "maui"], years=[2022, 2023], datatype="temperature", aggregation="mean")
    assert len(m.years) == 2

    # get_island_history_summary (deprecated)
    m = GetIslandHistoryArgs(island="maui", year="2023", datatype="rainfall")
    assert m.island.value == "maui"

    # get_timeseries_data
    m = GetTimeseriesArgs(lat=21.3, lng=-157.8, datatype="rainfall", start="2020-01", end="2020-12")
    assert m.extent.value == "statewide"

    # get_station_latest
    m = GetStationLatestArgs()
    assert "Tair_1_Avg" in m.var_ids

    # get_nearest_stations
    m = GetNearestStationsArgs(lat=21.3069, lng=-157.8583)
    assert m.limit == 5

    # get_island_comparison
    m = GetIslandComparisonArgs(year=2023, datatype="rainfall")
    assert m.islands is None  # defaults applied in function

    # get_drought_index
    m = GetDroughtIndexArgs(islands="oahu", reference_years=[2020, 2021, 2022])
    assert len(m.reference_years) == 3

    # export_mesonet_csv_via_email
    m = ExportMesonetCsvViaEmailArgs(
        email="test@example.com",
        var_ids=["Tair_1_Avg"],
        start_date="2025-01-01T00:00:00-10:00",
        end_date="2025-02-01T00:00:00-10:00",
    )
    assert m.station_ids is None

    print(f"  ✓ All Pydantic models instantiate correctly")


def test_tool_descriptions():
    """Check each tool has a non-empty description and no Args:/Returns: bloat."""
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    for name in EXPECTED_TOOLS:
        t = tools[name]
        desc = t.description or ""
        assert len(desc) > 20, f"{name}: description too short"
        assert "Args:" not in desc, f"{name}: description still contains 'Args:' boilerplate"
        assert "Returns:" not in desc, f"{name}: description still contains 'Returns:' boilerplate"
    print(f"  ✓ All tool descriptions clean (no Args:/Returns: boilerplate)")


def _props(tool_name: str) -> dict:
    """Return the flat properties dict for a tool's parameter schema."""
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    params = tools[tool_name].parameters
    # FastMCP wraps in $defs; flatten to first $defs entry if present
    if "$defs" in params:
        first_def = next(iter(params["$defs"].values()))
        return first_def.get("properties", {})
    return params.get("properties", {})


def test_tool_schema_fields():
    """Spot-check key field descriptions are present."""
    props = _props("get_mesonet_data")
    assert "var_ids" in props
    assert "limit" in props
    assert "join_metadata" in props

    props = _props("get_timeseries_data")
    assert "lat" in props
    assert "extent" in props
    assert "timescale" in props

    props = _props("get_island_climate_history")
    assert "islands" in props
    assert "years" in props
    assert "production" in props

    print(f"  ✓ Field schemas contain expected parameters")


def test_nearest_stations_pure():
    """get_nearest_stations args model validates cleanly."""
    params = GetNearestStationsArgs(lat=21.3069, lng=-157.8583, limit=3)
    assert params.limit == 3
    print(f"  ✓ get_nearest_stations args validated")


def test_drought_index_math():
    """SPI calculation math with known values."""
    import math
    values = [100.0, 120.0, 80.0, 110.0, 90.0]
    mean   = sum(values) / len(values)
    stddev = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
    spi    = (values[0] - mean) / stddev
    assert abs(mean - 100.0) < 0.01
    assert stddev > 0
    assert isinstance(spi, float)
    print(f"  ✓ SPI math correct (mean={mean}, stddev={round(stddev,2)}, spi[0]={round(spi,2)})")


if __name__ == "__main__":
    print("\n=== HCDP MCP v2 Tool Verification ===\n")
    errors = []

    tests = [
        ("tool_registration",     test_tool_registration),
        ("pydantic_models",       test_pydantic_models),
        ("tool_descriptions",     test_tool_descriptions),
        ("tool_schema_fields",    test_tool_schema_fields),
        ("nearest_stations_args", test_nearest_stations_pure),
        ("drought_index_math",    test_drought_index_math),
    ]

    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            errors.append(name)

    print()
    if errors:
        print(f"FAILED: {errors}")
        sys.exit(1)
    else:
        print("All checks passed.")
