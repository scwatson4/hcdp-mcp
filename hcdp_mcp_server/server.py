"""HCDP MCP Server - Main server implementation (v2.0)."""

import asyncio
import json
import math
import os
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

load_dotenv()

# ── Server ────────────────────────────────────────────────────────────────────
mcp = FastMCP("hcdp_mcp")

# ── Constants ─────────────────────────────────────────────────────────────────
HCDP_API_BASE   = os.environ.get("HCDP_BASE_URL", "https://api.hcdp.ikewai.org")
HCDP_API_TOKEN  = os.environ.get("HCDP_API_TOKEN", "")
REQUEST_TIMEOUT = 30.0

# Representative lat/lng points per island (domain knowledge — not in API)
ISLAND_REGIONS: Dict[str, List[Dict[str, Any]]] = {
    "oahu": [
        {"location": "Honolulu (South)",   "lat": 21.3069, "lng": -157.8583},
        {"location": "Kaneohe (Windward)", "lat": 21.4022, "lng": -157.8025},
        {"location": "Kapolei (Leeward)",  "lat": 21.3356, "lng": -158.0709},
        {"location": "Wahiawa (Central)",  "lat": 21.5027, "lng": -158.0241},
        {"location": "North Shore",        "lat": 21.6389, "lng": -158.0617},
    ],
    "big_island": [
        {"location": "Hilo (East/Wet)",        "lat": 19.7297, "lng": -155.0900},
        {"location": "Kona (West/Dry)",         "lat": 19.6400, "lng": -155.9969},
        {"location": "Volcano (Highland/Wet)",  "lat": 19.4328, "lng": -155.2835},
        {"location": "South Point",             "lat": 18.9109, "lng": -155.6831},
        {"location": "Waimea (Upcountry)",      "lat": 20.0211, "lng": -155.6694},
    ],
    "maui": [
        {"location": "Kahului (Central)",  "lat": 20.8893, "lng": -156.4729},
        {"location": "Hana (East/Wet)",    "lat": 20.7579, "lng": -155.9894},
        {"location": "Lahaina (West/Dry)", "lat": 20.8783, "lng": -156.6825},
        {"location": "Kula (Upcountry)",   "lat": 20.7644, "lng": -156.3322},
    ],
    "kauai": [
        {"location": "Lihue (East)",        "lat": 21.9811, "lng": -159.3711},
        {"location": "Poipu (South)",       "lat": 21.8722, "lng": -159.4681},
        {"location": "Princeville (North)", "lat": 22.2161, "lng": -159.4814},
        {"location": "Waimea (West)",       "lat": 21.9567, "lng": -159.6667},
        {"location": "Kokee (Mountain)",    "lat": 22.1167, "lng": -159.6333},
    ],
    "molokai": [
        {"location": "Kaunakakai (Central)", "lat": 21.0894, "lng": -157.0222},
        {"location": "East Molokai",          "lat": 21.1333, "lng": -156.7500},
    ],
    "lanai": [
        {"location": "Lanai City",  "lat": 20.8283, "lng": -156.9200},
        {"location": "Shipwreck",   "lat": 20.9000, "lng": -156.8333},
    ],
}

# Maps human-friendly datatype names → Mesonet var_ids (for get_mesonet_data)
MESONET_DATATYPE_VAR_MAP: Dict[str, str] = {
    "rainfall":    "RF_1_Tot3600s",
    "temperature": "Tair_1_Avg",
    "humidity":    "RH_1_Avg",
    "wind_speed":  "WS_1_Avg",
    "vpd":         "VPD_1_Avg",
}

# Maps island names → raster extent codes (for /raster/timeseries)
# Per YAML: extent enum is [statewide, bi, ka, oa, mn]
ISLAND_EXTENT_MAP: Dict[str, str] = {
    "oahu":       "oa",
    "big_island": "bi",
    "maui":       "mn",   # Maui County (includes Molokai/Lanai)
    "kauai":      "ka",
    "molokai":    "mn",   # Maui County
    "lanai":      "mn",   # Maui County
}


# ── Shared enums ──────────────────────────────────────────────────────────────
class ResponseFormat(str, Enum):
    JSON     = "json"
    MARKDOWN = "markdown"


class IslandName(str, Enum):
    OAHU       = "oahu"
    BIG_ISLAND = "big_island"
    MAUI       = "maui"
    KAUAI      = "kauai"
    MOLOKAI    = "molokai"
    LANAI      = "lanai"


# Raster API datatypes — per YAML: [rainfall, temperature, relative_humidity, spi, ndvi_modis, ignition_probability]
class RasterDatatype(str, Enum):
    RAINFALL             = "rainfall"
    TEMPERATURE          = "temperature"
    RELATIVE_HUMIDITY    = "relative_humidity"
    SPI                  = "spi"
    NDVI_MODIS           = "ndvi_modis"
    IGNITION_PROBABILITY = "ignition_probability"


# Mesonet-friendly datatype names (mapped to var_ids internally)
class MesonetDatatype(str, Enum):
    RAINFALL    = "rainfall"
    TEMPERATURE = "temperature"
    HUMIDITY    = "humidity"
    WIND_SPEED  = "wind_speed"
    VPD         = "vpd"


# Raster extent codes — per YAML enum
class RasterExtent(str, Enum):
    STATEWIDE  = "statewide"
    BIG_ISLAND = "bi"
    KAUAI      = "ka"
    OAHU       = "oa"
    MAUI       = "mn"


# Temperature aggregation — per YAML enum [min, max, mean]
class TempAggregation(str, Enum):
    MIN  = "min"
    MAX  = "max"
    MEAN = "mean"


# SPI timescale — per YAML enum
class SpiTimescale(str, Enum):
    T001 = "timescale001"
    T003 = "timescale003"
    T006 = "timescale006"
    T009 = "timescale009"
    T012 = "timescale012"
    T024 = "timescale024"
    T036 = "timescale036"
    T048 = "timescale048"
    T060 = "timescale060"


# Period — per YAML enum [month, day]
class Period(str, Enum):
    MONTH = "month"
    DAY   = "day"


# ── Shared HTTP helpers ───────────────────────────────────────────────────────
def _auth_headers() -> Dict[str, str]:
    if HCDP_API_TOKEN:
        return {"Authorization": f"Bearer {HCDP_API_TOKEN}"}
    return {}


