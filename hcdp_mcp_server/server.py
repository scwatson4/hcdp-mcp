"""HCDP MCP Server - Main server implementation."""

import asyncio
import base64
import json
import math
from typing import Any, Sequence, Dict, List, Optional
from datetime import datetime, timedelta
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from pydantic import BaseModel, Field, field_validator
from .client import HCDPClient

# Constants for Location Data
ISLAND_EXTENTS = {
    "oahu": "oa",
    "big_island": "bi",
    "maui": "mn",
    "kauai": "ka",
    "molokai": "mn",
    "lanai": "mn",
    "statewide": "statewide",
}

CITY_LOCATIONS = {
    # Oahu
    "honolulu": {"lat": 21.3069, "lng": -157.8583, "island": "oahu"},
    "manoa": {"lat": 21.333, "lng": -157.803, "island": "oahu"},
    "kaneohe": {"lat": 21.4111, "lng": -157.7967, "island": "oahu"},
    "kapolei": {"lat": 21.3358, "lng": -158.0561, "island": "oahu"},
    "wahiawa": {"lat": 21.5028, "lng": -158.0236, "island": "oahu"},
    # Big Island
    "hilo": {"lat": 19.7241, "lng": -155.0868, "island": "big_island"},
    "kona": {"lat": 19.6393, "lng": -155.9969, "island": "big_island"},
    "waimea_bi": {"lat": 20.0201, "lng": -155.6677, "island": "big_island"},
    "volcano": {"lat": 19.4315, "lng": -155.2323, "island": "big_island"},
    # Maui
    "kahului": {"lat": 20.8893, "lng": -156.4729, "island": "maui"},
    "lahaina": {"lat": 20.8783, "lng": -156.6825, "island": "maui"},
    "hana": {"lat": 20.7575, "lng": -155.9884, "island": "maui"},
    "kula": {"lat": 20.7922, "lng": -156.3267, "island": "maui"},
    # Kauai
    "lihue": {"lat": 21.9811, "lng": -159.3711, "island": "kauai"},
    "poipu": {"lat": 21.8817, "lng": -159.4580, "island": "kauai"},
    "princeville": {"lat": 22.2201, "lng": -159.4831, "island": "kauai"},
    "waimea_ka": {"lat": 21.9568, "lng": -159.6698, "island": "kauai"},
    # Molokai
    "kaunakakai": {"lat": 21.0905, "lng": -157.0226, "island": "molokai"},
    "kualapuu": {"lat": 21.1611, "lng": -157.0683, "island": "molokai"},
    # Lanai
    "lanai_city": {"lat": 20.8264, "lng": -156.9182, "island": "lanai"},
    # American Samoa
    "pago_pago": {"lat": -14.2794, "lng": -170.7006, "island": "tutuila"},
}

# Mapping from friendly names to mesonet variable IDs
MESONET_DATATYPE_MAP = {
    "temperature": "Tair_1_Avg",
    "temp": "Tair_1_Avg",
    "humidity": "RH_1_Avg",
    "rh": "RH_1_Avg",
    "relative_humidity": "RH_1_Avg",
    "rainfall": "RF_1_Tot300s",
    "rain": "RF_1_Tot300s",
    "precipitation": "RF_1_Tot300s",
    "wind": "WS_1_Avg",
    "wind_speed": "WS_1_Avg",
    "solar": "SWin_1_Avg",
    "solar_radiation": "SWin_1_Avg",
    "pressure": "P_1",
    "soil_moisture": "SM_1_Avg",
    "soil_temperature": "Tsoil_1_Avg",
}

# Approximate bounding boxes per island (lat_min, lat_max, lng_min, lng_max)
ISLAND_BOUNDS = {
    "oahu": (21.2, 21.8, -158.3, -157.6),
    "big_island": (18.9, 20.3, -156.1, -154.8),
    "maui": (20.5, 21.1, -156.7, -155.9),
    "kauai": (21.8, 22.3, -159.8, -159.2),
    "molokai": (21.0, 21.3, -157.3, -156.7),
    "lanai": (20.7, 21.0, -157.0, -156.8),
}

CITY_ALIASES = {
    "waimea": "waimea_bi",
    "lanai": "lanai_city",
    "pago_pago": "pago_pago",
}

