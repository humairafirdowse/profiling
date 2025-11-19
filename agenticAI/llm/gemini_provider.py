"""
Google Gemini LLM provider implementation.
"""
from typing import Any, Dict, List, Optional
import google.generativeai as genai
from .base import LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    """Google Gemini API provider"""
    
    def __init__(self, config):
        super().__init__(config)
        genai.configure(api_key=config.api_key)
        self.model_name = config.model
        self.model = genai.GenerativeModel(self.model_name)
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                      tools: Optional[List[Dict[str, Any]]] = None,
                      tool_choice: Optional[str] = None) -> LLMResponse:
        """Generate response using Gemini API"""
        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Note: Gemini's function calling support may vary by model version
        # This is a simplified implementation
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens
            )
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            content = response.text if response.text else ""
            
            return LLMResponse(
                content=content,
                model=self.model_name,
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else None,
                    "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else None,
                    "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None
                },
                finish_reason=response.candidates[0].finish_reason.name if response.candidates else None,
                metadata=None
            )
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None,
                            tools: Optional[List[Dict[str, Any]]] = None):
        """Generate streaming response"""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        generation_config = genai.types.GenerationConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens
        )
        
        response = self.model.generate_content(
            full_prompt,
            generation_config=generation_config,
            stream=True
        )
        
        async def stream_generator():
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        
        return stream_generator()
    
    def format_tools_for_llm(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format tools for Gemini (may need adjustment based on Gemini's function calling API)"""
        # Gemini's function calling format may differ
        # This is a placeholder - adjust based on actual Gemini API
        return tools