async def hcdp_get(path: str, params: Dict[str, Any]) -> Any:
    """GET request to HCDP API with auth and error handling."""
    # Remove None values — HCDP rejects null params
    clean = {k: v for k, v in params.items() if v is not None}
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(
            f"{HCDP_API_BASE}{path}", params=clean, headers=_auth_headers()
        )
    resp.raise_for_status()
    return resp.json()


async def hcdp_post(path: str, body: Dict[str, Any]) -> Any:
    """POST request to HCDP API with JSON body and auth."""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{HCDP_API_BASE}{path}",
            json=body,
            headers={**_auth_headers(), "Content-Type": "application/json"},
        )
    resp.raise_for_status()
    # 202 responses return plain text confirmation
    if resp.status_code == 202:
        return {"status": 202, "message": resp.text}
    return resp.json()


def _handle_error(e: Exception) -> str:
    """Consistent actionable error messages."""
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        msgs = {
            400: "Bad request — check parameter values (dates, var_ids, extent, datatype).",
            401: "Auth failed — check HCDP_API_TOKEN env var.",
            404: "Not found — the requested resource does not exist.",
            429: "Rate limited — wait before retrying.",
        }
        return json.dumps({"error": msgs.get(code, f"API error {code}."), "status": code})
    if isinstance(e, httpx.TimeoutException):
        return json.dumps({"error": "Request timed out. Try narrowing the date range."})
    return json.dumps({"error": f"{type(e).__name__}: {e}"})


