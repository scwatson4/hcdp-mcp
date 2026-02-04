#!/usr/bin/env python3
"""Test known working parameter combinations."""

import asyncio
import json
from hcdp_mcp_server.client import HCDPClient

async def test_working_params():
    client = HCDPClient()
    
    print("Testing known working parameter combinations...\n")
    
    # Test 1: Rainfall raster (we know this works)
    print("1. Rainfall raster - February 2022, Big Island:")
    try:
        result = await client.get_raster_data(
            datatype="rainfall",
            date="2022-02",
            extent="bi",
            production="new",
            period="month"
        )
        print(f"   SUCCESS - Got {len(result.get('data', b''))} bytes")
    except Exception as e:
        print(f"   FAILED: {e}")
    
    # Test 2: Timeseries from comprehensive samples
    print("\n2. Timeseries - Hilo area, 2024:")
    try:
        result = await client.get_timeseries_data(
            datatype="rainfall",
            start="2024-01-01",
            end="2024-12-31",
            extent="bi",
            lat=19.7167,
            lng=-155.0833,
            production="new",
            period="month"
        )
        print(f"   SUCCESS - Got {len(result)} data points")
        if result:
            print(f"   Sample: {json.dumps(result[:2] if isinstance(result, list) else result, indent=2)}")
    except Exception as e:
        print(f"   FAILED: {e}")
    
    # Test 3: Station data with proper query format
    print("\n3. Station data - All stations:")
    try:
        result = await client.get_station_data(q="{}")
        print(f"   SUCCESS - Got {len(result)} results")
    except Exception as e:
        print(f"   FAILED: {e}")
    
    # Test 4: Mesonet stations
    print("\n4. Mesonet stations:")
    try:
        result = await client.get_mesonet_stations(location="hawaii")
        print(f"   SUCCESS - Got {len(result)} stations")
    except Exception as e:
        print(f"   FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_working_params())
