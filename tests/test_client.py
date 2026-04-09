"""Tests for HCDP API client implementation.

Validates HCDPClient initialization, endpoint methods, error handling,
and parameter construction using mocked HTTP responses.
"""

import pytest
import httpx
from unittest.mock import Mock, patch
import json

from hcdp_mcp_server.client import HCDPClient


class TestHCDPClientInitialization:
    """Test HCDP client initialization and configuration."""

    def test_client_init_with_token(self):
        """Test client initialization with explicit token."""
        client = HCDPClient(api_token="test_token")
        assert client.api_token == "test_token"
        assert client.base_url == "https://api.hcdp.ikewai.org"
        assert client.headers["Authorization"] == "Bearer test_token"
        assert client.headers["Content-Type"] == "application/json"

    def test_client_init_with_custom_base_url(self):
        """Test client initialization with custom base URL."""
        custom_url = "https://api.custom.com"
        client = HCDPClient(api_token="test_token", base_url=custom_url)
        assert client.base_url == custom_url

    @patch.dict(
        "os.environ",
        {"HCDP_API_TOKEN": "env_token", "HCDP_BASE_URL": "https://env.api.com"},
    )
    def test_client_init_from_env_vars(self):
        """Test client initialization from environment variables."""
        client = HCDPClient()
        assert client.api_token == "env_token"
        assert client.base_url == "https://env.api.com"

    @patch.dict("os.environ", {}, clear=True)
    def test_client_init_no_token_raises_error(self):
        """Test that missing API token raises ValueError."""
        with pytest.raises(ValueError, match="HCDP API token is required"):
            HCDPClient()


class TestRasterDataEndpoint:
    """Test the raster data endpoint."""

    @pytest.fixture
    def client(self):
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_get_raster_data_basic(self, client):
        """Test basic raster data request with current API signature."""
        mock_response_data = {"status": "success", "data": "raster_content"}

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.headers = {"content-type": "application/json"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = await client.get_raster_data(
                datatype="rainfall",
                date="2024-01",
                extent="oa",
            )

            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "raster" in call_args[0][0]

            params = call_args[1]["params"]
            assert params["datatype"] == "rainfall"
            assert params["date"] == "2024-01"
            assert params["extent"] == "oa"

            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_raster_data_with_optional_params(self, client):
        """Test raster data with optional parameters."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "success"}
            mock_response.headers = {"content-type": "application/json"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            await client.get_raster_data(
                datatype="rainfall",
                date="2024-01",
                extent="oa",
                production="new",
                period="month",
            )

            params = mock_get.call_args[1]["params"]
            assert params["production"] == "new"
            assert params["period"] == "month"

    @pytest.mark.asyncio
    async def test_get_raster_data_binary_response(self, client):
        """Test handling of binary raster data (e.g., GeoTIFF)."""
        binary_data = b"fake_tiff_data"

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.content = binary_data
            mock_response.headers = {"content-type": "image/tiff"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = await client.get_raster_data(
                datatype="rainfall", date="2024-01", extent="oa"
            )

            assert result == {"data": binary_data}

    @pytest.mark.asyncio
    async def test_get_raster_data_http_error(self, client):
        """Test handling of HTTP errors."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=Mock()
            )
            mock_get.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                await client.get_raster_data(
                    datatype="rainfall", date="2024-01", extent="oa"
                )


class TestTimeseriesEndpoint:
    """Test the timeseries data endpoint."""

    @pytest.fixture
    def client(self):
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_get_timeseries_data_basic(self, client):
        """Test basic timeseries request with current signature."""
        mock_response_data = {"2024-01": 125.5, "2024-02": 98.2}

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = await client.get_timeseries_data(
                datatype="rainfall",
                start="2024-01-01",
                end="2024-12-31",
                extent="oa",
                lat=21.3099,
                lng=-157.8581,
            )

            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "raster/timeseries" in call_args[0][0]

            params = call_args[1]["params"]
            assert params["datatype"] == "rainfall"
            assert params["start"] == "2024-01-01"
            assert params["end"] == "2024-12-31"
            assert params["extent"] == "oa"
            assert params["lat"] == 21.3099
            assert params["lng"] == -157.8581
            assert params["location"] == "hawaii"

            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_timeseries_data_with_production(self, client):
        """Test timeseries with production parameter."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            await client.get_timeseries_data(
                datatype="rainfall",
                start="2024-01-01",
                end="2024-12-31",
                extent="oa",
                production="new",
                period="month",
            )

            params = mock_get.call_args[1]["params"]
            assert params["production"] == "new"
            assert params["period"] == "month"

    @pytest.mark.asyncio
    async def test_get_timeseries_data_location_override(self, client):
        """Test timeseries with location override to American Samoa."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            await client.get_timeseries_data(
                datatype="rainfall",
                start="2024-01-01",
                end="2024-12-31",
                extent="as",
                location="american_samoa",
            )

            params = mock_get.call_args[1]["params"]
            assert params["location"] == "american_samoa"


