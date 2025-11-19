"""
Configuration management for the coding agent.
"""
import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class LLMConfig(BaseModel):
    """LLM provider configuration"""
    provider: str = Field(default="openai", description="LLM provider: 'openai' or 'gemini'")
    api_key: Optional[str] = Field(default=None, description="API key for the LLM provider")
    model: str = Field(default="gpt-4", description="Model name to use")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    max_tokens: int = Field(default=2000, description="Maximum tokens to generate")
    base_url: Optional[str] = Field(default=None, description="Base URL for API (for custom endpoints)")


class AgentConfig(BaseModel):
    """Main agent configuration"""
    workspace_path: str = Field(default=".", description="Workspace directory path")
    max_iterations: int = Field(default=50, description="Maximum agent iterations")
    enable_mcp: bool = Field(default=True, description="Enable MCP protocol support")
    tool_timeout: int = Field(default=30, description="Tool execution timeout in seconds")
    verbose: bool = Field(default=True, description="Enable verbose logging")


class Config:
    """Global configuration manager"""
    
    def __init__(self):
        # LLM Configuration
        self.llm = LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            api_key=os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY"),
            model=os.getenv("LLM_MODEL", "gpt-4"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        # Agent Configuration
        self.agent = AgentConfig(
            workspace_path=os.getenv("WORKSPACE_PATH", "."),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "50")),
            enable_mcp=os.getenv("ENABLE_MCP", "true").lower() == "true",
            tool_timeout=int(os.getenv("TOOL_TIMEOUT", "30")),
            verbose=os.getenv("VERBOSE", "true").lower() == "true"
        )
    
    def validate(self):
        """Validate configuration"""
        if not self.llm.api_key:
            raise ValueError("LLM API key is required. Set OPENAI_API_KEY or GEMINI_API_KEY")
        if self.llm.provider not in ["openai", "gemini"]:
            raise ValueError(f"Unsupported LLM provider: {self.llm.provider}")


# Global config instance
config = Config()


