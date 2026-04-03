"""Tool for getting station-specific climate data."""

from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field


class GetStationDataArgs(BaseModel):
    """Arguments for getting station data."""

    q: str = Field(
        description="Search query: station name, ID, or network (e.g. 'Manoa', 'HN151')"
    )
    limit: int | None = Field(default=None, description="Limit number of results")
    offset: int | None = Field(default=None, description="Offset for pagination")


tool_definition = Tool(
    name="get_station_data",
    description="Search HCDP station metadata by name or ID. Returns station info, not measurements (use get_mesonet_data for measurements).",
    inputSchema=GetStationDataArgs.model_json_schema(),
)


async def handle(
    client, arguments: dict
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_station_data tool call."""
    args = GetStationDataArgs(**arguments)
    result = await client.get_station_data(
        q=args.q, limit=args.limit, offset=args.offset
    )
    return result
