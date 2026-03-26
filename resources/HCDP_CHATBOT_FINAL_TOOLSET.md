# HCDP Chatbot — Final Recommended MCP Toolset

**Date:** 2026-03-17  
**Goal:** Define the best MCP tools for a production HCDP chatbot, optimized for real user questions and reliable API behavior.

---

## Design Principles

1. **Semantic over raw API passthrough**: tools should match user intent ("what’s the temperature in Honolulu now?") rather than expose low-level query mechanics.
2. **Explicit names by data system**: keep Mesonet and Raster/Station clearly separated in naming.
3. **Small, predictable parameter sets**: default required companion params internally when safe.
4. **Backward-compatible migration**: keep legacy tool names as aliases during transition.
5. **Avoid known-broken wrappers as primary tools**: replace with reliable, composable alternatives.

---

## Final Tool List (Recommended)

## A) Mesonet Real-Time Tools (Primary for “current conditions”)

### 1) `get_mesonet_measurements`
**Purpose:** Query Mesonet measurement rows/time-series directly (primary data retrieval tool).  
**Replaces/Aliases:** current `get_mesonet_data`  
**Why:** Most reliable real-time endpoint; supports station/variable/date filtering and row modes.

### 2) `get_mesonet_stations`
**Purpose:** List station metadata (lat/lng, status, IDs).  
**Replaces/Aliases:** current `get_mesonet_stations` (same)  
**Why:** Required for station discovery, geographic filtering, and validation.

### 3) `get_mesonet_variables`
**Purpose:** List variable metadata and IDs (`Tair_1_Avg`, `RF_1_Tot300s`, etc.).  
**Replaces/Aliases:** current `get_mesonet_variables` (same)  
**Why:** Required for robust NL-to-var_id mapping.

### 4) `get_station_latest`
**Purpose:** Fast latest snapshot by station/variable from station monitor data.  
**Underlying:** `/mesonet/db/stationMonitor`  
**Why:** Handles “right now at station X” better than full measurement query.

### 5) `get_nearest_stations`
**Purpose:** Return active stations near a lat/lng (optionally filtered by variable).  
**Why:** Core geographic routing primitive for city/place questions.

### 6) `get_network_status`
**Purpose:** Report station online/offline recency and currently reporting variables.  
**Why:** Makes empty-result explanations accurate and transparent.

### 7) `export_mesonet_csv`
**Purpose:** Email Mesonet data extracts for larger/time-ranged requests.  
**Underlying:** `/mesonet/db/measurements/email`  
**Why:** Useful when users request downloadable data products.

---

## B) Raster & Historical Climate Tools (Primary for “history/trends”)

### 8) `get_raster_map`
**Purpose:** Retrieve a GeoTIFF raster for a date/product.  
**Replaces/Aliases:** (re-enable/replace current commented `get_climate_raster`)  
**Why:** Direct map product access with explicit climate product semantics.

### 9) `get_raster_timeseries`
**Purpose:** Point/grid-cell historical timeseries.  
**Replaces/Aliases:** current `get_timeseries_data`  
**Why:** Clearer name and scope than generic `get_timeseries_data`.

### 10) `get_rainfall_product`
**Purpose:** Safe rainfall timeseries wrapper with correct defaults (`production`, `period`).  
**Why:** Prevents common `{}` failures from missing companion params.

### 11) `get_drought_index`
**Purpose:** SPI timeseries with user-friendly `timescale_months` input and interpretation bins.  
**Why:** Makes drought workflows usable without raw timescale enum knowledge.

### 12) `batch_raster_download`
**Purpose:** Multi-dataset packaged retrieval via genzip (link/email/inline).  
**Underlying:** `/genzip/*`  
**Why:** Essential for analysts requesting many files in one task.

---

## C) Station Product Tools (Historical station records)

### 13) `query_station_metadata`
**Purpose:** Return station metadata documents from `/stations`.  
**Replaces/Aliases:** split from current `get_station_data`  
**Why:** Removes fragile Mongo query-string burden from chatbot logic.

### 14) `query_station_value`
**Purpose:** Return station value for specific date and product keys.  
**Replaces/Aliases:** split from current `get_station_data`  
**Why:** Covers targeted historical station lookups safely.

### 15) `query_station_timeseries`
**Purpose:** Return station values across date range with validated filters.  
**Replaces/Aliases:** split from current `get_station_data`  
**Why:** Covers trend queries while preserving required station query constraints.

---

## D) Chatbot-Oriented Composite Tools (High-value UX layer)

### 16) `get_city_current_weather`
**Purpose:** City-level current summary using nearest active stations + correct var_id mapping.  
**Status Note:** Keep only after fixing current wrapper behavior.  
**Why:** Very common user query shape.

### 17) `get_city_climate_history`
**Purpose:** City historical climate summary with correct raster companion params, plus optional current comparison.  
**Why:** Replaces brittle current-vs-historical pipeline with deterministic behavior.

### 18) `get_island_history_summary`
**Purpose:** Parallel representative-point island history summary.  
**Replaces/Aliases:** current `get_island_history_summary` (keep, refine)  
**Why:** Strong fit for island-level “how was year X” questions.

### 19) `get_island_comparison`
**Purpose:** One-call cross-island ranking/comparison for a period/year.  
**Why:** High-frequency comparative climate question pattern.

### 20) `resolve_location`
**Purpose:** Normalize natural-language Hawaii places into lat/lng + candidate stations.  
**Why:** Critical for colloquial geography (“windward Oahu”, “upcountry Maui”).

---

## Recommended Naming Convention

Use this convention consistently:

- `get_mesonet_*` for Mesonet endpoints
- `get_raster_*` for gridded/raster endpoints
- `query_station_*` for `/stations` document queries
- `batch_*` or `export_*` for bulk delivery workflows
- `resolve_*` for chatbot utility/routing helpers

This convention is preferred over generic names like `get_station_data` because it improves tool discoverability, model tool selection accuracy, and maintenance clarity.

---

## Keep / Deprecate Matrix (from current server)

## Keep (or keep as alias)
- `get_mesonet_stations`
- `get_mesonet_variables`
- `get_mesonet_data` → alias to `get_mesonet_measurements`
- `get_timeseries_data` → alias to `get_raster_timeseries`
- `get_island_history_summary` (refine internals as needed)

## Deprecate as primary (replace with above)
- `get_station_data` (replace with `query_station_metadata/value/timeseries`)
- `get_island_current_summary` (replace with robust nearest-station/monitor-based implementation)
- `get_city_current_weather` (current version unreliable; keep only after fix)
- `compare_current_vs_historical` (replace with `get_city_climate_history`)

---

## Minimum Viable “Best” Tool Subset (if you want to launch quickly)

If you only want a lean first release, ship these first:

1. `get_mesonet_measurements`
2. `get_mesonet_stations`
3. `get_mesonet_variables`
4. `get_station_latest`
5. `get_nearest_stations`
6. `get_raster_timeseries`
7. `get_rainfall_product`
8. `query_station_metadata`
9. `query_station_value`
10. `resolve_location`

This MVP covers most real chatbot requests accurately while avoiding known failure patterns.
