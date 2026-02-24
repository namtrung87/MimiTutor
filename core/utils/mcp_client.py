import asyncio
import json
import contextlib
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import List, Dict, Any, Optional

class MCPClient:
    """
    A unified client for interacting with MCP servers.
    Supports tool discovery and execution.
    """
    def __init__(self, server_params: StdioServerParameters):
        self.server_params = server_params
        self.session: Optional[ClientSession] = None
        self._exit_stack = None

    async def __aenter__(self):
        self._exit_stack = contextlib.AsyncExitStack()
        read, write = await self._exit_stack.enter_async_context(stdio_client(self.server_params))
        self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._exit_stack:
            await self._exit_stack.aclose()

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Lists tools available on the MCP server."""
        if not self.session:
            raise RuntimeError("MCP session not initialized.")
        response = await self.session.list_tools()
        return [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in response.tools]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Calls a specific tool on the MCP server."""
        if not self.session:
            raise RuntimeError("MCP session not initialized.")
        return await self.session.call_tool(name, arguments)

async def quick_mcp_call(server_cmd: str, server_args: List[str], tool_name: str, tool_args: Dict[str, Any], env: Optional[Dict[str, str]] = None):
    """Utility for a one-off MCP tool call."""
    params = StdioServerParameters(command=server_cmd, args=server_args, env=env)
    async with MCPClient(params) as client:
        return await client.call_tool(tool_name, tool_args)

if __name__ == "__main__":
    # Example usage (would need a real server installed)
    # params = StdioServerParameters(command="npx", args=["-y", "@modelcontextprotocol/server-everything"])
    pass
