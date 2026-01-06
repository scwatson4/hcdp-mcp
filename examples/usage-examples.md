# HCDP MCP Server Usage Examples

## Natural Language Queries

Once configured in your AI assistant, you can use these types of natural language queries:

### Climate Data Queries

**Rainfall Data:**
```
"Get rainfall data for Oahu on January 1st, 2023"
"Show me precipitation maps for the Big Island in December 2022"
"What was the rainfall for statewide Hawaii in 2023?"
```

**Temperature Data:**
```
"Get temperature data for Maui on July 4th, 2023"
"Show mean temperature for Hawaii from June to August 2023"
"What were the minimum temperatures across all islands in January?"
```

### Time Series Analysis

```
"Show me temperature time series for coordinates 21.3, -157.8 from 2022 to 2023"
"Get rainfall time series for Honolulu coordinates from January to December 2023"
"Extract climate data for specific lat/lng 19.5, -155.5 over the past year"
```

### Station Queries

```
"Find all weather stations in Hawaii"
"Show me stations on Oahu with temperature measurements"
"Get information about weather stations near Hilo"
```

### Real-time Data

```
"Get latest mesonet data from Big Island weather stations"
"Show current conditions from Oahu weather stations"
"What are the recent measurements from station ID 12345?"
```

### Data Package Generation

```
"Create a data package with rainfall data for the Big Island in 2023"
"Generate a download package of temperature data for Maui from 2020-2023"
"Email me a zip file of humidity data for American Samoa"
```

## Direct Tool Usage Examples

### get_climate_raster

**Get statewide rainfall for a specific date:**
```json
{
  "tool": "get_climate_raster",
  "parameters": {
    "datatype": "rainfall",
    "date": "2023-01-15",
    "extent": "statewide",
    "location": "hawaii"
  }
}
```

**Get temperature data for Oahu:**
```json
{
  "tool": "get_climate_raster", 
  "parameters": {
    "datatype": "temp_mean",
    "date": "2023-07-01",
    "extent": "oahu",
    "aggregation": "month"
  }
}
```

### get_timeseries_data

**Temperature time series for specific coordinates:**
```json
{
  "tool": "get_timeseries_data",
  "parameters": {
    "datatype": "temp_mean",
    "start": "2023-01-01",
    "end": "2023-12-31",
    "extent": "statewide",
    "lat": 21.3099,
    "lng": -157.8581
  }
}
```

**Rainfall time series for Big Island:**
```json
{
  "tool": "get_timeseries_data",
  "parameters": {
    "datatype": "rainfall",
    "start": "2023-06-01", 
    "end": "2023-08-31",
    "extent": "big_island",
    "production": "daily"
  }
}
```

### get_station_data

**Find all stations:**
```json
{
  "tool": "get_station_data",
  "parameters": {
    "q": "{}",
    "limit": 50
  }
}
```

**Search for stations by name:**
```json
{
  "tool": "get_station_data",
  "parameters": {
    "q": "{\"name\": {\"$regex\": \"Honolulu\", \"$options\": \"i\"}}",
    "limit": 10
  }
}
```

**Find stations on specific island:**
```json
{
  "tool": "get_station_data", 
  "parameters": {
    "q": "{\"island\": \"Oahu\"}",
    "limit": 25
  }
}
```

### get_mesonet_data

**Get recent data from all Big Island stations:**
```json
{
  "tool": "get_mesonet_data",
  "parameters": {
    "start_date": "2023-12-01",
    "end_date": "2023-12-31", 
    "location": "hawaii",
    "join_metadata": true
  }
}
```

**Get specific variables from specific stations:**
```json
{
  "tool": "get_mesonet_data",
  "parameters": {
    "station_ids": "1,15,23",
    "var_ids": "temperature,humidity,pressure",
    "start_date": "2023-11-01",
    "end_date": "2023-11-30"
  }
}
```

### generate_data_package

**Create rainfall data package:**
```json
{
  "tool": "generate_data_package",
  "parameters": {
    "email": "researcher@university.edu",
    "datatype": "rainfall",
    "extent": "statewide",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "zipName": "Hawaii_Rainfall_2023"
  }
}
```

**Generate temperature package for specific island:**
```json
{
  "tool": "generate_data_package",
  "parameters": {
    "email": "climate@research.org", 
    "datatype": "temp_mean",
    "extent": "maui",
    "start_date": "2020-01-01",
    "end_date": "2023-12-31",
    "aggregation": "monthly"
  }
}
```

## Common Workflows

### Climate Research Workflow
1. "Find all temperature stations on the Big Island"
2. "Get temperature time series for coordinates near Hilo from 2020-2023"
3. "Create a data package with Big Island temperature and rainfall data"
4. "Generate maps showing temperature trends across Hawaii"

### Agricultural Analysis
1. "Get rainfall data for Oahu farmland areas in growing season 2023"
2. "Show humidity levels for Maui during summer months"
3. "Compare precipitation between different Hawaiian islands"
4. "Create irrigation planning data package for Central Valley farms"

### Disaster Planning
1. "Get historical extreme precipitation events for all islands"
2. "Show temperature extremes during hurricane seasons"
3. "Find weather stations near evacuation routes"
4. "Generate climate data package for emergency planning"

## Response Formats

The MCP server returns structured JSON data that AI assistants can interpret and present in user-friendly formats. Typical response structures include:

- **Raster data**: GeoTIFF file references and metadata
- **Time series**: Arrays of date/value pairs with units
- **Station data**: Lists of station metadata and locations
- **Mesonet data**: Real-time measurements with timestamps
- **Data packages**: Download links and package information

The AI assistant will automatically format this data into tables, charts, maps, or other visualizations as appropriate.