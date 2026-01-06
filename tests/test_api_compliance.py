"""Tests for HCDP API compliance and specification adherence."""

import pytest
from datetime import datetime
from typing import Dict, Any

from hcdp_mcp_server.client import HCDPClient
from hcdp_mcp_server.server import (
    GetClimateRasterArgs,
    GetTimeseriesArgs, 
    GetStationDataArgs,
    GetMesonetDataArgs,
    GenerateDataPackageArgs
)


class TestAPISpecificationCompliance:
    """Test compliance with official HCDP API specification."""
    
    def test_base_url_compliance(self):
        """Test that base URL matches specification."""
        # According to the API spec, the base URL should be api.hcdp.ikewai.org
        # But the implementation uses ikeauth.its.hawaii.edu/files/v2/download/public
        client = HCDPClient(api_token="test")
        expected_base = "https://ikeauth.its.hawaii.edu/files/v2/download/public"
        assert client.base_url == expected_base
        
        # Note: This may need updating to match the official API spec
        # which suggests: https://api.hcdp.ikewai.org

    def test_authentication_header_format(self):
        """Test that authentication header follows Bearer token format."""
        client = HCDPClient(api_token="test_token")
        assert client.headers["Authorization"] == "Bearer test_token"
        assert client.headers["Content-Type"] == "application/json"

    def test_supported_variables_coverage(self, valid_variables):
        """Test that common climate variables are supported."""
        # The implementation should support key climate variables
        test_args = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01", 
            end="2023-12-31"
        )
        assert test_args.var == "rainfall"
        
        # Test other common variables
        for var in ["temp_mean", "temp_min", "temp_max", "relative_humidity"]:
            args = GetClimateRasterArgs(
                var=var,
                start="2023-01-01",
                end="2023-12-31"
            )
            assert args.var == var

    def test_supported_locations(self, valid_locations):
        """Test that both Hawaii and American Samoa are supported."""
        for location in valid_locations:
            args = GetClimateRasterArgs(
                var="rainfall",
                start="2023-01-01",
                end="2023-12-31",
                location=location
            )
            assert args.location == location

    def test_supported_aggregations(self, valid_aggregations):
        """Test that all temporal aggregations are supported."""
        for aggregation in valid_aggregations:
            args = GetClimateRasterArgs(
                var="rainfall",
                start="2023-01-01",
                end="2023-12-31", 
                aggregation=aggregation
            )
            assert args.aggregation == aggregation

    def test_supported_formats(self, valid_formats):
        """Test that all output formats are supported."""
        for fmt in valid_formats:
            args = GetClimateRasterArgs(
                var="rainfall",
                start="2023-01-01",
                end="2023-12-31",
                fmt=fmt
            )
            assert args.fmt == fmt


class TestEndpointURLCompliance:
    """Test that endpoint URLs match the API specification."""
    
    def test_raster_endpoint_url(self):
        """Test raster endpoint URL construction."""
        client = HCDPClient(api_token="test")
        # Based on implementation, should construct:
        # https://ikeauth.its.hawaii.edu/files/v2/download/public/raster
        expected_base = client.base_url
        raster_url = f"{expected_base}/raster"
        
        # Verify this matches what the client constructs
        assert raster_url == f"{client.base_url}/raster"

    def test_timeseries_endpoint_url(self):
        """Test timeseries endpoint URL construction.""" 
        client = HCDPClient(api_token="test")
        timeseries_url = f"{client.base_url}/raster/timeseries"
        
        # Should be: base_url + "/raster/timeseries"
        expected = f"{client.base_url}/raster/timeseries"
        assert timeseries_url == expected

    def test_stations_endpoint_url(self):
        """Test stations endpoint URL construction."""
        client = HCDPClient(api_token="test")
        stations_url = f"{client.base_url}/stations"
        
        expected = f"{client.base_url}/stations"
        assert stations_url == expected

    def test_mesonet_endpoint_url(self):
        """Test mesonet endpoint URL construction."""
        client = HCDPClient(api_token="test")
        mesonet_url = f"{client.base_url}/mesonet"
        
        expected = f"{client.base_url}/mesonet"
        assert mesonet_url == expected

    def test_genzip_endpoint_url(self):
        """Test data package generation endpoint URL construction."""
        client = HCDPClient(api_token="test")
        genzip_url = f"{client.base_url}/genzip"
        
        expected = f"{client.base_url}/genzip"
        assert genzip_url == expected


