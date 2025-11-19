"""
MCP Server implementation (for exposing agent capabilities).
"""
from typing import Any, Dict, List, Optional
from .protocol import MCPRequest, MCPResponse, MCPResource, MCPTool


class MCPServer:
    """MCP Server for exposing agent capabilities"""
    
    def __init__(self, tool_registry=None):
        self.tool_registry = tool_registry
        self.resources: List[MCPResource] = []
        self.tools: List[MCPTool] = []
    
    def register_resource(self, resource: MCPResource):
        """Register a resource"""
        self.resources.append(resource)
    
    def register_tool(self, tool: MCPTool):
        """Register a tool"""
        self.tools.append(tool)
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an incoming MCP request"""
        method = request.method
        
        if method == "initialize":
            return MCPResponse(
                id=request.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "resources": {},
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "coding-agent",
                        "version": "1.0.0"
                    }
                }
            )
        elif method == "resources/list":
            return MCPResponse(
                id=request.id,
                result={"resources": [r.dict() for r in self.resources]}
            )
        elif method == "tools/list":
            return MCPResponse(
                id=request.id,
                result={"tools": [t.dict() for t in self.tools]}
            )
        elif method == "tools/call":
            return await self._handle_tool_call(request)
        else:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            )
    
    async def _handle_tool_call(self, request: MCPRequest) -> MCPResponse:
        """Handle tool call request"""
        params = request.params
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not self.tool_registry:
            return MCPResponse(
                id=request.id,
                error={"code": -32603, "message": "Tool registry not available"}
            )
        
        result = await self.tool_registry.execute_tool(tool_name, **arguments)
        
        if result.get("success"):
            return MCPResponse(
                id=request.id,
                result={"content": [{"type": "text", "text": str(result.get("result"))}]}
            )
        else:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32603,
                    "message": result.get("error", "Tool execution failed")
                }
            )


