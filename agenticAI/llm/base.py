"""
Base classes for LLM providers.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Response from LLM"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Base class for LLM providers"""
    
    def __init__(self, config):
        self.config = config
    
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                      tools: Optional[List[Dict[str, Any]]] = None,
                      tool_choice: Optional[str] = None) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: System/instruction prompt
            tools: List of tool schemas for function calling
            tool_choice: Tool choice mode ('auto', 'none', or tool name)
        
        Returns:
            LLMResponse object
        """
        pass
    
    @abstractmethod
    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None,
                            tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        """
        Generate a streaming response from the LLM.
        Returns an async generator.
        """
        pass
    
    def format_tools_for_llm(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format tool schemas for the specific LLM provider"""
        return tools