# ── Tool 1: get_mesonet_data ──────────────────────────────────────────────────
class GetMesonetDataArgs(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    var_ids: str = Field(
        ...,
        description=(
            "Comma-separated Mesonet variable IDs. "
            "Use get_mesonet_variables to discover valid IDs. "
            "Examples: 'RF_1_Tot300s', 'Tair_1_Avg', 'RH_1_Avg,WS_1_Avg,VPD_1_Avg'"
        ),
    )
    start_date: Optional[str] = Field(
        default=None,
        description=(
            "ISO 8601 date string. Formats: YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss-10:00. "
            "Mesonet data available from ~2023 onward."
        ),
    )
    end_date: Optional[str] = Field(
        default=None,
        description="ISO 8601 end date string (inclusive).",
    )
    station_ids: Optional[str] = Field(
        default=None,
        description=(
            "Comma-separated 4-digit station IDs (e.g. '0502,0521'). "
            "Use get_mesonet_stations to discover IDs."
        ),
    )
    limit: int = Field(
        default=10000,
        ge=1,
        le=1000000,
        description=(
            "Max records per page. API default is 10,000; max is 1,000,000. "
            "For Code Mode pagination loops, use date ranges instead of high limits."
        ),
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Records to skip for pagination. Use with limit.",
    )
    join_metadata: Optional[str] = Field(
        default="true",
        description=(
            "If any value provided, station and variable metadata is included per row. "
            "Pass 'true' to enable (API checks presence, not value)."
        ),
    )
    flags: Optional[str] = Field(
        default=None,
        description="Comma-separated data flag values to filter by.",
    )
    reverse: Optional[str] = Field(
        default=None,
        description=(
            "If any value provided, results are sorted oldest-first. "
            "Default (None) returns most-recent-first."
        ),
    )
    local_tz: Optional[str] = Field(
        default=None,
        description="If any value provided, timestamps are converted to Hawaii local time.",
    )
    row_mode: Optional[str] = Field(
        default=None,
        description=(
            "Response row format. Options: 'array', 'wide_array', 'json', 'wide_json'. "
            "Default (None) returns JSON array of objects."
        ),
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'json' for Code Mode programs, 'markdown' for human display.",
    )


@mcp.tool(
    name="get_mesonet_data",
    annotations={
        "title": "Mesonet Time-Series Measurements",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_mesonet_data(params: GetMesonetDataArgs) -> str:
    """Fetch raw Mesonet station measurements with full pagination support.

    Returns time-series records for requested variables and date range.
    Each record contains timestamp, station_id, variable, value, units,
    and (if join_metadata set) station name, lat, lng, elevation.

    PAGINATION: Check has_more in response. Use next_offset for subsequent pages.
    For Code Mode programs handling long date ranges, prefer date-range slicing
    over high offsets — date ranges are better optimized per the API spec.

    DATA AVAILABILITY: Mesonet data available from ~2023 onward.
    For pre-2023 historical data use get_island_climate_history or get_timeseries_data.

    Args:
        params (GetMesonetDataArgs): Validated input parameters.

    Returns:
        str: JSON with keys:
            - records (list): measurement rows
            - count (int): records in this page
            - offset (int): current offset
            - has_more (bool): whether more pages likely exist
            - next_offset (int|null): offset for next page
    """
    try:
        api_params: Dict[str, Any] = {
            "location":      "hawaii",
            "var_ids":       params.var_ids,
            "limit":         params.limit,
            "offset":        params.offset,
            "join_metadata": params.join_metadata,
            "start_date":    params.start_date,
            "end_date":      params.end_date,
            "station_ids":   params.station_ids,
            "flags":         params.flags,
            "reverse":       params.reverse,
            "local_tz":      params.local_tz,
            "row_mode":      params.row_mode,
        }

        data = await hcdp_get("/mesonet/db/measurements", api_params)
        records = data if isinstance(data, list) else data.get("data", data)
        count = len(records) if isinstance(records, list) else 0
        has_more = count == params.limit
        next_offset = params.offset + count if has_more else None

        result = {
            "records":     records,
            "count":       count,
            "offset":      params.offset,
            "has_more":    has_more,
            "next_offset": next_offset,
        }

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [
                f"## Mesonet Data — {count} records (offset {params.offset})",
                f"**has_more:** {has_more} | **next_offset:** {next_offset}",
                "",
                "| Timestamp | Station | Variable | Value | Units |",
                "|---|---|---|---|---|",
            ]
            for r in (records[:50] if isinstance(records, list) else []):
                lines.append(
                    f"| {r.get('timestamp','')} | {r.get('station_id','')} "
                    f"| {r.get('variable','')} | {r.get('value','')} | {r.get('units','')} |"
                )
            if count > 50:
                lines.append(f"_...{count - 50} more rows. Use JSON format for full data._")
            return "\n".join(lines)

        return json.dumps(result)

    except Exception as e:
        return _handle_error(e)


# ── Tool 2: get_mesonet_stations ──────────────────────────────────────────────
class GetMesonetStationsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: str = Field(
        default="hawaii",
        description="Network location. Options: 'hawaii', 'american_samoa'.",
    )
    status: Optional[str] = Field(
        default="active",
        description=(
            "Filter by station status client-side: 'active', 'inactive', 'planned', or null for all. "
            "NOTE: This is a client-side filter — the API returns all stations regardless."
        ),
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'json' for Code Mode programs, 'markdown' for human display.",
    )


@mcp.tool(
    name="get_mesonet_stations",
    annotations={
        "title": "Mesonet Station Metadata",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_mesonet_stations(params: GetMesonetStationsArgs) -> str:
    """List all Mesonet weather stations with metadata.

    Returns station IDs, names, lat/lng, elevation, and status for all stations.
    Use to discover station_ids for get_mesonet_data, or to find stations on a
    specific island for get_nearest_stations.

    Island bounding boxes for Code Mode filtering:
      - Oahu:       lat 21.2-21.7,  lng -158.3 to -157.6
      - Big Island: lat 18.9-20.3,  lng -156.1 to -154.8
      - Maui:       lat 20.5-21.0,  lng -156.7 to -155.9
      - Kauai:      lat 21.8-22.3,  lng -159.8 to -159.2

    Args:
        params (GetMesonetStationsArgs): Validated input parameters.

    Returns:
        str: JSON with keys:
            - stations (list): station objects with station_id, name, lat, lng, elevation, status
            - count (int): number of stations returned
    """
    try:
        data = await hcdp_get("/mesonet/db/stations", {"location": params.location})
        stations = data if isinstance(data, list) else data.get("data", [])

        # Client-side status filter (API does not support this param)
        if params.status:
            stations = [s for s in stations if s.get("status") == params.status]

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [
                f"## Mesonet Stations ({len(stations)} {params.status or 'all'})",
                "",
                "| ID | Name | Lat | Lng | Elevation | Status |",
                "|---|---|---|---|---|---|",
            ]
            for s in stations:
                lines.append(
                    f"| {s.get('station_id')} | {s.get('full_name', s.get('name'))} "
                    f"| {s.get('lat')} | {s.get('lng')} | {s.get('elevation')}m | {s.get('status')} |"
                )
            return "\n".join(lines)

        return json.dumps({"stations": stations, "count": len(stations)})

    except Exception as e:
        return _handle_error(e)


# ── Tool 3: get_mesonet_variables ─────────────────────────────────────────────
class GetMesonetVariablesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'json' for Code Mode programs, 'markdown' for human display.",
    )


@mcp.tool(
    name="get_mesonet_variables",
    annotations={
        "title": "Mesonet Variable Definitions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_mesonet_variables(params: GetMesonetVariablesArgs) -> str:
    """List all measurable Mesonet weather variables with units and display names.

    Returns the full variable catalog. Code Mode programs use this to map
    user intent ('humidity') to the correct var_id ('RH_1_Avg') for get_mesonet_data.

    Key variables for common queries:
      - Rainfall 5-min:      RF_1_Tot300s   (mm)
      - Rainfall hourly:     RF_1_Tot3600s  (mm)
      - Rainfall daily:      RF_1_Tot86400s (mm)
      - Temperature:         Tair_1_Avg     (degrees C)
      - Relative Humidity:   RH_1_Avg       (%)
      - Wind Speed:          WS_1_Avg       (m/s)
      - Vapor Pressure Def:  VPD_1_Avg      (kPa)
      - Fuel Moisture:       FM_1_Avg       (%)

    Args:
        params (GetMesonetVariablesArgs): Validated input parameters.

    Returns:
        str: JSON with keys:
            - variables (list): variable objects with standard_name, display_name, units
            - count (int)
    """
    try:
        # No location param for this endpoint per spec
        data = await hcdp_get("/mesonet/db/variables", {})
        variables = data if isinstance(data, list) else data.get("data", [])

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [
                f"## Mesonet Variables ({len(variables)} total)",
                "",
                "| var_id (standard_name) | Display Name | Units |",
                "|---|---|---|",
            ]
            for v in variables:
                if v.get("standard_name"):
                    lines.append(
                        f"| `{v['standard_name']}` | {v.get('display_name','')} | {v.get('units_plain','')} |"
                    )
            return "\n".join(lines)

        return json.dumps({"variables": variables, "count": len(variables)})

    except Exception as e:
        return _handle_error(e)


# ── Tool 4: get_island_climate_history ────────────────────────────────────────
class GetIslandClimateHistoryArgs(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    islands: Union[IslandName, List[IslandName]] = Field(
        ...,
        description=(
            "Island or list of islands. "
            "Single: 'oahu'. Multi: ['oahu','maui','big_island','kauai']. "
            "Valid: 'oahu', 'big_island', 'maui', 'kauai', 'molokai', 'lanai'."
        ),
    )
    years: Union[int, List[int]] = Field(
        ...,
        description=(
            "Year or list of years. "
            "Rainfall available: 1990-present (new) or 1920-2012 (legacy monthly). "
            "Single: 2024. Multi: [2020,2021,2022,2023,2024]."
        ),
    )
    datatype: RasterDatatype = Field(
        ...,
        description=(
            "Raster climate variable. "
            "Options: 'rainfall', 'temperature', 'relative_humidity', "
            "'spi', 'ndvi_modis', 'ignition_probability'."
        ),
    )
    production: str = Field(
        default="new",
        description=(
            "Rainfall production method (only used when datatype='rainfall'). "
            "'new' = 1990-present. 'legacy' = 1920-2012 monthly only."
        ),
    )
    aggregation: Optional[TempAggregation] = Field(
        default=None,
        description=(
            "Temperature aggregation (only used when datatype='temperature'). "
            "Options: 'min', 'max', 'mean'."
        ),
    )
    period: Period = Field(
        default=Period.MONTH,
        description="Aggregation period: 'month' (default) or 'day'.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'json' for Code Mode programs, 'markdown' for human/chatbot display.",
    )


async def _fetch_single_island_year(
    island: str,
    year: int,
    datatype: str,
    production: str,
    aggregation: Optional[str],
    period: str,
) -> Dict[str, Any]:
    """Fetch one island-year combination from /raster/timeseries. Called in parallel."""
    # Per YAML spec: /raster/timeseries uses start/end (not start_date/end_date)
    # and requires extent; uses datatype (not var_id); no fill param
    extent = ISLAND_EXTENT_MAP.get(island, "statewide")
    regions = ISLAND_REGIONS.get(island, [])
    if not regions:
        return {
            "island": island, "year": year, "datatype": datatype,
            "island_wide_average": None, "regional_breakdown": [],
            "coverage_note": f"No representative regions defined for {island}.",
        }

    async def fetch_region(region: Dict[str, Any]) -> Dict[str, Any]:
        try:
            params: Dict[str, Any] = {
                "lat":        region["lat"],
                "lng":        region["lng"],
                "start":      f"{year}-01",       # YYYY-MM format per spec
                "end":        f"{year}-12",        # YYYY-MM format per spec
                "datatype":   datatype,            # raster uses datatype, not var_id
                "extent":     extent,              # required per spec
                "period":     period,
                "production": production,          # required for rainfall
            }
            if aggregation:
                params["aggregation"] = aggregation
            data = await hcdp_get("/raster/timeseries", params)
            # Response is a JSON object with date keys and numeric values
            if isinstance(data, dict):
                values = [float(v) for v in data.values() if v is not None]
            elif isinstance(data, list):
                values = [float(v) for v in data if v is not None]
            else:
                return {"location": region["location"], "message": "Unexpected response format"}
            if not values:
                return {"location": region["location"], "message": "No data returned"}
            return {
                "location":    region["location"],
                "average":     round(sum(values) / len(values), 3),
                "min":         round(min(values), 3),
                "max":         round(max(values), 3),
                "data_points": len(values),
            }
        except Exception as ex:
            return {"location": region["location"], "message": f"Error: {ex}"}

    regional_results = await asyncio.gather(*[fetch_region(r) for r in regions])
    valid = [r for r in regional_results if "average" in r]
    island_wide = round(sum(r["average"] for r in valid) / len(valid), 3) if valid else None
    return {
        "island":              island,
        "year":                year,
        "datatype":            datatype,
        "island_wide_average": island_wide,
        "regional_breakdown":  list(regional_results),
        "coverage_note":       None if valid else "No data returned for any region.",
    }


@mcp.tool(
    name="get_island_climate_history",
    annotations={
        "title": "Island Climate History (Multi-Island, Multi-Year)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_island_climate_history(params: GetIslandClimateHistoryArgs) -> str:
    """Fetch historical climate data for one or more Hawaiian islands across one or more years.

    Returns regional breakdowns with island_wide_average per year per island.
    Accepts arrays for both islands and years — all combinations fetched in parallel.
    A single call replaces what previously required 20 sequential calls (4 islands x 5 years).

    Internally calls /raster/timeseries for each representative regional point.
    Rainfall data available from 1990 (new) or 1920 (legacy monthly).

    DO NOT use for real-time conditions — use get_station_latest instead.

    Code Mode example (statewide 5-year drought analysis in one call):
        result = get_island_climate_history(
            islands=["oahu","maui","big_island","kauai"],
            years=[2020,2021,2022,2023,2024],
            datatype="rainfall"
        )
        # Returns 20 island-year records. Compute SPI locally. Write to Postgres.

    Args:
        params (GetIslandClimateHistoryArgs): Validated input parameters.

    Returns:
        str: JSON with keys:
            - results (list): one entry per island-year with island_wide_average,
              regional_breakdown (avg/min/max/data_points per region), coverage_note
            - total_combinations (int)
            - missing_data (list): island-year pairs with no data
    """
    try:
        island_list = [params.islands] if isinstance(params.islands, str) else list(params.islands)
        year_list   = [params.years]   if isinstance(params.years, int)   else list(params.years)

        # Normalise enum values to strings
        island_strs  = [i.value if hasattr(i, "value") else i for i in island_list]
        datatype_str = params.datatype.value if hasattr(params.datatype, "value") else params.datatype
        agg_str      = params.aggregation.value if params.aggregation and hasattr(params.aggregation, "value") else params.aggregation

        tasks = [
            _fetch_single_island_year(island, year, datatype_str, params.production, agg_str, params.period.value)
            for island in island_strs
            for year in year_list
        ]
        results = await asyncio.gather(*tasks)

        missing = [f"{r['island']}-{r['year']}" for r in results if r.get("island_wide_average") is None]
        response = {
            "results":            list(results),
            "total_combinations": len(results),
            "missing_data":       missing,
        }

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [
                f"## Island Climate History — {params.datatype.value}",
                f"**Islands:** {', '.join(island_strs)} | **Years:** {', '.join(str(y) for y in year_list)}",
                "",
                "| Island | Year | Island-Wide Avg | Coverage |",
                "|---|---|---|---|",
            ]
            for r in results:
                avg  = f"{r['island_wide_average']:.2f}" if r["island_wide_average"] is not None else "—"
                note = r.get("coverage_note") or "ok"
                lines.append(f"| {r['island']} | {r['year']} | {avg} | {note} |")
            if missing:
                lines.append(f"\nMissing data for: {', '.join(missing)}")
            return "\n".join(lines)

        return json.dumps(response)

    except Exception as e:
        return _handle_error(e)


# ── Tool 5: get_island_history_summary (deprecated alias) ────────────────────
class GetIslandHistoryArgs(BaseModel):
    """DEPRECATED: Use get_island_climate_history with array parameters instead."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    island: IslandName   = Field(..., description="Island name.")
    year:   str          = Field(..., description="Year string e.g. '2024'.")
    datatype: RasterDatatype = Field(..., description="Climate variable (raster datatype).")


@mcp.tool(
    name="get_island_history_summary",
    annotations={
        "title": "Island History Summary [DEPRECATED — use get_island_climate_history]",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_island_history_summary(params: GetIslandHistoryArgs) -> str:
    """DEPRECATED: Use get_island_climate_history instead (accepts arrays, 20x more efficient).
    Kept for backward compatibility only.
    """
    evolved = GetIslandClimateHistoryArgs(
        islands=params.island,
        years=int(params.year),
        datatype=params.datatype,
        response_format=ResponseFormat.JSON,
    )
    result_str = await get_island_climate_history(evolved)
    result = json.loads(result_str)
    if result.get("results"):
        r = result["results"][0]
        return json.dumps({
            "island":              r["island"],
            "year":                params.year,
            "datatype":            r["datatype"],
            "island_wide_average": r["island_wide_average"],
            "regional_breakdown":  r["regional_breakdown"],
        })
    return result_str


# ── Tool 6: get_timeseries_data ───────────────────────────────────────────────
class GetTimeseriesArgs(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    lat: float = Field(..., ge=18.0, le=23.0, description="Latitude (Hawaii: 18.0-23.0).")
    lng: float = Field(..., ge=-161.0, le=-154.0, description="Longitude (Hawaii: -161.0 to -154.0).")
    datatype: RasterDatatype = Field(
        ...,
        description=(
            "Raster climate variable. Per YAML spec: "
            "'rainfall', 'temperature', 'relative_humidity', "
            "'spi', 'ndvi_modis', 'ignition_probability'."
        ),
    )
    start: str = Field(
        ...,
        description=(
            "ISO 8601 start date. Use YYYY-MM for monthly (e.g. '1920-01'). "
            "Rainfall legacy data goes back to 1920-01."
        ),
    )
    end: str = Field(
        ...,
        description="ISO 8601 end date (inclusive). Use YYYY-MM for monthly.",
    )
    extent: RasterExtent = Field(
        default=RasterExtent.STATEWIDE,
        description=(
            "Spatial extent of raster. Per spec: "
            "'statewide', 'bi' (Big Island), 'ka' (Kauai), 'oa' (Oahu), 'mn' (Maui County). "
            "Use 'statewide' if unsure."
        ),
    )
    period: Period = Field(
        default=Period.MONTH,
        description="Aggregation period: 'month' (default) or 'day'.",
    )
    production: Optional[str] = Field(
        default="new",
        description=(
            "Rainfall production method (only for datatype='rainfall'). "
            "'new' = 1990-present. 'legacy' = 1920-2012 monthly."
        ),
    )
    aggregation: Optional[TempAggregation] = Field(
        default=None,
        description="Temperature aggregation (only for datatype='temperature'): 'min', 'max', 'mean'.",
    )
    timescale: Optional[SpiTimescale] = Field(
        default=None,
        description=(
            "SPI evaluation timescale (only for datatype='spi'). "
            "e.g. 'timescale001' (1 month), 'timescale012' (12 months)."
        ),
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'json' for Code Mode programs, 'markdown' for human display.",
    )


@mcp.tool(
    name="get_timeseries_data",
    annotations={
        "title": "Historical Raster Timeseries (Point Query)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_timeseries_data(params: GetTimeseriesArgs) -> str:
    """Fetch historical climate timeseries for a lat/lng point from raster data.

    The ONLY tool that accesses pre-2023 historical data (rainfall back to 1920
    with 'legacy' production, or 1990 with 'new' production).

    Date format note: use YYYY-MM for monthly (e.g. start='1920-01', end='2024-12').
    Do NOT pass YYYY-MM-DD for monthly data — use YYYY-MM per spec examples.

    Companion params (required for specific datatypes):
      - datatype='rainfall'    -> production required ('new' or 'legacy')
      - datatype='temperature' -> aggregation required ('min', 'max', 'mean')
      - datatype='spi'         -> timescale required (e.g. 'timescale012')

    Args:
        params (GetTimeseriesArgs): Validated input parameters.

    Returns:
        str: JSON with keys:
            - timeseries (dict|list): date-value pairs from API
            - lat (float), lng (float), datatype (str), extent (str), period (str)
            - count (int): number of data points
            - mean (float), min (float), max (float): summary stats
    """
    try:
        api_params: Dict[str, Any] = {
            "lat":      params.lat,
            "lng":      params.lng,
            "start":    params.start,            # YAML spec uses 'start' not 'start_date'
            "end":      params.end,              # YAML spec uses 'end' not 'end_date'
            "datatype": params.datatype.value,
            "extent":   params.extent.value,     # required per spec
            "period":   params.period.value,
        }
        # Conditional companion params per YAML spec
        if params.datatype == RasterDatatype.RAINFALL and params.production:
            api_params["production"] = params.production
        if params.datatype == RasterDatatype.TEMPERATURE and params.aggregation:
            api_params["aggregation"] = params.aggregation.value
        if params.datatype == RasterDatatype.SPI and params.timescale:
            api_params["timescale"] = params.timescale.value

        data = await hcdp_get("/raster/timeseries", api_params)

        # Response is a JSON object with date-string keys and numeric values
        if isinstance(data, dict):
            values = [float(v) for v in data.values() if v is not None]
        elif isinstance(data, list):
            values = [float(v) for v in data if v is not None]
        else:
            values = []

        summary: Dict[str, Any] = {}
        if values:
            summary = {
                "mean": round(sum(values) / len(values), 3),
                "min":  round(min(values), 3),
                "max":  round(max(values), 3),
            }

        result = {
            "timeseries": data,
            "lat":        params.lat,
            "lng":        params.lng,
            "datatype":   params.datatype.value,
            "extent":     params.extent.value,
            "period":     params.period.value,
            "count":      len(values),
            **summary,
        }

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [
                f"## Historical Timeseries — {params.datatype.value} at ({params.lat}, {params.lng})",
                f"**Period:** {params.start} to {params.end} | **Extent:** {params.extent.value} | **Aggregation:** {params.period.value}",
                f"**Records:** {len(values)} | **Mean:** {summary.get('mean','—')} | "
                f"**Min:** {summary.get('min','—')} | **Max:** {summary.get('max','—')}",
            ]
            return "\n".join(lines)

        return json.dumps(result)

    except Exception as e:
        return _handle_error(e)


# ── Tool 7: get_station_latest ────────────────────────────────────────────────
class GetStationLatestArgs(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    var_ids: Optional[str] = Field(
        default="RF_1_Tot300s,Tair_1_Avg,RH_1_Avg,WS_1_Avg,VPD_1_Avg",
        description=(
            "Comma-separated variable IDs to retrieve latest values for. "
            "The stationMonitor endpoint returns the last value of each requested variable "
            "for ALL active stations — filter by station_id client-side from the result. "
            "Default covers the most common weather variables."
        ),
    )
    station_id: Optional[str] = Field(
        default=None,
        description=(
            "4-digit station ID to filter results client-side (e.g. '0502'). "
            "NOTE: The /mesonet/db/stationMonitor API does not accept station_ids as a param — "
            "this filter is applied after fetching all station data."
        ),
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'json' for Code Mode programs, 'markdown' for human display.",
    )


@mcp.tool(
    name="get_station_latest",
    annotations={
        "title": "Station Latest Readings (Real-Time Snapshot)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def get_station_latest(params: GetStationLatestArgs) -> str:
    """Fetch the most recent measurements for Mesonet stations (real-time snapshot).

    Uses /mesonet/db/stationMonitor which returns a dict keyed by station ID.
    Per the API spec, this endpoint only accepts 'location' and 'var_ids' params.
    Station filtering is applied client-side after fetching.

    The response contains 24hr_latest, 24hr_max, 24hr_min, 24hr_avg_diff per station.

    To get data for a specific station, provide station_id to filter the response.
    To get all active station snapshots, leave station_id as null.

    Pair with get_nearest_stations to find station IDs for a location first.

    Args:
        params (GetStationLatestArgs): Validated input parameters.

    Returns:
        str: JSON with keys:
            - stations (list): each containing station_id, 24hr_latest readings,
              24hr_max, 24hr_min per variable
            - count (int)
            - timestamp_note (str)
    """
    try:
        # Per YAML spec: stationMonitor only accepts location and var_ids
        api_params: Dict[str, Any] = {"location": "hawaii"}
        if params.var_ids:
            api_params["var_ids"] = params.var_ids

        data = await hcdp_get("/mesonet/db/stationMonitor", api_params)

        # Response is a dict keyed by station_id, per MesonetStationMonitorData schema
        if not isinstance(data, dict):
            return json.dumps({
                "error": "Unexpected response format from stationMonitor.",
                "raw": str(data)[:200],
            })

        stations_out = []
        for station_id_key, station_data in data.items():
            # Client-side station filter
            if params.station_id and station_id_key != params.station_id:
                continue

            latest = station_data.get("24hr_latest", {})
            readings = [
                {
                    "variable":  var_id,
                    "value":     reading.get("value"),
                    "timestamp": reading.get("timestamp"),
                }
                for var_id, reading in latest.items()
            ]
            stations_out.append({
                "station_id":    station_id_key,
                "24hr_latest":   readings,
                "24hr_max":      station_data.get("24hr_max", {}),
                "24hr_min":      station_data.get("24hr_min", {}),
                "24hr_avg_diff": station_data.get("24hr_avg_diff", {}),
            })

        if not stations_out and params.station_id:
            return json.dumps({
                "error": (
                    f"Station {params.station_id} not found in stationMonitor response. "
                    "Station may be offline or ID may be incorrect. "
                    "Use get_mesonet_stations to verify the station ID."
                )
            })

        result = {
            "stations":       stations_out,
            "count":          len(stations_out),
            "timestamp_note": "Values are the most recent reading within the last 24 hours per station.",
        }

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [f"## Station Latest Readings ({len(stations_out)} stations)", ""]
            for s in stations_out[:10]:
                lines.append(f"### Station {s['station_id']}")
                lines.append("| Variable | Value | Timestamp |")
                lines.append("|---|---|---|")
                for r in s["24hr_latest"]:
                    lines.append(f"| {r['variable']} | {r['value']} | {r['timestamp']} |")
                lines.append("")
            if len(stations_out) > 10:
                lines.append(f"_...{len(stations_out) - 10} more stations. Use JSON format._")
            return "\n".join(lines)

        return json.dumps(result)

    except Exception as e:
        return _handle_error(e)


# ── Tool 8: get_nearest_stations ──────────────────────────────────────────────
class GetNearestStationsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float    = Field(..., ge=18.0, le=23.0,    description="Latitude of target location.")
    lng: float    = Field(..., ge=-161.0, le=-154.0, description="Longitude of target location.")
    limit: int    = Field(default=5, ge=1, le=20,   description="Number of nearest stations to return.")
    status: str   = Field(default="active",          description="Filter by station status client-side.")
    response_format: ResponseFormat = Field(default=ResponseFormat.JSON)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@mcp.tool(
    name="get_nearest_stations",
    annotations={
        "title": "Nearest Mesonet Stations to a Location",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_nearest_stations(params: GetNearestStationsArgs) -> str:
    """Find the nearest active Mesonet stations to a given lat/lng point.

    Geographic routing primitive. Use to translate place names to station_ids
    for get_mesonet_data or get_station_latest.

    Common Hawaii coordinates:
      - Honolulu:       21.3069, -157.8583
      - Hilo:           19.7297, -155.0900
      - Kona:           19.6400, -155.9969
      - Kahului (Maui): 20.8893, -156.4729
      - Lihue (Kauai):  21.9811, -159.3711

    Args:
        params (GetNearestStationsArgs): Validated input parameters.

    Returns:
        str: JSON with keys:
            - stations (list): sorted by distance_km, each with station_id, name,
              lat, lng, elevation, distance_km, status
            - query_lat (float), query_lng (float), count (int)
    """
    try:
        data = await hcdp_get("/mesonet/db/stations", {"location": "hawaii"})
        stations = data if isinstance(data, list) else data.get("data", [])

        candidates = [
            s for s in stations
            if s.get("status") == params.status and s.get("lat") and s.get("lng")
        ]
        for s in candidates:
            s["distance_km"] = round(
                _haversine_km(params.lat, params.lng, float(s["lat"]), float(s["lng"])), 2
            )
        nearest = sorted(candidates, key=lambda x: x["distance_km"])[:params.limit]

        result = {
            "stations": [
                {
                    "station_id":  s["station_id"],
                    "name":        s.get("name"),
                    "full_name":   s.get("full_name"),
                    "lat":         float(s["lat"]),
                    "lng":         float(s["lng"]),
                    "elevation":   s.get("elevation"),
                    "distance_km": s["distance_km"],
                    "status":      s.get("status"),
                }
                for s in nearest
            ],
            "query_lat": params.lat,
            "query_lng": params.lng,
            "count":     len(nearest),
        }

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [
                f"## Nearest Stations to ({params.lat}, {params.lng})",
                "",
                "| Station ID | Name | Distance | Elevation |",
                "|---|---|---|---|",
            ]
            for s in result["stations"]:
                lines.append(
                    f"| {s['station_id']} | {s['full_name']} | {s['distance_km']} km | {s['elevation']}m |"
                )
            return "\n".join(lines)

        return json.dumps(result)

    except Exception as e:
        return _handle_error(e)


# ── Tool 9: get_island_comparison ─────────────────────────────────────────────
class GetIslandComparisonArgs(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    year: int = Field(..., ge=1920, le=2030, description="Year to compare across islands.")
    datatype: RasterDatatype = Field(..., description="Raster climate variable.")
    islands: Optional[List[IslandName]] = Field(
        default=None,
        description="Islands to compare. Defaults to ['oahu','maui','big_island','kauai'].",
    )
    production: str = Field(default="new", description="Rainfall production method.")
    aggregation: Optional[TempAggregation] = Field(
        default=None, description="Temperature aggregation."
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.JSON)


@mcp.tool(
    name="get_island_comparison",
    annotations={
        "title": "Cross-Island Climate Comparison (Ranked)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_island_comparison(params: GetIslandComparisonArgs) -> str:
    """Fetch and rank climate data across all Hawaiian islands for a given year.

    Returns a sorted comparison answering: 'Which island was driest in 2024?'

    All island fetches run in parallel via get_island_climate_history.

    Args:
        params (GetIslandComparisonArgs): Validated input parameters.

    Returns:
        str: JSON with keys:
            - year (int), datatype (str)
            - ranked (list): sorted ascending by island_wide_average, each with
              rank, island, island_wide_average, min, max, driest_region, wettest_region
            - summary (str): human-readable one-liner
    """
    try:
        island_list = params.islands or [
            IslandName.OAHU, IslandName.MAUI, IslandName.BIG_ISLAND, IslandName.KAUAI
        ]
        fetch_params = GetIslandClimateHistoryArgs(
            islands=island_list,
            years=params.year,
            datatype=params.datatype,
            production=params.production,
            aggregation=params.aggregation,
            response_format=ResponseFormat.JSON,
        )
        raw_str = await get_island_climate_history(fetch_params)
        raw = json.loads(raw_str)
        results = raw.get("results", [])

        ranked_data = []
        for r in results:
            avg   = r.get("island_wide_average")
            valid = [b for b in r.get("regional_breakdown", []) if "average" in b]
            ranked_data.append({
                "island":              r["island"],
                "island_wide_average": avg,
                "min":                 round(min(b["average"] for b in valid), 3) if valid else None,
                "max":                 round(max(b["average"] for b in valid), 3) if valid else None,
                "driest_region":       min(valid, key=lambda x: x["average"])["location"] if valid else None,
                "wettest_region":      max(valid, key=lambda x: x["average"])["location"] if valid else None,
            })

        ranked_data.sort(key=lambda x: (x["island_wide_average"] is None, x["island_wide_average"] or 0))
        for i, item in enumerate(ranked_data):
            item["rank"] = i + 1

        summary = (
            f"In {params.year}, {ranked_data[0]['island']} had the lowest {params.datatype.value} "
            f"({ranked_data[0].get('island_wide_average','—')}) and "
            f"{ranked_data[-1]['island']} had the highest ({ranked_data[-1].get('island_wide_average','—')})."
        ) if ranked_data else ""

        result = {
            "year":     params.year,
            "datatype": params.datatype.value,
            "ranked":   ranked_data,
            "summary":  summary,
        }

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [
                f"## Island {params.datatype.value.title()} Comparison — {params.year}",
                f"_{summary}_", "",
                "| Rank | Island | Avg | Min | Max | Driest Region |",
                "|---|---|---|---|---|---|",
            ]
            for r in ranked_data:
                lines.append(
                    f"| {r['rank']} | {r['island']} | {r['island_wide_average'] or '—'} "
                    f"| {r['min'] or '—'} | {r['max'] or '—'} | {r['driest_region'] or '—'} |"
                )
            return "\n".join(lines)

        return json.dumps(result)

    except Exception as e:
        return _handle_error(e)


# ── Tool 10: get_drought_index ────────────────────────────────────────────────
class GetDroughtIndexArgs(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    islands: Union[IslandName, List[IslandName]] = Field(
        ..., description="Island or list of islands."
    )
    reference_years: List[int] = Field(
        ...,
        min_length=2,
        description="Years defining the reference window. Min 2. SPI computed for each year.",
    )
    datatype: RasterDatatype = Field(
        default=RasterDatatype.RAINFALL,
        description="Raster climate variable. Typically 'rainfall'.",
    )
    production: str = Field(default="new", description="Rainfall production method.")
    response_format: ResponseFormat = Field(default=ResponseFormat.JSON)

    @field_validator("reference_years")
    @classmethod
    def validate_years(cls, v: List[int]) -> List[int]:
        if len(set(v)) < 2:
            raise ValueError("reference_years must have at least 2 distinct years.")
        return sorted(set(v))


@mcp.tool(
    name="get_drought_index",
    annotations={
        "title": "SPI Drought Index (Standardized Precipitation Index)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_drought_index(params: GetDroughtIndexArgs) -> str:
    """Compute SPI (Standardized Precipitation Index) for one or more islands.

    SPI = (observed - mean) / stddev over the reference period.

    Interpretation: >= +2.0 extremely wet | +1.0 to +1.99 moderately wet |
    -0.99 to +0.99 near normal | -1.0 to -1.49 moderate drought |
    -1.5 to -1.99 severe drought | <= -2.0 extreme drought.

    Fetches all data in one parallel call, computes SPI locally.

    Args:
        params (GetDroughtIndexArgs): Validated input parameters.

    Returns:
        str: JSON with keys:
            - datatype (str), reference_period (list[int])
            - results (list): per island — reference_mean, reference_stddev,
              spi_by_year (year: {value, spi, interpretation}), trend
    """
    try:
        island_list = (
            [params.islands] if isinstance(params.islands, (str, IslandName)) else list(params.islands)
        )
        fetch_params = GetIslandClimateHistoryArgs(
            islands=island_list,
            years=params.reference_years,
            datatype=params.datatype,
            production=params.production,
            response_format=ResponseFormat.JSON,
        )
        raw_str = await get_island_climate_history(fetch_params)
        raw = json.loads(raw_str)

        by_island: Dict[str, Dict[int, float]] = {}
        for r in raw.get("results", []):
            island = r["island"]
            val    = r.get("island_wide_average")
            if val is not None:
                by_island.setdefault(island, {})[r["year"]] = val

        def interpret_spi(spi: float) -> str:
            if spi >= 2.0:    return "Extremely wet"
            if spi >= 1.5:    return "Very wet"
            if spi >= 1.0:    return "Moderately wet"
            if spi >= -0.99:  return "Near normal"
            if spi >= -1.49:  return "Moderate drought"
            if spi >= -1.99:  return "Severe drought"
            return "Extreme drought"

        island_strs = [i.value if hasattr(i, "value") else i for i in island_list]
        results = []
        for island_name in island_strs:
            yearly = by_island.get(island_name, {})
            values = list(yearly.values())
            if len(values) < 2:
                results.append({"island": island_name, "error": "Insufficient data for SPI."})
                continue
            mean   = sum(values) / len(values)
            stddev = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))

            spi_by_year: Dict[str, Any] = {}
            for year in params.reference_years:
                val = yearly.get(year)
                if val is not None and stddev > 0:
                    spi = round((val - mean) / stddev, 2)
                    spi_by_year[str(year)] = {
                        "value":          val,
                        "spi":            spi,
                        "interpretation": interpret_spi(spi),
                    }
                elif val is not None:
                    spi_by_year[str(year)] = {
                        "value":          val,
                        "spi":            None,
                        "interpretation": "Insufficient variance",
                    }

            spi_vals = [v["spi"] for v in spi_by_year.values() if v.get("spi") is not None]
            trend = "stable"
            if len(spi_vals) >= 2:
                slope = (spi_vals[-1] - spi_vals[0]) / (len(spi_vals) - 1)
                trend = "drying" if slope < -0.1 else "wetting" if slope > 0.1 else "stable"

            results.append({
                "island":           island_name,
                "reference_mean":   round(mean, 3),
                "reference_stddev": round(stddev, 3),
                "spi_by_year":      spi_by_year,
                "trend":            trend,
            })

        result = {
            "datatype":         params.datatype.value,
            "reference_period": params.reference_years,
            "results":          results,
        }

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [f"## SPI Drought Index — {params.datatype.value}", ""]
            for r in results:
                lines.append(f"### {r['island'].title()}")
                if "error" in r:
                    lines.append(f"Warning: {r['error']}")
                    continue
                lines.append(
                    f"**Mean:** {r['reference_mean']} | **Stddev:** {r['reference_stddev']} | **Trend:** {r['trend']}"
                )
                lines.append("\n| Year | Value | SPI | Interpretation |\n|---|---|---|---|")
                for yr, v in r["spi_by_year"].items():
                    lines.append(
                        f"| {yr} | {v.get('value','—')} | {v.get('spi','—')} | {v.get('interpretation','')} |"
                    )
                lines.append("")
            return "\n".join(lines)

        return json.dumps(result)

    except Exception as e:
        return _handle_error(e)


# ── Tool 11: export_mesonet_csv_via_email ─────────────────────────────────────
class ExportMesonetCsvViaEmailArgs(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    email: str = Field(
        ...,
        description="Email address to receive the CSV export.",
    )
    var_ids: List[str] = Field(
        ...,
        min_length=1,
        description=(
            "List of variable IDs to export (e.g. ['RH_1_Min', 'Tair_2_Max']). "
            "Use get_mesonet_variables to discover valid IDs."
        ),
    )
    start_date: str = Field(
        ...,
        description="ISO 8601 start datetime, e.g. '2025-04-01T00:00:00-10:00'.",
    )
    end_date: str = Field(
        ...,
        description="ISO 8601 end datetime, e.g. '2025-05-01T00:00:00-10:00'.",
    )
    station_ids: Optional[List[str]] = Field(
        default=None,
        description=(
            "List of 4-digit station IDs to include (e.g. ['0145','0141','0115']). "
            "If null, all active stations are included."
        ),
    )
    output_name: Optional[str] = Field(
        default=None,
        description="Optional filename for the output CSV.",
    )


@mcp.tool(
    name="export_mesonet_csv_via_email",
    annotations={
        "title": "Export Mesonet Data as CSV via Email (for Climate Scientists)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def export_mesonet_csv_via_email(params: ExportMesonetCsvViaEmailArgs) -> str:
    """Request a bulk CSV export of Mesonet data delivered to a specified email address.

    Designed for climate scientists who need raw station data for offline analysis.
    The HCDP API processes the request asynchronously and emails the CSV.

    POSTs to /mesonet/db/measurements/email. The API processes the request
    asynchronously and emails the CSV (wide format: columns timestamp, station_id, variables).
    Returns 202 on success — the actual data arrives via email.

    For Code Mode programs handling large date ranges: use this instead of
    paginating get_mesonet_data hundreds of times. Call once, wait for email.

    Request body format per YAML spec:
      {
        "email": "user@example.com",
        "data": {
          "location": "hawaii",
          "station_ids": ["0145", "0141"],
          "var_ids": ["RH_1_Min", "Tair_2_Max"],
          "start_date": "2025-04-01T00:00:00-10:00",
          "end_date": "2025-05-01T00:00:00-10:00"
        }
      }

    Args:
        params (ExportMesonetCsvViaEmailArgs): Validated input parameters.

    Returns:
        str: JSON with keys:
            - status (int): 202 on success
            - message (str): confirmation
            - email_sent_to (str)
    """
    try:
        data_spec: Dict[str, Any] = {
            "location":   "hawaii",
            "var_ids":    params.var_ids,       # array per spec
            "start_date": params.start_date,
            "end_date":   params.end_date,
        }
        if params.station_ids:
            data_spec["station_ids"] = params.station_ids  # array per spec

        body: Dict[str, Any] = {
            "email": params.email,
            "data":  data_spec,
        }
        if params.output_name:
            body["outputName"] = params.output_name

        response = await hcdp_post("/mesonet/db/measurements/email", body)

        return json.dumps({
            "status":        response.get("status", 202),
            "message":       f"Export queued. CSV will be emailed to {params.email}.",
            "email_sent_to": params.email,
            "api_response":  response.get("message", ""),
        })

    except Exception as e:
        return _handle_error(e)


# ── Entry point ───────────────────────────────────────────────────────────────
def cli_main():
    """Entry point for the hcdp-mcp-server CLI command."""
    mcp.run()


if __name__ == "__main__":
    cli_main()