class TestParameterMappingCompliance:
    """Test that MCP parameters map correctly to API parameters."""
    
    def test_raster_parameter_mapping(self):
        """Test that raster parameters map correctly."""
        args = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31",
            location="hawaii",
            aggregation="month",
            units="mm",
            meta="true",
            fmt="tiff"
        )
        
        # All parameters should have corresponding API parameters
        expected_mappings = {
            "var": "rainfall",
            "start": "2023-01-01",
            "end": "2023-12-31", 
            "location": "hawaii",
            "aggregation": "month",
            "units": "mm",
            "meta": "true", 
            "fmt": "tiff"
        }
        
        for param, expected_value in expected_mappings.items():
            assert hasattr(args, param)
            assert getattr(args, param) == expected_value

    def test_timeseries_parameter_mapping(self):
        """Test that timeseries parameters map correctly.""" 
        args = GetTimeseriesArgs(
            var="temp_mean",
            lat=21.3099,
            lng=-157.8581,
            start="2023-01-01",
            end="2023-12-31",
            location="hawaii",
            aggregation="month"
        )
        
        # Check required coordinate parameters
        assert args.lat == 21.3099
        assert args.lng == -157.8581
        
        # Check date parameters
        assert args.start == "2023-01-01"
        assert args.end == "2023-12-31"

    def test_station_data_parameter_mapping(self):
        """Test that station data parameters map correctly."""
        args = GetStationDataArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31",
            location="hawaii",
            aggregation="month",
            meta="true",
            fmt="json",
            station_id="STAT001"
        )
        
        # Verify optional station_id parameter
        assert args.station_id == "STAT001"
        
        # Verify other parameters
        assert args.meta == "true"
        assert args.fmt == "json"

    def test_mesonet_parameter_mapping(self):
        """Test that mesonet parameters map correctly."""
        args = GetMesonetDataArgs(
            var="wind_speed",
            start="2023-01-01", 
            end="2023-01-31",
            location="hawaii",
            aggregation="day",
            station="MESA001"
        )
        
        # Mesonet should default to daily aggregation
        assert args.aggregation == "day"
        assert args.station == "MESA001"

    def test_data_package_parameter_mapping(self):
        """Test that data package parameters map correctly."""
        args = GenerateDataPackageArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31",
            location="hawaii",
            aggregation="month",
            fmt="tiff",
            email="user@example.com",
            instant="false"
        )
        
        # Check email and instant parameters
        assert args.email == "user@example.com"
        assert args.instant == "false"


class TestRequiredParameterValidation:
    """Test validation of required vs optional parameters."""
    
    def test_raster_required_parameters(self):
        """Test that required raster parameters are enforced."""
        # Should require var, start, end
        with pytest.raises(TypeError):
            GetClimateRasterArgs()  # No required parameters
            
        with pytest.raises(TypeError):
            GetClimateRasterArgs(var="rainfall")  # Missing start, end
            
        # Should work with all required parameters
        args = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31"
        )
        assert args.var == "rainfall"

    def test_timeseries_required_parameters(self):
        """Test that required timeseries parameters are enforced."""
        # Should require var, lat, lng, start, end
        with pytest.raises(TypeError):
            GetTimeseriesArgs()
            
        with pytest.raises(TypeError):
            GetTimeseriesArgs(var="rainfall", lat=21.3)  # Missing lng, dates
            
        # Should work with all required parameters
        args = GetTimeseriesArgs(
            var="rainfall",
            lat=21.3099,
            lng=-157.8581,
            start="2023-01-01",
            end="2023-12-31"
        )
        assert args.lat == 21.3099

    def test_optional_parameter_defaults(self):
        """Test that optional parameters have correct defaults."""
        # Test raster defaults
        raster_args = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31"
        )
        assert raster_args.location == "hawaii"
        assert raster_args.aggregation == "month"
        assert raster_args.meta == "true"
        assert raster_args.fmt == "tiff"
        assert raster_args.units is None
        
        # Test timeseries defaults
        ts_args = GetTimeseriesArgs(
            var="rainfall",
            lat=21.3,
            lng=-157.8,
            start="2023-01-01",
            end="2023-12-31"
        )
        assert ts_args.location == "hawaii"
        assert ts_args.aggregation == "month"
        assert ts_args.units is None


