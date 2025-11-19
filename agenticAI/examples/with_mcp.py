"""
Example using MCP (Model Context Protocol) support.
"""
import asyncio
from pathlib import Path
from agenticAI import CodingAgent
from agenticAI.mcp import MCPClient


async def example_with_mcp():
    """Example: Using agent with MCP client"""
    print("=" * 60)
    print("Example: Agent with MCP Support")
    print("=" * 60)
    
    workspace = Path("./example_workspace")
    agent = CodingAgent(workspace_path=str(workspace))
    
    # Create an MCP client (example - you'd connect to actual MCP server)
    # mcp_client = MCPClient(server_url="http://localhost:8000")
    # await agent.add_mcp_client("example_server", mcp_client)
    
    # Now agent can use MCP resources and tools
    task = """
    Use available tools to create a simple REST API server in Python using Flask
    """
    
    result = await agent.run(task, max_iterations=15)
    print(f"\n✅ Task completed: {result['success']}")


if __name__ == "__main__":
    asyncio.run(example_with_mcp())


