"""
MCP Protocol definitions.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MCPRequest(BaseModel):
    """MCP request message"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)


class MCPResponse(BaseModel):
    """MCP response message"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPResource(BaseModel):
    """MCP resource definition"""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class MCPTool(BaseModel):
    """MCP tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any] = Field(default_factory=dict)


class MCPPrompt(BaseModel):
    """MCP prompt template"""
    name: str
    description: Optional[str] = None
    arguments: List[Dict[str, Any]] = Field(default_factory=list)


