"""Comprehensive tests for HCDP API client implementation."""

import pytest
import httpx
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

from hcdp_mcp_server.client import HCDPClient


class TestHCDPClientInitialization:
    """Test HCDP client initialization and configuration."""
    
    def test_client_init_with_token(self):
        """Test client initialization with explicit token."""
        client = HCDPClient(api_token="test_token")
        assert client.api_token == "test_token"
        assert client.base_url == "https://ikeauth.its.hawaii.edu/files/v2/download/public"
        assert client.headers["Authorization"] == "Bearer test_token"
        assert client.headers["Content-Type"] == "application/json"

    def test_client_init_with_custom_base_url(self):
        """Test client initialization with custom base URL."""
        custom_url = "https://api.custom.com"
        client = HCDPClient(api_token="test_token", base_url=custom_url)
        assert client.base_url == custom_url

    @patch.dict('os.environ', {'HCDP_API_TOKEN': 'env_token', 'HCDP_BASE_URL': 'https://env.api.com'})
    def test_client_init_from_env_vars(self):
        """Test client initialization from environment variables."""
        client = HCDPClient()
        assert client.api_token == "env_token"
        assert client.base_url == "https://env.api.com"

    @patch.dict('os.environ', {}, clear=True)
    def test_client_init_no_token_raises_error(self):
        """Test that missing API token raises ValueError."""
        with pytest.raises(ValueError, match="HCDP API token is required"):
            HCDPClient()


