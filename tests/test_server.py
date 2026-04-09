"""Tests for HCDP MCP Server implementation.

Validates tool registration, Args model validation, tool dispatch,
and error handling in the server layer.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from mcp.types import TextContent

from hcdp_mcp_server.server import (
    handle_call_tool,
    handle_list_tools,
    GetTimeseriesArgs,
    GetStationDataArgs,
    GetMesonetDataArgs,
    GetMesonetStationsArgs,
    GetMesonetVariablesArgs,
    GetNearbyStationsArgs,
    GetIslandSummaryArgs,
    GetCityWeatherArgs,
    CompareHistoryArgs,
    GetIslandHistoryArgs,
)

EXPECTED_TOOLS = [
    "get_timeseries_data",
    "get_station_data",
    "get_mesonet_data",
    "get_mesonet_stations",
    "get_mesonet_variables",
    "get_nearby_stations",
    "get_island_current_summary",
    "get_city_current_weather",
    "compare_current_vs_historical",
    "get_island_history_summary",
]


class TestMCPServerTools:
    """Test MCP server tool definitions."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_ten_tools(self):
        """Test that all 10 expected tools are listed."""
        tools = await handle_list_tools()
        assert len(tools) == 10
        tool_names = [tool.name for tool in tools]
        for expected in EXPECTED_TOOLS:
            assert expected in tool_names, f"Missing tool: {expected}"

    @pytest.mark.asyncio
    async def test_no_extra_tools(self):
        """Test that no unexpected tools are registered."""
        tools = await handle_list_tools()
        tool_names = {tool.name for tool in tools}
        expected_set = set(EXPECTED_TOOLS)
        extra = tool_names - expected_set
        assert len(extra) == 0, f"Unexpected tools registered: {extra}"


class TestArgsModelValidation:
    """Test Pydantic Args model validation for each tool."""

    def test_timeseries_args_required_fields(self):
        """Test GetTimeseriesArgs requires datatype, start, end."""
        args = GetTimeseriesArgs(
            datatype="rainfall", start="2024-01-01", end="2024-12-31"
        )
        assert args.datatype == "rainfall"
        assert args.location == "hawaii"  # default
        assert args.extent is None
        assert args.lat is None

    def test_timeseries_args_with_coordinates(self):
        """Test GetTimeseriesArgs with lat/lng."""
        args = GetTimeseriesArgs(
            datatype="rainfall",
            start="2024-01-01",
            end="2024-12-31",
            lat=21.33,
            lng=-157.80,
            extent="oa",
        )
        assert args.lat == 21.33
        assert args.lng == -157.80
        assert args.extent == "oa"

    def test_station_data_args(self):
        """Test GetStationDataArgs requires q."""
        args = GetStationDataArgs(q='{"name": "Lyon"}')
        assert args.q == '{"name": "Lyon"}'
        assert args.limit is None
        assert args.offset is None

    def test_mesonet_data_args_all_optional(self):
        """Test GetMesonetDataArgs has all optional fields."""
        args = GetMesonetDataArgs()
        assert args.station_ids is None
        assert args.start_date is None
        assert args.var_ids is None
        assert args.location == "hawaii"
        assert args.join_metadata is True

    def test_mesonet_stations_args(self):
        """Test GetMesonetStationsArgs defaults."""
        args = GetMesonetStationsArgs()
        assert args.location == "hawaii"

    def test_mesonet_variables_args(self):
        """Test GetMesonetVariablesArgs defaults."""
        args = GetMesonetVariablesArgs()
        assert args.location == "hawaii"

    def test_nearby_stations_args(self):
        """Test GetNearbyStationsArgs requires lat/lng."""
        args = GetNearbyStationsArgs(lat=21.33, lng=-157.80)
        assert args.lat == 21.33
        assert args.limit == 3  # default

    def test_island_summary_args(self):
        """Test GetIslandSummaryArgs requires island and datatype."""
        args = GetIslandSummaryArgs(island="oahu", datatype="temperature")
        assert args.island == "oahu"
        assert args.datatype == "temperature"

    def test_city_weather_args(self):
        """Test GetCityWeatherArgs requires city and datatype."""
        args = GetCityWeatherArgs(city="honolulu", datatype="weather")
        assert args.city == "honolulu"

    def test_compare_history_args(self):
        """Test CompareHistoryArgs requires city and datatype."""
        args = CompareHistoryArgs(city="hilo", datatype="temperature")
        assert args.city == "hilo"

    def test_island_history_args(self):
        """Test GetIslandHistoryArgs requires island, datatype, year."""
        args = GetIslandHistoryArgs(island="maui", datatype="rainfall", year="2024")
        assert args.island == "maui"
        assert args.year == "2024"


class TestMCPServerToolCalls:
    """Test MCP server tool call dispatch and error handling."""

    @pytest.fixture
    def mock_client(self):
        """Mock HCDPClient for testing tool dispatch."""
        with patch("hcdp_mcp_server.server.HCDPClient") as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            mock_instance.get_timeseries_data = AsyncMock(
                return_value={"2024-01": 125.5}
            )
            mock_instance.get_station_data = AsyncMock(
                return_value=[{"station_id": "0501"}]
            )
            mock_instance.get_mesonet_data = AsyncMock(return_value=[])
            mock_instance.get_mesonet_stations = AsyncMock(return_value=[])
            mock_instance.get_mesonet_variables = AsyncMock(return_value=[])

            yield mock_instance

    @pytest.mark.asyncio
    async def test_unknown_tool_error(self, mock_client):
        """Test error handling for unknown tool names."""
        result = await handle_call_tool("nonexistent_tool", {})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_client_exception_returns_error(self, mock_client):
        """Test that client exceptions are caught and returned as error text."""
        mock_client.get_mesonet_stations.side_effect = Exception("API down")

        result = await handle_call_tool("get_mesonet_stations", {"location": "hawaii"})

        assert len(result) == 1
        assert "Error calling HCDP API" in result[0].text
        assert "API down" in result[0].text

    @pytest.mark.asyncio
    async def test_successful_tool_returns_json(self, mock_client):
        """Test that successful tool calls return JSON TextContent."""
        mock_client.get_mesonet_variables.return_value = [
            {"standard_name": "RF_1_Tot300s", "units": "mm"}
        ]

        result = await handle_call_tool("get_mesonet_variables", {"location": "hawaii"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert isinstance(data, list)
        assert data[0]["standard_name"] == "RF_1_Tot300s"
