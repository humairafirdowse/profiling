# Quick Start Guide

Get started with the Coding Agent in 5 minutes!

## Prerequisites

- Python 3.8+
- OpenAI API key OR Gemini API key

## Installation

1. **Clone or navigate to the project:**
```bash
cd agenticAI
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**

Create a `.env` file in the `agenticAI` directory:

```env
# For OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4

# OR for Gemini
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=your-key-here
# LLM_MODEL=gemini-pro

# Optional settings
WORKSPACE_PATH=./workspace
MAX_ITERATIONS=50
VERBOSE=true
```

## Basic Usage

### Example 1: Simple File Creation

```python
import asyncio
from agenticAI import CodingAgent

async def main():
    # Create agent
    agent = CodingAgent(workspace_path="./my_workspace")
    
    # Give it a task
    task = "Create a Python file called hello.py that prints 'Hello, World!'"
    
    # Run the agent
    result = await agent.run(task)
    
    # Check results
    print(f"Success: {result['success']}")
    print(f"Iterations: {result['iterations']}")

asyncio.run(main())
```

### Example 2: Code Analysis

```python
import asyncio
from agenticAI import CodingAgent

async def main():
    agent = CodingAgent(workspace_path="./my_workspace")
    
    # First, create a file
    await agent.run("Create a Python file with a Calculator class")
    
    # Then analyze it
    result = await agent.run("Analyze all Python files in the workspace")
    print(result)

asyncio.run(main())
```

### Example 3: Search and Edit

```python
import asyncio
from agenticAI import CodingAgent

async def main():
    agent = CodingAgent(workspace_path="./my_workspace")
    
    task = """
    Search for all Python files containing 'def' and add a docstring 
    to the first function you find
    """
    
    result = await agent.run(task, max_iterations=10)
    print(result)

asyncio.run(main())
```

## Available Tools

The agent has access to these tools automatically:

### File Tools
- `read_file`: Read file contents
- `write_file`: Write/create file
- `edit_file`: Edit file by replacing text
- `list_directory`: List directory contents
- `delete_file`: Delete a file

### Code Tools
- `search_code`: Search for code patterns (regex)
- `analyze_code`: Analyze code structure

### Search Tools
- `semantic_search`: Semantic code search
- `find_files`: Find files by glob pattern

## Running Examples

```bash
# Basic examples
python examples/basic_usage.py

# MCP example
python examples/with_mcp.py
```

## Understanding the Output

When `VERBOSE=true`, you'll see:
- 🤖 Agent status messages
- 📁 Workspace information
- 🔧 Available tools
- 🔨 Action execution
- ✅ Success indicators
- ❌ Error messages

## Common Issues

### "API key not found"
- Make sure your `.env` file exists
- Check that the API key variable name matches your provider
- Verify the key is correct

### "Tool execution failed"
- Check workspace path exists
- Verify file permissions
- Check tool parameters are correct

### "Max iterations reached"
- The task may be too complex
- Try breaking it into smaller tasks
- Increase `MAX_ITERATIONS` in config

## Next Steps

1. **Read the Architecture**: See `ARCHITECTURE.md` for detailed design
2. **Explore Examples**: Check `examples/` directory
3. **Add Custom Tools**: See `README.md` for tool creation guide
4. **Integrate MCP**: Connect to MCP servers for extended capabilities

## Tips

- Start with simple tasks to understand the agent's behavior
- Use verbose mode to see what the agent is doing
- Break complex tasks into smaller steps
- Check the workspace directory to see what was created
- Review conversation history for debugging

## Getting Help

- Check `README.md` for full documentation
- Review `ARCHITECTURE.md` for system design
- Look at examples in `examples/` directory
- Check tool schemas: `agent.get_tool_schemas()`

Happy coding! 🚀