ISLAND_REPRESENTATIVE_POINTS = {
    "oahu": {
        "Honolulu (South)": {"lat": 21.3069, "lng": -157.8583},
        "Kaneohe (Windward)": {"lat": 21.4111, "lng": -157.7967},
        "Kapolei (Leeward)": {"lat": 21.3358, "lng": -158.0561},
        "Wahiawa (Central)": {"lat": 21.5028, "lng": -158.0236},
        "North Shore": {"lat": 21.5956, "lng": -158.1070},
    },
    "big_island": {
        "Hilo (East/Wet)": {"lat": 19.7241, "lng": -155.0868},
        "Kona (West/Dry)": {"lat": 19.6393, "lng": -155.9969},
        "Waimea (Upcountry)": {"lat": 20.0201, "lng": -155.6677},
        "Volcano (Highland/Wet)": {"lat": 19.4315, "lng": -155.2323},
        "South Point": {"lat": 18.9136, "lng": -155.6793},
    },
    "maui": {
        "Kahului (Central)": {"lat": 20.8893, "lng": -156.4729},
        "Hana (East/Wet)": {"lat": 20.7575, "lng": -155.9884},
        "Lahaina (West/Dry)": {"lat": 20.8783, "lng": -156.6825},
        "Kula (Upcountry)": {"lat": 20.7922, "lng": -156.3267},
    },
    "kauai": {
        "Lihue (East)": {"lat": 21.9811, "lng": -159.3711},
        "Poipu (South)": {"lat": 21.8817, "lng": -159.4580},
        "Princeville (North)": {"lat": 22.2201, "lng": -159.4831},
        "Waimea (West)": {"lat": 21.9568, "lng": -159.6698},
        "Kokee (Mountain)": {"lat": 22.1264, "lng": -159.6467},
    },
    "molokai": {
        "Kaunakakai (South)": {"lat": 21.0905, "lng": -157.0226},
        "Kualapuu (Central)": {"lat": 21.1611, "lng": -157.0683},
        "Halawa (East)": {"lat": 21.1578, "lng": -156.7442},
    },
    "lanai": {
        "Lanai City": {"lat": 20.8264, "lng": -156.9182},
        "Manele (South)": {"lat": 20.7389, "lng": -156.8886},
    },
    "statewide": {
        "Honolulu (Oahu)": {"lat": 21.3069, "lng": -157.8583},
        "Hilo (Big Island)": {"lat": 19.7241, "lng": -155.0868},
        "Kahului (Maui)": {"lat": 20.8893, "lng": -156.4729},
        "Lihue (Kauai)": {"lat": 21.9811, "lng": -159.3711},
    },
}


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate Haversine distance between two points in km."""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def resolve_mesonet_datatype(raw: str) -> str:
    """Map friendly name to mesonet var_id, or pass through as raw var_id."""
    return MESONET_DATATYPE_MAP.get(raw.lower().strip(), raw)


def normalize_city_name(raw: str) -> str:
    """Normalize city input to CITY_LOCATIONS key."""
    name = raw.lower().strip().replace(" ", "_").replace("-", "_")
    return CITY_ALIASES.get(name, name)


def resolve_extent_from_coords(lat: float, lng: float) -> str:
    """Determine island extent code from coordinates."""
    for island, (lat_min, lat_max, lng_min, lng_max) in ISLAND_BOUNDS.items():
        if lat_min <= lat <= lat_max and lng_min <= lng <= lng_max:
            return ISLAND_EXTENTS[island]
    return "statewide"


class GetClimateRasterArgs(BaseModel):
    """Arguments for getting climate raster data."""

    datatype: str = Field(
        description="Climate variable: 'rainfall' (or 'precipitation'), 'temp_mean' (or 'temperature', 'mean temperature'), 'temp_min' (minimum temperature), 'temp_max' (maximum temperature), 'rh' (relative humidity)"
    )
    date: str = Field(
        description="Date in YYYY-MM format (e.g., '2024-01' for January 2024, '2022-02' for February 2022). Use current/recent dates for latest data."
    )
    extent: str = Field(
        description="Spatial extent code: 'bi' (Big Island/Hawaii County), 'oa' (Oahu/Honolulu County), 'ka' (Kauai County), 'mn' (Maui County), or 'statewide' (all islands)"
    )
    location: str = Field(
        default="hawaii", description="Location ('hawaii' or 'american_samoa')"
    )
    production: str | None = Field(
        default=None,
        description="Production level for RAINFALL only. Use 'new' for recent/preliminary data (1990-present), 'legacy' for historical archive (1920-2012).",
    )
    aggregation: str | None = Field(
        default=None,
        description="Temporal aggregation for TEMPERATURE data. Use 'month' for monthly averages. Required for temperature queries.",
    )
    timescale: str | None = Field(default=None, description="Timescale (for SPI data)")
    period: str | None = Field(default=None, description="Period specification")


class GetTimeseriesArgs(BaseModel):
    """Arguments for getting time series data."""

    datatype: str = Field(
        description="Climate variable: 'rainfall', 'temperature', 'relative_humidity', 'spi', 'ndvi_modis', or 'ignition_probability'. Use aggregation for temperature min/max/mean."
    )
    start: str = Field(description="Start date in YYYY-MM-DD format")
    end: str = Field(description="End date in YYYY-MM-DD format")
    extent: str | None = Field(
        default=None,
        description="Island extent code ('bi','oa','ka','mn','statewide'). Auto-resolved from lat/lng if omitted.",
    )
    lat: float | str | None = Field(default=None, description="Latitude coordinate")
    lng: float | str | None = Field(default=None, description="Longitude coordinate")
    location: str = Field(
        default="hawaii", description="Location ('hawaii' or 'american_samoa')"
    )
    production: str | None = Field(
        default=None,
        description="For rainfall only: 'new' (1990-present) or 'legacy' (1920-2012)",
    )
    aggregation: str | None = Field(
        default=None, description="For temperature only: 'min', 'max', or 'mean'"
    )
    timescale: str | None = Field(
        default=None,
        description="For SPI only: e.g. 'timescale001', 'timescale003', 'timescale012'",
    )
    period: str | None = Field(
        default=None, description="Time period: 'month' or 'day'"
    )

    @field_validator("lat", "lng", mode="before")
    @classmethod
    def convert_to_float(cls, v):
        """Convert string coordinates to floats."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return float(v)
        return v


