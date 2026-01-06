# HCDP MCP Sample Data

This directory contains test files and examples for using the Hawaii Climate Data Portal (HCDP) MCP server.

## Test Results

The MCP server is configured and ready to download climate data. However, actual data downloads require a valid HCDP API token.

### Requested Data (December 2024, Big Island)

- **Temperature (Mean)**: `sample_temp_mean_2024-12-15_big_island.tiff`
- **Precipitation**: `sample_rainfall_2024-12-15_big_island.tiff`

### API Configuration Required

To download actual data, update `.env` with a valid HCDP API token:

```bash
HCDP_API_TOKEN=your_actual_token_here
```

### Example MCP Tool Calls

```python
# Temperature data
mcp__hcdp__get_climate_raster(
    datatype="temp_mean",
    date="2024-12-15", 
    extent="big_island"
)

# Precipitation data  
mcp__hcdp__get_climate_raster(
    datatype="rainfall",
    date="2024-12-15",
    extent="big_island"
)
```

### Available Datatypes
- `temp_mean`, `temp_min`, `temp_max` - Temperature data
- `rainfall` - Precipitation data
- `rh` - Relative humidity
- `spi` - Standardized Precipitation Index

### Available Extents
- `statewide` - All Hawaiian islands
- `big_island` - Hawaii (Big Island)
- `oahu` - Oahu island
- `maui` - Maui island
- `molokai` - Molokai island
- `lanai` - Lanai island
- `kauai` - Kauai island