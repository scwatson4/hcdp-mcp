"""Tool for listing mesonet weather measurement variables."""

from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field


class GetMesonetVariablesArgs(BaseModel):
    """Arguments for getting mesonet variable definitions."""

    location: str = Field(default="hawaii", description="Location")


tool_definition = Tool(
    name="get_mesonet_variables",
    description="List valid mesonet variable IDs and descriptions. Use this to discover var_ids for get_mesonet_data.",
    inputSchema=GetMesonetVariablesArgs.model_json_schema(),
)


async def handle(
    client, arguments: dict
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle get_mesonet_variables tool call."""
    args = GetMesonetVariablesArgs(**arguments)
    result = await client.get_mesonet_variables(location=args.location)
    return result