class GetStationDataArgs(BaseModel):
    """Arguments for getting station data."""

    q: str = Field(
        description="Search query: station name, ID, or network (e.g. 'Manoa', 'HN151')"
    )
    limit: int | None = Field(default=None, description="Limit number of results")
    offset: int | None = Field(default=None, description="Offset for pagination")


class GetMesonetDataArgs(BaseModel):
    """Arguments for getting mesonet data."""

    station_ids: str | None = Field(
        default=None, description="Comma-separated station IDs (e.g. '0145,0141')"
    )
    start_date: str | None = Field(
        default=None, description="Start date in YYYY-MM-DD format"
    )
    end_date: str | None = Field(
        default=None, description="End date in YYYY-MM-DD format"
    )
    var_ids: str | None = Field(
        default=None,
        description="Comma-separated mesonet variable IDs (e.g. 'Tair_1_Avg,RH_1_Avg'). Use get_mesonet_variables to list valid IDs.",
    )
    location: str = Field(
        default="hawaii", description="Location ('hawaii' or 'american_samoa')"
    )
    intervals: str | None = Field(default=None, description="Time intervals")
    limit: int | None = Field(default=None, description="Limit number of results")
    offset: int | None = Field(default=None, description="Offset for pagination")
    join_metadata: bool = Field(default=True, description="Include metadata in results")


class GenerateDataPackageEmailArgs(BaseModel):
    """Arguments for generating data packages via email."""

    email: str = Field(description="Email address for package delivery")
    datatype: str = Field(description="Climate data type")
    production: str | None = Field(
        default=None, description="Production level (optional)"
    )
    period: str | None = Field(
        default=None, description="Period specification (optional)"
    )
    extent: str | None = Field(default=None, description="Spatial extent (optional)")
    start_date: str | None = Field(default=None, description="Start date (optional)")
    end_date: str | None = Field(default=None, description="End date (optional)")
    files: str | None = Field(
        default=None, description="Specific files to include (optional)"
    )
    zipName: str | None = Field(
        default=None, description="Custom zip file name (optional)"
    )


class GenerateDataPackageInstantArgs(BaseModel):
    """Arguments for generating instant data packages."""

    email: str = Field(description="Email address for logging")
    datatype: str = Field(description="Climate data type")
    production: str | None = Field(
        default=None, description="Production level (optional)"
    )
    period: str | None = Field(
        default=None, description="Period specification (optional)"
    )
    extent: str | None = Field(default=None, description="Spatial extent (optional)")
    start_date: str | None = Field(default=None, description="Start date (optional)")
    end_date: str | None = Field(default=None, description="End date (optional)")
    zipName: str | None = Field(
        default=None, description="Custom zip file name (optional)"
    )


class ListProductionFilesArgs(BaseModel):
    """Arguments for listing production files."""

    datatype: str = Field(description="Climate data type")
    production: str | None = Field(
        default=None, description="Production level (optional)"
    )
    period: str | None = Field(
        default=None, description="Period specification (optional)"
    )
    extent: str | None = Field(default=None, description="Spatial extent (optional)")


class RetrieveProductionFileArgs(BaseModel):
    """Arguments for retrieving a production file."""

    file_path: str = Field(description="Path to the file to retrieve")


class GetMesonetStationsArgs(BaseModel):
    """Arguments for getting mesonet station info."""

    location: str = Field(default="hawaii", description="Location")


class GetMesonetVariablesArgs(BaseModel):
    """Arguments for getting mesonet variable definitions."""

    location: str = Field(default="hawaii", description="Location")


class GetMesonetStationMonitorArgs(BaseModel):
    """Arguments for getting mesonet station monitoring data."""

    location: str = Field(default="hawaii", description="Location")


class GetIslandSummaryArgs(BaseModel):
    """Arguments for island-wide weather summary."""

    island: str = Field(
        description="Island name: 'oahu', 'big_island', 'maui', 'kauai', 'molokai', 'lanai'"
    )
    datatype: str = Field(
        description="Mesonet variable: friendly name ('temperature','rainfall','humidity','wind','solar') or raw var_id ('Tair_1_Avg')"
    )


