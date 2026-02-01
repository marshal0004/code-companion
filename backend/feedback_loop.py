"""Immediate Feedback Loop for CodeCompanion

Runs verification immediately after file changes to catch errors fast.
"""

import asyncio
import subprocess
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class FeedbackResult:
    """Result from feedback loop"""
    success: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    checks_run: List[str]


class ImmediateFeedbackLoop:
    """Run checks immediately after file modifications"""
    
    def __init__(self, workspace_root: str):
        self.workspace = Path(workspace_root)
    
    async def run_feedback(
        self, 
        changed_files: List[str],
        run_tests: bool = False,
        quick: bool = True
    ) -> FeedbackResult:
        """
        Run immediate feedback on changed files.
        
        Args:
            changed_files: List of file paths that were modified
            run_tests: Whether to run tests (slow)
            quick: If True, only run fast checks (syntax, basic lint)
        
        Returns:
            FeedbackResult with errors, warnings, suggestions
        """
        errors = []
        warnings = []
        suggestions = []
        checks_run = []
        
        for file_path in changed_files:
            full_path = self.workspace / file_path
            
            if not full_path.exists():
                errors.append(f"File not found: {file_path}")
                continue
            
            # Determine file type
            suffix = full_path.suffix.lower()
            
            # Python files
            if suffix == '.py':
                result = await self._check_python(full_path, quick)
                errors.extend(result['errors'])
                warnings.extend(result['warnings'])
                checks_run.extend(result['checks'])
            
            # JavaScript/TypeScript files
            elif suffix in ['.js', '.jsx', '.ts', '.tsx']:
                result = await self._check_javascript(full_path, quick)
                errors.extend(result['errors'])
                warnings.extend(result['warnings'])
                checks_run.extend(result['checks'])
            
            # JSON files
            elif suffix == '.json':
                result = self._check_json(full_path)
                errors.extend(result['errors'])
                checks_run.extend(result['checks'])
        
        # Generate suggestions based on errors
        if errors:
            suggestions = self.get_fix_suggestions({'errors': errors})
        
        return FeedbackResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            checks_run=checks_run
        )
    
    async def _check_python(self, file_path: Path, quick: bool = True) -> Dict:
        """Check Python file"""
        errors = []
        warnings = []
        checks = []
        
        # 1. Syntax check (always run)
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            compile(code, str(file_path), 'exec')
            checks.append('python_syntax')
        except SyntaxError as e:
            errors.append(f"Syntax error in {file_path.name} line {e.lineno}: {e.msg}")
            return {'errors': errors, 'warnings': warnings, 'checks': checks}
        except Exception as e:
            errors.append(f"Could not read {file_path.name}: {e}")
            return {'errors': errors, 'warnings': warnings, 'checks': checks}
        
        # 2. Import check (quick)
        if not quick:
            import_errors = self._check_imports_python(code)
            if import_errors:
                warnings.extend(import_errors)
            checks.append('python_imports')
        
        # 3. Basic lint (if ruff available)
        if not quick:
            lint_result = await self._run_ruff(file_path)
            if lint_result:
                warnings.extend(lint_result)
            checks.append('python_lint')
        
        return {'errors': errors, 'warnings': warnings, 'checks': checks}
    
    async def _check_javascript(self, file_path: Path, quick: bool = True) -> Dict:
        """Check JavaScript/TypeScript file"""
        errors = []
        warnings = []
        checks = []
        
        # 1. Basic syntax check using Node
        try:
            process = await asyncio.create_subprocess_shell(
                f"node --check {file_path}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace
            )
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
            
            if process.returncode != 0:
                error_msg = stderr.decode()[:300]
                errors.append(f"Syntax error in {file_path.name}: {error_msg}")
            else:
                checks.append('js_syntax')
        except Exception as e:
            warnings.append(f"Could not check JS syntax: {e}")
        
        # 2. TypeScript check (if .ts/.tsx)
        if file_path.suffix in ['.ts', '.tsx'] and not quick:
            try:
                process = await asyncio.create_subprocess_shell(
                    f"npx tsc --noEmit {file_path}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.workspace
                )
                _, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
                
                if process.returncode != 0:
                    error_msg = stderr.decode()[:300]
                    warnings.append(f"Type errors in {file_path.name}: {error_msg}")
                else:
                    checks.append('ts_types')
            except Exception:
                pass
        
        return {'errors': errors, 'warnings': warnings, 'checks': checks}
    
    def _check_json(self, file_path: Path) -> Dict:
        """Check JSON file"""
        errors = []
        checks = []
        
        try:
            import json
            with open(file_path, 'r') as f:
                json.load(f)
            checks.append('json_syntax')
        except json.JSONDecodeError as e:
            errors.append(f"JSON error in {file_path.name} line {e.lineno}: {e.msg}")
        except Exception as e:
            errors.append(f"Could not read {file_path.name}: {e}")
        
        return {'errors': errors, 'warnings': [], 'checks': checks}
    
    def _check_imports_python(self, code: str) -> List[str]:
        """Check Python imports are valid"""
        import ast
        import_errors = []
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Try to import (in a safe way)
                        try:
                            __import__(alias.name)
                        except ImportError:
                            import_errors.append(f"Import not found: {alias.name}")
                        except Exception:
                            pass
        except:
            pass
        
        return import_errors[:5]  # Limit to 5
    
    async def _run_ruff(self, file_path: Path) -> List[str]:
        """Run ruff linter on Python file"""
        try:
            process = await asyncio.create_subprocess_shell(
                f"ruff check {file_path}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
            
            if stdout:
                # Parse ruff output
                output = stdout.decode()
                lines = output.split('\n')
                return [line for line in lines if line.strip()][:10]  # First 10 issues
        except:
            pass
        
        return []
    
    def get_fix_suggestions(self, feedback_result: Dict) -> List[str]:
        """Generate fix suggestions based on feedback"""
        suggestions = []
        errors = feedback_result.get('errors', [])
        
        for error in errors[:5]:  # Top 5 errors
            error_lower = error.lower()
            
            # Syntax errors
            if "syntax" in error_lower:
                suggestions.append("Check for missing brackets, quotes, or semicolons")
            
            # Undefined errors
            if "undefined" in error_lower or "not defined" in error_lower:
                suggestions.append("Ensure the variable/function is defined before use")
            
            # Test failures
            if "assert" in error_lower or "expected" in error_lower:
                suggestions.append("Review test expectations vs actual output")
        
        return suggestions


# Quick integration function
async def run_quick_feedback(workspace: str, changed_file: str) -> Dict:
    """Quick function to run feedback on a single file"""
    loop = ImmediateFeedbackLoop(workspace)
    result = await loop.run_feedback([changed_file], run_tests=False)
    
    return {
        "success": result.success,
        "errors": result.errors,
        "suggestions": loop.get_fix_suggestions({'errors': result.errors})
    }
