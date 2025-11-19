"""
File operation tools: read, write, edit, list, etc.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from .base import Tool, ToolParameter


class ReadFileTool(Tool):
    """Read contents of a file"""
    
    def __init__(self):
        super().__init__(
            name="read_file",
            description="Read the contents of a file. Returns the file content as text.",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file to read (relative to workspace or absolute)",
                    required=True
                ),
                ToolParameter(
                    name="offset",
                    type="integer",
                    description="Line number to start reading from (1-indexed, optional)",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Maximum number of lines to read (optional)",
                    required=False,
                    default=None
                )
            ]
        )
    
    async def execute(self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            if not path.is_absolute():
                # Resolve relative to workspace
                workspace = Path(kwargs.get("workspace_path", "."))
                path = workspace / path
            
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            if not path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}
            
            with open(path, 'r', encoding='utf-8') as f:
                if offset is not None or limit is not None:
                    lines = f.readlines()
                    start = (offset - 1) if offset else 0
                    end = (start + limit) if limit else len(lines)
                    content = ''.join(lines[start:end])
                else:
                    content = f.read()
            
            return {
                "success": True,
                "result": {
                    "content": content,
                    "file_path": str(path),
                    "lines": content.count('\n') + 1 if content else 0
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class WriteFileTool(Tool):
    """Write content to a file (creates or overwrites)"""
    
    def __init__(self):
        super().__init__(
            name="write_file",
            description="Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file to write",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write to the file",
                    required=True
                )
            ]
        )
    
    async def execute(self, file_path: str, content: str, **kwargs) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            if not path.is_absolute():
                workspace = Path(kwargs.get("workspace_path", "."))
                path = workspace / path
            
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "result": {
                    "file_path": str(path),
                    "bytes_written": len(content.encode('utf-8'))
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class EditFileTool(Tool):
    """Edit a file by replacing specific content"""
    
    def __init__(self):
        super().__init__(
            name="edit_file",
            description="Edit a file by replacing old_string with new_string. Supports replace_all flag.",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file to edit",
                    required=True
                ),
                ToolParameter(
                    name="old_string",
                    type="string",
                    description="The text to replace (must match exactly including whitespace)",
                    required=True
                ),
                ToolParameter(
                    name="new_string",
                    type="string",
                    description="The replacement text",
                    required=True
                ),
                ToolParameter(
                    name="replace_all",
                    type="boolean",
                    description="If true, replace all occurrences; if false, replace only the first",
                    required=False,
                    default=False
                )
            ]
        )
    
    async def execute(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False, **kwargs) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            if not path.is_absolute():
                workspace = Path(kwargs.get("workspace_path", "."))
                path = workspace / path
            
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if old_string not in content:
                return {"success": False, "error": f"old_string not found in file"}
            
            if replace_all:
                new_content = content.replace(old_string, new_string)
                count = content.count(old_string)
            else:
                if content.count(old_string) > 1:
                    return {"success": False, "error": f"old_string appears multiple times. Use replace_all=true or provide more context"}
                new_content = content.replace(old_string, new_string, 1)
                count = 1
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                "success": True,
                "result": {
                    "file_path": str(path),
                    "replacements": count
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class ListDirectoryTool(Tool):
    """List files and directories in a path"""
    
    def __init__(self):
        super().__init__(
            name="list_directory",
            description="List files and directories in a given path",
            parameters=[
                ToolParameter(
                    name="directory_path",
                    type="string",
                    description="Path to the directory to list",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="ignore_patterns",
                    type="array",
                    description="Glob patterns to ignore (e.g., ['*.pyc', '__pycache__'])",
                    required=False,
                    default=None
                )
            ]
        )
    
    async def execute(self, directory_path: str = ".", ignore_patterns: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        try:
            path = Path(directory_path)
            if not path.is_absolute():
                workspace = Path(kwargs.get("workspace_path", "."))
                path = workspace / path
            
            if not path.exists():
                return {"success": False, "error": f"Directory not found: {directory_path}"}
            
            if not path.is_dir():
                return {"success": False, "error": f"Path is not a directory: {directory_path}"}
            
            items = []
            for item in path.iterdir():
                # Skip hidden files/dirs by default
                if item.name.startswith('.'):
                    continue
                
                # Apply ignore patterns
                if ignore_patterns:
                    import fnmatch
                    if any(fnmatch.fnmatch(item.name, pattern) for pattern in ignore_patterns):
                        continue
                
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": str(item)
                })
            
            return {
                "success": True,
                "result": {
                    "directory": str(path),
                    "items": sorted(items, key=lambda x: (x["type"] == "file", x["name"]))
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class DeleteFileTool(Tool):
    """Delete a file"""
    
    def __init__(self):
        super().__init__(
            name="delete_file",
            description="Delete a file from the filesystem",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file to delete",
                    required=True
                )
            ]
        )
    
    async def execute(self, file_path: str, **kwargs) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            if not path.is_absolute():
                workspace = Path(kwargs.get("workspace_path", "."))
                path = workspace / path
            
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            if not path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}
            
            path.unlink()
            
            return {
                "success": True,
                "result": {
                    "file_path": str(path),
                    "deleted": True
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class FileTools:
    """Collection of file operation tools"""
    
    @staticmethod
    def register_all(registry: 'ToolRegistry', workspace_path: str = "."):
        """Register all file tools with workspace context"""
        tools = [
            ReadFileTool(),
            WriteFileTool(),
            EditFileTool(),
            ListDirectoryTool(),
            DeleteFileTool()
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

