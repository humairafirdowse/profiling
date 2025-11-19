"""
Main coding agent orchestrator.
Coordinates LLM, tools, actions, and MCP to accomplish coding tasks.
"""
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path

from .config import config
from .tools.base import ToolRegistry
from .tools.file_tools import FileTools
from .tools.code_tools import CodeTools
from .tools.search_tools import SearchTools
from .llm.factory import create_llm_provider
from .llm.base import LLMProvider
from .actions.generator import ActionGenerator
from .actions.executor import ActionExecutor
from .actions.action import Action, ActionType, ActionResult
from .mcp.client import MCPClient


class CodingAgent:
    """
    Main coding agent that orchestrates tools, LLM, and actions.
    
    Architecture:
    1. User provides a task/query
    2. Agent uses LLM to generate actions (tool calls, etc.)
    3. Actions are executed via ActionExecutor
    4. Results are fed back to LLM for next steps
    5. Process repeats until task is complete
    """
    
    def __init__(self, workspace_path: Optional[str] = None, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize the coding agent.
        
        Args:
            workspace_path: Path to workspace directory
            llm_provider: Optional LLM provider (uses config if not provided)
        """
        self.workspace_path = Path(workspace_path or config.agent.workspace_path)
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.tool_registry = ToolRegistry()
        self.llm_provider = llm_provider or create_llm_provider()
        self.action_generator = ActionGenerator(self.tool_registry)
        self.action_executor = ActionExecutor(self.tool_registry, self.llm_provider)
        
        # Register all tools
        self._register_tools()
        
        # MCP support
        self.mcp_clients: Dict[str, MCPClient] = {}
        
        # Conversation history
        self.conversation_history: List[Dict[str, str]] = []
    
    def _register_tools(self):
        """Register all available tools"""
        FileTools.register_all(self.tool_registry, str(self.workspace_path))
        CodeTools.register_all(self.tool_registry, str(self.workspace_path))
        SearchTools.register_all(self.tool_registry, str(self.workspace_path))
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        tool_schemas = self.tool_registry.get_tool_schemas()
        tools_description = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in tool_schemas
        ])
        
        return f"""You are a coding agent with access to the following tools:

{tools_description}

You can:
1. Read and write files
2. Search and analyze code
3. Edit code files
4. Execute various coding tasks

When given a task:
1. Break it down into steps
2. Use the appropriate tools to accomplish each step
3. Verify your work
4. Provide clear feedback on what was done

Always be careful with file operations and verify before making destructive changes."""

    async def run(self, task: str, max_iterations: Optional[int] = None) -> Dict[str, Any]:
        """
        Run the agent on a task.
        
        Args:
            task: The task description
            max_iterations: Maximum number of iterations (defaults to config)
        
        Returns:
            Dictionary with execution results
        """
        max_iterations = max_iterations or config.agent.max_iterations
        iterations = 0
        results = []
        
        if config.agent.verbose:
            print(f"🤖 Agent starting task: {task}")
            print(f"📁 Workspace: {self.workspace_path}")
            print(f"🔧 Available tools: {len(self.tool_registry.list_tools())}")
            print("-" * 60)
        
        # Add initial user message
        self.conversation_history.append({"role": "user", "content": task})
        
        while iterations < max_iterations:
            iterations += 1
            
            if config.agent.verbose:
                print(f"\n[Iteration {iterations}/{max_iterations}]")
            
            # Generate response from LLM
            try:
                # Build context from conversation history
                context = self._build_context()
                
                response = await self.llm_provider.generate(
                    prompt=task if iterations == 1 else context,
                    system_prompt=self.get_system_prompt(),
                    tools=self.tool_registry.get_tool_schemas(),
                    tool_choice="auto"
                )
                
                # Add assistant response to history
                self.conversation_history.append({"role": "assistant", "content": response.content})
                
                # Generate actions from response
                actions = self.action_generator.generate_from_llm_response(response)
                
                if not actions:
                    if config.agent.verbose:
                        print("✅ Task completed (no actions generated)")
                    break
                
                # Execute actions
                action_results = []
                for action in actions:
                    if config.agent.verbose:
                        print(f"  🔨 Executing: {action.type.value} - {action.name}")
                    
                    result = await self.action_executor.execute(action, str(self.workspace_path))
                    action_results.append({
                        "action": action.dict(),
                        "result": result.dict()
                    })
                    
                    if config.agent.verbose:
                        if result.success:
                            print(f"    ✅ Success")
                        else:
                            print(f"    ❌ Error: {result.error}")
                    
                    # Check for finish action
                    if action.type == ActionType.FINISH:
                        if config.agent.verbose:
                            print("✅ Agent finished")
                        return {
                            "success": True,
                            "iterations": iterations,
                            "results": results + action_results,
                            "final_message": response.content
                        }
                
                results.extend(action_results)
                
                # Update context with results for next iteration
                task = self._format_results_for_llm(action_results)
                
            except Exception as e:
                error_msg = f"Error in iteration {iterations}: {str(e)}"
                if config.agent.verbose:
                    print(f"❌ {error_msg}")
                results.append({
                    "error": error_msg,
                    "iteration": iterations
                })
                break
        
        return {
            "success": iterations < max_iterations,
            "iterations": iterations,
            "results": results,
            "message": "Reached max iterations" if iterations >= max_iterations else "Task completed"
        }
    
    def _build_context(self) -> str:
        """Build context from conversation history and recent results"""
        context_parts = []
        
        # Add recent conversation
        for msg in self.conversation_history[-5:]:  # Last 5 messages
            role = msg["role"]
            content = msg["content"]
            context_parts.append(f"{role.upper()}: {content}")
        
        return "\n\n".join(context_parts)
    
    def _format_results_for_llm(self, results: List[Dict[str, Any]]) -> str:
        """Format action results for LLM context"""
        formatted = []
        for result in results:
            action = result["action"]
            result_data = result["result"]
            
            if result_data["success"]:
                formatted.append(
                    f"Action '{action['name']}' completed successfully. "
                    f"Result: {str(result_data.get('result', 'N/A'))[:200]}"
                )
            else:
                formatted.append(
                    f"Action '{action['name']}' failed: {result_data.get('error', 'Unknown error')}"
                )
        
        return "\n".join(formatted)
    
    async def add_mcp_client(self, name: str, client: MCPClient):
        """Add an MCP client to the agent"""
        self.mcp_clients[name] = client
        await client.initialize()
        
        # Register MCP tools with tool registry
        mcp_tools = await client.list_tools()
        # Convert MCP tools to agent tools (simplified)
        # In production, you'd create proper Tool instances
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all registered tools"""
        return self.tool_registry.get_tool_schemas()
    
    def list_tools(self) -> List[str]:
        """List all available tool names"""
        return [tool["name"] for tool in self.tool_registry.list_tools()]


async def main():
    """Example usage"""
    agent = CodingAgent(workspace_path="./workspace")
    
    # Example task
    task = "Create a simple Python hello world script"
    
    result = await agent.run(task)
    print("\n" + "=" * 60)
    print("Final Result:")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())


