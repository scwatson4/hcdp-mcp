"""Integration tests for HCDP MCP Server with realistic scenarios."""

import pytest
import json
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime, timedelta

from hcdp_mcp_server.server import handle_call_tool
from hcdp_mcp_server.client import HCDPClient


class TestRealisticUsageScenarios:
    """Test realistic usage scenarios for HCDP MCP Server."""
    
    @pytest.fixture
    def mock_successful_client(self):
        """Mock client that returns realistic successful responses."""
        with patch('hcdp_mcp_server.server.HCDPClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            # Setup realistic responses for each endpoint
            mock_instance.get_raster_data = AsyncMock(return_value={
                "status": "success",
                "download_url": "https://data.hcdp.com/raster_123.tiff",
                "file_size_mb": 25.4,
                "metadata": {
                    "variable": "rainfall",
                    "aggregation": "month",
                    "projection": "EPSG:4326",
                    "resolution": "250m"
                }
            })
            
            mock_instance.get_timeseries_data = AsyncMock(return_value={
                "data": [
                    {"date": "2023-01-01", "value": 125.5, "quality": "good"},
                    {"date": "2023-02-01", "value": 98.2, "quality": "good"}, 
                    {"date": "2023-03-01", "value": 156.8, "quality": "fair"}
                ],
                "metadata": {
                    "coordinates": {"lat": 21.3099, "lng": -157.8581},
                    "station_nearest": "HONOLULU_AIRPORT",
                    "elevation_m": 5.0
                }
            })
            
            mock_instance.get_station_data = AsyncMock(return_value={
                "stations": [
                    {
                        "id": "STAT001",
                        "name": "Honolulu International Airport",
                        "coordinates": {"lat": 21.3187, "lng": -157.9224},
                        "measurements": [
                            {"date": "2023-01-01", "value": 125.5},
                            {"date": "2023-02-01", "value": 98.2}
                        ]
                    }
                ]
            })
            
            mock_instance.get_mesonet_data = AsyncMock(return_value={
                "measurements": [
                    {
                        "timestamp": "2023-01-01T00:00:00Z",
                        "station_id": "MESA001",
                        "value": 15.2,
                        "unit": "m/s"
                    }
                ]
            })
            
            mock_instance.generate_data_package = AsyncMock(return_value={
                "package_id": "pkg_abc123",
                "status": "queued",
                "estimated_completion_time": "2023-01-01T12:00:00Z",
                "email_notification": True
            })
            
            yield mock_instance

    @pytest.mark.asyncio
    async def test_rainfall_analysis_workflow(self, mock_successful_client):
        """Test a complete rainfall analysis workflow."""
        # Step 1: Get rainfall raster data for a specific month
        raster_result = await handle_call_tool("get_climate_raster", {
            "var": "rainfall",
            "start": "2023-01-01",
            "end": "2023-01-31",
            "location": "hawaii",
            "aggregation": "month",
            "fmt": "tiff"
        })
        
        # Verify raster data request was successful
        assert len(raster_result) == 1
        raster_data = json.loads(raster_result[0].text)
        assert raster_data["status"] == "success"
        assert "download_url" in raster_data
        
        # Step 2: Get time series data for a specific location
        timeseries_result = await handle_call_tool("get_timeseries_data", {
            "var": "rainfall", 
            "lat": 21.3099,
            "lng": -157.8581,
            "start": "2023-01-01",
            "end": "2023-03-31",
            "aggregation": "month"
        })
        
        # Verify time series data
        ts_data = json.loads(timeseries_result[0].text)
        assert "data" in ts_data
        assert len(ts_data["data"]) == 3  # 3 months of data
        assert ts_data["data"][0]["value"] == 125.5

    @pytest.mark.asyncio 
    async def test_temperature_monitoring_workflow(self, mock_successful_client):
        """Test temperature monitoring across multiple locations."""
        # Configure mock for temperature data
        mock_successful_client.get_timeseries_data.return_value = {
            "data": [
                {"date": "2023-06-01", "value": 26.8, "unit": "celsius"},
                {"date": "2023-07-01", "value": 27.2, "unit": "celsius"},
                {"date": "2023-08-01", "value": 28.1, "unit": "celsius"}
            ],
            "metadata": {"variable": "temp_mean"}
        }
        
        # Test temperature monitoring for Honolulu
        temp_result = await handle_call_tool("get_timeseries_data", {
            "var": "temp_mean",
            "lat": 21.3099, 
            "lng": -157.8581,
            "start": "2023-06-01",
            "end": "2023-08-31",
            "aggregation": "month"
        })
        
        temp_data = json.loads(temp_result[0].text)
        assert temp_data["data"][0]["value"] == 26.8
        assert temp_data["metadata"]["variable"] == "temp_mean"

    @pytest.mark.asyncio
    async def test_station_comparison_workflow(self, mock_successful_client):
        """Test comparing data from multiple weather stations."""
        # Configure mock for multiple stations
        mock_successful_client.get_station_data.return_value = {
            "stations": [
                {
                    "id": "HONOLULU_AP",
                    "name": "Honolulu International Airport",
                    "elevation": 5.0,
                    "measurements": [{"date": "2023-01-01", "value": 125.5}]
                },
                {
                    "id": "HALEAKALA", 
                    "name": "Haleakala Summit",
                    "elevation": 3055.0,
                    "measurements": [{"date": "2023-01-01", "value": 45.2}]
                }
            ]
        }
        
        station_result = await handle_call_tool("get_station_data", {
            "var": "rainfall",
            "start": "2023-01-01",
            "end": "2023-01-31",
            "location": "hawaii"
        })
        
        station_data = json.loads(station_result[0].text)
        assert len(station_data["stations"]) == 2
        
        # Check elevation differences affect rainfall
        airport_station = station_data["stations"][0]
        mountain_station = station_data["stations"][1] 
        assert airport_station["elevation"] < mountain_station["elevation"]

    @pytest.mark.asyncio
    async def test_real_time_monitoring_workflow(self, mock_successful_client):
        """Test real-time mesonet monitoring workflow."""
        # Configure mock for recent mesonet data
        recent_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        mock_successful_client.get_mesonet_data.return_value = {
            "measurements": [
                {
                    "timestamp": recent_time,
                    "station": "KONA_AIRPORT",
                    "value": 15.2,
                    "variable": "wind_speed",
                    "unit": "m/s"
                }
            ],
            "metadata": {
                "last_updated": recent_time,
                "data_freshness_minutes": 5
            }
        }
        
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        
        mesonet_result = await handle_call_tool("get_mesonet_data", {
            "var": "wind_speed",
            "start": yesterday,
            "end": today,
            "aggregation": "day",
            "station": "KONA_AIRPORT"
        })
        
        mesonet_data = json.loads(mesonet_result[0].text)
        assert len(mesonet_data["measurements"]) == 1
        assert mesonet_data["measurements"][0]["value"] == 15.2

    @pytest.mark.asyncio
    async def test_data_package_generation_workflow(self, mock_successful_client):
        """Test generating downloadable data packages."""
        package_result = await handle_call_tool("generate_data_package", {
            "var": "rainfall",
            "start": "2023-01-01",
            "end": "2023-12-31", 
            "location": "hawaii",
            "fmt": "tiff",
            "email": "researcher@university.edu",
            "instant": "false"
        })
        
        package_data = json.loads(package_result[0].text)
        assert "package_id" in package_data
        assert package_data["status"] == "queued"
        assert package_data["email_notification"] == True


class TestMultiLocationAnalysis:
    """Test analysis across multiple geographic locations."""
    
    @pytest.fixture
    def mock_multi_location_client(self):
        """Mock client with location-specific responses."""
        with patch('hcdp_mcp_server.server.HCDPClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            # Setup location-specific responses
            def mock_timeseries_response(*args, **kwargs):
                location = kwargs.get('location', 'hawaii')
                lat = kwargs.get('lat', 0)
                
                if location == 'hawaii':
                    base_temp = 26.0
                elif location == 'american_samoa':
                    base_temp = 28.0  # Warmer tropical climate
                else:
                    base_temp = 25.0
                    
                return {
                    "data": [
                        {"date": "2023-01-01", "value": base_temp + (lat - 20) * 0.5},
                        {"date": "2023-02-01", "value": base_temp + (lat - 20) * 0.5 + 0.5}
                    ],
                    "metadata": {"location": location}
                }
            
            mock_instance.get_timeseries_data = AsyncMock(side_effect=mock_timeseries_response)
            yield mock_instance

    @pytest.mark.asyncio
    async def test_hawaii_vs_american_samoa_comparison(self, mock_multi_location_client):
        """Test comparing climate data between Hawaii and American Samoa."""
        # Get data for Hawaii
        hawaii_result = await handle_call_tool("get_timeseries_data", {
            "var": "temp_mean",
            "lat": 21.3,
            "lng": -157.8,
            "start": "2023-01-01",
            "end": "2023-02-28",
            "location": "hawaii"
        })
        
        hawaii_data = json.loads(hawaii_result[0].text)
        
        # Get data for American Samoa  
        samoa_result = await handle_call_tool("get_timeseries_data", {
            "var": "temp_mean",
            "lat": -14.3,
            "lng": -170.7,
            "start": "2023-01-01", 
            "end": "2023-02-28",
            "location": "american_samoa"
        })
        
        samoa_data = json.loads(samoa_result[0].text)
        
        # Verify both locations returned data
        assert hawaii_data["metadata"]["location"] == "hawaii"
        assert samoa_data["metadata"]["location"] == "american_samoa"
        
        # American Samoa should generally be warmer
        hawaii_temp = hawaii_data["data"][0]["value"]
        samoa_temp = samoa_data["data"][0]["value"]
        assert samoa_temp > hawaii_temp


class TestErrorHandlingIntegration:
    """Test error handling in realistic failure scenarios."""
    
    @pytest.fixture
    def mock_failing_client(self):
        """Mock client that simulates various failure modes."""
        with patch('hcdp_mcp_server.server.HCDPClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            # Different endpoints fail in different ways
            mock_instance.get_raster_data = AsyncMock(side_effect=Exception("Server temporarily unavailable"))
            mock_instance.get_timeseries_data = AsyncMock(side_effect=Exception("Invalid coordinates"))
            mock_instance.get_station_data = AsyncMock(side_effect=Exception("No data available for date range"))
            mock_instance.get_mesonet_data = AsyncMock(side_effect=Exception("Station not found"))
            mock_instance.generate_data_package = AsyncMock(side_effect=Exception("Email delivery failed"))
            
            yield mock_instance

    @pytest.mark.asyncio
    async def test_server_unavailable_error(self, mock_failing_client):
        """Test handling of server unavailability."""
        result = await handle_call_tool("get_climate_raster", {
            "var": "rainfall",
            "start": "2023-01-01", 
            "end": "2023-12-31"
        })
        
        assert len(result) == 1
        error_text = result[0].text
        assert "Error calling HCDP API" in error_text
        assert "Server temporarily unavailable" in error_text

    @pytest.mark.asyncio
    async def test_invalid_coordinates_error(self, mock_failing_client):
        """Test handling of invalid coordinate errors."""
        result = await handle_call_tool("get_timeseries_data", {
            "var": "rainfall",
            "lat": 999.0,  # Invalid latitude
            "lng": -157.8,
            "start": "2023-01-01",
            "end": "2023-12-31"
        })
        
        error_text = result[0].text
        assert "Error calling HCDP API" in error_text
        assert "Invalid coordinates" in error_text

    @pytest.mark.asyncio
    async def test_no_data_available_error(self, mock_failing_client):
        """Test handling of no data available scenarios."""
        result = await handle_call_tool("get_station_data", {
            "var": "rainfall",
            "start": "1900-01-01",  # Very old date with no data
            "end": "1900-12-31"
        })
        
        error_text = result[0].text
        assert "Error calling HCDP API" in error_text
        assert "No data available for date range" in error_text

    @pytest.mark.asyncio
    async def test_station_not_found_error(self, mock_failing_client):
        """Test handling of non-existent station errors."""
        result = await handle_call_tool("get_mesonet_data", {
            "var": "wind_speed",
            "start": "2023-01-01",
            "end": "2023-01-31",
            "station": "INVALID_STATION"
        })
        
        error_text = result[0].text
        assert "Error calling HCDP API" in error_text
        assert "Station not found" in error_text

    @pytest.mark.asyncio
    async def test_email_delivery_error(self, mock_failing_client):
        """Test handling of email delivery failures."""
        result = await handle_call_tool("generate_data_package", {
            "var": "rainfall",
            "start": "2023-01-01",
            "end": "2023-12-31",
            "email": "invalid@email"  # Invalid email format
        })
        
        error_text = result[0].text
        assert "Error calling HCDP API" in error_text
        assert "Email delivery failed" in error_text


class TestDataQualityAndValidation:
    """Test data quality validation and edge cases."""
    
    @pytest.fixture  
    def mock_data_quality_client(self):
        """Mock client with data quality indicators."""
        with patch('hcdp_mcp_server.server.HCDPClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            mock_instance.get_timeseries_data = AsyncMock(return_value={
                "data": [
                    {"date": "2023-01-01", "value": 125.5, "quality": "good"},
                    {"date": "2023-02-01", "value": -999.0, "quality": "missing"},  # Missing data flag
                    {"date": "2023-03-01", "value": 156.8, "quality": "poor"},     # Poor quality data
                    {"date": "2023-04-01", "value": 203.4, "quality": "good"},
                ],
                "metadata": {
                    "data_completeness": 75.0,  # 3 out of 4 good values
                    "quality_flags": ["missing_data", "poor_quality_sensor"]
                }
            })
            
            mock_instance.get_station_data = AsyncMock(return_value={
                "stations": [
                    {
                        "id": "STAT001",
                        "status": "active",
                        "last_maintenance": "2023-01-15",
                        "measurements": [
                            {"date": "2023-01-01", "value": 125.5, "quality": "good"},
                            {"date": "2023-02-01", "value": None, "quality": "missing"}
                        ]
                    }
                ]
            })
            
            yield mock_instance

    @pytest.mark.asyncio
    async def test_data_quality_indicators(self, mock_data_quality_client):
        """Test handling of data quality indicators in responses."""
        result = await handle_call_tool("get_timeseries_data", {
            "var": "rainfall",
            "lat": 21.3099,
            "lng": -157.8581,
            "start": "2023-01-01",
            "end": "2023-04-30"
        })
        
        data = json.loads(result[0].text)
        
        # Check that quality information is preserved
        assert "data" in data
        assert len(data["data"]) == 4
        
        # Verify quality flags are included
        good_data = [d for d in data["data"] if d.get("quality") == "good"]
        missing_data = [d for d in data["data"] if d.get("quality") == "missing"]
        poor_data = [d for d in data["data"] if d.get("quality") == "poor"]
        
        assert len(good_data) == 2
        assert len(missing_data) == 1
        assert len(poor_data) == 1
        
        # Check metadata includes quality statistics
        assert data["metadata"]["data_completeness"] == 75.0

    @pytest.mark.asyncio
    async def test_missing_data_handling(self, mock_data_quality_client):
        """Test proper handling of missing data points."""
        result = await handle_call_tool("get_station_data", {
            "var": "rainfall",
            "start": "2023-01-01",
            "end": "2023-02-28",
            "station_id": "STAT001"
        })
        
        data = json.loads(result[0].text)
        station = data["stations"][0]
        
        # Check that missing data is properly represented
        measurements = station["measurements"]
        assert measurements[1]["value"] is None
        assert measurements[1]["quality"] == "missing"

    @pytest.mark.asyncio
    async def test_edge_case_date_ranges(self, mock_data_quality_client):
        """Test handling of edge case date ranges."""
        # Same start and end date (single day)
        result = await handle_call_tool("get_timeseries_data", {
            "var": "rainfall", 
            "lat": 21.3099,
            "lng": -157.8581,
            "start": "2023-01-01",
            "end": "2023-01-01"  # Same date
        })
        
        # Should not error, may return single day or no data
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "data" in data or "error" not in data


class TestPerformanceConsiderations:
    """Test performance-related scenarios and timeouts."""
    
    @pytest.mark.asyncio
    async def test_large_date_range_handling(self):
        """Test handling of large date ranges that might cause timeouts."""
        with patch('hcdp_mcp_server.server.HCDPClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            # Simulate slow response for large data request
            mock_instance.get_raster_data = AsyncMock(return_value={
                "status": "processing",
                "estimated_completion": "2023-01-01T15:30:00Z",
                "data_size_mb": 1250.0,  # Large dataset
                "warning": "Large date range may result in slower processing"
            })
            
            # Request 10 years of data
            result = await handle_call_tool("get_climate_raster", {
                "var": "rainfall",
                "start": "2014-01-01",
                "end": "2023-12-31",  # 10 year range
                "aggregation": "month"
            })
            
            data = json.loads(result[0].text)
            assert data["status"] == "processing"
            assert "Large date range" in data.get("warning", "")

    @pytest.mark.asyncio
    async def test_data_package_timeout_handling(self):
        """Test timeout handling for data package generation."""
        with patch('hcdp_mcp_server.server.HCDPClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            # Simulate successful queuing but long processing time
            mock_instance.generate_data_package = AsyncMock(return_value={
                "package_id": "pkg_large_123",
                "status": "queued",
                "estimated_completion": "2023-01-02T08:00:00Z", # Next day
                "queue_position": 5,
                "message": "Large data package queued for processing"
            })
            
            result = await handle_call_tool("generate_data_package", {
                "var": "rainfall",
                "start": "2020-01-01",
                "end": "2023-12-31",  # 4 year range
                "fmt": "tiff",
                "email": "researcher@example.com"
            })
            
            data = json.loads(result[0].text)
            assert data["status"] == "queued"
            assert "queue_position" in data