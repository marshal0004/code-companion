import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import json
import re

try:
    from vector_store import VectorStore
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False

# PHASE 2: Import Read-First Protocol for accuracy
try:
    from read_first_protocol import ReadFirstProtocol
    READ_FIRST_AVAILABLE = True
except ImportError:
    READ_FIRST_AVAILABLE = False
    ReadFirstProtocol = None

WORKSPACE_ROOT = os.environ.get('WORKSPACE_ROOT', '/app')
BACKUP_DIR = os.path.expanduser("~/.local/share/codecompanion/backups")

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
    r':\(\){',  # Fork bomb
    r'>\/dev\/sd',
    r'>\/dev\/null\s+2>&1\s*&',  # Background with no output (suspicious)
]


class ToolExecutor:
    def __init__(self, workspace_root: str = WORKSPACE_ROOT):
        self.workspace_root = Path(workspace_root)
        self.backup_dir = Path(BACKUP_DIR)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize vector store for semantic search
        self.vector_store = VectorStore(str(self.workspace_root)) if VECTOR_STORE_AVAILABLE else None
        
        # PHASE 2: Initialize read-first protocol
        self.read_first = ReadFirstProtocol() if READ_FIRST_AVAILABLE else None
        self.current_session = "default"
    
    def set_session(self, session_id: str):
        """Set current session for read-first tracking"""
        self.current_session = session_id
    
    def sanitize_path(self, path: str) -> Path:
        """Ensure path is within workspace and resolve it"""
        # Handle absolute paths
        if path.startswith('/'):
            full_path = Path(path).resolve()
        else:
            full_path = (self.workspace_root / path).resolve()
        
        # Allow paths within workspace OR standard safe paths
        workspace_str = str(self.workspace_root.resolve())
        full_path_str = str(full_path)
        
        if not (full_path_str.startswith(workspace_str) or 
                full_path_str.startswith('/tmp') or
                full_path_str.startswith(os.path.expanduser('~/.local'))):
            raise ValueError(f"Path traversal detected: {path}")
        return full_path
    
    def is_command_safe(self, command: str) -> bool:
        """Check if command matches blocked patterns"""
        for pattern in BLOCKED_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return False
        return True
    
    def create_backup(self, file_path: Path) -> str:
        """Create backup of file before editing"""
        if not file_path.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        relative_path = file_path.relative_to(self.workspace_root) if str(file_path).startswith(str(self.workspace_root)) else file_path.name
        backup_name = f"{relative_path}_{timestamp}.bak".replace('/', '_')
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        return str(backup_path)
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with read-first enforcement and immediate feedback"""
        try:
            # PHASE 2: Read-First Protocol Enforcement
            if READ_FIRST_AVAILABLE and self.read_first:
                # Record reads
                if tool_name == "read_file":
                    result = self._execute_tool_internal(tool_name, arguments)
                    if result.get('success'):
                        path = arguments.get('path', '')
                        if path:
                            self.read_first.record_read(path, self.current_session)
                    return result
                
                # Enforce read-first for writes/edits on existing files
                elif tool_name in ['write_file', 'edit_file']:
                    path = arguments.get('path', '')
                    
                    if path:
                        try:
                            file_path = self.sanitize_path(path)
                            # Only enforce for existing files
                            if file_path.exists():
                                allowed, msg = self.read_first.can_write(path, self.current_session)
                                
                                if not allowed:
                                    return {
                                        'success': False,
                                        'error': f'READ-FIRST VIOLATION: {msg}',
                                        'blocked': True,
                                        'suggestion': f'Use read_file on {path} before modifying it'
                                    }
                        except Exception:
                            pass  # If path check fails, allow operation
            
            # Execute the tool normally
            result = self._execute_tool_internal(tool_name, arguments)
            
            # PHASE 4: Immediate Feedback - Quick syntax check after writes
            if result.get('success') and tool_name in ['write_file', 'edit_file']:
                path = arguments.get('path', '')
                if path and path.endswith('.py'):
                    syntax_check = self._quick_syntax_check(path)
                    if not syntax_check['success']:
                        result['warning'] = f"⚠️ Syntax error: {syntax_check['error']}"
                        result['needs_fix'] = True
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_tool_internal(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Internal tool execution (original logic)"""
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
        elif tool_name == "git_status":
            return self.git_status(**arguments)
        elif tool_name == "git_diff":
            return self.git_diff(**arguments)
        elif tool_name == "git_log":
            return self.git_log(**arguments)
        elif tool_name == "git_blame":
            return self.git_blame(**arguments)
        elif tool_name == "semantic_search":
            return self.semantic_search(**arguments)
        elif tool_name == "index_workspace":
            return self.index_workspace(**arguments)
        elif tool_name == "index_stats":
            return self.index_stats(**arguments)
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    def _quick_syntax_check(self, path: str) -> Dict:
        """Quick Python syntax check (PHASE 4: Immediate Feedback)"""
        try:
            import ast
            file_path = self.sanitize_path(path)
            with open(file_path, 'r') as f:
                code = f.read()
            ast.parse(code)
            return {'success': True}
        except SyntaxError as e:
            return {'success': False, 'error': f"Line {e.lineno}: {e.msg}"}
        except Exception:
            return {'success': True}  # Don't fail on other errors
    
    def read_file(self, path: str, start_line: int = None, end_line: int = None) -> Dict:
        """Read file contents"""
        try:
            file_path = self.sanitize_path(path)
            if not file_path.exists():
                return {"success": False, "error": f"File not found: {path}"}
            
            # Check file size (limit to 1MB)
            if file_path.stat().st_size > 1048576:
                return {"success": False, "error": "File too large (>1MB)"}
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            if start_line is not None or end_line is not None:
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                lines = lines[start:end]
            
            content = ''.join(lines)
            return {"success": True, "content": content, "line_count": len(lines), "path": str(file_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def write_file(self, path: str, content: str) -> Dict:
        """Write content to file with backup"""
        try:
            file_path = self.sanitize_path(path)
            
            # Create backup if file exists
            backup_path = None
            if file_path.exists():
                backup_path = self.create_backup(file_path)
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            result = {"success": True, "path": str(file_path), "size": len(content)}
            if backup_path:
                result["backup"] = backup_path
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def edit_file(self, path: str, old_text: str, new_text: str) -> Dict:
        """Edit file using search and replace with backup"""
        try:
            file_path = self.sanitize_path(path)
            if not file_path.exists():
                return {"success": False, "error": f"File not found: {path}"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if old_text not in content:
                return {"success": False, "error": "Old text not found in file"}
            
            # Create backup before editing
            backup_path = self.create_backup(file_path)
            
            new_content = content.replace(old_text, new_text, 1)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                "success": True, 
                "message": "File edited successfully",
                "backup": backup_path
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_directory(self, path: str = ".", recursive: bool = False, max_depth: int = 3) -> Dict:
        """List directory contents"""
        try:
            dir_path = self.sanitize_path(path)
            if not dir_path.exists():
                return {"success": False, "error": f"Directory not found: {path}"}
            
            if not dir_path.is_dir():
                return {"success": False, "error": f"Not a directory: {path}"}
            
            files = []
            
            def add_entry(item: Path, depth: int = 0):
                if depth > max_depth:
                    return
                
                # Skip hidden files and common ignore patterns
                if item.name.startswith('.') and item.name not in ['.env', '.gitignore']:
                    return
                if item.name in ['node_modules', '__pycache__', '.git', 'venv', '.venv']:
                    return
                
                try:
                    rel_path = item.relative_to(self.workspace_root)
                except ValueError:
                    rel_path = item.name
                
                entry = {
                    "path": str(rel_path),
                    "type": "file" if item.is_file() else "directory",
                    "size": item.stat().st_size if item.is_file() else None
                }
                files.append(entry)
                
                if recursive and item.is_dir() and depth < max_depth:
                    for child in sorted(item.iterdir()):
                        add_entry(child, depth + 1)
            
            for item in sorted(dir_path.iterdir()):
                add_entry(item, 0)
            
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
            
            # Truncate output if too long
            stdout = result.stdout[:50000] if len(result.stdout) > 50000 else result.stdout
            stderr = result.stderr[:10000] if len(result.stderr) > 10000 else result.stderr
            
            return {
                "success": result.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_text(self, query: str, path: str = ".", file_pattern: str = None) -> Dict:
        """Search for text in files using grep/ripgrep"""
        try:
            search_path = self.sanitize_path(path)
            
            # Try ripgrep first, fall back to grep
            if shutil.which('rg'):
                cmd = f"rg -n --color=never '{query}' {search_path}"
                if file_pattern:
                    cmd = f"rg -n --color=never -g '{file_pattern}' '{query}' {search_path}"
            else:
                cmd = f"grep -r -n '{query}' {search_path}"
                if file_pattern:
                    cmd = f"grep -r -n --include='{file_pattern}' '{query}' {search_path}"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            matches = result.stdout.strip().split('\n') if result.stdout else []
            matches = [m for m in matches if m]  # Filter empty lines
            
            return {
                "success": True,
                "matches": matches[:100],  # Limit to 100 results
                "count": len(matches)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Git Tools
    def git_status(self, **kwargs) -> Dict:
        """Get git repository status"""
        try:
            result = subprocess.run(
                "git status --porcelain -b",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.workspace_root)
            )
            
            if result.returncode != 0:
                return {"success": False, "error": result.stderr or "Not a git repository"}
            
            # Parse status
            lines = result.stdout.strip().split('\n')
            branch = lines[0] if lines else "unknown"
            
            files = {
                "modified": [],
                "added": [],
                "deleted": [],
                "untracked": [],
                "staged": []
            }
            
            for line in lines[1:]:
                if not line:
                    continue
                status = line[:2]
                filename = line[3:]
                
                if status[0] == 'M' or status[1] == 'M':
                    files["modified"].append(filename)
                if status[0] == 'A':
                    files["staged"].append(filename)
                if status[0] == 'D' or status[1] == 'D':
                    files["deleted"].append(filename)
                if status == '??':
                    files["untracked"].append(filename)
            
            return {
                "success": True,
                "branch": branch.replace("## ", ""),
                "files": files,
                "raw": result.stdout
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def git_diff(self, staged: bool = False, file: str = None, **kwargs) -> Dict:
        """Show git diff"""
        try:
            cmd = "git diff"
            if staged:
                cmd += " --staged"
            if file:
                safe_file = self.sanitize_path(file)
                cmd += f" -- {safe_file}"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace_root)
            )
            
            if result.returncode != 0:
                return {"success": False, "error": result.stderr or "Git diff failed"}
            
            diff = result.stdout[:100000] if len(result.stdout) > 100000 else result.stdout
            
            return {
                "success": True,
                "diff": diff,
                "has_changes": bool(diff.strip())
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def git_log(self, count: int = 10, file: str = None, **kwargs) -> Dict:
        """Show git commit history"""
        try:
            cmd = f"git log --oneline --no-decorate -n {min(count, 50)}"
            if file:
                safe_file = self.sanitize_path(file)
                cmd += f" -- {safe_file}"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.workspace_root)
            )
            
            if result.returncode != 0:
                return {"success": False, "error": result.stderr or "Git log failed"}
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(' ', 1)
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1] if len(parts) > 1 else ""
                    })
            
            return {
                "success": True,
                "commits": commits,
                "count": len(commits)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def git_blame(self, path: str, start_line: int = None, end_line: int = None, **kwargs) -> Dict:
        """Show git blame for a file"""
        try:
            file_path = self.sanitize_path(path)
            if not file_path.exists():
                return {"success": False, "error": f"File not found: {path}"}
            
            cmd = f"git blame --line-porcelain {file_path}"
            if start_line and end_line:
                cmd = f"git blame -L {start_line},{end_line} --line-porcelain {file_path}"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace_root)
            )
            
            if result.returncode != 0:
                return {"success": False, "error": result.stderr or "Git blame failed"}
            
            # Parse blame output (simplified)
            blame_lines = []
            current_commit = {}
            
            for line in result.stdout.split('\n'):
                if line.startswith('\t'):
                    current_commit['content'] = line[1:]
                    blame_lines.append(current_commit.copy())
                    current_commit = {}
                elif line.startswith('author '):
                    current_commit['author'] = line[7:]
                elif ' ' in line and len(line.split()[0]) == 40:
                    current_commit['commit'] = line.split()[0][:8]
            
            return {
                "success": True,
                "blame": blame_lines[:200],  # Limit output
                "line_count": len(blame_lines)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def semantic_search(self, query: str, top_k: int = 5, **kwargs) -> Dict:
        """Semantic search using embeddings"""
        if not VECTOR_STORE_AVAILABLE or not self.vector_store or not self.vector_store.is_available():
            # Fall back to text search
            return self.search_text(query=query)
        
        try:
            # Try semantic search first
            result = self.vector_store.search(query, top_k)
            
            if result.get('success'):
                # Format results for display
                formatted_results = []
                for item in result.get('results', []):
                    formatted_results.append(
                        f"File: {item['file']} (Score: {item['score']:.2f})\n{item['chunk'][:200]}..."
                    )
                
                return {
                    "success": True,
                    "matches": formatted_results,
                    "count": result.get('count', 0),
                    "search_type": "semantic"
                }
            else:
                # Fall back to text search
                return self.search_text(query=query)
        except Exception as e:
            # Fall back to text search on error
            return self.search_text(query=query)
    
    def index_workspace(self, **kwargs) -> Dict:
        """Index workspace for semantic search"""
        if not VECTOR_STORE_AVAILABLE or not self.vector_store:
            return {"success": False, "error": "Vector store not available"}
        
        if not self.vector_store.is_available():
            return {"success": False, "error": "Vector store not initialized"}
        
        try:
            result = self.vector_store.index_workspace()
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def index_stats(self, **kwargs) -> Dict:
        """Get index statistics"""
        if not VECTOR_STORE_AVAILABLE or not self.vector_store:
            return {"success": False, "error": "Vector store not available"}
        
        if not self.vector_store.is_available():
            return {"success": False, "error": "Vector store not initialized"}
        
        try:
            return self.vector_store.get_stats()
        except Exception as e:
            return {"success": False, "error": str(e)}