class GetCityWeatherArgs(BaseModel):
    """Arguments for city-specific weather."""

    city: str = Field(
        description="City/town name in snake_case (e.g. 'honolulu', 'manoa', 'kaneohe', 'lahaina')"
    )
    datatype: str = Field(
        description="Mesonet variable: friendly name ('temperature','rainfall','humidity','wind','solar') or raw var_id ('Tair_1_Avg')"
    )


class CompareHistoryArgs(BaseModel):
    """Arguments for comparing current vs historical weather."""

    city: str = Field(
        description="City/town name in snake_case (e.g. 'honolulu', 'manoa', 'kaneohe', 'lahaina')"
    )
    datatype: str = Field(
        description="Variable: 'temperature', 'rainfall', or 'humidity'. Mapped to API names internally."
    )


class GetIslandHistoryArgs(BaseModel):
    """Arguments for island history summary."""

    island: str = Field(
        description="Island name: 'oahu', 'big_island', 'maui', 'kauai', 'molokai', 'lanai'"
    )
    datatype: str = Field(
        description="Variable: 'rainfall', 'temperature', or 'relative_humidity'"
    )
    year: str = Field(description="Year to summarize, e.g. '2024'")


class EmailMesonetMeasurementsArgs(BaseModel):
    """Arguments for emailing mesonet measurements."""

    email: str = Field(description="Email address for CSV delivery")
    location: str = Field(default="hawaii", description="Location")
    station_ids: str | None = Field(
        default=None, description="Comma-separated station IDs (optional)"
    )
    start_date: str | None = Field(
        default=None, description="Start date in YYYY-MM-DD format (optional)"
    )
    end_date: str | None = Field(
        default=None, description="End date in YYYY-MM-DD format (optional)"
    )
    var_ids: str | None = Field(
        default=None, description="Comma-separated variable IDs (optional)"
    )
    intervals: str | None = Field(default=None, description="Time intervals (optional)")


SERVER_INSTRUCTIONS = """HCDP (Hawaii Climate Data Portal) - Tool Routing Guide

CURRENT/REAL-TIME WEATHER (mesonet stations, updated every 15 min):
  Weather for a city/town -> get_city_current_weather
  Weather summary for an island -> get_island_current_summary
  Raw measurements by station ID -> get_mesonet_data

HISTORICAL/GRIDDED DATA (processed climate maps, days-months lag):
  Time series at a lat/lng point -> get_timeseries_data
  Island-wide annual patterns -> get_island_history_summary
  Compare today vs last year -> compare_current_vs_historical

DISCOVERY (use these first when unsure):
  List weather stations -> get_mesonet_stations
  List available variable IDs -> get_mesonet_variables
  Search station metadata by name -> get_station_data

TIPS:
- City names use snake_case: honolulu, manoa, kaneohe, lahaina, lanai_city
- Friendly datatype names accepted for current weather: 'temperature', 'rainfall', 'humidity', 'wind', 'solar'
- For raw mesonet var_ids (e.g. Tair_1_Avg), call get_mesonet_variables first
- Dates: YYYY-MM-DD for mesonet/station tools, YYYY-MM-DD for timeseries start/end
- Historical/gridded datatypes: 'rainfall', 'temperature' (with aggregation), 'relative_humidity', 'spi', 'ndvi_modis', 'ignition_probability'
- Production values for rainfall: 'new' (1990-present) or 'legacy' (1920-2012)
"""

