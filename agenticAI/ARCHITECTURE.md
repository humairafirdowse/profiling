# Architecture Overview

This document explains the architecture of the Coding Agent system.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Coding Agent                            │
│                    (agent.py)                               │
│                                                             │
│  - Orchestrates all components                             │
│  - Manages conversation history                            │
│  - Controls iteration loop                                 │
│  - Coordinates LLM, tools, and actions                     │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  LLM Layer   │    │ Tool System  │    │  MCP Layer   │
│              │    │              │    │              │
│ - OpenAI     │    │ - FileTools  │    │ - Client     │
│ - Gemini     │    │ - CodeTools  │    │ - Server     │
│ - Factory    │    │ - SearchTools│    │ - Protocol   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │
        └─────────┬──────┘
                      │
                      ▼
            ┌─────────────────┐
            │  Action System   │
            │                  │
            │ - Generator      │
            │ - Executor       │
            └─────────────────┘
```

## Component Details

### 1. Agent Orchestrator (`agent.py`)

**Responsibilities:**
- Main entry point for the coding agent
- Manages the agent's execution loop
- Coordinates between LLM, tools, and actions
- Maintains conversation history
- Handles iteration control

**Key Methods:**
- `run(task, max_iterations)`: Execute a task
- `get_system_prompt()`: Generate system prompt with tool descriptions
- `_build_context()`: Build context from conversation history
- `add_mcp_client()`: Register MCP clients

**Flow:**
1. Receive task from user
2. Generate LLM response with tool schemas
3. Convert LLM response to actions
4. Execute actions
5. Feed results back to LLM
6. Repeat until task complete

### 2. Tool System (`tools/`)

**Architecture:**
```
ToolRegistry
    ├── FileTools
    │   ├── ReadFileTool
    │   ├── WriteFileTool
    │   ├── EditFileTool
    │   ├── ListDirectoryTool
    │   └── DeleteFileTool
    ├── CodeTools
    │   ├── SearchCodeTool
    │   └── AnalyzeCodeTool
    └── SearchTools
        ├── SemanticSearchTool
        └── FindFilesTool
```

**Base Classes:**
- `Tool`: Abstract base class for all tools
- `ToolParameter`: Parameter definition
- `ToolRegistry`: Manages tool registration and execution

**Tool Interface:**
```python
class Tool:
    name: str
    description: str
    parameters: List[ToolParameter]
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        # Returns {"success": bool, "result": Any, "error": str}
        pass
```

**Tool Registration:**
- Tools are registered with the ToolRegistry
- Each tool gets a JSON schema for LLM function calling
- Tools can be discovered and executed dynamically

### 3. LLM Integration (`llm/`)

**Providers:**
- `OpenAIProvider`: OpenAI API with function calling
- `GeminiProvider`: Google Gemini API
- `LLMProvider`: Abstract base class

**Features:**
- Function calling support (tool schemas)
- Streaming support
- Configurable temperature, max tokens, etc.
- Provider factory pattern

**LLM Response Format:**
```python
LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    metadata: Dict[str, Any]  # May contain function_call
```

### 4. Action System (`actions/`)

**Components:**
- `Action`: Represents an action to execute
- `ActionType`: Types of actions (tool_call, llm_generate, mcp_request, etc.)
- `ActionGenerator`: Converts LLM responses to actions
- `ActionExecutor`: Executes actions

**Action Types:**
- `TOOL_CALL`: Execute a tool
- `LLM_GENERATE`: Generate LLM content
- `MCP_REQUEST`: Make MCP request
- `CONDITIONAL`: Conditional execution (future)
- `LOOP`: Loop execution (future)
- `FINISH`: Signal task completion

**Action Flow:**
```
LLM Response → ActionGenerator → Actions → ActionExecutor → Results
```

### 5. MCP Support (`mcp/`)

**Components:**
- `MCPClient`: Client for connecting to MCP servers
- `MCPServer`: Server for exposing agent capabilities
- `MCPProtocol`: Request/response definitions

**MCP Protocol:**
- JSON-RPC 2.0 based
- Supports resources, tools, prompts
- Bidirectional communication

**Use Cases:**
- Connect to external MCP servers for additional capabilities
- Expose agent as MCP server for other tools
- Integrate with MCP ecosystem

## Data Flow

### Task Execution Flow

```
1. User Task
   │
   ▼
2. Agent.run(task)
   │
   ▼
3. Build System Prompt (with tool schemas)
   │
   ▼
4. LLM.generate(prompt, tools=schemas)
   │
   ▼
5. LLM Response (may contain function_call)
   │
   ▼
6. ActionGenerator.generate_from_llm_response()
   │
   ▼
7. Actions (tool_call, etc.)
   │
   ▼
8. ActionExecutor.execute(action)
   │
   ├─→ Tool Call → ToolRegistry → Tool.execute() → Result
   ├─→ MCP Request → MCPClient → MCP Server → Result
   └─→ LLM Generate → LLMProvider → Result
   │
   ▼
9. Format Results for LLM
   │
   ▼
10. Feed back to LLM (next iteration)
    │
    └─→ Repeat until task complete or max iterations
```

### Tool Execution Flow

```
Tool Call Request
    │
    ▼
ActionExecutor.execute_tool()
    │
    ▼
ToolRegistry.get(tool_name)
    │
    ▼
Tool.execute(**params)
    │
    ├─→ File Operations (read, write, edit)
    ├─→ Code Operations (search, analyze)
    └─→ Search Operations (semantic, find)
    │
    ▼
Result: {"success": bool, "result": Any, "error": str}
    │
    ▼
ActionResult (wrapped)
```

## Extension Points

### Adding New Tools

1. Create tool class inheriting from `Tool`
2. Define parameters using `ToolParameter`
3. Implement `execute()` method
4. Register with `ToolRegistry`

Example:
```python
class MyTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Does something",
            parameters=[...]
        )
    
    async def execute(self, **kwargs):
        # Implementation
        return {"success": True, "result": ...}
```

### Adding New LLM Providers

1. Create provider class inheriting from `LLMProvider`
2. Implement `generate()` and `generate_stream()`
3. Implement `format_tools_for_llm()`
4. Add to factory in `llm/factory.py`

### Adding New Action Types

1. Add to `ActionType` enum
2. Implement handling in `ActionExecutor.execute()`
3. Update `ActionGenerator` if needed

## Configuration

Configuration is managed through:
- Environment variables (`.env` file)
- `config.py` with Pydantic models
- Runtime overrides

Key configuration:
- LLM provider and API keys
- Model selection
- Generation parameters
- Workspace path
- Max iterations
- Tool timeout

## Error Handling

- Tools return structured results with success/error
- Actions wrap results in `ActionResult`
- Agent handles errors gracefully and continues
- Errors are logged and included in results

## Security Considerations

- File operations are scoped to workspace
- Tool execution has timeout limits
- API keys are loaded from environment
- No arbitrary code execution (tools are predefined)

## Performance

- Async/await throughout for concurrency
- Tool execution is non-blocking
- LLM calls are async
- Results are streamed when possible

## Future Enhancements

- Vector embeddings for semantic search
- Tool result caching
- Parallel action execution
- Conditional and loop actions
- Better MCP transport implementations
- Tool result validation
- Action planning and optimization


