"""Comprehensive tests for HCDP MCP Server implementation."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from hcdp_mcp_server.server import (
    app,
    GetClimateRasterArgs,
    GetTimeseriesArgs,
    GetStationDataArgs,
    GetMesonetDataArgs,
    GenerateDataPackageArgs,
    handle_call_tool,
    handle_list_tools
)
from mcp.types import TextContent


class TestMCPServerTools:
    """Test MCP server tool definitions and parameter validation."""
    
    @pytest.mark.asyncio
    async def test_list_tools_returns_five_tools(self):
        """Test that all 5 expected tools are listed."""
        tools = await handle_list_tools()
        
        assert len(tools) == 5
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "get_climate_raster",
            "get_timeseries_data",
            "get_station_data",
            "get_mesonet_data", 
            "generate_data_package"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_get_climate_raster_args_validation(self):
        """Test GetClimateRasterArgs parameter validation."""
        # Valid arguments
        valid_args = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31"
        )
        assert valid_args.var == "rainfall"
        assert valid_args.location == "hawaii"  # default
        assert valid_args.aggregation == "month"  # default
        assert valid_args.fmt == "tiff"  # default
        
        # Test with custom values
        custom_args = GetClimateRasterArgs(
            var="temp_mean",
            start="2023-06-01", 
            end="2023-06-30",
            location="american_samoa",
            aggregation="day",
            units="celsius",
            meta="false",
            fmt="json"
        )
        assert custom_args.location == "american_samoa"
        assert custom_args.aggregation == "day"
        assert custom_args.units == "celsius"
        assert custom_args.meta == "false"
        assert custom_args.fmt == "json"

    def test_get_timeseries_args_validation(self):
        """Test GetTimeseriesArgs parameter validation."""
        # Valid coordinates for Hawaii
        valid_args = GetTimeseriesArgs(
            var="rainfall",
            lat=21.3099,
            lng=-157.8581,
            start="2023-01-01",
            end="2023-12-31"
        )
        assert valid_args.lat == 21.3099
        assert valid_args.lng == -157.8581
        
        # Test boundary coordinates
        boundary_args = GetTimeseriesArgs(
            var="temp_max",
            lat=19.0,  # Southern Hawaii boundary
            lng=-178.0,  # Western boundary
            start="2022-01-01",
            end="2022-12-31",
            location="hawaii",
            aggregation="day"
        )
        assert boundary_args.lat == 19.0
        assert boundary_args.lng == -178.0

    def test_get_station_data_args_validation(self):
        """Test GetStationDataArgs parameter validation."""
        valid_args = GetStationDataArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31"
        )
        assert valid_args.var == "rainfall"
        assert valid_args.station_id is None  # optional parameter
        
        # With station ID
        station_args = GetStationDataArgs(
            var="temp_mean",
            start="2023-01-01",
            end="2023-12-31",
            station_id="STAT001"
        )
        assert station_args.station_id == "STAT001"

    def test_get_mesonet_data_args_validation(self):
        """Test GetMesonetDataArgs parameter validation."""
        valid_args = GetMesonetDataArgs(
            var="wind_speed",
            start="2023-01-01",
            end="2023-01-31"
        )
        assert valid_args.var == "wind_speed"
        assert valid_args.aggregation == "day"  # default for mesonet
        assert valid_args.station is None

    def test_generate_data_package_args_validation(self):
        """Test GenerateDataPackageArgs parameter validation."""
        valid_args = GenerateDataPackageArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31"
        )
        assert valid_args.instant == "false"  # default
        assert valid_args.email is None
        
        # With email for async delivery
        email_args = GenerateDataPackageArgs(
            var="temp_mean",
            start="2023-01-01", 
            end="2023-12-31",
            email="test@example.com",
            instant="true"
        )
        assert email_args.email == "test@example.com"
        assert email_args.instant == "true"


class TestMCPServerToolCalls:
    """Test MCP server tool call execution."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock HCDP client for testing."""
        with patch('hcdp_mcp_server.server.HCDPClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            # Setup async mock methods
            mock_instance.get_raster_data = AsyncMock()
            mock_instance.get_timeseries_data = AsyncMock()
            mock_instance.get_station_data = AsyncMock()
            mock_instance.get_mesonet_data = AsyncMock()
            mock_instance.generate_data_package = AsyncMock()
            
            yield mock_instance

    @pytest.mark.asyncio
    async def test_get_climate_raster_tool_call(self, mock_client):
        """Test climate raster tool call with valid parameters."""
        # Setup mock response
        mock_response = {
            "status": "success",
            "data": {"url": "https://example.com/raster.tiff"},
            "metadata": {"variable": "rainfall", "aggregation": "month"}
        }
        mock_client.get_raster_data.return_value = mock_response
        
        # Call tool
        arguments = {
            "var": "rainfall",
            "start": "2023-01-01",
            "end": "2023-12-31",
            "location": "hawaii",
            "aggregation": "month",
            "fmt": "tiff"
        }
        
        result = await handle_call_tool("get_climate_raster", arguments)
        
        # Verify call was made with correct parameters
        mock_client.get_raster_data.assert_called_once_with(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31",
            location="hawaii",
            aggregation="month",
            units=None,
            meta="true",
            fmt="tiff"
        )
        
        # Verify response format
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        response_data = json.loads(result[0].text)
        assert response_data["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_timeseries_data_tool_call(self, mock_client):
        """Test timeseries data tool call with valid parameters."""
        mock_response = {
            "data": [
                {"date": "2023-01-01", "value": 25.5},
                {"date": "2023-02-01", "value": 27.2}
            ],
            "metadata": {"lat": 21.3099, "lng": -157.8581}
        }
        mock_client.get_timeseries_data.return_value = mock_response
        
        arguments = {
            "var": "temp_mean",
            "lat": 21.3099,
            "lng": -157.8581,
            "start": "2023-01-01",
            "end": "2023-12-31"
        }
        
        result = await handle_call_tool("get_timeseries_data", arguments)
        
        mock_client.get_timeseries_data.assert_called_once_with(
            var="temp_mean",
            lat=21.3099,
            lng=-157.8581,
            start="2023-01-01",
            end="2023-12-31",
            location="hawaii",
            aggregation="month",
            units=None
        )
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert len(response_data["data"]) == 2

    @pytest.mark.asyncio
    async def test_get_station_data_tool_call(self, mock_client):
        """Test station data tool call with valid parameters."""
        mock_response = {
            "stations": [
                {"id": "STAT001", "name": "Honolulu Station", "measurements": []}
            ]
        }
        mock_client.get_station_data.return_value = mock_response
        
        arguments = {
            "var": "rainfall",
            "start": "2023-01-01",
            "end": "2023-12-31",
            "station_id": "STAT001"
        }
        
        result = await handle_call_tool("get_station_data", arguments)
        
        mock_client.get_station_data.assert_called_once_with(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31",
            location="hawaii",
            aggregation="month",
            meta="true",
            fmt="json",
            station_id="STAT001"
        )
        
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_mesonet_data_tool_call(self, mock_client):
        """Test mesonet data tool call with valid parameters."""
        mock_response = {
            "measurements": [
                {"timestamp": "2023-01-01T00:00:00Z", "value": 15.2, "station": "MESA001"}
            ]
        }
        mock_client.get_mesonet_data.return_value = mock_response
        
        arguments = {
            "var": "wind_speed",
            "start": "2023-01-01",
            "end": "2023-01-31",
            "station": "MESA001"
        }
        
        result = await handle_call_tool("get_mesonet_data", arguments)
        
        mock_client.get_mesonet_data.assert_called_once_with(
            var="wind_speed",
            start="2023-01-01",
            end="2023-01-31",
            location="hawaii",
            aggregation="day",
            meta="true",
            fmt="json",
            station="MESA001"
        )

    @pytest.mark.asyncio
    async def test_generate_data_package_tool_call(self, mock_client):
        """Test data package generation tool call."""
        mock_response = {
            "package_id": "pkg_123",
            "status": "processing",
            "estimated_completion": "2023-01-01T12:00:00Z"
        }
        mock_client.generate_data_package.return_value = mock_response
        
        arguments = {
            "var": "rainfall",
            "start": "2023-01-01",
            "end": "2023-12-31",
            "email": "user@example.com",
            "instant": "false"
        }
        
        result = await handle_call_tool("generate_data_package", arguments)
        
        mock_client.generate_data_package.assert_called_once_with(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31",
            location="hawaii",
            aggregation="month",
            fmt="tiff",
            email="user@example.com",
            instant="false"
        )

    @pytest.mark.asyncio
    async def test_unknown_tool_error(self, mock_client):
        """Test error handling for unknown tool names."""
        result = await handle_call_tool("unknown_tool", {})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_client_error_handling(self, mock_client):
        """Test error handling when client raises exceptions."""
        mock_client.get_raster_data.side_effect = Exception("API connection failed")
        
        arguments = {
            "var": "rainfall",
            "start": "2023-01-01",
            "end": "2023-12-31"
        }
        
        result = await handle_call_tool("get_climate_raster", arguments)
        
        assert len(result) == 1
        assert "Error calling HCDP API: API connection failed" in result[0].text


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_invalid_date_formats(self):
        """Test handling of invalid date formats."""
        with pytest.raises(Exception):  # Pydantic validation should catch this
            args = GetClimateRasterArgs(
                var="rainfall",
                start="invalid-date",
                end="2023-12-31"
            )

    def test_invalid_coordinates(self):
        """Test handling of invalid coordinates."""
        # Valid range for Hawaii approximately: lat 18-23, lng -180 to -150
        valid_args = GetTimeseriesArgs(
            var="rainfall",
            lat=21.3099,
            lng=-157.8581,
            start="2023-01-01",
            end="2023-12-31"
        )
        assert valid_args.lat == 21.3099
        
        # Note: The current implementation doesn't validate coordinate ranges
        # This might be an area for improvement

    def test_date_range_validation(self):
        """Test date range validation logic."""
        # Current implementation doesn't validate that start < end
        # This could be added as a custom validator
        args = GetClimateRasterArgs(
            var="rainfall", 
            start="2023-12-31",
            end="2023-01-01"  # End before start
        )
        # This currently passes but probably shouldn't
        assert args.start == "2023-12-31"
        assert args.end == "2023-01-01"

    def test_long_date_ranges(self):
        """Test handling of very long date ranges."""
        # 10 year range - might cause performance issues
        long_range_args = GetClimateRasterArgs(
            var="rainfall",
            start="2014-01-01",
            end="2023-12-31"
        )
        assert long_range_args.start == "2014-01-01"
        assert long_range_args.end == "2023-12-31"


class TestAPIParameterMapping:
    """Test that MCP parameters map correctly to HCDP API parameters."""
    
    def test_climate_raster_parameter_mapping(self):
        """Test parameter mapping for climate raster endpoint."""
        args = GetClimateRasterArgs(
            var="temp_mean",
            start="2023-01-01",
            end="2023-12-31",
            location="american_samoa",
            aggregation="day",
            units="fahrenheit",
            meta="false",
            fmt="json"
        )
        
        # All parameters should map 1:1 to API
        expected_params = {
            "var": "temp_mean",
            "start": "2023-01-01", 
            "end": "2023-12-31",
            "location": "american_samoa",
            "aggregation": "day",
            "units": "fahrenheit",
            "meta": "false",
            "fmt": "json"
        }
        
        # Verify all expected parameters are present
        for param, value in expected_params.items():
            assert hasattr(args, param)
            assert getattr(args, param) == value

    def test_timeseries_parameter_mapping(self):
        """Test parameter mapping for timeseries endpoint."""
        args = GetTimeseriesArgs(
            var="rainfall",
            lat=21.3099,
            lng=-157.8581,
            start="2023-01-01",
            end="2023-12-31",
            location="hawaii",
            aggregation="month",
            units="inches"
        )
        
        # Check all required and optional parameters
        assert args.var == "rainfall"
        assert args.lat == 21.3099
        assert args.lng == -157.8581
        assert args.start == "2023-01-01"
        assert args.end == "2023-12-31"
        assert args.location == "hawaii"
        assert args.aggregation == "month"
        assert args.units == "inches"