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

## Key Implementation Notes

- All HTTP requests use 60-120 second timeouts to accommodate large data downloads
- Authentication uses Bearer tokens in Authorization headers
- Date parameters must be in YYYY-MM-DD format
- The MCP server runs over stdio for integration with AI assistants
- Error handling preserves original HCDP API error messages for debugging