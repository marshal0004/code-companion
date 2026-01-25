import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List
import json
import re

WORKSPACE_ROOT = os.environ.get('WORKSPACE_ROOT', '/app')

# Blocked command patterns for safety
BLOCKED_COMMANDS = [
    r'rm\s+-rf\s+/',
    r'rm\s+-rf\s+~',
    r'rm\s+-rf\s+\*',
    r'sudo',
    r'su\s+-',
    r'chmod\s+777',
    r'curl.*\|.*sh',
    r'wget.*\|.*sh',
    r'dd\s+if=',
    r'mkfs',
]

class ToolExecutor:
    def __init__(self, workspace_root: str = WORKSPACE_ROOT):
        self.workspace_root = Path(workspace_root)
    
    def sanitize_path(self, path: str) -> Path:
        """Ensure path is within workspace and resolve it"""
        full_path = (self.workspace_root / path).resolve()
        if not str(full_path).startswith(str(self.workspace_root)):
            raise ValueError(f"Path traversal detected: {path}")
        return full_path
    
    def is_command_safe(self, command: str) -> bool:
        """Check if command matches blocked patterns"""
        for pattern in BLOCKED_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return False
        return True
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return result"""
        try:
            if tool_name == "read_file":
                return self.read_file(**arguments)
            elif tool_name == "write_file":
                return self.write_file(**arguments)
            elif tool_name == "edit_file":
                return self.edit_file(**arguments)
            elif tool_name == "list_directory":
                return self.list_directory(**arguments)
            elif tool_name == "run_command":
                return self.run_command(**arguments)
            elif tool_name == "search_text":
                return self.search_text(**arguments)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def read_file(self, path: str, start_line: int = None, end_line: int = None) -> Dict:
        """Read file contents"""
        try:
            file_path = self.sanitize_path(path)
            if not file_path.exists():
                return {"success": False, "error": f"File not found: {path}"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if start_line is not None or end_line is not None:
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                lines = lines[start:end]
            
            content = ''.join(lines)
            return {"success": True, "content": content, "line_count": len(lines)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def write_file(self, path: str, content: str) -> Dict:
        """Write content to file"""
        try:
            file_path = self.sanitize_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {"success": True, "path": str(file_path), "size": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def edit_file(self, path: str, old_text: str, new_text: str) -> Dict:
        """Edit file using search and replace"""
        try:
            file_path = self.sanitize_path(path)
            if not file_path.exists():
                return {"success": False, "error": f"File not found: {path}"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if old_text not in content:
                return {"success": False, "error": "Old text not found in file"}
            
            new_content = content.replace(old_text, new_text, 1)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {"success": True, "message": "File edited successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_directory(self, path: str = ".", recursive: bool = False) -> Dict:
        """List directory contents"""
        try:
            dir_path = self.sanitize_path(path)
            if not dir_path.exists():
                return {"success": False, "error": f"Directory not found: {path}"}
            
            if not dir_path.is_dir():
                return {"success": False, "error": f"Not a directory: {path}"}
            
            files = []
            if recursive:
                for item in dir_path.rglob('*'):
                    rel_path = item.relative_to(self.workspace_root)
                    files.append({
                        "path": str(rel_path),
                        "type": "file" if item.is_file() else "directory",
                        "size": item.stat().st_size if item.is_file() else None
                    })
            else:
                for item in dir_path.iterdir():
                    rel_path = item.relative_to(self.workspace_root)
                    files.append({
                        "path": str(rel_path),
                        "type": "file" if item.is_file() else "directory",
                        "size": item.stat().st_size if item.is_file() else None
                    })
            
            return {"success": True, "files": files, "count": len(files)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_command(self, command: str, timeout: int = 30) -> Dict:
        """Execute shell command with safety checks"""
        try:
            if not self.is_command_safe(command):
                return {"success": False, "error": "Command blocked for safety reasons"}
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.workspace_root)
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_text(self, query: str, path: str = ".", file_pattern: str = None) -> Dict:
        """Search for text in files using grep"""
        try:
            search_path = self.sanitize_path(path)
            
            cmd = f"grep -r -n '{query}' {search_path}"
            if file_pattern:
                cmd = f"grep -r -n --include='{file_pattern}' '{query}' {search_path}"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            matches = result.stdout.strip().split('\n') if result.stdout else []
            matches = [m for m in matches if m]  # Filter empty lines
            
            return {
                "success": True,
                "matches": matches[:50],  # Limit to 50 results
                "count": len(matches)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
