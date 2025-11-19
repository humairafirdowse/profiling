"""
Basic usage example of the coding agent.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path if needed (for development)
# This allows running the script directly without installing the package
# We need the parent of agenticAI directory in the path so Python can find agenticAI as a module
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from agenticAI import CodingAgent


async def example_basic_task():
    """Example: Basic file operations"""
    print("=" * 60)
    print("Example 1: Basic File Operations")
    print("=" * 60)
    
    # Create agent with workspace
    workspace = Path("./example_workspace")
    agent = CodingAgent(workspace_path=str(workspace))
    
    # Task: Create a simple Python file
    task = """
    Create a Python file called 'hello.py' with a function that prints 'Hello, World!'
    """
    
    result = await agent.run(task, max_iterations=5)
    print(f"\n[SUCCESS] Task completed: {result['success']}")
    print(f"   Iterations: {result['iterations']}")


async def example_code_analysis():
    """Example: Code analysis and modification"""
    print("\n" + "=" * 60)
    print("Example 2: Code Analysis")
    print("=" * 60)
    
    workspace = Path("./example_workspace")
    agent = CodingAgent(workspace_path=str(workspace))
    
    # First, create a file to analyze
    task1 = """
    Create a Python file 'calculator.py' with a Calculator class that has:
    - add(a, b) method
    - subtract(a, b) method
    - multiply(a, b) method
    - divide(a, b) method
    """
    
    await agent.run(task1, max_iterations=5)
    
    # Then analyze it
    task2 = """
    Analyze the calculator.py file and tell me what functions it contains
    """
    
    result = await agent.run(task2, max_iterations=3)
    print(f"\n[SUCCESS] Analysis completed: {result['success']}")


async def example_search_and_edit():
    """Example: Search and edit code"""
    print("\n" + "=" * 60)
    print("Example 3: Search and Edit")
    print("=" * 60)
    
    workspace = Path("./example_workspace")
    agent = CodingAgent(workspace_path=str(workspace))
    
    task = """
    Search for all Python files in the workspace that contain 'def' and 
    add a docstring to the first function you find
    """
    
    result = await agent.run(task, max_iterations=10)
    print(f"\n[SUCCESS] Search and edit completed: {result['success']}")


async def main():
    """Run all examples"""
    # Make sure API key is set
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("WARNING: No API key found. Set OPENAI_API_KEY or GEMINI_API_KEY")
        print("   You can create a .env file with: OPENAI_API_KEY=your_key_here")
        return
    
    await example_basic_task()
    await example_code_analysis()
    await example_search_and_edit()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


