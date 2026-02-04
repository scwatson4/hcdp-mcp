#!/usr/bin/env python3
"""Test with CORRECT extent codes from API documentation."""

import asyncio
from hcdp_mcp_server.client import HCDPClient

async def test_correct_extents():
    client = HCDPClient()
    
    print("Testing CORRECT extent codes from API docs...\n")
    
    # Honolulu coordinates
    lat, lng = 21.333, -157.8025
    
    print("=== TIMESERIES with CORRECT codes ===")
    correct_extents = {
        "oa": "Oahu/Honolulu County",
        "bi": "Big Island",
        "ka": "Kauai",
        "mn": "Maui County",
        "statewide": "Statewide"
    }
    
    for code, name in correct_extents.items():
        print(f"\n{code} ({name}):")
        try:
            result = await client.get_timeseries_data(
                datatype="rainfall",
                start="2025-01-01",
                end="2025-01-31",
                extent=code,
                lat=lat,
                lng=lng,
                production="new",
                period="month"
            )
            if result:
                print(f"  SUCCESS - Got {len(result)} data points")
                print(f"  Value: {list(result.values())[0]:.2f} mm")
            else:
                print(f"  EMPTY (no data)")
        except Exception as e:
            print(f"  ERROR: {str(e)[:80]}")
    
    print("\n\n=== RASTER with CORRECT codes ===")
    for code, name in correct_extents.items():
        print(f"\n{code} ({name}):")
        try:
            result = await client.get_raster_data(
                datatype="rainfall",
                date="2025-01",
                extent=code,
                production="new",
                period="month"
            )
            print(f"  SUCCESS - {len(result.get('data', b''))} bytes")
        except Exception as e:
            print(f"  ERROR: {str(e)[:80]}")

if __name__ == "__main__":
    asyncio.run(test_correct_extents())
