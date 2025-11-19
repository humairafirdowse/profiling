"""
OpenAI LLM provider implementation.
"""
from typing import Any, Dict, List, Optional
import openai
from .base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""
    
    def __init__(self, config):
        super().__init__(config)
        self.client = openai.OpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        self.model = config.model
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                      tools: Optional[List[Dict[str, Any]]] = None,
                      tool_choice: Optional[str] = None) -> LLMResponse:
        """Generate response using OpenAI API"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        # Format tools for OpenAI function calling
        functions = None
        function_call = None
        
        if tools:
            functions = self.format_tools_for_llm(tools)
            if tool_choice == "none":
                function_call = "none"
            elif tool_choice and tool_choice != "auto":
                function_call = {"name": tool_choice}
            else:
                function_call = "auto"
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                functions=functions,
                function_call=function_call
            )
            message = response.choices[0].message
            content = message.content or ""
            
            # Handle function calls
            function_call_data = None
            if message.function_call:
                function_call_data = {
                    "name": message.function_call.name,
                    "arguments": message.function_call.arguments
                }
            
            return LLMResponse(
                content=content,
                model=self.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                finish_reason=response.choices[0].finish_reason,
                metadata={"function_call": function_call_data} if function_call_data else None
            )
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None,
                            tools: Optional[List[Dict[str, Any]]] = None):
        """Generate streaming response"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        functions = None
        if tools:
            functions = self.format_tools_for_llm(tools)
        
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            functions=functions,
            stream=True
        )
        
        async def stream_generator():
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        return stream_generator()
    
    def format_tools_for_llm(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format tools for OpenAI function calling format"""
        formatted = []
        for tool in tools:
            formatted.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            })
        return formatted


