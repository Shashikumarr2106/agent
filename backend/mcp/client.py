"""MCP Client used by LangGraph nodes to invoke MCP tools."""
from typing import Any, Dict
from .server import mcp_server

class MCPClient:
    """Client interface for invoking MCP tools from within LangGraph workflow nodes."""

    def call(self, tool_name: str, **kwargs) -> Any:
        return mcp_server.call_tool(tool_name, **kwargs)

    def list_tools(self):
        return mcp_server.list_tools()

mcp_client = MCPClient()
