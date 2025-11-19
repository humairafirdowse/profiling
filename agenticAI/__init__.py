"""
Coding Agent - An AI-powered coding assistant with tool support, LLM integration,
MCP protocol support, and action generation.
"""
from .agent import CodingAgent
from .config import config, Config
from .tools.base import Tool, ToolRegistry
from .llm.factory import create_llm_provider
from .actions.action import Action, ActionType, ActionResult

__version__ = "1.0.0"

__all__ = [
    "CodingAgent",
    "config",
    "Config",
    "Tool",
    "ToolRegistry",
    "create_llm_provider",
    "Action",
    "ActionType",
    "ActionResult",
]


