#!/usr/bin/env python3
"""Test what temperature data is actually available."""

import asyncio
from hcdp_mcp_server.client import HCDPClient

async def test_temp_availability():
    client = HCDPClient()
    
    print("Testing temperature data availability...\n")
    
    # Test various dates going backwards
    test_dates = [
        "2024-11",  # November 2024 (known to work from earlier tests)
        "2024-10",
        "2024-06",
        "2024-01",
        "2023-12",
        "2023-06",
    ]
    
    extents = ["statewide", "oahu", "bi"]
    
    for extent in extents:
        print(f"\n{extent.upper()}:")
        for date in test_dates:
            try:
                result = await client.get_raster_data(
                    datatype="temp_mean",
                    date=date,
                    extent=extent,
                    aggregation="month"
                )
                print(f"  {date}: SUCCESS ({len(result.get('data', b''))} bytes)")
                break  # Found working date for this extent
            except Exception as e:
                if "404" in str(e):
                    print(f"  {date}: Not available")
                else:
                    print(f"  {date}: ERROR - {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(test_temp_availability())
