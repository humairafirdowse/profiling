# Coding Agent

An AI-powered coding agent with comprehensive tool support, LLM integration (OpenAI/Gemini), MCP protocol support, and intelligent action generation.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Coding Agent                         │
│                  (agent.py)                             │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   LLM Layer  │  │  Tool System │  │  MCP Support │
│              │  │              │  │              │
│ - OpenAI     │  │ - FileTools  │  │ - Client     │
│ - Gemini     │  │ - CodeTools  │  │ - Server     │
│ - Factory    │  │ - SearchTools│  │ - Protocol   │
│              │  │ - Profiling  │  │              │
│              │  │   Tools      │  │              │
│              │  │   * nsys     │  │              │
│              │  │   * SQLite    │  │              │
│              │  │   * Analysis  │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │
        └─────────┬───────┘
                  ▼
         ┌─────────────────┐
         │ Action System   │
         │                 │
         │ - Generator     │
         │ - Executor      │
         └─────────────────┘
```

## Components

### 1. **Agent Orchestrator** (`agent.py`)
- Main entry point for the coding agent
- Coordinates LLM, tools, and actions
- Manages conversation history and iteration loops

### 2. **Tool System** (`tools/`)
- **FileTools**: Read, write, edit, list, delete files
- **CodeTools**: Search code, analyze structure
- **SearchTools**: Semantic search, find files
- **ProfilingTools**: GPU profiling with nsys, SQLite analysis, bottleneck detection
  - `profile_with_nsys`: Run scripts with NVIDIA Nsight Systems profiling
  - `analyze_nsys_sqlite`: Analyze SQLite databases for computation/communication bottlenecks
- Extensible tool registry system

### 3. **LLM Integration** (`llm/`)
- **OpenAIProvider**: OpenAI API integration with function calling
- **GeminiProvider**: Google Gemini API integration
- **Factory**: Creates appropriate provider based on config

### 4. **Action System** (`actions/`)
- **ActionGenerator**: Converts LLM responses to executable actions
- **ActionExecutor**: Executes actions (tool calls, LLM generation, MCP requests)
- Supports multiple action types (tool_call, llm_generate, mcp_request, etc.)

### 5. **MCP Support** (`mcp/`)
- **MCPClient**: Client for connecting to MCP servers
- **MCPServer**: Server for exposing agent capabilities via MCP
- **Protocol**: MCP protocol definitions (requests, responses, resources, tools)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. **For GPU Profiling (optional):** Install NVIDIA Nsight Systems:
   - Download from: https://developer.nvidia.com/nsight-systems
   - Or install via package manager (e.g., `apt install nsight-systems` on Ubuntu)
   - Verify installation: `nsys --version`

3. Set up environment variables (create `.env` file):
```env
# LLM Configuration
LLM_PROVIDER=openai  # or "gemini"
OPENAI_API_KEY=your_openai_key_here
# OR
GEMINI_API_KEY=your_gemini_key_here

# Agent Configuration
WORKSPACE_PATH=./workspace
MAX_ITERATIONS=50
ENABLE_MCP=true
VERBOSE=true
```

## Usage

### Basic Usage

```python
import asyncio
from agenticAI import CodingAgent

async def main():
    # Create agent
    agent = CodingAgent(workspace_path="./my_workspace")
    
    # Run a task
    task = "Create a Python file with a function that calculates fibonacci numbers"
    result = await agent.run(task)
    
    print(f"Success: {result['success']}")
    print(f"Iterations: {result['iterations']}")

asyncio.run(main())
```

### Advanced Usage with Custom Tools

```python
from agenticAI import CodingAgent, Tool, ToolParameter
from agenticAI.tools.base import ToolRegistry

# Create custom tool
class MyCustomTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Does something custom",
            parameters=[
                ToolParameter(name="param1", type="string", description="A parameter")
            ]
        )
    
    async def execute(self, param1: str, **kwargs):
        # Your tool logic
        return {"success": True, "result": f"Processed: {param1}"}

# Register tool
agent = CodingAgent()
agent.tool_registry.register(MyCustomTool())

# Use agent
result = await agent.run("Use my_tool with param1='test'")
```

### Using MCP

```python
from agenticAI import CodingAgent
from agenticAI.mcp import MCPClient

agent = CodingAgent()

# Connect to MCP server
mcp_client = MCPClient(server_url="http://localhost:8000")
await agent.add_mcp_client("my_server", mcp_client)