class TestRasterDataEndpoint:
    """Test the raster data endpoint implementation."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_get_raster_data_basic(self, client):
        """Test basic raster data request."""
        mock_response_data = {
            "status": "success",
            "data": {"url": "https://example.com/raster.tiff"},
            "metadata": {"variable": "rainfall"}
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.headers = {"content-type": "application/json"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = await client.get_raster_data(
                var="rainfall",
                start="2023-01-01",
                end="2023-12-31"
            )
            
            # Verify API call was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "https://ikeauth.its.hawaii.edu/files/v2/download/public/raster"
            
            # Check parameters
            params = call_args[1]["params"]
            assert params["var"] == "rainfall"
            assert params["start"] == "2023-01-01"
            assert params["end"] == "2023-12-31"
            assert params["location"] == "hawaii"
            assert params["aggregation"] == "month"
            assert params["meta"] == "true"
            assert params["fmt"] == "tiff"
            
            # Verify response
            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_raster_data_with_units(self, client):
        """Test raster data request with units parameter."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "success"}
            mock_response.headers = {"content-type": "application/json"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            await client.get_raster_data(
                var="temp_mean",
                start="2023-01-01",
                end="2023-12-31",
                units="celsius"
            )
            
            params = mock_get.call_args[1]["params"]
            assert params["units"] == "celsius"

    @pytest.mark.asyncio
    async def test_get_raster_data_binary_response(self, client):
        """Test handling of binary raster data response."""
        binary_data = b"fake_tiff_data"
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.content = binary_data
            mock_response.headers = {"content-type": "image/tiff"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = await client.get_raster_data(
                var="rainfall",
                start="2023-01-01",
                end="2023-12-31"
            )
            
            assert result == {"data": binary_data}

    @pytest.mark.asyncio
    async def test_get_raster_data_http_error(self, client):
        """Test handling of HTTP errors."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=Mock()
            )
            mock_get.return_value = mock_response
            
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_raster_data(
                    var="rainfall",
                    start="2023-01-01",
                    end="2023-12-31"
                )


class TestTimeseriesEndpoint:
    """Test the timeseries data endpoint implementation."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_get_timeseries_data_basic(self, client):
        """Test basic timeseries data request."""
        mock_response_data = {
            "data": [
                {"date": "2023-01-01", "value": 25.5},
                {"date": "2023-02-01", "value": 27.2}
            ]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = await client.get_timeseries_data(
                var="temp_mean",
                lat=21.3099,
                lng=-157.8581,
                start="2023-01-01",
                end="2023-12-31"
            )
            
            # Verify API call
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "https://ikeauth.its.hawaii.edu/files/v2/download/public/raster/timeseries"
            
            # Check parameters
            params = call_args[1]["params"]
            assert params["var"] == "temp_mean"
            assert params["lat"] == 21.3099
            assert params["lng"] == -157.8581
            assert params["start"] == "2023-01-01"
            assert params["end"] == "2023-12-31"
            assert params["location"] == "hawaii"
            assert params["aggregation"] == "month"
            
            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_timeseries_data_with_units(self, client):
        """Test timeseries request with units parameter."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"data": []}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            await client.get_timeseries_data(
                var="rainfall",
                lat=21.3099,
                lng=-157.8581,
                start="2023-01-01",
                end="2023-12-31",
                units="inches"
            )
            
            params = mock_get.call_args[1]["params"]
            assert params["units"] == "inches"

    @pytest.mark.asyncio
    async def test_get_timeseries_data_american_samoa(self, client):
        """Test timeseries request for American Samoa."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"data": []}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            await client.get_timeseries_data(
                var="rainfall",
                lat=-14.3,
                lng=-170.7,
                start="2023-01-01",
                end="2023-12-31",
                location="american_samoa"
            )
            
            params = mock_get.call_args[1]["params"]
            assert params["location"] == "american_samoa"


class TestStationDataEndpoint:
    """Test the station data endpoint implementation."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_get_station_data_basic(self, client):
        """Test basic station data request."""
        mock_response_data = {
            "stations": [
                {"id": "STAT001", "name": "Honolulu Station", "measurements": []}
            ]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = await client.get_station_data(
                var="rainfall",
                start="2023-01-01",
                end="2023-12-31"
            )
            
            # Verify API call
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "https://ikeauth.its.hawaii.edu/files/v2/download/public/stations"
            
            # Check parameters
            params = call_args[1]["params"]
            assert params["var"] == "rainfall"
            assert params["start"] == "2023-01-01"
            assert params["end"] == "2023-12-31"
            assert params["meta"] == "true"
            assert params["fmt"] == "json"
            
            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_station_data_with_station_id(self, client):
        """Test station data request with specific station ID."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"stations": []}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            await client.get_station_data(
                var="temp_mean",
                start="2023-01-01",
                end="2023-12-31",
                station_id="STAT001"
            )
            
            params = mock_get.call_args[1]["params"]
            assert params["station_id"] == "STAT001"


class TestMesonetDataEndpoint:
    """Test the mesonet data endpoint implementation."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_get_mesonet_data_basic(self, client):
        """Test basic mesonet data request."""
        mock_response_data = {
            "measurements": [
                {"timestamp": "2023-01-01T00:00:00Z", "value": 15.2}
            ]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = await client.get_mesonet_data(
                var="wind_speed",
                start="2023-01-01",
                end="2023-01-31"
            )
            
            # Verify API call
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "https://ikeauth.its.hawaii.edu/files/v2/download/public/mesonet"
            
            # Check parameters
            params = call_args[1]["params"]
            assert params["var"] == "wind_speed"
            assert params["start"] == "2023-01-01"
            assert params["end"] == "2023-01-31"
            assert params["aggregation"] == "day"  # mesonet default
            
            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_mesonet_data_with_station(self, client):
        """Test mesonet data request with specific station."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"measurements": []}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            await client.get_mesonet_data(
                var="temperature",
                start="2023-01-01",
                end="2023-01-31",
                station="MESA001"
            )
            
            params = mock_get.call_args[1]["params"]
            assert params["station"] == "MESA001"