app = Server("hcdp-mcp-server", instructions=SERVER_INSTRUCTIONS)


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    return [
        # Tool(
        #     name="get_climate_raster",
        #     description="""Retrieve climate raster data (GeoTIFF maps) from HCDP.
        #
        #     Use this for queries like:
        #     - 'Get rainfall data for Big Island in February 2022'
        #     - 'Show me temperature data for Oahu last month'
        #     - 'Download precipitation map for statewide Hawaii'
        #
        #     Key parameters:
        #     - datatype: 'rainfall' (requires production='new' and period='month'), 'temp_mean'/'temp_min'/'temp_max' (requires aggregation='month'), 'rh' (relative humidity)
        #     - extent: Use 'bi' (Big Island), 'oa' (Oahu), 'ka' (Kauai), 'mn' (Maui County), or 'statewide'
        #     - date: YYYY-MM format (e.g., '2024-01')
        #     """,
        #     inputSchema=GetClimateRasterArgs.model_json_schema(),
        # ),
        Tool(
            name="get_timeseries_data",
            description="Historical gridded climate data at a specific point. Requires lat and lng coordinates. Returns values over a date range.",
            inputSchema=GetTimeseriesArgs.model_json_schema(),
        ),
        Tool(
            name="get_station_data",
            description="Search HCDP station metadata by name or ID. Returns station info, not measurements (use get_mesonet_data for measurements).",
            inputSchema=GetStationDataArgs.model_json_schema(),
        ),
        Tool(
            name="get_mesonet_data",
            description="Fetch real-time mesonet measurements by station ID, date range, and variable. Use get_mesonet_variables to discover valid var_ids.",
            inputSchema=GetMesonetDataArgs.model_json_schema(),
        ),
        # Tool(
        #     name="generate_data_package_email",
        #     description="Generate downloadable zip packages of climate data and email them",
        #     inputSchema=GenerateDataPackageEmailArgs.model_json_schema(),
        # ),
        # Tool(
        #     name="generate_data_package_instant_link",
        #     description="Generate instant download links for climate data packages",
        #     inputSchema=GenerateDataPackageInstantArgs.model_json_schema(),
        # ),
        # Tool(
        #     name="generate_data_package_instant_content",
        #     description="Generate instant download content for climate data packages",
        #     inputSchema=GenerateDataPackageInstantArgs.model_json_schema(),
        # ),
        # Tool(
        #     name="generate_data_package_splitlink",
        #     description="Generate split download links for large climate data packages",
        #     inputSchema=GenerateDataPackageInstantArgs.model_json_schema(),
        # ),
        # Tool(
        #     name="list_production_files",
        #     description="List available production climate data files",
        #     inputSchema=ListProductionFilesArgs.model_json_schema(),
        # ),
        # Tool(
        #     name="retrieve_production_file",
        #     description="Retrieve a specific production climate data file",
        #     inputSchema=RetrieveProductionFileArgs.model_json_schema(),
        # ),
        Tool(
            name="get_island_current_summary",
            description="Current weather summary (avg/min/max) for an entire island from active mesonet stations.",
            inputSchema=GetIslandSummaryArgs.model_json_schema(),
        ),
        Tool(
            name="get_city_current_weather",
            description="Current weather for a named city or town. Averages nearby mesonet stations within 15km.",
            inputSchema=GetCityWeatherArgs.model_json_schema(),
        ),
        Tool(
            name="compare_current_vs_historical",
            description="Compare today's city weather to the same month last year. Returns the difference from historical average.",
            inputSchema=CompareHistoryArgs.model_json_schema(),
        ),
        Tool(
            name="get_island_history_summary",
            description="Historical weather patterns for an island across representative points for a given year.",
            inputSchema=GetIslandHistoryArgs.model_json_schema(),
        ),
        Tool(
            name="get_mesonet_stations",
            description="List all mesonet weather stations with location and metadata.",
            inputSchema=GetMesonetStationsArgs.model_json_schema(),
        ),
        Tool(
            name="get_mesonet_variables",
            description="List valid mesonet variable IDs and descriptions. Use this to discover var_ids for get_mesonet_data.",
            inputSchema=GetMesonetVariablesArgs.model_json_schema(),
        ),
        # Tool(
        #     name="get_mesonet_station_monitor",
        #     description="Get mesonet station monitoring and status data",
        #     inputSchema=GetMesonetStationMonitorArgs.model_json_schema(),
        # ),
        # Tool(
        #     name="email_mesonet_measurements",
        #     description="Email mesonet measurement data as CSV files",
        #     inputSchema=EmailMesonetMeasurementsArgs.model_json_schema(),
        # ),
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls."""
    client = HCDPClient()

    try:
        # if name == "get_climate_raster":
        #     args = GetClimateRasterArgs(**arguments)
        #     result = await client.get_raster_data(
        #         datatype=args.datatype,
        #         date=args.date,
        #         extent=args.extent,
        #         location=args.location,
        #         production=args.production,
        #         aggregation=args.aggregation,
        #         timescale=args.timescale,
        #         period=args.period
        #     )
        #
        if name == "get_timeseries_data":
            args = GetTimeseriesArgs(**arguments)
            if args.extent is None and args.lat is not None and args.lng is not None:
                args.extent = resolve_extent_from_coords(
                    float(args.lat), float(args.lng)
                )
            elif args.extent is None:
                args.extent = "statewide"
            result = await client.get_timeseries_data(
                datatype=args.datatype,
                start=args.start,
                end=args.end,
                extent=args.extent,
                lat=args.lat,
                lng=args.lng,
                location=args.location,
                production=args.production,
                aggregation=args.aggregation,
                timescale=args.timescale,
                period=args.period,
            )

        elif name == "get_station_data":
            args = GetStationDataArgs(**arguments)
            result = await client.get_station_data(
                q=args.q, limit=args.limit, offset=args.offset
            )

        elif name == "get_mesonet_data":
            args = GetMesonetDataArgs(**arguments)
            result = await client.get_mesonet_data(
                station_ids=args.station_ids,
                start_date=args.start_date,
                end_date=args.end_date,
                var_ids=args.var_ids,
                location=args.location,
                intervals=args.intervals,
                limit=args.limit,
                offset=args.offset,
                join_metadata=args.join_metadata,
            )

        # elif name == "generate_data_package_email":
        #     args = GenerateDataPackageEmailArgs(**arguments)
        #     result = await client.generate_data_package_email(
        #         email=args.email,
        #         datatype=args.datatype,
        #         production=args.production,
        #         period=args.period,
        #         extent=args.extent,
        #         start_date=args.start_date,
        #         end_date=args.end_date,
        #         files=args.files,
        #         zipName=args.zipName
        #     )
        #
        # elif name == "generate_data_package_instant_link":
        #     args = GenerateDataPackageInstantArgs(**arguments)
        #     result = await client.generate_data_package_instant_link(
        #         email=args.email,
        #         datatype=args.datatype,
        #         production=args.production,
        #         period=args.period,
        #         extent=args.extent,
        #         start_date=args.start_date,
        #         end_date=args.end_date,
        #         zipName=args.zipName
        #     )
        #
        # elif name == "generate_data_package_instant_content":
        #     args = GenerateDataPackageInstantArgs(**arguments)
        #     result = await client.generate_data_package_instant_content(
        #         email=args.email,
        #         datatype=args.datatype,
        #         production=args.production,
        #         period=args.period,
        #         extent=args.extent,
        #         start_date=args.start_date,
        #         end_date=args.end_date,
        #         zipName=args.zipName
        #     )
        #
        # elif name == "generate_data_package_splitlink":
        #     args = GenerateDataPackageInstantArgs(**arguments)
        #     result = await client.generate_data_package_splitlink(
        #         email=args.email,
        #         datatype=args.datatype,
        #         production=args.production,
        #         period=args.period,
        #         extent=args.extent,
        #         start_date=args.start_date,
        #         end_date=args.end_date,
        #         zipName=args.zipName
        #     )
        #
        # elif name == "list_production_files":
        #     args = ListProductionFilesArgs(**arguments)
        #     result = await client.list_production_files(
        #         datatype=args.datatype,
        #         production=args.production,
        #         period=args.period,
        #         extent=args.extent
        #     )
        #
        # elif name == "retrieve_production_file":
        #     args = RetrieveProductionFileArgs(**arguments)
        #     result = await client.retrieve_production_file(
        #         file_path=args.file_path
        #     )
        #
        elif name == "get_mesonet_stations":
            args = GetMesonetStationsArgs(**arguments)
            result = await client.get_mesonet_stations(location=args.location)

        elif name == "get_mesonet_variables":
            args = GetMesonetVariablesArgs(**arguments)
            result = await client.get_mesonet_variables(location=args.location)

        # elif name == "get_mesonet_station_monitor":
        #     args = GetMesonetStationMonitorArgs(**arguments)
        #     result = await client.get_mesonet_station_monitor(
        #         location=args.location
        #     )
        #
        # elif name == "email_mesonet_measurements":
        #     args = EmailMesonetMeasurementsArgs(**arguments)
        #     result = await client.email_mesonet_measurements(
        #         email=args.email,
        #         location=args.location,
        #         station_ids=args.station_ids,
        #         start_date=args.start_date,
        #         end_date=args.end_date,
        #         var_ids=args.var_ids,
        #         intervals=args.intervals
        #     )

        elif name == "get_island_current_summary":
            args = GetIslandSummaryArgs(**arguments)
            resolved_var = resolve_mesonet_datatype(args.datatype)
            # 1. Get all stations
            stations = await client.get_mesonet_stations()
            if "error" in stations:
                raise ValueError(f"Failed to fetch stations: {stations['error']}")

            # 2. Filter by island
            target_island = args.island.lower()
            if target_island not in ISLAND_EXTENTS:
                raise ValueError(f"Unknown island: {target_island}")

            # 3. Get list of station IDs using bounding box
            station_ids = []

            bounds = ISLAND_BOUNDS.get(target_island)
            if not bounds:
                # Fallback: Just take first 20 stations if bounds unknown (e.g. statewide)
                station_ids = [s["station_id"] for s in stations[:20]]
            else:
                lat_min, lat_max, lng_min, lng_max = bounds
                for s in stations:
                    try:
                        slat, slng = float(s["lat"]), float(s["lng"])
                        if lat_min <= slat <= lat_max and lng_min <= slng <= lng_max:
                            station_ids.append(s["station_id"])
                    except:
                        continue

            if not station_ids:
                result = {"error": f"No stations found on {args.island}"}
            else:
                # Limit to 50 to avoid timeouts
                station_ids = station_ids[:50]

                # 4. Fetch data
                today = datetime.now().strftime("%Y-%m-%d")
                measurements = await client.get_mesonet_data(
                    station_ids=station_ids,
                    start_date=today,
                    end_date=today,
                    var_ids=[resolved_var],
                    limit=100,
                )

                vals = []
                for m in measurements:
                    if resolved_var in m:
                        try:
                            vals.append(float(m[resolved_var]))
                        except:
                            continue

                if not vals:
                    result = {
                        "island": args.island,
                        "stations_checked": len(station_ids),
                        "message": f"No recent data for {args.datatype} ({resolved_var}) found",
                    }
                else:
                    avg_val = sum(vals) / len(vals)
                    result = {
                        "island": args.island,
                        "date": today,
                        "datatype": args.datatype,
                        "variable_id": resolved_var,
                        "average": round(avg_val, 2),
                        "min": min(vals),
                        "max": max(vals),
                        "station_count": len(vals),
                        "note": "Averaged from active mesonet stations",
                    }

        elif name == "get_city_current_weather":
            args = GetCityWeatherArgs(**arguments)
            city_key = normalize_city_name(args.city)
            city_data = CITY_LOCATIONS.get(city_key)
            if not city_data:
                raise ValueError(f"Unknown city: {args.city}")

            resolved_var = resolve_mesonet_datatype(args.datatype)

            # 1. Get all stations
            stations = await client.get_mesonet_stations()

            # 2. Find nearby stations
            nearby_stations = []
            for station in stations:
                try:
                    dist = calculate_distance(
                        city_data["lat"],
                        city_data["lng"],
                        float(station["lat"]),
                        float(station["lng"]),
                    )
                    if dist <= 15:  # within 15km
                        nearby_stations.append(station)
                except (ValueError, KeyError, TypeError):
                    continue

            if not nearby_stations:
                result = {
                    "error": f"No weather stations found within 15km of {args.city}"
                }
            else:
                # 3. Get data for these stations
                station_ids = [s["station_id"] for s in nearby_stations]
                today = datetime.now().strftime("%Y-%m-%d")

                measurements = await client.get_mesonet_data(
                    station_ids=station_ids,
                    start_date=today,
                    end_date=today,
                    var_ids=[resolved_var],
                    limit=100,
                )

                # 4. Aggregation
                vals = []
                for m in measurements:
                    if resolved_var in m:
                        try:
                            vals.append(float(m[resolved_var]))
                        except:
                            continue

                if not vals:
                    result = {
                        "city": args.city,
                        "stations_found": len(nearby_stations),
                        "message": f"Found {len(nearby_stations)} stations but no recent data for {args.datatype} ({resolved_var})",
                    }
                else:
                    avg_val = sum(vals) / len(vals)
                    result = {
                        "city": args.city,
                        "date": today,
                        "datatype": args.datatype,
                        "variable_id": resolved_var,
                        "average": round(avg_val, 2),
                        "min": min(vals),
                        "max": max(vals),
                        "station_count": len(vals),
                        "stations_used": station_ids,
                    }

        elif name == "compare_current_vs_historical":
            args = CompareHistoryArgs(**arguments)
            city_key = normalize_city_name(args.city)
            city_data = CITY_LOCATIONS.get(city_key)
            if not city_data:
                raise ValueError(f"Unknown city: {args.city}")

            resolved_var = resolve_mesonet_datatype(args.datatype)

            # 1. Get Current Data (Logic similar to get_city_current_weather)
            stations = await client.get_mesonet_stations()
            nearby_stations = []
            for station in stations:
                try:
                    dist = calculate_distance(
                        city_data["lat"],
                        city_data["lng"],
                        float(station["lat"]),
                        float(station["lng"]),
                    )
                    if dist <= 15:
                        nearby_stations.append(station)
                except:
                    continue

            current_val = None
            if nearby_stations:
                station_ids = [s["station_id"] for s in nearby_stations]
                today = datetime.now().strftime("%Y-%m-%d")
                measurements = await client.get_mesonet_data(
                    station_ids=station_ids,
                    start_date=today,
                    end_date=today,
                    var_ids=[resolved_var],
                    limit=100,
                )
                vals = []
                for m in measurements:
                    if resolved_var in m:
                        try:
                            vals.append(float(m[resolved_var]))
                        except:
                            continue
                if vals:
                    current_val = sum(vals) / len(vals)

            # 2. Get Historical Data (Timeseries for same month, previous year)
            # We use the extent for the island the city is on
            # And use the city coordinates
            last_year = datetime.now().replace(year=datetime.now().year - 1)
            start_date = last_year.replace(day=1).strftime("%Y-%m-%d")
            # End date is end of that month
            next_month = last_year.replace(day=28) + timedelta(days=4)
            end_date = (next_month - timedelta(days=next_month.day)).strftime(
                "%Y-%m-%d"
            )

            # Timeseries params
            ts_datatype = args.datatype
            if args.datatype == "temperature":
                ts_datatype = "temp_mean"
            if args.datatype == "precipitation":
                ts_datatype = "rainfall"

            historical_val = None
            try:
                # Use island extent code from city data
                island_code = ISLAND_EXTENTS.get(city_data["island"], "statewide")

                # Fetch timeseries
                ts_data = await client.get_timeseries_data(
                    datatype=ts_datatype,
                    start=start_date,
                    end=end_date,
                    lat=city_data["lat"],
                    lng=city_data["lng"],
                    extent=island_code,
                    production="new" if ts_datatype == "rainfall" else None,
                    aggregation="month" if ts_datatype != "rainfall" else None,
                    period="month" if ts_datatype == "rainfall" else None,
                )

                if ts_data and len(ts_data) > 0:
                    # Average the monthly values (should be just 1 for a month, but handle list)
                    ts_vals = list(ts_data.values())
                    historical_val = sum(ts_vals) / len(ts_vals)
            except Exception as e:
                print(f"Historical fetch failed: {e}")

            # 3. Compare
            result = {
                "city": args.city,
                "datatype": args.datatype,
                "current_value": (
                    round(current_val, 2) if current_val is not None else "No data"
                ),
                "historical_avg": (
                    round(historical_val, 2)
                    if historical_val is not None
                    else "No data"
                ),
                "historical_period": f"{start_date} to {end_date}",
                "comparison": "N/A",
            }

            if current_val is not None and historical_val is not None:
                diff = current_val - historical_val
                sign = "+" if diff > 0 else ""
                result["comparison"] = (
                    f"{sign}{diff:.2f} difference from historical average"
                )
                result["details"] = (
                    f"Current ({round(current_val, 1)}) is {'higher' if diff > 0 else 'lower'} than historical ({round(historical_val, 1)})"
                )

        elif name == "get_island_history_summary":
            args = GetIslandHistoryArgs(**arguments)
            target_island = args.island.lower()
            points = ISLAND_REPRESENTATIVE_POINTS.get(target_island)

            if not points:
                raise ValueError(
                    f"Unknown island or no representative points for: {args.island}"
                )

            # Prepare arguments for parallel fetching
            ts_datatype = args.datatype
            production = "new" if ts_datatype == "rainfall" else None
            aggregation = "month" if ts_datatype != "rainfall" else None
            period = "month" if ts_datatype == "rainfall" else None
            if ts_datatype == "temperature":
                ts_datatype = "temp_mean"
            if ts_datatype == "precipitation":
                ts_datatype = "rainfall"

            start_date = f"{args.year}-01-01"
            end_date = f"{args.year}-12-31"
            island_code = ISLAND_EXTENTS.get(target_island, "statewide")

            # Create tasks (Parallel Fetching!)
            tasks = []
            location_names = []

            for loc_name, coords in points.items():
                location_names.append(loc_name)
                tasks.append(
                    client.get_timeseries_data(
                        datatype=ts_datatype,
                        start=start_date,
                        end=end_date,
                        lat=coords["lat"],
                        lng=coords["lng"],
                        extent=island_code,
                        production=production,
                        aggregation=aggregation,
                        period=period,
                    )
                )

            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            point_summaries = []
            all_vals = []

            for i, res in enumerate(results):
                loc_name = location_names[i]
                if isinstance(res, Exception):
                    point_summaries.append({"location": loc_name, "error": str(res)})
                    continue

                if res and isinstance(res, dict) and len(res) > 0:
                    try:
                        vals = list(res.values())
                        valid_vals = [v for v in vals if v is not None and v != -9999]
                        if valid_vals:
                            avg = sum(valid_vals) / len(valid_vals)
                            point_summaries.append(
                                {
                                    "location": loc_name,
                                    "average": round(avg, 2),
                                    "min": min(valid_vals),
                                    "max": max(valid_vals),
                                    "data_points": len(valid_vals),
                                }
                            )
                            all_vals.extend(valid_vals)
                        else:
                            point_summaries.append(
                                {"location": loc_name, "message": "No valid data"}
                            )
                    except Exception as e:
                        point_summaries.append({"location": loc_name, "error": str(e)})
                else:
                    point_summaries.append(
                        {"location": loc_name, "message": "No data returned"}
                    )

            # Island-wide aggregation
            island_avg = None
            if all_vals:
                island_avg = sum(all_vals) / len(all_vals)

            result = {
                "island": args.island,
                "year": args.year,
                "datatype": args.datatype,
                "island_wide_average": round(island_avg, 2) if island_avg else "N/A",
                "regional_breakdown": point_summaries,
            }

        else:
            raise ValueError(f"Unknown tool: {name}")

        # Process the result to handle binary data
        processed_result = result
        if isinstance(result, dict) and "data" in result:
            data_content = result["data"]
            # Check if it's bytes
            if isinstance(data_content, bytes):
                # Base64 encode binary data
                processed_result["data"] = base64.b64encode(data_content).decode(
                    "utf-8"
                )
                processed_result["encoding"] = "base64"
                processed_result["media_type"] = (
                    "application/octet-stream"  # Generic binary
                )

                # Try to guess specific type based on tool name
                if "raster" in name:
                    processed_result["media_type"] = "image/tiff"
                elif "zip" in str(arguments.get("zipName", "")):
                    processed_result["media_type"] = "application/zip"

        return [
            TextContent(
                type="text", text=json.dumps(processed_result, indent=2, default=str)
            )
        ]

    except Exception as e:
        return [TextContent(type="text", text=f"Error calling HCDP API: {str(e)}")]


async def main():
    """Main entry point for the server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="hcdp-mcp-server",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def cli_main():
    """Entry point for the CLI script."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
