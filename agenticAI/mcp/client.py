"""
MCP Client implementation.
"""
import json
from typing import Any, Dict, List, Optional
from .protocol import MCPRequest, MCPResponse


class MCPClient:
    """Client for communicating with MCP servers"""
    
    def __init__(self, server_url: Optional[str] = None, transport: Optional[Any] = None):
        """
        Initialize MCP client.
        
        Args:
            server_url: URL of MCP server (for HTTP transport)
            transport: Custom transport implementation
        """
        self.server_url = server_url
        self.transport = transport
        self.request_id_counter = 0
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize connection with MCP server"""
        request = MCPRequest(
            id=self._next_id(),
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "coding-agent",
                    "version": "1.0.0"
                }
            }
        )
        return await self.send_request(request)
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources from MCP server"""
        request = MCPRequest(
            id=self._next_id(),
            method="resources/list"
        )
        response = await self.send_request(request)
        return response.get("result", {}).get("resources", [])
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from MCP server"""
        request = MCPRequest(
            id=self._next_id(),
            method="resources/read",
            params={"uri": uri}
        )
        response = await self.send_request(request)
        return response.get("result", {})
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from MCP server"""
        request = MCPRequest(
            id=self._next_id(),
            method="tools/list"
        )
        response = await self.send_request(request)
        return response.get("result", {}).get("tools", [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        request = MCPRequest(
            id=self._next_id(),
            method="tools/call",
            params={
                "name": name,
                "arguments": arguments
            }
        )
        response = await self.send_request(request)
        return response.get("result", {})
    
    async def send_request(self, request: MCPRequest) -> Dict[str, Any]:
        """Send a request to the MCP server"""
        if self.transport:
            return await self.transport.send(request.dict())
        elif self.server_url:
            # HTTP transport implementation would go here
            # For now, return a placeholder
            return {"result": None, "error": "HTTP transport not implemented"}
        else:
            raise ValueError("No transport or server URL configured")
    
    def _next_id(self) -> str:
        """Generate next request ID"""
        self.request_id_counter += 1
        return str(self.request_id_counter)


