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
