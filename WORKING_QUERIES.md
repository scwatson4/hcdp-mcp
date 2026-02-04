# HCDP MCP Server - Working Query Examples

## ✅ Working Endpoints

### 1. Rainfall Raster Data
```
Tool: get_climate_raster
Parameters:
  - datatype: "rainfall"
  - date: "2022-02" (YYYY-MM format)
  - extent: "bi" (Big Island)
  - production: "new"
  - period: "month"
Result: Returns GeoTIFF binary data (~885KB)
```

### 2. Rainfall Timeseries Data
```
Tool: get_timeseries_data
Parameters:
  - datatype: "rainfall"
  - start: "2024-01-01"
  - end: "2024-12-31"
  - extent: "bi" (Big Island - matches coordinates)
  - lat: 19.7167 (Hilo coordinates)
  - lng: -155.0833
  - production: "new"
  - period: "month"
Result: Returns 12 monthly data points with rainfall values
```

### 3. Mesonet Stations
```
Tool: get_mesonet_stations
Parameters:
  - location: "hawaii"
Result: Returns 103 weather stations with metadata
```

### 4. Mesonet Data
```
Tool: get_mesonet_data
Parameters:
  - location: "hawaii"
  - start_date: "2024-12-01"
  - end_date: "2024-12-02"
  - limit: 100
Result: Returns recent weather measurements
```

## ❌ Known Issues

### Station Data Query
- **Issue**: Returns 400 Bad Request
- **Attempted**: `q="rainfall"` and `q="{}"`
- **Status**: Query format may need adjustment

### List Production Files
- **Issue**: Returns 400 Bad Request
- **Attempted**: Various datatype/extent combinations
- **Status**: May require additional parameters

## 📝 Key Findings

1. **Timeseries requires specific coordinates** - Empty results mean no data for those lat/lng
2. **Production parameter** - Only works for rainfall, not temperature
3. **Temperature data** - Use `aggregation="month"` instead of `production`
4. **Date formats** - Use YYYY-MM for rasters, YYYY-MM-DD for timeseries
5. **Extent codes**: `bi` (Big Island), `statewide`, `oahu`, `maui_county`, etc.

## 🎯 Recommended Queries for Claude Desktop

**Get recent rainfall for Hilo:**
> "Get rainfall timeseries data for Hilo (19.7167, -155.0833) for 2024"

**Get rainfall map:**
> "Get rainfall raster data for Big Island in February 2022"

**List weather stations:**
> "Show me all mesonet weather stations in Hawaii"

**Get recent weather data:**
> "Get mesonet measurements for Hawaii from December 1-2, 2024"
