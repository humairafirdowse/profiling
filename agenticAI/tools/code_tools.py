"""
Code-specific tools: search, analyze, format, etc.
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from .base import Tool, ToolParameter


class SearchCodeTool(Tool):
    """Search for code patterns using regex"""
    
    def __init__(self):
        super().__init__(
            name="search_code",
            description="Search for code patterns in files using regular expressions",
            parameters=[
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Regular expression pattern to search for",
                    required=True
                ),
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="File or directory to search in (default: workspace root)",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="file_type",
                    type="string",
                    description="File extension filter (e.g., 'py', 'js', 'ts')",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="case_sensitive",
                    type="boolean",
                    description="Whether search is case sensitive",
                    required=False,
                    default=False
                )
            ]
        )
    
    async def execute(self, pattern: str, file_path: Optional[str] = None, file_type: Optional[str] = None, 
                     case_sensitive: bool = False, **kwargs) -> Dict[str, Any]:
        try:
            workspace = Path(kwargs.get("workspace_path", "."))
            search_path = workspace / file_path if file_path else workspace
            
            if not search_path.exists():
                return {"success": False, "error": f"Path not found: {search_path}"}
            
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
            matches = []
            
            if search_path.is_file():
                files_to_search = [search_path]
            else:
                # Search recursively
                if file_type:
                    files_to_search = list(search_path.rglob(f"*.{file_type}"))
                else:
                    files_to_search = list(search_path.rglob("*"))
                    files_to_search = [f for f in files_to_search if f.is_file()]
            
            for file in files_to_search:
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                matches.append({
                                    "file": str(file.relative_to(workspace)),
                                    "line": line_num,
                                    "content": line.strip()
                                })
                except Exception:
                    continue
            
            return {
                "success": True,
                "result": {
                    "pattern": pattern,
                    "matches": matches,
                    "count": len(matches)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class AnalyzeCodeTool(Tool):
    """Analyze code structure and extract information"""
    
    def __init__(self):
        super().__init__(
            name="analyze_code",
            description="Analyze code file structure: functions, classes, imports, etc.",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the code file to analyze",
                    required=True
                )
            ]
        )
    
    async def execute(self, file_path: str, **kwargs) -> Dict[str, Any]:
        try:
            workspace = Path(kwargs.get("workspace_path", "."))
            path = workspace / file_path if not Path(file_path).is_absolute() else Path(file_path)
            
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                "file_path": str(path),
                "language": path.suffix[1:] if path.suffix else "unknown",
                "lines": len(content.splitlines()),
                "functions": [],
                "classes": [],
                "imports": []
            }
            
            # Simple Python analysis
            if path.suffix == '.py':
                # Find functions
                func_pattern = re.compile(r'^\s*(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE)
                for match in func_pattern.finditer(content):
                    analysis["functions"].append({
                        "name": match.group(1),
                        "line": content[:match.start()].count('\n') + 1
                    })
                
                # Find classes
                class_pattern = re.compile(r'^\s*class\s+(\w+)', re.MULTILINE)
                for match in class_pattern.finditer(content):
                    analysis["classes"].append({
                        "name": match.group(1),
                        "line": content[:match.start()].count('\n') + 1
                    })
                
                # Find imports
                import_pattern = re.compile(r'^\s*(?:from\s+[\w.]+\s+)?import\s+(.+)', re.MULTILINE)
                for match in import_pattern.finditer(content):
                    analysis["imports"].append(match.group(1).strip())
            
            return {
                "success": True,
                "result": analysis
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class CodeTools:
    """Collection of code-specific tools"""
    
    @staticmethod
    def register_all(registry: 'ToolRegistry', workspace_path: str = "."):
        """Register all code tools"""
        tools = [
            SearchCodeTool(),
            AnalyzeCodeTool()
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

