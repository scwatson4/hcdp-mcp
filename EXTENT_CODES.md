# HCDP Extent Codes Reference

## Official API Extent Codes

Based on the HCDP API specification, these are the **correct** extent codes:

| API Code | Island/Region | County Name |
|----------|---------------|-------------|
| `bi` | Big Island | Hawaii County |
| `oa` | Oahu | Honolulu County |
| `ka` | Kauai | Kauai County |
| `mn` | Maui County | Maui County (includes Maui, Molokai, Lanai) |
| `statewide` | All Islands | Entire State of Hawaii |

## ✅ Correct Usage

```python
# Raster data
extent="bi"         # Big Island
extent="oa"         # Oahu
extent="ka"         # Kauai  
extent="mn"         # Maui County
extent="statewide"  # All islands

# Timeseries data (match extent to coordinates)
extent="oa", lat=21.3, lng=-157.8      # Honolulu, Oahu
extent="bi", lat=19.7, lng=-155.1      # Hilo, Big Island
extent="ka", lat=22.0, lng=-159.5      # Kauai
extent="mn", lat=20.9, lng=-156.4      # Maui
```

## ❌ Common Mistakes (DO NOT USE)

| Wrong | Correct | Notes |
|-------|---------|-------|
| `oahu` | `oa` | API uses 2-letter codes |
| `kauai` | `ka` | API uses 2-letter codes |
| `maui_county` | `mn` | API uses 2-letter codes |
| `maui` | `mn` | Use county code, not island name |
| `molokai` | `mn` | Part of Maui County |
| `lanai` | `mn` | Part of Maui County |
| `big_island` | `bi` | Use official code |
| `hawaii_island` | `bi` | Use official code |

## Natural Language Mapping

When Claude receives natural language queries, it should map:

| User Says | Use Code |
|-----------|----------|
| "Big Island" | `bi` |
| "Oahu" | `oa` |
| "Honolulu" | `oa` |
| "Kauai" | `ka` |
| "Maui" | `mn` |
| "Maui County" | `mn` |
| "Molokai" | `mn` |
| "Lanai" | `mn` |
| "statewide" | `statewide` |
| "all islands" | `statewide` |
| "Hawaii" (ambiguous) | `statewide` (safest) |

## Data Availability by Extent

### Raster Data
All extent codes work for raster data:
- ✅ `bi`, `oa`, `ka`, `mn`, `statewide`

### Timeseries Data  
For timeseries, the extent must match the coordinate location:
- ✅ Use `oa` for Oahu coordinates (21.x, -157.x)
- ✅ Use `bi` for Big Island coordinates (19.x, -155.x)
- ✅ Use `statewide` as fallback (works for all coordinates)

## Testing Results

From `test_correct_extents.py`:

**Timeseries** (Honolulu coordinates 21.333, -157.8025):
- `oa`: ✅ 589.73 mm
- `statewide`: ✅ 581.73 mm
- `bi`, `ka`, `mn`: ❌ Empty (wrong island)

**Raster** (January 2025):
- `oa`: ✅ 136 KB
- `bi`: ✅ 848 KB
- `ka`: ✅ 119 KB
- `mn`: ✅ 281 KB
- `statewide`: ✅ 1.75 MB
