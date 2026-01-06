#!/usr/bin/env python3
"""Try to download December 2024 climate data."""

import asyncio
import json
import base64
from hcdp_mcp_server.client import HCDPClient

async def download_december_2024():
    """Try to download December 2024 data."""
    
    print("Attempting to download December 2024 climate data...")
    print("=" * 50)
    
    client = HCDPClient()
    
    # Try different date formats and production levels for December 2024
    test_configs = [
        {"date": "2024-12", "production": "new"},
        {"date": "2024-12", "production": "preliminary"},  
        {"date": "2024-12", "production": None},
        {"date": "2024-11", "production": "new"},  # Try November instead
        {"date": "2024-10", "production": "new"},  # Try October
    ]
    
    # Try both extents
    extents = ["bi", "statewide"]
    
    for extent in extents:
        print(f"\n--- Testing extent: {extent} ---")
        for config in test_configs:
            try:
                print(f"Trying date={config['date']}, production={config['production']}")
                
                params = {
                    "datatype": "rainfall",
                    "date": config["date"],
                    "extent": extent,
                    "period": "month"
                }
                if config["production"]:
                    params["production"] = config["production"]
                
                result = await client.get_raster_data(**params)
                
                if 'data' in result and result['data']:
                    raster_data = base64.b64decode(result['data'])
                    filename = f"sample_data/rainfall_{config['date']}_{extent}_{config['production'] or 'default'}.tiff"
                    with open(filename, 'wb') as f:
                        f.write(raster_data)
                    print(f"✓ SUCCESS! Saved: {filename} ({len(raster_data):,} bytes)")
                    
                    # Try to get temperature data with the same successful parameters
                    try:
                        temp_result = await client.get_raster_data(
                            datatype="temp_mean",
                            date=config["date"],
                            extent=extent,
                            period="month",
                            production=config["production"]
                        )
                        if 'data' in temp_result and temp_result['data']:
                            temp_data = base64.b64decode(temp_result['data'])
                            temp_filename = f"sample_data/temp_mean_{config['date']}_{extent}_{config['production'] or 'default'}.tiff"
                            with open(temp_filename, 'wb') as f:
                                f.write(temp_data)
                            print(f"✓ BONUS! Temperature data: {temp_filename} ({len(temp_data):,} bytes)")
                    except Exception as te:
                        print(f"  Temperature failed: {str(te)[:80]}...")
                    
                else:
                    print("  No data in response")
                    
            except Exception as e:
                print(f"  ✗ Failed: {str(e)[:80]}...")

if __name__ == "__main__":
    asyncio.run(download_december_2024())