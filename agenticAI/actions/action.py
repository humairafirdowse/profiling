"""
Action definitions and types.
"""
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Types of actions the agent can take"""
    TOOL_CALL = "tool_call"
    LLM_GENERATE = "llm_generate"
    MCP_REQUEST = "mcp_request"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    FINISH = "finish"


class Action(BaseModel):
    """Represents an action to be executed"""
    type: ActionType
    name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    """Result of executing an action"""
    success: bool
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def success_result(cls, result: Any, metadata: Optional[Dict[str, Any]] = None):
        """Create a successful result"""
        return cls(
            success=True,
            result=result,
            metadata=metadata or {}
        )
    
    @classmethod
    def error_result(cls, error: str, metadata: Optional[Dict[str, Any]] = None):
        """Create an error result"""
        return cls(
            success=False,
            error=error,
            metadata=metadata or {}
        )


