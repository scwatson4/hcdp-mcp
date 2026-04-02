"""Tool for listing mesonet weather stations."""

from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field


class GetMesonetStationsArgs(BaseModel):
    """Arguments for getting mesonet station info."""

    location: str = Field(default="hawaii", description="Location")


tool_definition = Tool(
    name="get_mesonet_stations",
    description="List all mesonet weather stations with location and metadata.",
    inputSchema=GetMesonetStationsArgs.model_json_schema(),
)


async def handle(
    client, arguments: dict
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_mesonet_stations tool call."""
    args = GetMesonetStationsArgs(**arguments)
    result = await client.get_mesonet_stations(location=args.location)
    return result
