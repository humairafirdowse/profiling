"""
Base classes for tool system.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
import inspect


class ToolParameter(BaseModel):
    """Parameter definition for a tool"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class Tool(BaseModel, ABC):
    """Base class for all tools"""
    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.
        Returns a dictionary with 'success', 'result', and optionally 'error'.
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for this tool"""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    
    @classmethod
    def from_function(cls, func, name: Optional[str] = None, description: Optional[str] = None):
        """Create a Tool from a Python function"""
        sig = inspect.signature(func)
        params = []
        
        for param_name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list or param.annotation == List:
                    param_type = "array"
            
            params.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=param.__doc__ or f"Parameter {param_name}",
                required=param.default == inspect.Parameter.empty,
                default=param.default if param.default != inspect.Parameter.empty else None
            ))
        
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or f"Tool: {tool_name}"
        
        class FunctionTool(Tool):
            name = tool_name
            description = tool_description
            parameters = params
            
            async def execute(self, **kwargs):
                try:
                    result = await func(**kwargs) if inspect.iscoroutinefunction(func) else func(**kwargs)
                    return {"success": True, "result": result}
                except Exception as e:
                    return {"success": False, "error": str(e)}
        
        return FunctionTool()


class ToolRegistry:
    """Registry for managing all available tools"""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        """Register a tool"""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their schemas"""
        return [tool.get_schema() for tool in self._tools.values()]
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all tools (for LLM function calling)"""
        return self.list_tools()
    
    async def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name"""
        tool = self.get(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' not found"}
        
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {str(e)}"}


