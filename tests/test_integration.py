"""Integration tests for HCDP MCP Server with realistic scenarios.

Uses mocked HCDPClient to test end-to-end tool dispatch through the
server layer, validating that tool calls are routed correctly and
responses are formatted as expected.
"""

import pytest
import json
from unittest.mock import patch, Mock, AsyncMock

from hcdp_mcp_server.server import handle_call_tool


class TestRealisticUsageScenarios:
    """Test realistic usage scenarios for HCDP MCP Server."""

    @pytest.fixture
    def mock_successful_client(self):
        """Mock client that returns realistic successful responses."""
        with patch("hcdp_mcp_server.server.HCDPClient") as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            mock_instance.get_timeseries_data = AsyncMock(
                return_value={"2024-01": 125.5, "2024-02": 98.2, "2024-03": 156.8}
            )

            mock_instance.get_station_data = AsyncMock(
                return_value=[
                    {
                        "station_id": "0501",
                        "name": "Lyon Arboretum",
                        "lat": "21.333",
                        "lng": "-157.8025",
                    }
                ]
            )

            mock_instance.get_mesonet_data = AsyncMock(
                return_value=[
                    {
                        "station_id": "0501",
                        "timestamp": "2024-01-01T10:00:00Z",
                        "variable": "Tair_1_Avg",
                        "value": "24.5",
                    }
                ]
            )

            mock_instance.get_mesonet_stations = AsyncMock(
                return_value=[
                    {
                        "station_id": "0501",
                        "name": "Lyon Arboretum",
                        "lat": "21.333",
                        "lng": "-157.8025",
                        "elevation": "151",
                        "status": "active",
                    }
                ]
            )

            mock_instance.get_mesonet_variables = AsyncMock(
                return_value=[
                    {"standard_name": "RF_1_Tot300s", "units": "mm"},
                    {"standard_name": "Tair_1_Avg", "units": "deg_C"},
                ]
            )

            yield mock_instance

    @pytest.mark.asyncio
    async def test_timeseries_workflow(self, mock_successful_client):
        """Test timeseries data retrieval through server dispatch."""
        result = await handle_call_tool(
            "get_timeseries_data",
            {
                "datatype": "rainfall",
                "start": "2024-01-01",
                "end": "2024-03-31",
                "extent": "oa",
                "lat": 21.3099,
                "lng": -157.8581,
            },
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "2024-01" in data
        assert data["2024-01"] == 125.5

    @pytest.mark.asyncio
    async def test_station_data_workflow(self, mock_successful_client):
        """Test station data retrieval through server dispatch."""
        result = await handle_call_tool(
            "get_station_data",
            {"q": '{"name": "Lyon"}'},
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert isinstance(data, list)
        assert data[0]["station_id"] == "0501"

    @pytest.mark.asyncio
    async def test_mesonet_variables_workflow(self, mock_successful_client):
        """Test mesonet variables listing through server dispatch."""
        result = await handle_call_tool(
            "get_mesonet_variables",
            {"location": "hawaii"},
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert isinstance(data, list)
        assert len(data) == 2
        var_names = {v["standard_name"] for v in data}
        assert "RF_1_Tot300s" in var_names

    @pytest.mark.asyncio
    async def test_mesonet_stations_workflow(self, mock_successful_client):
        """Test mesonet stations listing through server dispatch."""
        result = await handle_call_tool(
            "get_mesonet_stations",
            {"location": "hawaii"},
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert isinstance(data, list)


class TestErrorHandlingIntegration:
    """Test error handling in realistic failure scenarios."""

    @pytest.fixture
    def mock_failing_client(self):
        """Mock client that simulates various failure modes."""
        with patch("hcdp_mcp_server.server.HCDPClient") as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            mock_instance.get_timeseries_data = AsyncMock(
                side_effect=Exception("Invalid coordinates")
            )
            mock_instance.get_station_data = AsyncMock(
                side_effect=Exception("No data available for query")
            )
            mock_instance.get_mesonet_data = AsyncMock(
                side_effect=Exception("Station not found")
            )
            mock_instance.get_mesonet_stations = AsyncMock(
                side_effect=Exception("Server temporarily unavailable")
            )

            yield mock_instance

    @pytest.mark.asyncio
    async def test_timeseries_error(self, mock_failing_client):
        """Test handling of timeseries API errors."""
        result = await handle_call_tool(
            "get_timeseries_data",
            {
                "datatype": "rainfall",
                "start": "2024-01-01",
                "end": "2024-12-31",
                "extent": "oa",
                "lat": 999.0,
                "lng": -157.8,
            },
        )

        error_text = result[0].text
        assert "Error calling HCDP API" in error_text
        assert "Invalid coordinates" in error_text

    @pytest.mark.asyncio
    async def test_station_data_error(self, mock_failing_client):
        """Test handling of station data errors."""
        result = await handle_call_tool(
            "get_station_data",
            {"q": '{"name": "nonexistent"}'},
        )

        error_text = result[0].text
        assert "Error calling HCDP API" in error_text

    @pytest.mark.asyncio
    async def test_mesonet_error(self, mock_failing_client):
        """Test handling of mesonet errors."""
        result = await handle_call_tool(
            "get_mesonet_data",
            {"station_ids": "INVALID", "var_ids": "RF_1_Tot300s"},
        )

        error_text = result[0].text
        assert "Error calling HCDP API" in error_text

    @pytest.mark.asyncio
    async def test_mesonet_stations_error(self, mock_failing_client):
        """Test handling of mesonet stations API unavailability."""
        result = await handle_call_tool(
            "get_mesonet_stations",
            {"location": "hawaii"},
        )

        error_text = result[0].text
        assert "Error calling HCDP API" in error_text
        assert "Server temporarily unavailable" in error_text


class TestDataQualityAndValidation:
    """Test data quality scenarios through the server layer."""

    @pytest.fixture
    def mock_data_client(self):
        """Mock client with various data quality responses."""
        with patch("hcdp_mcp_server.server.HCDPClient") as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            mock_instance.get_timeseries_data = AsyncMock(
                return_value={"2024-01": 125.5, "2024-02": None, "2024-03": -9999}
            )

            mock_instance.get_mesonet_data = AsyncMock(
                return_value=[
                    {
                        "station_id": "0501",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "variable": "RF_1_Tot300s",
                        "value": "0.5",
                    },
                    {
                        "station_id": "0501",
                        "timestamp": "2024-01-01T00:05:00Z",
                        "variable": "RF_1_Tot300s",
                        "value": "0.3",
                    },
                ]
            )

            yield mock_instance

    @pytest.mark.asyncio
    async def test_timeseries_with_missing_values(self, mock_data_client):
        """Test that timeseries responses preserve null and sentinel values."""
        result = await handle_call_tool(
            "get_timeseries_data",
            {
                "datatype": "rainfall",
                "start": "2024-01-01",
                "end": "2024-03-31",
                "extent": "oa",
                "lat": 21.33,
                "lng": -157.80,
            },
        )

        data = json.loads(result[0].text)
        assert data["2024-01"] == 125.5
        assert data["2024-02"] is None
        assert data["2024-03"] == -9999

    @pytest.mark.asyncio
    async def test_mesonet_multiple_records(self, mock_data_client):
        """Test handling of multiple mesonet measurements."""
        result = await handle_call_tool(
            "get_mesonet_data",
            {
                "station_ids": "0501",
                "start_date": "2024-01-01",
                "end_date": "2024-01-02",
                "var_ids": "RF_1_Tot300s",
            },
        )

        data = json.loads(result[0].text)
        assert isinstance(data, list)
        assert len(data) == 2


class TestUnknownToolHandling:
    """Test behavior for unknown or malformed tool calls."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Test that calling an unknown tool returns an error message."""
        result = await handle_call_tool("nonexistent_tool", {})
        assert len(result) == 1
        assert "Error" in result[0].text