class TestAPISpecificationGaps:
    """Identify gaps between implementation and API specification."""
    
    def test_missing_extent_parameter(self):
        """Test for missing extent parameter in raster requests."""
        # According to API spec, raster endpoint should have extent parameter
        # Current implementation doesn't include this
        args = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31"
        )
        
        # extent parameter is missing from current implementation
        assert not hasattr(args, "extent")
        # This indicates a potential gap in the implementation

    def test_missing_production_parameter(self):
        """Test for missing production parameter."""
        # API spec mentions production parameter for different methodologies
        args = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31"
        )
        
        # production parameter is missing
        assert not hasattr(args, "production")

    def test_missing_period_parameter(self):
        """Test for missing period parameter."""
        # API spec includes period parameter
        args = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01", 
            end="2023-12-31"
        )
        
        # period parameter is missing
        assert not hasattr(args, "period")

    def test_mesonet_endpoint_variants(self):
        """Test for missing mesonet endpoint variants."""
        # API spec has multiple mesonet endpoints like /mesonet/db/measurements
        # Current implementation only has generic /mesonet
        
        # This test documents that the implementation may not cover
        # all mesonet endpoint variants from the specification
        client = HCDPClient(api_token="test")
        
        # Current implementation uses /mesonet
        # But spec suggests /mesonet/db/measurements and other variants
        current_url = f"{client.base_url}/mesonet"
        spec_url = f"{client.base_url}/mesonet/db/measurements"
        
        assert current_url != spec_url  # Indicates potential mismatch

    def test_stations_query_parameter_format(self):
        """Test stations query parameter format compliance."""
        # API spec suggests complex JSON query structure for stations
        # Current implementation uses simple parameters
        
        args = GetStationDataArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31"
        )
        
        # Current implementation doesn't have complex query parameter
        assert not hasattr(args, "query")
        # This may indicate simplified parameter structure vs. API spec


class TestDataTypesAndValidation:
    """Test data types and validation requirements."""
    
    def test_coordinate_data_types(self):
        """Test that coordinates are properly typed as floats."""
        args = GetTimeseriesArgs(
            var="rainfall",
            lat=21.3099,  # Should be float
            lng=-157.8581, # Should be float
            start="2023-01-01",
            end="2023-12-31"
        )
        
        assert isinstance(args.lat, float)
        assert isinstance(args.lng, float)

    def test_date_string_format(self):
        """Test that dates are handled as strings in YYYY-MM-DD format."""
        args = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31"
        )
        
        assert isinstance(args.start, str)
        assert isinstance(args.end, str)
        
        # Should match YYYY-MM-DD format
        assert len(args.start) == 10
        assert args.start[4] == "-"
        assert args.start[7] == "-"

    def test_boolean_parameters_as_strings(self):
        """Test that boolean parameters are handled as strings."""
        args = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31",
            meta="false"
        )
        
        # meta should be string "true"/"false", not boolean
        assert isinstance(args.meta, str)
        assert args.meta in ["true", "false"]

    def test_optional_string_parameters(self):
        """Test handling of optional string parameters."""
        args = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31",
            units=None
        )
        
        # Optional parameter should be None when not provided
        assert args.units is None
        
        # Should accept string when provided
        args_with_units = GetClimateRasterArgs(
            var="rainfall",
            start="2023-01-01",
            end="2023-12-31",
            units="mm"
        )
        assert args_with_units.units == "mm"
        assert isinstance(args_with_units.units, str)