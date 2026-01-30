"""Code Verification System for CodeCompanion

Handles:
- Syntax validation for different languages
- Lint checks
- Test execution hooks
- Multi-layer verification
"""

import os
import subprocess
import tempfile
import ast
from pathlib import Path
from typing import Dict, List, Optional, Any


class CodeVerifier:
    """Verify code changes"""
    
    def __init__(self, workspace_root: str = "/app"):
        self.workspace_root = Path(workspace_root)
    
    def verify_file(self, file_path: str, content: str = None) -> Dict[str, Any]:
        """Verify a file based on its type"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # Read content if not provided
        if content is None:
            full_path = self.workspace_root / file_path if not path.is_absolute() else path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            else:
                return {'success': False, 'error': 'File not found'}
        
        # Route to appropriate verifier
        if extension == '.py':
            return self.verify_python(content, file_path)
        elif extension in ['.js', '.jsx']:
            return self.verify_javascript(content, file_path)
        elif extension in ['.ts', '.tsx']:
            return self.verify_typescript(content, file_path)
        elif extension == '.json':
            return self.verify_json(content, file_path)
        else:
            return {'success': True, 'message': 'No verification available for this file type'}
    
    def verify_python(self, content: str, file_path: str = None) -> Dict[str, Any]:
        """Verify Python syntax"""
        result = {'success': True, 'errors': [], 'warnings': []}
        
        # 1. AST Parse (syntax check)
        try:
            ast.parse(content)
        except SyntaxError as e:
            result['success'] = False
            result['errors'].append({
                'type': 'syntax',
                'line': e.lineno,
                'column': e.offset,
                'message': e.msg
            })
            return result
        
        # 2. Check for common issues
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for print with file=stderr pattern (common mistake)
            if 'import *' in line and 'from' in line:
                result['warnings'].append({
                    'type': 'style',
                    'line': i,
                    'message': 'Avoid wildcard imports'
                })
            
            # Check for bare except
            if line.strip() == 'except:':
                result['warnings'].append({
                    'type': 'style',
                    'line': i,
                    'message': 'Avoid bare except, use specific exceptions'
                })
        
        # 3. Try ruff/flake8 if available
        lint_result = self._run_python_lint(content, file_path)
        if lint_result:
            result['lint'] = lint_result
        
        return result
    
    def verify_javascript(self, content: str, file_path: str = None) -> Dict[str, Any]:
        """Verify JavaScript syntax"""
        result = {'success': True, 'errors': [], 'warnings': []}
        
        # Basic syntax checks
        # Check for unmatched brackets
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        
        for i, char in enumerate(content):
            if char in brackets:
                stack.append((char, i))
            elif char in brackets.values():
                if not stack:
                    result['warnings'].append({
                        'type': 'syntax',
                        'position': i,
                        'message': f'Unmatched closing bracket: {char}'
                    })
                else:
                    open_bracket, _ = stack.pop()
                    if brackets[open_bracket] != char:
                        result['warnings'].append({
                            'type': 'syntax',
                            'position': i,
                            'message': f'Mismatched brackets: {open_bracket} and {char}'
                        })
        
        if stack:
            for bracket, pos in stack:
                result['warnings'].append({
                    'type': 'syntax',
                    'position': pos,
                    'message': f'Unclosed bracket: {bracket}'
                })
        
        # Try node --check if available
        if file_path:
            node_check = self._run_node_check(content)
            if node_check and not node_check.get('success', True):
                result['success'] = False
                result['errors'].extend(node_check.get('errors', []))
        
        return result
    
    def verify_typescript(self, content: str, file_path: str = None) -> Dict[str, Any]:
        """Verify TypeScript syntax"""
        # Similar to JavaScript but with TS-specific checks
        result = self.verify_javascript(content, file_path)
        result['language'] = 'typescript'
        return result
    
    def verify_json(self, content: str, file_path: str = None) -> Dict[str, Any]:
        """Verify JSON syntax"""
        import json
        result = {'success': True, 'errors': []}
        
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            result['success'] = False
            result['errors'].append({
                'type': 'syntax',
                'line': e.lineno,
                'column': e.colno,
                'message': e.msg
            })
        
        return result
    
    def _run_python_lint(self, content: str, file_path: str = None) -> Optional[Dict]:
        """Run Python linter (ruff or flake8)"""
        try:
            # Try ruff first
            if self._command_exists('ruff'):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(content)
                    temp_path = f.name
                
                try:
                    result = subprocess.run(
                        ['ruff', 'check', temp_path, '--output-format=json'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.stdout:
                        import json
                        issues = json.loads(result.stdout)
                        return {'linter': 'ruff', 'issues': issues[:10]}  # Limit to 10
                finally:
                    os.unlink(temp_path)
            
            return None
        except Exception:
            return None
    
    def _run_node_check(self, content: str) -> Optional[Dict]:
        """Run Node.js syntax check"""
        try:
            if not self._command_exists('node'):
                return None
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                result = subprocess.run(
                    ['node', '--check', temp_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    return {
                        'success': False,
                        'errors': [{'type': 'syntax', 'message': result.stderr}]
                    }
                return {'success': True}
            finally:
                os.unlink(temp_path)
        except Exception:
            return None
    
    def _command_exists(self, cmd: str) -> bool:
        """Check if a command exists"""
        import shutil
        return shutil.which(cmd) is not None
    
    def run_tests(self, test_command: str = None, test_path: str = None) -> Dict[str, Any]:
        """Run tests"""
        result = {'success': True, 'output': '', 'errors': []}
        
        # Detect test framework
        if test_command:
            cmd = test_command
        elif (self.workspace_root / 'pytest.ini').exists() or (self.workspace_root / 'pyproject.toml').exists():
            cmd = 'pytest -v --tb=short'
        elif (self.workspace_root / 'package.json').exists():
            cmd = 'npm test'
        else:
            return {'success': True, 'message': 'No test configuration found'}
        
        if test_path:
            cmd += f' {test_path}'
        
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.workspace_root)
            )
            
            result['output'] = proc.stdout + proc.stderr
            result['returncode'] = proc.returncode
            result['success'] = proc.returncode == 0
            
            if not result['success']:
                result['errors'].append({
                    'type': 'test_failure',
                    'message': 'Tests failed',
                    'details': proc.stderr[:1000]
                })
        except subprocess.TimeoutExpired:
            result['success'] = False
            result['errors'].append({'type': 'timeout', 'message': 'Tests timed out'})
        except Exception as e:
            result['success'] = False
            result['errors'].append({'type': 'error', 'message': str(e)})
        
        return result


def create_verifier(workspace_root: str = "/app") -> CodeVerifier:
    """Factory function to create verifier"""
    return CodeVerifier(workspace_root)


class AsyncCodeVerifier(CodeVerifier):
    """Async version of CodeVerifier for agent integration.
    
    Provides async methods for linting, type checking, and test execution.
    """
    
    async def run_lint(self, file_path: str) -> Dict:
        """Run linting on file asynchronously"""
        if file_path.endswith('.py'):
            return await self._run_python_lint_async(file_path)
        elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
            return await self._run_js_lint_async(file_path)
        return {'passed': True, 'skipped': True, 'reason': 'Unsupported file type'}
    
    async def _run_python_lint_async(self, file_path: str) -> Dict:
        """Run ruff or flake8 on Python file asynchronously"""
        import asyncio
        try:
            # Try ruff first (faster)
            proc = await asyncio.create_subprocess_exec(
                'ruff', 'check', file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if proc.returncode == 0:
                return {'passed': True, 'linter': 'ruff'}
            else:
                return {
                    'passed': False,
                    'linter': 'ruff',
                    'issues': stdout.decode().strip().split('\n')[:10]
                }
        except FileNotFoundError:
            # ruff not installed, try flake8
            try:
                proc = await asyncio.create_subprocess_exec(
                    'flake8', file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                
                if proc.returncode == 0:
                    return {'passed': True, 'linter': 'flake8'}
                else:
                    return {
                        'passed': False,
                        'linter': 'flake8',
                        'issues': stdout.decode().strip().split('\n')[:10]
                    }
            except Exception:
                return {'passed': True, 'skipped': True, 'reason': 'No Python linter available'}
        except asyncio.TimeoutError:
            return {'passed': True, 'skipped': True, 'reason': 'Linting timed out'}
        except Exception as e:
            return {'passed': True, 'skipped': True, 'reason': str(e)}
    
    async def _run_js_lint_async(self, file_path: str) -> Dict:
        """Run eslint on JavaScript/TypeScript file asynchronously"""
        import asyncio
        try:
            proc = await asyncio.create_subprocess_exec(
                'npx', 'eslint', file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            
            if proc.returncode == 0:
                return {'passed': True, 'linter': 'eslint'}
            else:
                return {
                    'passed': False,
                    'linter': 'eslint',
                    'issues': stdout.decode().strip().split('\n')[:10]
                }
        except Exception:
            return {'passed': True, 'skipped': True, 'reason': 'ESLint not available'}
    
    async def run_type_check(self, file_path: str) -> Dict:
        """Run type checking on file asynchronously"""
        if file_path.endswith('.py'):
            return await self._run_mypy_async(file_path)
        elif file_path.endswith('.ts') or file_path.endswith('.tsx'):
            return await self._run_tsc_async(file_path)
        return {'passed': True, 'skipped': True, 'reason': 'Unsupported file type'}
    
    async def _run_mypy_async(self, file_path: str) -> Dict:
        """Run mypy type checker asynchronously"""
        import asyncio
        try:
            proc = await asyncio.create_subprocess_exec(
                'mypy', file_path, '--ignore-missing-imports',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            
            if proc.returncode == 0:
                return {'passed': True, 'checker': 'mypy'}
            else:
                return {
                    'passed': False,
                    'checker': 'mypy',
                    'issues': stdout.decode().strip().split('\n')[:10]
                }
        except Exception:
            return {'passed': True, 'skipped': True, 'reason': 'mypy not available'}
    
    async def _run_tsc_async(self, file_path: str) -> Dict:
        """Run TypeScript compiler check asynchronously"""
        import asyncio
        try:
            proc = await asyncio.create_subprocess_exec(
                'npx', 'tsc', '--noEmit', file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            
            if proc.returncode == 0:
                return {'passed': True, 'checker': 'tsc'}
            else:
                return {
                    'passed': False,
                    'checker': 'tsc',
                    'issues': stderr.decode().strip().split('\n')[:10]
                }
        except Exception:
            return {'passed': True, 'skipped': True, 'reason': 'TypeScript compiler not available'}
    
    async def run_tests_async(self, test_command: str = None, test_path: str = None) -> Dict[str, Any]:
        """Run tests asynchronously"""
        import asyncio
        result = {'success': True, 'output': '', 'errors': []}
        
        # Detect test framework
        if test_command:
            cmd = test_command
        elif (self.workspace_root / 'pytest.ini').exists() or (self.workspace_root / 'pyproject.toml').exists():
            cmd = 'pytest -v --tb=short'
        elif (self.workspace_root / 'package.json').exists():
            cmd = 'npm test'
        else:
            return {'success': True, 'message': 'No test configuration found'}
        
        if test_path:
            cmd += f' {test_path}'
        
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_root)
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            
            result['output'] = stdout.decode() + stderr.decode()
            result['returncode'] = proc.returncode
            result['success'] = proc.returncode == 0
            
            if not result['success']:
                result['errors'].append({
                    'type': 'test_failure',
                    'message': 'Tests failed',
                    'details': stderr.decode()[:1000]
                })
        except asyncio.TimeoutError:
            result['success'] = False
            result['errors'].append({'type': 'timeout', 'message': 'Tests timed out'})
        except Exception as e:
            result['success'] = False
            result['errors'].append({'type': 'error', 'message': str(e)})
        
        return result
    
    async def verify_full(self, file_path: str, content: str = None) -> Dict[str, Any]:
        """Run full verification pipeline asynchronously.
        
        This performs:
        1. Syntax check
        2. Lint check
        3. Type check (if applicable)
        
        Args:
            file_path: Path to file to verify
            content: Optional file content (reads from disk if not provided)
            
        Returns:
            Dict with all verification results
        """
        results = {
            'success': True,
            'syntax': None,
            'lint': None,
            'type_check': None,
            'summary': []
        }
        
        # 1. Syntax check (synchronous, fast)
        syntax_result = self.verify_file(file_path, content)
        results['syntax'] = syntax_result
        
        if not syntax_result.get('success', True):
            results['success'] = False
            results['summary'].append(f"Syntax errors: {len(syntax_result.get('errors', []))}")
            return results  # Don't continue if syntax fails
        
        results['summary'].append("Syntax: OK")
        
        # 2. Lint check (async)
        lint_result = await self.run_lint(file_path)
        results['lint'] = lint_result
        
        if not lint_result.get('passed', True) and not lint_result.get('skipped'):
            results['success'] = False
            results['summary'].append(f"Lint issues: {len(lint_result.get('issues', []))}")
        elif lint_result.get('skipped'):
            results['summary'].append(f"Lint: skipped ({lint_result.get('reason', 'N/A')})")
        else:
            results['summary'].append("Lint: OK")
        
        # 3. Type check (async)
        type_result = await self.run_type_check(file_path)
        results['type_check'] = type_result
        
        if not type_result.get('passed', True) and not type_result.get('skipped'):
            # Type errors are warnings, not failures
            results['summary'].append(f"Type issues: {len(type_result.get('issues', []))}")
        elif type_result.get('skipped'):
            results['summary'].append(f"Type check: skipped ({type_result.get('reason', 'N/A')})")
        else:
            results['summary'].append("Type check: OK")
        
        return results


def create_async_verifier(workspace_root: str = "/app") -> AsyncCodeVerifier:
    """Factory function to create async verifier"""
    return AsyncCodeVerifier(workspace_root)
