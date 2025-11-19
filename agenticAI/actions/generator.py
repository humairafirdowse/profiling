"""
Action generation from LLM responses and tool schemas.
"""
import json
from typing import Any, Dict, List, Optional
from .action import Action, ActionType
from ..llm.base import LLMResponse


class ActionGenerator:
    """Generates actions from LLM responses"""
    
    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
    
    def generate_from_llm_response(self, response: LLMResponse) -> List[Action]:
        """
        Generate actions from an LLM response.
        Handles both function calls and text responses.
        """
        actions = []
        
        # Check for function calls (OpenAI format)
        if response.metadata and "function_call" in response.metadata:
            func_call = response.metadata["function_call"]
            actions.append(Action(
                type=ActionType.TOOL_CALL,
                name=func_call["name"],
                parameters=self._parse_function_args(func_call.get("arguments", "{}")),
                description=f"Call tool: {func_call['name']}"
            ))
        
        # If no function call but there's content, might need LLM generation
        elif response.content:
            # Try to parse action from content (JSON format)
            parsed_action = self._parse_action_from_content(response.content)
            if parsed_action:
                actions.append(parsed_action)
            else:
                # Default: treat as LLM generation action
                actions.append(Action(
                    type=ActionType.LLM_GENERATE,
                    name="generate",
                    parameters={"content": response.content},
                    description="LLM generated content"
                ))
        
        return actions
    
    def _parse_function_args(self, args_str: str) -> Dict[str, Any]:
        """Parse function arguments string (JSON)"""
        try:
            return json.loads(args_str)
        except json.JSONDecodeError:
            return {}
    
    def _parse_action_from_content(self, content: str) -> Optional[Action]:
        """Try to parse an action from LLM content (if it's in JSON format)"""
        try:
            # Look for JSON in the content
            content = content.strip()
            if content.startswith("{") or content.startswith("["):
                data = json.loads(content)
                if isinstance(data, dict) and "type" in data:
                    return Action(**data)
        except (json.JSONDecodeError, Exception):
            pass
        return None
    
    def generate_tool_action(self, tool_name: str, **kwargs) -> Action:
        """Generate a tool call action"""
        return Action(
            type=ActionType.TOOL_CALL,
            name=tool_name,
            parameters=kwargs,
            description=f"Call tool: {tool_name}"
        )
    
    def generate_mcp_action(self, method: str, params: Dict[str, Any]) -> Action:
        """Generate an MCP action"""
        return Action(
            type=ActionType.MCP_REQUEST,
            name=method,
            parameters=params,
            description=f"MCP request: {method}"
        )


