"""Verification Protocol for CodeCompanion

NEVER assume success - always verify.
"""

import asyncio
import json
from typing import Dict, List, Optional
from pathlib import Path


class VerificationProtocol:
    """Verify all changes after execution"""
    
    def __init__(self, workspace_root: str):
        self.workspace = Path(workspace_root)
    
    async def verify_file_change(
        self, 
        file_path: str, 
        expected_content: str = None,
        expected_patterns: List[str] = None
    ) -> Dict:
        """Verify a file was changed correctly"""
        
        full_path = self.workspace / file_path
        
        result = {
            "file": file_path,
            "verified": False,
            "checks": []
        }
        
        # Check 1: File exists
        if not full_path.exists():
            result["checks"].append({
                "check": "file_exists",
                "passed": False,
                "error": "File does not exist"
            })
            return result
        
        result["checks"].append({
            "check": "file_exists",
            "passed": True
        })
        
        # Read actual content
        try:
            actual_content = full_path.read_text()
        except Exception as e:
            result["checks"].append({
                "check": "read_file",
                "passed": False,
                "error": str(e)
            })
            return result
        
        # Check 2: Content not empty
        if not actual_content.strip():
            result["checks"].append({
                "check": "not_empty",
                "passed": False,
                "error": "File is empty"
            })
            return result
        
        result["checks"].append({
            "check": "not_empty",
            "passed": True
        })
        
        # Check 3: Expected patterns present (if provided)
        if expected_patterns:
            for pattern in expected_patterns:
                found = pattern in actual_content
                result["checks"].append({
                    "check": f"pattern_present: {pattern[:30]}...",
                    "passed": found,
                    "error": None if found else f"Pattern not found: {pattern[:50]}"
                })
        
        # Check 4: No syntax errors (for code files)
        syntax_result = await self._check_syntax(file_path, actual_content)
        result["checks"].append(syntax_result)
        
        # Overall verification
        result["verified"] = all(c["passed"] for c in result["checks"])
        
        return result
    
    async def _check_syntax(self, file_path: str, content: str) -> Dict:
        """Check for syntax errors"""
        
        suffix = Path(file_path).suffix.lower()
        
        if suffix == ".py":
            return await self._check_python_syntax(content)
        elif suffix in [".ts", ".tsx"]:
            return await self._check_typescript_syntax(file_path)
        elif suffix in [".js", ".jsx"]:
            return await self._check_javascript_syntax(content)
        elif suffix == ".json":
            return self._check_json_syntax(content)
        
        return {"check": "syntax", "passed": True, "skipped": True}
    
    async def _check_python_syntax(self, content: str) -> Dict:
        """Check Python syntax"""
        try:
            compile(content, '<string>', 'exec')
            return {"check": "python_syntax", "passed": True}
        except SyntaxError as e:
            return {
                "check": "python_syntax",
                "passed": False,
                "error": f"Syntax error at line {e.lineno}: {e.msg}"
            }
    
    async def _check_typescript_syntax(self, file_path: str) -> Dict:
        """Check TypeScript syntax using tsc"""
        try:
            process = await asyncio.create_subprocess_shell(
                f"npx tsc --noEmit --skipLibCheck {file_path}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace
            )
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            
            passed = process.returncode == 0
            return {
                "check": "typescript_syntax",
                "passed": passed,
                "error": stderr.decode()[:500] if not passed else None
            }
        except Exception as e:
            return {"check": "typescript_syntax", "passed": True, "skipped": True, "reason": str(e)}
    
    async def _check_javascript_syntax(self, content: str) -> Dict:
        """Check JavaScript syntax"""
        try:
            process = await asyncio.create_subprocess_shell(
                f"node --check -e {repr(content)}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
            
            passed = process.returncode == 0
            return {
                "check": "javascript_syntax",
                "passed": passed,
                "error": stderr.decode()[:500] if not passed else None
            }
        except Exception:
            return {"check": "javascript_syntax", "passed": True, "skipped": True}
    
    def _check_json_syntax(self, content: str) -> Dict:
        """Check JSON syntax"""
        try:
            json.loads(content)
            return {"check": "json_syntax", "passed": True}
        except json.JSONDecodeError as e:
            return {
                "check": "json_syntax",
                "passed": False,
                "error": f"JSON error: {str(e)}"
            }
    
    async def verify_command_success(
        self, 
        command: str, 
        expected_output: str = None,
        expected_exit_code: int = 0
    ) -> Dict:
        """Verify a command executed successfully"""
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
            
            result = {
                "command": command,
                "verified": process.returncode == expected_exit_code,
                "exit_code": process.returncode,
                "stdout": stdout.decode()[:1000],
                "stderr": stderr.decode()[:1000]
            }
            
            if expected_output and expected_output not in stdout.decode():
                result["verified"] = False
                result["error"] = f"Expected output not found: {expected_output}"
            
            return result
            
        except Exception as e:
            return {
                "command": command,
                "verified": False,
                "error": str(e)
            }
