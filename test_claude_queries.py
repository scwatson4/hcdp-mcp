#!/usr/bin/env python3
"""Test the exact query Claude is trying."""

import asyncio
from hcdp_mcp_server.client import HCDPClient

async def test_claude_queries():
    client = HCDPClient()
    
    print("Testing queries Claude tried...\n")
    
    # What Claude probably tried
    tests = [
        {
            "name": "Claude's likely attempt 1",
            "params": {
                "datatype": "rainfall",
                "date": "2022-02",
                "extent": "big_island"
            }
        },
        {
            "name": "Claude's likely attempt 2", 
            "params": {
                "datatype": "rainfall",
                "date": "2022-02",
                "extent": "big_island",
                "production": "new"
            }
        },
        {
            "name": "What actually works",
            "params": {
                "datatype": "rainfall",
                "date": "2022-02",
                "extent": "bi",
                "production": "new",
                "period": "month"
            }
        }
    ]
    
    for test in tests:
        print(f"{test['name']}:")
        print(f"  Params: {test['params']}")
        try:
            result = await client.get_raster_data(**test['params'])
            print(f"  ✓ SUCCESS - Got {len(result.get('data', b''))} bytes\n")
        except Exception as e:
            print(f"  ✗ FAILED: {str(e)[:100]}...\n")

if __name__ == "__main__":
    asyncio.run(test_claude_queries())
