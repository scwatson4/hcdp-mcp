#!/usr/bin/env python3
"""
Test script for HCDP MCP functionality.
This script demonstrates how to use the HCDP MCP tools to download climate data.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hcdp_mcp_server.client import HCDPClient

async def test_hcdp_client():
    """Test the HCDP client functionality."""
    
    # Initialize the client
    client = HCDPClient()
    
    print("Testing HCDP Client...")
    print("===================")
    
    # Test parameters for Big Island December 2024 data
    test_params = [
        {
            "name": "Temperature (Mean) - Big Island Dec 2024",
            "datatype": "temp_mean",
            "date": "2024-12-15",
            "extent": "big_island"
        },
        {
            "name": "Rainfall - Big Island Dec 2024", 
            "datatype": "rainfall",
            "date": "2024-12-15",
            "extent": "big_island"
        }
    ]
    
    for params in test_params:
        print(f"\nTesting: {params['name']}")
        print(f"URL would be: {client.base_url}/raster")
        print(f"Parameters: {params}")
        
        try:
            # This would normally download the raster
            # result = await client.get_climate_raster(**params)
            print("Status: Ready to download (API token required)")
            
            # Create placeholder file to show expected output
            filename = f"sample_{params['datatype']}_{params['date']}_{params['extent']}.tiff"
            filepath = os.path.join("sample_data", filename)
            
            with open(filepath, "w") as f:
                f.write(f"# Placeholder for {params['name']}\n")
                f.write(f"# This would be a GeoTIFF file containing climate data\n")
                f.write(f"# Parameters: {params}\n")
            
            print(f"Created placeholder: {filepath}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_hcdp_client())