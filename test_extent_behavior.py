#!/usr/bin/env python3
"""Test extent parameter behavior for timeseries vs raster."""

import asyncio
from hcdp_mcp_server.client import HCDPClient

async def test_extent_behavior():
    client = HCDPClient()
    
    print("Testing extent parameter behavior...\n")
    
    # Honolulu coordinates
    lat, lng = 21.333, -157.8025
    
    # Test 1: Timeseries with different extents
    print("=== TIMESERIES TESTS ===")
    extents = ["oahu", "statewide", "bi"]
    
    for extent in extents:
        print(f"\nExtent: {extent}")
        try:
            result = await client.get_timeseries_data(
                datatype="rainfall",
                start="2025-01-01",
                end="2025-01-31",
                extent=extent,
                lat=lat,
                lng=lng,
                production="new",
                period="month"
            )
            if result:
                print(f"  SUCCESS - Got {len(result)} data points")
                print(f"    Sample: {list(result.items())[0] if result else 'empty'}")
            else:
                print(f"  EMPTY result (no data)")
        except Exception as e:
            print(f"  ERROR: {str(e)[:80]}")
    
    # Test 2: Raster with different extents
    print("\n\n=== RASTER TESTS ===")
    for extent in ["oahu", "statewide", "bi"]:
        print(f"\nExtent: {extent}")
        try:
            result = await client.get_raster_data(
                datatype="rainfall",
                date="2025-01",
                extent=extent,
                production="new",
                period="month"
            )
            print(f"  SUCCESS - Got {len(result.get('data', b''))} bytes")
        except Exception as e:
            print(f"  ERROR: {str(e)[:80]}")

if __name__ == "__main__":
    asyncio.run(test_extent_behavior())
