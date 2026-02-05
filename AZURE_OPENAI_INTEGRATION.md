# Integrating HCDP MCP Server with Your Azure OpenAI Chatbot

## Overview

Yes! Your HCDP MCP server can be used by your Azure OpenAI chatbot. The MCP protocol is client-agnostic and works with any LLM that supports function/tool calling.

## Installation

Install the MCP client library:

```bash
pip install mcp
```

## Architecture

```
Your Azure OpenAI Chatbot
    ↓
MCP Client (in your chatbot code)
    ↓
HCDP MCP Server (stdio)
    ↓
HCDP API
```

## Key Components

### 1. MCP Client Session
- Starts the HCDP MCP server as a subprocess
- Communicates via stdio (standard input/output)
- Manages the connection lifecycle

### 2. Tool Schema Conversion
- MCP tools → OpenAI function calling format
- Automatic schema translation

### 3. Tool Execution
- Azure OpenAI decides when to call tools
- Your code executes MCP tools
- Results are fed back to Azure OpenAI

## Quick Start

See `examples/azure_openai_integration.py` for a complete working example.

### Basic Usage

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AzureOpenAI

# 1. Connect to MCP server
server_params = StdioServerParameters(
    command="python",
    args=["-m", "hcdp_mcp_server.server"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # 2. Get available tools
        tools = await session.list_tools()
        
        # 3. Convert to OpenAI format
        openai_tools = convert_to_openai_format(tools)
        
        # 4. Use with Azure OpenAI
        response = azure_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Get rainfall for Oahu"}],
            tools=openai_tools
        )
        
        # 5. Execute tool calls
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                result = await session.call_tool(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments)
                )
```

## Configuration

### Environment Variables

The MCP server will automatically load your `.env` file from the `hcdp-mcp` directory:

```env
HCDP_API_TOKEN=your_token_here
HCDP_API_BASE_URL=https://api.hcdp.ikewai.org
```

### Server Parameters

You can customize how the server starts:

```python
server_params = StdioServerParameters(
    command="python",
    args=["-m", "hcdp_mcp_server.server"],
    cwd="c:\\Users\\sammy\\Documents\\GitHub\\hcdp-mcp",  # Set working directory
    env={"HCDP_API_TOKEN": "your_token"}  # Or pass env vars directly
)
```

## Advantages Over Direct API Calls

### Why use MCP instead of calling HCDP API directly?

1. **Standardized Interface**: MCP provides a consistent way to expose tools
2. **Schema Validation**: Automatic parameter validation
3. **Tool Discovery**: LLM can see all available tools and their descriptions
4. **Reusability**: Same server works with Claude Desktop, your chatbot, or any MCP client
5. **Maintainability**: Update server once, all clients benefit

## Example Queries

Once integrated, your Azure OpenAI chatbot can handle:

```
User: "Get rainfall data for Big Island in February 2022"
→ Calls get_climate_raster with correct parameters

User: "Compare rainfall between Oahu and Big Island for 2025"
→ Makes 2 API calls and analyzes results

User: "Show me all weather stations in Hawaii"
→ Calls get_mesonet_stations

User: "Get rainfall timeseries for Hilo for the past year"
→ Calls get_timeseries_data with coordinates
```

## Error Handling

```python
try:
    result = await session.call_tool(tool_name, arguments)
    # Process result
except Exception as e:
    # Handle MCP errors (404, 400, etc.)
    print(f"Tool call failed: {e}")
```

## Performance Considerations

- **Connection Pooling**: Keep the MCP session alive for multiple queries
- **Async Operations**: Use async/await for non-blocking tool calls
- **Timeout Handling**: HCDP API can be slow, set appropriate timeouts

## Next Steps

1. Install `mcp` package: `pip install mcp`
2. Copy `examples/azure_openai_integration.py` to your chatbot project
3. Modify with your Azure OpenAI credentials
4. Test with simple queries
5. Integrate into your existing chatbot architecture

## Troubleshooting

### Server Won't Start
- Check that `hcdp-mcp-server` is installed: `pip list | grep hcdp`
- Verify `.env` file exists with API token

### Tools Not Appearing
- Ensure `await session.initialize()` is called
- Check `await session.list_tools()` returns tools

### Tool Calls Failing
- Verify extent codes are correct ('oa', 'bi', 'ka', 'mn', 'statewide')
- Check HCDP API token is valid
- Review error messages from MCP server

## Resources

- MCP Documentation: https://modelcontextprotocol.io/
- HCDP API Docs: https://api.hcdp.ikewai.org/docs
- Example Code: `examples/azure_openai_integration.py`
