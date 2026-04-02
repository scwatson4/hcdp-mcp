# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that provides access to the Hawaii Climate Data Portal API. The server exposes HCDP's climate and weather data through standardized MCP tools for use with AI assistants.

## Development Commands

### Setup and Installation
```bash
pip install -e .                    # Install in development mode
pip install -e ".[dev]"            # Install with dev dependencies
cp .env.example .env               # Set up environment configuration
```

### Development Tools
```bash
black hcdp_mcp_server/             # Format code
ruff check hcdp_mcp_server/        # Lint code
pytest                             # Run tests
hcdp-mcp-server                   # Run the MCP server
```

## Architecture

### Two-Layer Design
The codebase follows a clean separation between API communication and MCP protocol handling:

- **`hcdp_mcp_server/client.py`** - `HCDPClient` class handles all HTTP communication with the Hawaii Climate Data Portal API
- **`hcdp_mcp_server/server.py`** - MCP server implementation that wraps the client into MCP tools

### MCP Tools Structure
Each MCP tool follows this pattern:
1. **Pydantic model** (e.g., `GetClimateRasterArgs`) defines and validates input parameters
2. **Tool registration** in `handle_list_tools()` exposes the tool to MCP clients
3. **Tool handler** in `handle_call_tool()` validates args, calls the appropriate client method, and formats responses

### API Client Architecture
The `HCDPClient` class uses:
- **httpx** for async HTTP requests with proper timeout handling (60-120s)
- **Bearer token authentication** from environment variables
- **Standardized parameter handling** across all HCDP endpoints (/raster, /stations, /mesonet, /genzip)
- **Error propagation** that preserves API error details

## Environment Configuration

The server requires a `.env` file with:
```
HCDP_API_TOKEN=<your_token>           # Required: API authentication
HCDP_BASE_URL=<api_base_url>         # Optional: defaults to HCDP production URL
```

## HCDP API Context

### Supported Data Types
- Climate rasters (rainfall, temperature, humidity, SPI, NDVI, ignition probability)
- Time series data for specific coordinates
- Station-based measurements
- Real-time mesonet weather data
- Bulk data package generation

### Geographic Coverage
- `hawaii` - Main Hawaiian islands (default)
- `american_samoa` - American Samoa territory

### Temporal Aggregations
- `day` - Daily data
- `month` - Monthly aggregated (default for most endpoints)
- `year` - Annual aggregated

### Data Formats
- `tiff` - GeoTIFF raster files (default for raster endpoints)
- `json` - JSON responses (default for metadata/station data)
- `csv` - Comma-separated values

## Tools Directory Structure

Each MCP tool lives in its own module under `hcdp_mcp_server/tools/`:

| File | Tool |
|------|------|
| `constants.py` | Shared constants (island extents, city locations, bounding boxes) and helpers |
| `timeseries.py` | `get_timeseries_data` — historical climate time series for coordinates |
| `station_data.py` | `get_station_data` — station-specific climate measurements |
| `mesonet_data.py` | `get_mesonet_data` — real-time mesonet weather measurements |
| `mesonet_stations.py` | `get_mesonet_stations` — list available mesonet stations |
| `mesonet_variables.py` | `get_mesonet_variables` — list mesonet measurement variables |
| `island_summary.py` | `get_island_current_summary` — island-wide weather aggregation |
| `city_weather.py` | `get_city_current_weather` — city-level current weather |
| `compare_historical.py` | `compare_current_vs_historical` — current vs historical comparison |
| `island_history.py` | `get_island_history_summary` — parallelized island history |

Each tool module exports:
- **Args model** — Pydantic `BaseModel` for input validation
- **`tool_definition`** — `mcp.types.Tool` instance
- **`handle(client, arguments)`** — async handler function

The `tools/__init__.py` provides:
- `TOOL_REGISTRY` — maps tool names to modules
- `get_all_tool_definitions()` — returns all Tool objects for registration
- `dispatch_tool(name, client, arguments)` — routes calls to the correct handler

## Mesonet Rainfall Data Rules

When working with HCDP Mesonet rainfall data, these rules are critical for correctness:

### 1. Always Convert UTC to HST Before Daily Aggregation
Mesonet timestamps are in UTC. Hawaii Standard Time is UTC−10 with no daylight saving. **Never group raw timestamps by calendar date** — subtract 10 hours first:
```python
from datetime import datetime, timedelta
hst_dt = datetime.fromisoformat(record['timestamp'].replace('Z','')) - timedelta(hours=10)
day = hst_dt.strftime('%Y-%m-%d')
```
Skipping this causes major storm events to appear as 0mm on the storm day and inflates adjacent days.

### 2. Use 5-Minute Totals for Recent Data
Daily aggregate variables (`RF_1_Tot86400s`) and hourly (`RF_1_Tot3600s`) frequently return empty arrays for dates within the past several months. **Always fall back to summing `RF_1_Tot300s`** (5-minute totals) with the HST conversion above.

### 3. Chunk Date Ranges (1MB Response Limit)
Querying `RF_1_Tot300s` across multiple stations for more than ~3 days hits the response size limit. **Limit each request to 2–3 day windows** and loop, or reduce the station count per call.

### 4. HCDP Processed Timeseries Lags by Months
`get_timeseries_data` and gridded rainfall products are not available for recent dates. For anything within the past ~6 months, **always use `get_mesonet_data` with `RF_1_Tot300s`** and sum manually.

### 5. CSV Export Discrepancies
HCDP CSV exports use a different daily accumulation window that may not align with midnight-to-midnight UTC sums from the raw Mesonet stream. Expect small discrepancies on non-storm days; major totals (peak storm days) should match closely.

## Mesonet Real-Time Data Behaviors

Discovered during live testing of `get_mesonet_data` (2026-04-01):

### 6. Sort Order Depends on end_date
- **WITH `end_date`**: results are **ascending** (oldest first). `offset=0` = earliest record in the window.
- **WITHOUT `end_date`**: results are **descending** (newest first). `offset=0` = most recent record available.

Omit `end_date` when you want the latest reading; include it when you need a historical window in chronological order.

### 7. Pattern for Most Recent Reading
To get the latest value for a station/variable:
```python
start_date = today's date   # YYYY-MM-DD
end_date = (omit)
limit = 1
offset = 0
```
This returns the single most recent 5-minute reading, approximately 20–25 minutes behind real time.

### 8. Data Lag ~20–25 Minutes
Mesonet data is near-real-time, not live. The most recent record is typically 20–30 minutes behind the current clock time. Do not expect sub-minute freshness.

### 9. Prefer Direct Station Queries for Microclimates
`get_city_current_weather` averages all stations within ~15 km of a city centre. This obscures local microclimates (valleys, upland areas). For precise readings, use `get_mesonet_stations` to locate the nearest individual station, then query it directly with `get_mesonet_data`.

Example: Lyon Arboretum (`station_id=0501`, lat=21.333, lng=−157.8025) gives a far more accurate reading for Mānoa valley than the Honolulu city average.

## Key Implementation Notes

- All HTTP requests use 60-120 second timeouts to accommodate large data downloads
- Authentication uses Bearer tokens in Authorization headers
- Date parameters must be in YYYY-MM-DD format
- The MCP server runs over stdio for integration with AI assistants
- Error handling preserves original HCDP API error messages for debugging