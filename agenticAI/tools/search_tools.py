"""
Semantic search and codebase exploration tools.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
from .base import Tool, ToolParameter


class SemanticSearchTool(Tool):
    """Semantic search across codebase (placeholder for vector search)"""
    
    def __init__(self):
        super().__init__(
            name="semantic_search",
            description="Search codebase semantically using natural language queries",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Natural language query describing what to search for",
                    required=True
                ),
                ToolParameter(
                    name="target_directories",
                    type="array",
                    description="Optional directories to limit search scope",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results to return",
                    required=False,
                    default=10
                )
            ]
        )
    
    async def execute(self, query: str, target_directories: Optional[List[str]] = None, 
                     max_results: int = 10, **kwargs) -> Dict[str, Any]:
        # This is a placeholder - in production, you'd use embeddings/vector search
        # For now, we'll do a simple keyword-based search
        try:
            workspace = Path(kwargs.get("workspace_path", "."))
            
            # Simple keyword extraction
            keywords = [q.lower() for q in query.split() if len(q) > 3]
            
            search_dirs = [workspace / d for d in (target_directories or ["."])]
            results = []
            
            for search_dir in search_dirs:
                if not search_dir.exists():
                    continue
                
                for file_path in search_dir.rglob("*.py"):
                    if file_path.is_file():
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read().lower()
                                if any(kw in content for kw in keywords):
                                    results.append({
                                        "file": str(file_path.relative_to(workspace)),
                                        "relevance": sum(1 for kw in keywords if kw in content)
                                    })
                        except Exception:
                            continue
            
            # Sort by relevance
            results.sort(key=lambda x: x["relevance"], reverse=True)
            results = results[:max_results]
            
            return {
                "success": True,
                "result": {
                    "query": query,
                    "results": results,
                    "count": len(results)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class FindFilesTool(Tool):
    """Find files by name pattern"""
    
    def __init__(self):
        super().__init__(
            name="find_files",
            description="Find files matching a glob pattern",
            parameters=[
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Glob pattern (e.g., '*.py', '**/test_*.ts')",
                    required=True
                ),
                ToolParameter(
                    name="directory",
                    type="string",
                    description="Directory to search in (default: workspace root)",
                    required=False,
                    default=None
                )
            ]
        )
    
    async def execute(self, pattern: str, directory: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        try:
            workspace = Path(kwargs.get("workspace_path", "."))
            search_dir = workspace / directory if directory else workspace
            
            if not search_dir.exists():
                return {"success": False, "error": f"Directory not found: {search_dir}"}
            
            matches = list(search_dir.rglob(pattern))
            matches = [m for m in matches if m.is_file()]
            
            return {
                "success": True,
                "result": {
                    "pattern": pattern,
                    "files": [str(m.relative_to(workspace)) for m in matches],
                    "count": len(matches)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class SearchTools:
    """Collection of search tools"""
    
    @staticmethod
    def register_all(registry: 'ToolRegistry', workspace_path: str = "."):
        """Register all search tools"""
        tools = [
            SemanticSearchTool(),
            FindFilesTool()
        ]
        
        def create_wrapper(orig_exec, ws_path):
            """Factory function to create a properly closed wrapper"""
            async def wrapped_execute(**kwargs):
                """Wrapper that injects workspace_path"""
                kwargs["workspace_path"] = ws_path
                # Call the original bound method
                return await orig_exec(**kwargs)
            return wrapped_execute
        
        for tool in tools:
            # Create a wrapper for this specific tool's execute method
            wrapped = create_wrapper(tool.execute, workspace_path)
            
            # Use object.__setattr__ to bypass Pydantic field validation
            # This allows us to replace the method without Pydantic treating it as a field
            object.__setattr__(tool, 'execute', wrapped)
            registry.register(tool)

