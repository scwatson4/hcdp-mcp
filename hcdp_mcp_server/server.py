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
        description="Comma-separated Mesonet variable IDs (e.g. 'Tair_1_Avg,RH_1_Avg'). Use get_mesonet_variables to discover IDs.",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="ISO 8601 start date (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss-10:00). Data from ~2023 onward.",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="ISO 8601 end date (inclusive).",
    )
    station_ids: Optional[str] = Field(
        default=None,
        description="Comma-separated 4-digit station IDs (e.g. '0502,0521'). Use get_mesonet_stations to find IDs.",
    )
    limit: int = Field(
        default=10000,
        ge=1,
        le=1000000,
        description="Max records per page (default 10,000; max 1,000,000).",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Records to skip for pagination.",
    )
    join_metadata: Optional[str] = Field(
        default="true",
        description="Pass 'true' to include station/variable metadata per row.",
    )
    flags: Optional[str] = Field(
        default=None,
        description="Comma-separated data flag values to filter by.",
    )
    reverse: Optional[str] = Field(
        default=None,
        description="Pass any value to sort oldest-first (default is newest-first).",
    )
    local_tz: Optional[str] = Field(
        default=None,
        description="Pass any value to convert timestamps to Hawaii local time.",
    )
    row_mode: Optional[str] = Field(
        default=None,
        description="Row format: 'array', 'wide_array', 'json', 'wide_json'. Default returns JSON objects.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'json' for programmatic use, 'markdown' for display.",
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
    """Fetch Mesonet station time-series measurements (~2023-present).

    Returns records with timestamp, station_id, variable, value, units, and
    (if join_metadata set) station name, lat, lng, elevation.
    Response includes has_more and next_offset for pagination.
    For pre-2023 data use get_timeseries_data instead.
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
        description="Network location: 'hawaii' or 'american_samoa'.",
    )
    status: Optional[str] = Field(
        default="active",
        description="Filter by status: 'active', 'inactive', 'planned', or null for all.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'json' for programmatic use, 'markdown' for display.",
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
    """List all Mesonet weather stations with station_id, name, lat, lng, elevation, status.

    Use to discover station_ids for get_mesonet_data or get_station_latest.
    Status filter is applied client-side (API returns all stations).
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
        description="'json' for programmatic use, 'markdown' for display.",
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
    """List all Mesonet variable IDs with display names and units.

    Use to map intent to the correct var_id for get_mesonet_data.
    Common: RF_1_Tot300s (rain 5-min), RF_1_Tot3600s (rain hourly),
    Tair_1_Avg (temp °C), RH_1_Avg (humidity %), WS_1_Avg (wind m/s).
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
        description="Island or list: 'oahu', 'big_island', 'maui', 'kauai', 'molokai', 'lanai'.",
    )
    years: Union[int, List[int]] = Field(
        ...,
        description="Year or list of years (e.g. 2024 or [2020,2021,2022]).",
    )
    datatype: RasterDatatype = Field(
        ...,
        description="Climate variable: 'rainfall', 'temperature', 'relative_humidity', 'spi', 'ndvi_modis', 'ignition_probability'.",
    )
    production: str = Field(
        default="new",
        description="Rainfall production: 'new' (1990-present) or 'legacy' (1920-2012 monthly).",
    )
    aggregation: Optional[TempAggregation] = Field(
        default=None,
        description="Temperature aggregation: 'min', 'max', or 'mean'. Required when datatype='temperature'.",
    )
    period: Period = Field(
        default=Period.MONTH,
        description="Aggregation period: 'month' or 'day'.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'json' for programmatic use, 'markdown' for display.",
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
    """Fetch historical raster climate data for one or more islands and years in parallel.

    Returns island_wide_average and regional_breakdown per island-year combination.
    Rainfall available from 1990 (new) or 1920 (legacy monthly).
    Not for real-time data — use get_station_latest for current conditions.
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
        description="Climate variable: 'rainfall', 'temperature', 'relative_humidity', 'spi', 'ndvi_modis', 'ignition_probability'.",
    )
    start: str = Field(
        ...,
        description="Start date. Use YYYY-MM for monthly (e.g. '1920-01'), YYYY-MM-DD for daily.",
    )
    end: str = Field(
        ...,
        description="End date (inclusive). Match format of start.",
    )
    extent: RasterExtent = Field(
        default=RasterExtent.STATEWIDE,
        description="Raster extent: 'statewide', 'bi' (Big Island), 'ka' (Kauai), 'oa' (Oahu), 'mn' (Maui County).",
    )
    period: Period = Field(
        default=Period.MONTH,
        description="Aggregation period: 'month' or 'day'.",
    )
    production: Optional[str] = Field(
        default="new",
        description="Rainfall production: 'new' (1990-present) or 'legacy' (1920-2012 monthly).",
    )
    aggregation: Optional[TempAggregation] = Field(
        default=None,
        description="Temperature aggregation: 'min', 'max', 'mean'. Required when datatype='temperature'.",
    )
    timescale: Optional[SpiTimescale] = Field(
        default=None,
        description="SPI timescale (e.g. 'timescale001'=1mo, 'timescale012'=12mo). Required when datatype='spi'.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'json' for programmatic use, 'markdown' for display.",
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
    """Fetch historical raster timeseries for a lat/lng point (rainfall back to 1920).

    Use YYYY-MM date format for monthly data (e.g. start='1990-01', end='2024-12').
    Companion params: rainfall→production, temperature→aggregation, spi→timescale.
    Returns date-value pairs plus summary stats (mean, min, max).
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
        description="Comma-separated variable IDs (default: rain, temp, humidity, wind, VPD).",
    )
    station_id: Optional[str] = Field(
        default=None,
        description="4-digit station ID to filter results (e.g. '0502'). Omit for all stations.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'json' for programmatic use, 'markdown' for display.",
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
    """Fetch the most recent 24-hour readings for Mesonet stations (real-time snapshot).

    Returns 24hr_latest, 24hr_max, 24hr_min per variable per station.
    Provide station_id to filter to one station; omit for all stations.
    Use get_nearest_stations first to find station IDs by location.
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
    """Find the nearest active Mesonet stations to a lat/lng point, sorted by distance.

    Use to translate place names to station_ids for get_mesonet_data or get_station_latest.
    Returns station_id, name, lat, lng, elevation, distance_km per result.
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
    """Rank Hawaiian islands by a climate variable for a given year.

    Answers: 'Which island was driest/wettest/hottest in 2024?'
    Returns islands sorted by island_wide_average with driest/wettest region per island.
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
    """Compute Standardized Precipitation Index (SPI) for one or more islands.

    SPI = (observed - mean) / stddev over the reference years.
    Interpretation: ≥2.0 extremely wet, ≥1.0 moderately wet, -1.0 to +1.0 near normal,
    ≤-1.0 moderate drought, ≤-1.5 severe drought, ≤-2.0 extreme drought.
    Returns spi_by_year with value, spi, interpretation, and trend per island.
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
        description="List of variable IDs to export (e.g. ['RH_1_Min', 'Tair_2_Max']).",
    )
    start_date: str = Field(
        ...,
        description="ISO 8601 start datetime (e.g. '2025-04-01T00:00:00-10:00').",
    )
    end_date: str = Field(
        ...,
        description="ISO 8601 end datetime (e.g. '2025-05-01T00:00:00-10:00').",
    )
    station_ids: Optional[List[str]] = Field(
        default=None,
        description="List of 4-digit station IDs. Omit to include all active stations.",
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
    """Request a bulk Mesonet CSV export delivered asynchronously to an email address.

    Use for large date ranges instead of paginating get_mesonet_data many times.
    Returns 202 immediately; CSV arrives via email when processing completes.
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
