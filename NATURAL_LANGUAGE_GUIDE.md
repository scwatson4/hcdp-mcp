# Natural Language Query Guide for Claude Desktop

## How It Works

After restarting Claude Desktop, you can use **natural language** to query HCDP data. Claude will automatically map your request to the correct parameters.

## ✅ Natural Language Examples

### Rainfall Queries
```
"Get rainfall data for Big Island in February 2022"
→ Claude infers: datatype='rainfall', extent='bi', date='2022-02', production='new', period='month'

"Show me precipitation for Oahu last month"
→ Claude infers: datatype='rainfall', extent='oa', date=(last month), production='new'

"Download rainfall map for statewide Hawaii in January 2024"
→ Claude infers: datatype='rainfall', extent='statewide', date='2024-01', production='new', period='month'
```

### Temperature Queries
```
"Get temperature data for Maui County in March 2024"
→ Claude infers: datatype='temp_mean', extent='mn', date='2024-03', aggregation='month'

"Show me minimum temperature for Big Island last summer"
→ Claude infers: datatype='temp_min', extent='bi', date=(summer months), aggregation='month'
```

### Timeseries Queries
```
"Get rainfall timeseries for Hilo for 2024"
→ Claude infers: datatype='rainfall', extent='bi', lat=19.7167, lng=-155.0833, start='2024-01-01', end='2024-12-31', production='new', period='month'

"Show monthly rainfall at coordinates 21.3, -157.8 for last year"
→ Claude infers: extent='oa', lat=21.3, lng=-157.8, start/end=(last year), period='month'
```

### Weather Station Queries
```
"Show me all weather stations in Hawaii"
→ Uses: get_mesonet_stations

"What weather variables can I measure?"
→ Uses: get_mesonet_variables

"Get recent weather data from December 2024"
→ Uses: get_mesonet_data with appropriate dates
```

## 🎯 Key Improvements Made

### 1. Enhanced Tool Descriptions
- Added example queries for each tool
- Included parameter requirements and formats
- Specified when to use production vs aggregation

### 2. Improved Field Descriptions
- **Datatype**: Recognizes aliases like "precipitation" → "rainfall", "temperature" → "temp_mean"
- **Extent**: Maps "Big Island" → "bi", includes all valid codes
- **Date**: Clarifies YYYY-MM format with examples
- **Production/Aggregation**: Explains when each is required

### 3. Coordinate Validation
- Accepts both string and float formats
- Automatically converts strings to floats

## 📝 Tips for Best Results

1. **Be specific about location**: "Big Island" or "Oahu" works better than just "Hawaii"
2. **Mention the data type**: "rainfall", "temperature", "humidity"
3. **Include time period**: "February 2022", "last month", "2024"
4. **For timeseries**: Provide coordinates or location name (Claude knows major cities)

## 🔄 After Making Changes

**Always restart Claude Desktop** to pick up schema updates:
1. Quit Claude Desktop completely
2. Restart it
3. Verify MCP connection (🔌 icon)
4. Try a natural language query

## Common Mappings

| You Say | Claude Uses |
|---------|-------------|
| "Big Island" | extent='bi' |
| "Oahu" | extent='oa' |
| "Kauai" | extent='ka' |
| "Maui" or "Maui County" | extent='mn' |
| "precipitation" | datatype='rainfall' |
| "temperature" | datatype='temp_mean' |
| "last month" | date=(calculates YYYY-MM) |
| "Hilo" | lat=19.7167, lng=-155.0833, extent='bi' |
| "Honolulu" | lat=21.3, lng=-157.8, extent='oa' |
