"""Download comprehensive climate data samples using HCDP MCP client."""

import asyncio
import json
from pathlib import Path
from hcdp_mcp_server.client import HCDPClient

async def download_comprehensive_samples():
    """Download various climate data samples for testing and documentation."""
    
    client = HCDPClient()
    sample_data_dir = Path("sample_data")
    sample_data_dir.mkdir(exist_ok=True)
    
    print("Downloading comprehensive climate data samples...")
    
    samples = []
    
    # 1. Rainfall data - Big Island, December 2024
    print("\n1. Downloading rainfall data - Big Island, December 2024...")
    try:
        result = await client.get_raster_data(
            datatype="rainfall",
            date="2024-12", 
            extent="bi",
            production="new",
            period="month"
        )
        if 'data' in result:
            filename = sample_data_dir / "rainfall_2024-12_big_island_monthly.tiff"
            with open(filename, 'wb') as f:
                f.write(result['data'])
            print(f"✓ Saved: {filename} ({len(result['data'])} bytes)")
            samples.append({
                "name": "Rainfall - Big Island - December 2024 - Monthly",
                "filename": str(filename),
                "datatype": "rainfall",
                "date": "2024-12",
                "extent": "bi", 
                "production": "new",
                "period": "month",
                "size_bytes": len(result['data'])
            })
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 2. Temperature mean - Statewide, November 2024
    print("\n2. Downloading temperature mean - Statewide, November 2024...")
    try:
        result = await client.get_raster_data(
            datatype="temp_mean",
            date="2024-11",
            extent="statewide",
            aggregation="month"
        )
        if 'data' in result:
            filename = sample_data_dir / "temp_mean_2024-11_statewide_monthly.tiff"
            with open(filename, 'wb') as f:
                f.write(result['data'])
            print(f"✓ Saved: {filename} ({len(result['data'])} bytes)")
            samples.append({
                "name": "Temperature Mean - Statewide - November 2024 - Monthly",
                "filename": str(filename),
                "datatype": "temp_mean",
                "date": "2024-11",
                "extent": "statewide",
                "aggregation": "month",
                "size_bytes": len(result['data'])
            })
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 3. Relative Humidity - Oahu, October 2024
    print("\n3. Downloading relative humidity - Oahu, October 2024...")
    try:
        result = await client.get_raster_data(
            datatype="rh",
            date="2024-10",
            extent="oahu",
            aggregation="month"
        )
        if 'data' in result:
            filename = sample_data_dir / "relative_humidity_2024-10_oahu_monthly.tiff"
            with open(filename, 'wb') as f:
                f.write(result['data'])
            print(f"✓ Saved: {filename} ({len(result['data'])} bytes)")
            samples.append({
                "name": "Relative Humidity - Oahu - October 2024 - Monthly",
                "filename": str(filename),
                "datatype": "rh",
                "date": "2024-10",
                "extent": "oahu",
                "aggregation": "month",
                "size_bytes": len(result['data'])
            })
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 4. Temperature minimum - Big Island, September 2024
    print("\n4. Downloading temperature minimum - Big Island, September 2024...")
    try:
        result = await client.get_raster_data(
            datatype="temp_min", 
            date="2024-09",
            extent="bi",
            aggregation="month"
        )
        if 'data' in result:
            filename = sample_data_dir / "temp_min_2024-09_big_island_monthly.tiff"
            with open(filename, 'wb') as f:
                f.write(result['data'])
            print(f"✓ Saved: {filename} ({len(result['data'])} bytes)")
            samples.append({
                "name": "Temperature Minimum - Big Island - September 2024 - Monthly",
                "filename": str(filename),
                "datatype": "temp_min",
                "date": "2024-09", 
                "extent": "bi",
                "aggregation": "month",
                "size_bytes": len(result['data'])
            })
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 5. Temperature maximum - Maui County, August 2024
    print("\n5. Downloading temperature maximum - Maui County, August 2024...")
    try:
        result = await client.get_raster_data(
            datatype="temp_max",
            date="2024-08",
            extent="maui_county",
            aggregation="month"
        )
        if 'data' in result:
            filename = sample_data_dir / "temp_max_2024-08_maui_county_monthly.tiff"
            with open(filename, 'wb') as f:
                f.write(result['data'])
            print(f"✓ Saved: {filename} ({len(result['data'])} bytes)")
            samples.append({
                "name": "Temperature Maximum - Maui County - August 2024 - Monthly",
                "filename": str(filename),
                "datatype": "temp_max",
                "date": "2024-08",
                "extent": "maui_county",
                "aggregation": "month",
                "size_bytes": len(result['data'])
            })
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 6. Get timeseries data sample
    print("\n6. Downloading timeseries data - Hilo area, 2024...")
    try:
        result = await client.get_timeseries_data(
            datatype="rainfall",
            start="2024-01-01",
            end="2024-12-31",
            extent="bi",
            lat=19.7167,  # Hilo coordinates
            lng=-155.0833,
            production="new",
            period="month"
        )
        filename = sample_data_dir / "timeseries_rainfall_2024_hilo.json"
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"✓ Saved: {filename}")
        samples.append({
            "name": "Rainfall Timeseries - Hilo Area - 2024 - Monthly",
            "filename": str(filename),
            "datatype": "rainfall",
            "start": "2024-01-01",
            "end": "2024-12-31",
            "extent": "bi",
            "lat": 19.7167,
            "lng": -155.0833,
            "production": "new",
            "period": "month",
            "data_points": len(result)
        })
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 7. Get mesonet station info
    print("\n7. Downloading mesonet station information...")
    try:
        result = await client.get_mesonet_stations(location="hawaii")
        filename = sample_data_dir / "mesonet_stations_hawaii.json"
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"✓ Saved: {filename} ({len(result)} stations)")
        samples.append({
            "name": "Mesonet Stations - Hawaii",
            "filename": str(filename),
            "location": "hawaii",
            "station_count": len(result)
        })
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 8. Get mesonet variables
    print("\n8. Downloading mesonet variable definitions...")
    try:
        result = await client.get_mesonet_variables(location="hawaii")
        filename = sample_data_dir / "mesonet_variables_hawaii.json"
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"✓ Saved: {filename} ({len(result)} variables)")
        samples.append({
            "name": "Mesonet Variables - Hawaii", 
            "filename": str(filename),
            "location": "hawaii",
            "variable_count": len(result)
        })
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 9. Get recent mesonet measurements
    print("\n9. Downloading recent mesonet measurements...")
    try:
        result = await client.get_mesonet_data(
            location="hawaii",
            start_date="2024-12-01",
            end_date="2024-12-02",
            limit=100
        )
        filename = sample_data_dir / "mesonet_measurements_recent.json"
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"✓ Saved: {filename} ({len(result)} measurements)")
        samples.append({
            "name": "Mesonet Measurements - Recent",
            "filename": str(filename),
            "location": "hawaii",
            "start_date": "2024-12-01",
            "end_date": "2024-12-02",
            "measurement_count": len(result)
        })
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Save samples index
    samples_index = {
        "downloaded_at": "2024-12-XX",
        "total_samples": len(samples),
        "samples": samples
    }
    
    index_file = sample_data_dir / "samples_index.json"
    with open(index_file, 'w') as f:
        json.dump(samples_index, f, indent=2)
    
    print(f"\n{'='*60}")
    print("SAMPLE DOWNLOAD COMPLETE")
    print(f"{'='*60}")
    print(f"Total samples downloaded: {len(samples)}")
    print(f"Samples index saved to: {index_file}")
    print("\nSample files:")
    for sample in samples:
        print(f"  - {sample['filename']}")
    
    return samples

if __name__ == "__main__":
    asyncio.run(download_comprehensive_samples())