class TestDataPackageEndpoint:
    """Test the data package generation endpoint implementation."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_generate_data_package_basic(self, client):
        """Test basic data package generation request."""
        mock_response_data = {
            "package_id": "pkg_123",
            "status": "processing"
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = await client.generate_data_package(
                var="rainfall",
                start="2023-01-01",
                end="2023-12-31"
            )
            
            # Verify API call
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "https://ikeauth.its.hawaii.edu/files/v2/download/public/genzip"
            
            # Check parameters
            params = call_args[1]["params"]
            assert params["var"] == "rainfall"
            assert params["start"] == "2023-01-01"
            assert params["end"] == "2023-12-31"
            assert params["instant"] == "false"
            
            # Verify timeout is longer for data package generation
            assert call_args[1]["timeout"] == 120.0
            
            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_generate_data_package_with_email(self, client):
        """Test data package generation with email delivery."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "queued"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            await client.generate_data_package(
                var="temp_mean",
                start="2023-01-01",
                end="2023-12-31",
                email="user@example.com",
                instant="true"
            )
            
            params = mock_get.call_args[1]["params"]
            assert params["email"] == "user@example.com"
            assert params["instant"] == "true"


class TestClientErrorHandling:
    """Test error handling in HCDP client."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_network_timeout(self, client):
        """Test handling of network timeouts."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")
            
            with pytest.raises(httpx.TimeoutException):
                await client.get_raster_data(
                    var="rainfall",
                    start="2023-01-01",
                    end="2023-12-31"
                )

    @pytest.mark.asyncio
    async def test_http_error_status_codes(self, client):
        """Test handling of various HTTP error status codes."""
        error_codes = [400, 401, 403, 404, 500, 503]
        
        for status_code in error_codes:
            with patch('httpx.AsyncClient.get') as mock_get:
                mock_response = Mock()
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    f"{status_code} Error", request=Mock(), response=Mock(status_code=status_code)
                )
                mock_get.return_value = mock_response
                
                with pytest.raises(httpx.HTTPStatusError):
                    await client.get_raster_data(
                        var="rainfall",
                        start="2023-01-01",
                        end="2023-12-31"
                    )

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, client):
        """Test handling of invalid JSON responses."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            with pytest.raises(json.JSONDecodeError):
                await client.get_timeseries_data(
                    var="rainfall",
                    lat=21.3099,
                    lng=-157.8581,
                    start="2023-01-01",
                    end="2023-12-31"
                )


class TestClientParameterValidation:
    """Test client parameter validation and edge cases."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return HCDPClient(api_token="test_token")

    @pytest.mark.asyncio
    async def test_boundary_coordinates(self, client):
        """Test requests with boundary coordinates."""
        # Test extreme coordinates that are still valid
        boundary_cases = [
            (18.0, -178.0),  # Southwest boundary
            (23.0, -154.0),  # Northeast boundary  
            (-14.7, -171.0), # American Samoa coordinates
        ]
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"data": []}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            for lat, lng in boundary_cases:
                await client.get_timeseries_data(
                    var="rainfall",
                    lat=lat,
                    lng=lng,
                    start="2023-01-01",
                    end="2023-12-31"
                )
                
                params = mock_get.call_args[1]["params"]
                assert params["lat"] == lat
                assert params["lng"] == lng

    @pytest.mark.asyncio
    async def test_date_edge_cases(self, client):
        """Test requests with edge case dates."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"data": []}
            mock_response.headers = {"content-type": "application/json"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Same start and end date
            await client.get_raster_data(
                var="rainfall",
                start="2023-01-01",
                end="2023-01-01"
            )
            
            params = mock_get.call_args[1]["params"]
            assert params["start"] == params["end"]

    @pytest.mark.asyncio
    async def test_optional_parameters_excluded_when_none(self, client):
        """Test that None optional parameters are not included in requests."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"data": []}
            mock_response.headers = {"content-type": "application/json"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            await client.get_raster_data(
                var="rainfall",
                start="2023-01-01",
                end="2023-12-31",
                units=None  # Should not be included in request
            )
            
            params = mock_get.call_args[1]["params"]
            assert "units" not in params