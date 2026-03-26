"""Tool for getting station-specific climate data."""

from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field


class GetStationDataArgs(BaseModel):
    """Arguments for getting station data."""
    q: str = Field(description="Query parameter for station search")
    limit: int | None = Field(default=None, description="Limit number of results (optional)")
    offset: int | None = Field(default=None, description="Offset for pagination (optional)")


tool_definition = Tool(
    name="get_station_data",
    description="Retrieve station-specific climate measurements and metadata",
    inputSchema=GetStationDataArgs.model_json_schema(),
)


async def handle(client, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_station_data tool call."""
    args = GetStationDataArgs(**arguments)
    result = await client.get_station_data(
        q=args.q,
        limit=args.limit,
        offset=args.offset
    )
    return result
