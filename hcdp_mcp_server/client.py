"""HCDP API client for making requests to the Hawaii Climate Data Portal."""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
from dotenv import load_dotenv

load_dotenv()


class HCDPClient:
    """Client for interacting with the HCDP API."""
    
    def __init__(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        self.api_token = api_token or os.getenv("HCDP_API_TOKEN")
        self.base_url = base_url or os.getenv("HCDP_BASE_URL", "https://ikeauth.its.hawaii.edu/files/v2/download/public")
        
        if not self.api_token:
            raise ValueError("HCDP API token is required. Set HCDP_API_TOKEN environment variable.")
            
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def get_raster_data(
        self,
        datatype: str,
        date: str,
        extent: str,
        location: str = "hawaii",
        production: Optional[str] = None,
        aggregation: Optional[str] = None,
        timescale: Optional[str] = None,
        period: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get climate raster data."""
        params = {
            "datatype": datatype,
            "date": date,
            "extent": extent,
            "location": location
        }
        if production:
            params["production"] = production
        if aggregation:
            params["aggregation"] = aggregation
        if timescale:
            params["timescale"] = timescale
        if period:
            params["period"] = period
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/raster",
                params=params,
                headers=self.headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json() if response.headers.get("content-type", "").startswith("application/json") else {"data": response.content}
    
    async def get_timeseries_data(
        self,
        datatype: str,
        start: str,
        end: str,
        extent: str,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        location: str = "hawaii",
        production: Optional[str] = None,
        aggregation: Optional[str] = None,
        timescale: Optional[str] = None,
        period: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get time series data for a specific location."""
        params = {
            "datatype": datatype,
            "start": start,
            "end": end,
            "extent": extent,
            "location": location
        }
        if lat is not None and lng is not None:
            params["lat"] = lat
            params["lng"] = lng
        if production:
            params["production"] = production
        if aggregation:
            params["aggregation"] = aggregation
        if timescale:
            params["timescale"] = timescale
        if period:
            params["period"] = period
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/raster/timeseries",
                params=params,
                headers=self.headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_station_data(
        self,
        q: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get station data using query parameter."""
        params = {
            "q": q
        }
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/stations",
                params=params,
                headers=self.headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_mesonet_data(
        self,
        station_ids: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        var_ids: Optional[str] = None,
        location: str = "hawaii",
        intervals: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        join_metadata: bool = True
    ) -> Dict[str, Any]:
        """Get mesonet weather station measurements."""
        params = {
            "location": location,
            "join_metadata": str(join_metadata).lower()
        }
        if station_ids:
            params["station_ids"] = station_ids
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if var_ids:
            params["var_ids"] = var_ids
        if intervals:
            params["intervals"] = intervals
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/mesonet/db/measurements",
                params=params,
                headers=self.headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
    
    async def generate_data_package(
        self,
        email: str,
        datatype: str,
        production: Optional[str] = None,
        period: Optional[str] = None,
        extent: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        files: Optional[str] = None,
        zipName: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a downloadable data package."""
        data_config = {
            "datatype": datatype
        }
        if production:
            data_config["production"] = production
        if period:
            data_config["period"] = period
        if extent:
            data_config["extent"] = extent
        if start_date:
            data_config["start_date"] = start_date
        if end_date:
            data_config["end_date"] = end_date
        if files:
            data_config["files"] = files
            
        params = {
            "email": email,
            "data": json.dumps(data_config)
        }
        if zipName:
            params["zipName"] = zipName
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/genzip",
                params=params,
                headers=self.headers,
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()