class TestStationDataEndpoint:
    """Test the station data endpoint."""

    @pytest.fixture
    def client(self):
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_get_station_data_basic(self, client):
        """Test station data with query parameter."""
        mock_response_data = [{"station_id": "0501", "name": "Lyon Arboretum"}]

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = await client.get_station_data(q='{"name": "Lyon"}')

            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "stations" in call_args[0][0]

            params = call_args[1]["params"]
            assert params["q"] == '{"name": "Lyon"}'

            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_station_data_with_limit(self, client):
        """Test station data with limit and offset."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            await client.get_station_data(q="{}", limit=10, offset=5)

            params = mock_get.call_args[1]["params"]
            assert params["limit"] == 10
            assert params["offset"] == 5


class TestMesonetDataEndpoint:
    """Test the mesonet data endpoint."""

    @pytest.fixture
    def client(self):
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_get_mesonet_data_basic(self, client):
        """Test mesonet data with current signature."""
        mock_response_data = [
            {"station_id": "0501", "timestamp": "2024-01-01T00:00:00Z", "value": "1.5"}
        ]

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = await client.get_mesonet_data(
                station_ids="0501",
                start_date="2024-01-01",
                end_date="2024-01-02",
                var_ids="RF_1_Tot300s",
            )

            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "mesonet/db/measurements" in call_args[0][0]

            params = call_args[1]["params"]
            assert params["station_ids"] == "0501"
            assert params["start_date"] == "2024-01-01"
            assert params["end_date"] == "2024-01-02"
            assert params["var_ids"] == "RF_1_Tot300s"
            assert params["location"] == "hawaii"

            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_mesonet_data_join_metadata(self, client):
        """Test mesonet data with join_metadata parameter."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            await client.get_mesonet_data(station_ids="0501", join_metadata=False)

            params = mock_get.call_args[1]["params"]
            assert params["join_metadata"] == "false"


class TestMesonetStationsEndpoint:
    """Test the mesonet stations endpoint."""

    @pytest.fixture
    def client(self):
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_get_mesonet_stations(self, client):
        """Test mesonet stations listing."""
        mock_response_data = [{"station_id": "0501", "name": "Lyon Arboretum"}]

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = await client.get_mesonet_stations()

            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "mesonet/db/stations" in call_args[0][0]
            assert call_args[1]["params"]["location"] == "hawaii"

            assert result == mock_response_data


class TestMesonetVariablesEndpoint:
    """Test the mesonet variables endpoint."""

    @pytest.fixture
    def client(self):
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_get_mesonet_variables(self, client):
        """Test mesonet variables listing."""
        mock_response_data = [{"standard_name": "RF_1_Tot300s", "units": "mm"}]

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = await client.get_mesonet_variables()

            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "mesonet/db/variables" in call_args[0][0]

            assert result == mock_response_data


class TestDataPackageEndpoints:
    """Test the data package generation endpoints."""

    @pytest.fixture
    def client(self):
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_generate_data_package_email(self, client):
        """Test email-based data package generation (POST)."""
        mock_response_data = {
            "status": "queued",
            "message": "Package generation started",
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            result = await client.generate_data_package_email(
                email="test@example.com",
                datatype="rainfall",
                production="new",
                extent="oa",
            )

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "genzip/email" in call_args[0][0]
            assert call_args[1]["timeout"] == 120.0

            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_generate_data_package_instant_link(self, client):
        """Test instant link data package generation."""
        mock_response_data = {"url": "https://example.com/download/pkg123"}

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            result = await client.generate_data_package_instant_link(
                email="test@example.com",
                datatype="rainfall",
            )

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "genzip/instant/link" in call_args[0][0]

            assert result == mock_response_data


class TestClientErrorHandling:
    """Test error handling in HCDP client."""

    @pytest.fixture
    def client(self):
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_network_timeout(self, client):
        """Test handling of network timeouts."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(httpx.TimeoutException):
                await client.get_raster_data(
                    datatype="rainfall", date="2024-01", extent="oa"
                )

    @pytest.mark.asyncio
    async def test_http_error_status_codes(self, client):
        """Test handling of various HTTP error status codes."""
        error_codes = [400, 401, 403, 404, 500, 503]

        for status_code in error_codes:
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = Mock()
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    f"{status_code} Error",
                    request=Mock(),
                    response=Mock(status_code=status_code),
                )
                mock_get.return_value = mock_response

                with pytest.raises(httpx.HTTPStatusError):
                    await client.get_mesonet_stations()

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, client):
        """Test handling of invalid JSON responses."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            with pytest.raises(json.JSONDecodeError):
                await client.get_mesonet_variables()


class TestClientParameterValidation:
    """Test client parameter validation and edge cases."""

    @pytest.fixture
    def client(self):
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_timeseries_without_coordinates(self, client):
        """Test timeseries request without lat/lng (extent only)."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            await client.get_timeseries_data(
                datatype="rainfall",
                start="2024-01-01",
                end="2024-12-31",
                extent="oa",
            )

            params = mock_get.call_args[1]["params"]
            assert "lat" not in params
            assert "lng" not in params

    @pytest.mark.asyncio
    async def test_mesonet_optional_params_excluded(self, client):
        """Test that None optional parameters are excluded from requests."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            await client.get_mesonet_data()

            params = mock_get.call_args[1]["params"]
            assert "station_ids" not in params
            assert "start_date" not in params
            assert "end_date" not in params
            assert "var_ids" not in params
            assert params["location"] == "hawaii"
            assert params["join_metadata"] == "true"
