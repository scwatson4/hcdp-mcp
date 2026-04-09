"""Tests for HCDP API compliance and specification adherence.

Validates that the client and server configuration match the current
HCDP API specification, including base URL, authentication, endpoint
URLs, and parameter models.
"""

import pytest

from hcdp_mcp_server.client import HCDPClient
from hcdp_mcp_server.server import (
    GetTimeseriesArgs,
    GetStationDataArgs,
    GetMesonetDataArgs,
    GetNearbyStationsArgs,
    GetIslandSummaryArgs,
    GetCityWeatherArgs,
    GetIslandHistoryArgs,
)


class TestAPISpecificationCompliance:
    """Test compliance with current HCDP API specification."""

    def test_base_url_compliance(self):
        """Test that default base URL matches the HCDP API."""
        client = HCDPClient(api_token="test")
        assert client.base_url == "https://api.hcdp.ikewai.org"

    def test_authentication_header_format(self):
        """Test that authentication header follows Bearer token format."""
        client = HCDPClient(api_token="test_token")
        assert client.headers["Authorization"] == "Bearer test_token"
        assert client.headers["Content-Type"] == "application/json"

    def test_timeseries_supports_key_datatypes(self):
        """Test that timeseries accepts common climate datatypes."""
        for datatype in ["rainfall", "temperature", "relative_humidity", "spi"]:
            args = GetTimeseriesArgs(
                datatype=datatype, start="2024-01-01", end="2024-12-31"
            )
            assert args.datatype == datatype

    def test_timeseries_supports_locations(self):
        """Test that timeseries accepts both Hawaii and American Samoa."""
        for location in ["hawaii", "american_samoa"]:
            args = GetTimeseriesArgs(
                datatype="rainfall",
                start="2024-01-01",
                end="2024-12-31",
                location=location,
            )
            assert args.location == location

    def test_timeseries_has_production_and_period(self):
        """Test that timeseries Args supports production and period parameters."""
        args = GetTimeseriesArgs(
            datatype="rainfall",
            start="2024-01-01",
            end="2024-12-31",
            production="new",
            period="month",
        )
        assert args.production == "new"
        assert args.period == "month"


class TestEndpointURLCompliance:
    """Test that endpoint URLs match the current API specification."""

    def test_raster_endpoint_url(self):
        """Test raster endpoint URL."""
        client = HCDPClient(api_token="test")
        assert f"{client.base_url}/raster" == "https://api.hcdp.ikewai.org/raster"

    def test_timeseries_endpoint_url(self):
        """Test timeseries endpoint URL."""
        client = HCDPClient(api_token="test")
        expected = "https://api.hcdp.ikewai.org/raster/timeseries"
        assert f"{client.base_url}/raster/timeseries" == expected

    def test_stations_endpoint_url(self):
        """Test stations endpoint URL."""
        client = HCDPClient(api_token="test")
        assert f"{client.base_url}/stations" == "https://api.hcdp.ikewai.org/stations"

    def test_mesonet_measurements_endpoint_url(self):
        """Test mesonet measurements endpoint URL."""
        client = HCDPClient(api_token="test")
        expected = "https://api.hcdp.ikewai.org/mesonet/db/measurements"
        assert f"{client.base_url}/mesonet/db/measurements" == expected

    def test_mesonet_stations_endpoint_url(self):
        """Test mesonet stations endpoint URL."""
        client = HCDPClient(api_token="test")
        expected = "https://api.hcdp.ikewai.org/mesonet/db/stations"
        assert f"{client.base_url}/mesonet/db/stations" == expected

    def test_mesonet_variables_endpoint_url(self):
        """Test mesonet variables endpoint URL."""
        client = HCDPClient(api_token="test")
        expected = "https://api.hcdp.ikewai.org/mesonet/db/variables"
        assert f"{client.base_url}/mesonet/db/variables" == expected

    def test_genzip_email_endpoint_url(self):
        """Test data package email endpoint URL."""
        client = HCDPClient(api_token="test")
        expected = "https://api.hcdp.ikewai.org/genzip/email"
        assert f"{client.base_url}/genzip/email" == expected


class TestParameterMappingCompliance:
    """Test that MCP Args parameters map correctly to API parameters."""

    def test_timeseries_parameter_names(self):
        """Test timeseries Args fields match API parameter names."""
        args = GetTimeseriesArgs(
            datatype="rainfall",
            start="2024-01-01",
            end="2024-12-31",
            extent="oa",
            lat=21.33,
            lng=-157.80,
            location="hawaii",
            production="new",
            period="month",
        )
        # All these fields should map directly to API query params
        assert args.datatype == "rainfall"
        assert args.start == "2024-01-01"
        assert args.end == "2024-12-31"
        assert args.extent == "oa"
        assert args.lat == 21.33
        assert args.lng == -157.80

    def test_station_data_uses_q_parameter(self):
        """Test station data uses 'q' parameter for queries."""
        args = GetStationDataArgs(q='{"name": "Lyon"}')
        assert args.q == '{"name": "Lyon"}'

    def test_mesonet_data_parameter_names(self):
        """Test mesonet data Args use correct API parameter names."""
        args = GetMesonetDataArgs(
            station_ids="0501,0502",
            start_date="2024-01-01",
            end_date="2024-01-02",
            var_ids="RF_1_Tot300s",
            location="hawaii",
            join_metadata=True,
        )
        assert args.station_ids == "0501,0502"
        assert args.start_date == "2024-01-01"
        assert args.var_ids == "RF_1_Tot300s"
        assert args.join_metadata is True


class TestRequiredParameterValidation:
    """Test validation of required vs optional parameters."""

    def test_timeseries_required_fields(self):
        """Test that timeseries requires datatype, start, end."""
        with pytest.raises(Exception):
            GetTimeseriesArgs()

        # Works with required fields
        args = GetTimeseriesArgs(
            datatype="rainfall", start="2024-01-01", end="2024-12-31"
        )
        assert args.datatype == "rainfall"

    def test_station_data_requires_q(self):
        """Test that station data requires the q parameter."""
        with pytest.raises(Exception):
            GetStationDataArgs()

    def test_mesonet_data_all_optional(self):
        """Test that mesonet data has no required fields."""
        args = GetMesonetDataArgs()
        assert args.location == "hawaii"

    def test_island_summary_required_fields(self):
        """Test that island summary requires island and datatype."""
        with pytest.raises(Exception):
            GetIslandSummaryArgs()

        args = GetIslandSummaryArgs(island="oahu", datatype="temperature")
        assert args.island == "oahu"

    def test_city_weather_required_fields(self):
        """Test that city weather requires city and datatype."""
        with pytest.raises(Exception):
            GetCityWeatherArgs()

        args = GetCityWeatherArgs(city="honolulu", datatype="weather")
        assert args.city == "honolulu"

    def test_nearby_stations_required_fields(self):
        """Test that nearby stations requires lat and lng."""
        with pytest.raises(Exception):
            GetNearbyStationsArgs()

        args = GetNearbyStationsArgs(lat=21.33, lng=-157.80)
        assert args.limit == 3  # default

    def test_island_history_required_fields(self):
        """Test that island history requires island, datatype, year."""
        with pytest.raises(Exception):
            GetIslandHistoryArgs()

        args = GetIslandHistoryArgs(island="oahu", datatype="rainfall", year="2024")
        assert args.year == "2024"
