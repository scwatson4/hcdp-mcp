#!/usr/bin/env python3
"""Download actual HCDP climate data."""

import asyncio
import json
import base64
from hcdp_mcp_server.client import HCDPClient

async def download_climate_data():
    """Download climate data to sample_data folder."""
    
    print("Downloading HCDP climate data...")
    print("=" * 40)
    
    client = HCDPClient()
    
    # Download rainfall data (we know this works)
    try:
        print("Downloading rainfall data for February 2022, Big Island...")
        rainfall_result = await client.get_raster_data(
            datatype="rainfall",
            date="2022-02",
            extent="bi", 
            production="new",
            period="month"
        )
        
        # Save the data
        if 'data' in rainfall_result and rainfall_result['data']:
            # Decode base64 data and save to file
            raster_data = base64.b64decode(rainfall_result['data'])
            with open('sample_data/rainfall_2022-02_big_island.tiff', 'wb') as f:
                f.write(raster_data)
            print("✓ Saved: sample_data/rainfall_2022-02_big_island.tiff")
        else:
            print("No raster data found in response")
            
    except Exception as e:
        print(f"✗ Rainfall error: {e}")
    
    # Try different temperature datatypes
    temp_types = ["temp_mean", "temp_max", "temp_min", "temperature"]
    
    for temp_type in temp_types:
        try:
            print(f"Trying temperature datatype: {temp_type}")
            temp_result = await client.get_raster_data(
                datatype=temp_type,
                date="2022-02",
                extent="bi",
                production="new", 
                period="month"
            )
            
            # Save the data
            if 'data' in temp_result and temp_result['data']:
                raster_data = base64.b64decode(temp_result['data'])
                with open(f'sample_data/{temp_type}_2022-02_big_island.tiff', 'wb') as f:
                    f.write(raster_data)
                print(f"✓ Saved: sample_data/{temp_type}_2022-02_big_island.tiff")
                break  # Found working temperature datatype
            else:
                print("No raster data found in response")
                
        except Exception as e:
            print(f"✗ {temp_type} error: {e}")
            
    print("\nChecking what we downloaded:")
    import os
    for file in os.listdir('sample_data'):
        if file.endswith('.tiff'):
            size = os.path.getsize(f'sample_data/{file}')
            print(f"  {file}: {size:,} bytes")

if __name__ == "__main__":
    asyncio.run(download_climate_data())