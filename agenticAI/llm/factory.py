"""
Factory for creating LLM providers.
"""
from typing import Optional
from ..config import config
from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider


def create_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """
    Create an LLM provider based on configuration.
    
    Args:
        provider_name: Override provider name from config
    
    Returns:
        LLMProvider instance
    """
    provider = provider_name or config.llm.provider
    
    if provider == "openai":
        return OpenAIProvider(config.llm)
    elif provider == "gemini":
        return GeminiProvider(config.llm)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