# Agent can now use MCP resources and tools
result = await agent.run("Use MCP tools to accomplish task")
```

## Available Tools

### File Operations
- `read_file`: Read file contents
- `write_file`: Write/create file
- `edit_file`: Edit file by replacing text
- `list_directory`: List directory contents
- `delete_file`: Delete a file

### Code Operations
- `search_code`: Search for code patterns (regex)
- `analyze_code`: Analyze code structure (functions, classes, imports)

### Search Operations
- `semantic_search`: Semantic code search
- `find_files`: Find files by glob pattern

### Profiling Operations
- `profile_with_nsys`: Run a Python script with nsys profiling and convert to SQLite
- `analyze_nsys_sqlite`: Analyze nsys SQLite database for bottlenecks and optimization opportunities

`profile_with_nsys` launcher options:
- `launcher`: choose `python`, `torchrun`, or provide a full custom command
- `nproc_per_node`: world size for `torchrun` (defaults to 1)
- `launcher_args`: extra launcher flags (e.g., `--standalone`)
- `cuda_visible_devices`: pin profiling to specific GPUs (e.g., `0,1`)
- `env_vars`: JSON string of additional environment variables (e.g., `{"MASTER_PORT": "29999"}`)

## Configuration

See `config.py` for all configuration options. Key settings:

- **LLM Provider**: Choose OpenAI or Gemini
- **Model**: Specific model to use
- **Temperature**: Generation temperature
- **Max Tokens**: Maximum tokens per generation
- **Workspace Path**: Default workspace directory
- **Max Iterations**: Maximum agent iterations per task
- **Tool Timeout**: Timeout for tool execution

## Architecture Details

### How It Works

1. **User provides task** → Agent receives task description
2. **LLM generates actions** → Agent uses LLM with tool schemas to generate actions
3. **Actions executed** → ActionExecutor runs tool calls, MCP requests, etc.
4. **Results fed back** → Results become context for next LLM call
5. **Iterate** → Process repeats until task complete or max iterations

### Tool Execution Flow

```
LLM Response → ActionGenerator → Actions → ActionExecutor → Tool Registry → Tool.execute()
                                                                                ↓
                                                                          Results
```

### GPU Profiling Workflow

The profiling tools enable end-to-end GPU performance analysis:

```
1. Profile Script
   │
   ├─→ Run script with nsys: profile_with_nsys(script_path)
   │   │
   │   ├─→ Execute: nsys profile --output script.nsys-rep torchrun --nproc_per_node=2 script.py
   │   └─→ Convert: nsys export --type sqlite --output script.sqlite script.nsys-rep
   │
   ▼
2. Analyze Database
   │
   └─→ Analyze SQLite: analyze_nsys_sqlite(sqlite_db_path)
       │
       ├─→ Query CUDA kernels (computation bottlenecks)
       ├─→ Query NCCL operations (communication bottlenecks)
       ├─→ Analyze overlap between compute and communication
       └─→ Generate optimization suggestions
```

**Example Usage:**
```python
# Profile a distributed PyTorch script
task = """
Use profile_with_nsys to profile matmul_allreduce.py with:
  launcher='torchrun'
  nproc_per_node=2
  launcher_args='--standalone'
  cuda_visible_devices='0,1'
  nsys_args='--trace=cuda,nvtx,osrt --force-overwrite=true'
Then run analyze_nsys_sqlite on the generated SQLite DB to find
compute/communication bottlenecks and overlap opportunities.
"""

result = await agent.run(task)
# Agent will:
# 1. Run nsys profiling
# 2. Convert to SQLite
# 3. Analyze for bottlenecks
# 4. Provide optimization suggestions
```

### MCP Integration

The agent can:
- Connect to MCP servers as a client
- Expose its capabilities as an MCP server
- Use MCP resources and tools in its workflow

## Examples

See `examples/` directory for:
- `basic_usage.py`: Basic file operations
- `with_mcp.py`: MCP integration example
- `profile_matmul.py`: GPU profiling example with nsys and bottleneck analysis

## Development

### Adding New Tools

1. Create a tool class inheriting from `Tool`
2. Implement `execute()` method
3. Register with `ToolRegistry`

### Adding New LLM Providers

1. Create provider class inheriting from `LLMProvider`
2. Implement `generate()` and `generate_stream()` methods
3. Add to factory in `llm/factory.py`

## License

MIT


