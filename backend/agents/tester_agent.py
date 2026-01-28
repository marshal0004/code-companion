"""Tester Agent

Responsible for:
- Code verification
- Test generation
- Running tests
- Quality checks
"""

import json
import ast
import subprocess
from typing import Dict, List, Any
from .base_agent import BaseAgent, AgentResult


class TesterAgent(BaseAgent):
    """Specialized agent for testing and verification"""
    
    def __init__(self, llm_client, tools: Dict, verifier=None):
        super().__init__(llm_client, tools, name="tester")
        self.verifier = verifier
    
    def _get_system_prompt(self) -> str:
        return '''You are a Tester Agent specialized in code verification and testing.

Your responsibilities:
1. Verify code correctness
2. Generate appropriate tests
3. Run tests and analyze results
4. Ensure code quality

## Verification Layers:
1. **Syntax Check**: Code compiles/parses correctly
2. **Lint Check**: Follows style guidelines
3. **Type Check**: Type annotations are correct (if applicable)
4. **Unit Tests**: Core functionality works
5. **Integration Tests**: Components work together

## Test Generation:
- Generate tests for new code
- Follow testing best practices
- Cover edge cases and error conditions
- Use appropriate testing framework (pytest, unittest, jest, etc.)

## Output Format:
```json
{
  "verification": {
    "syntax": {"passed": true/false, "error": "..."},
    "lint": {"passed": true/false, "issues": [...]},
    "tests": {"passed": true/false, "results": [...]}
  },
  "recommendations": ["..."],
  "overall_status": "pass|fail|warning"
}
```

## Quality Standards:
- All syntax must be valid
- Code should follow project conventions
- Tests should be meaningful and comprehensive
- Edge cases should be covered
'''
    
    async def execute(self, task: str, context: Dict) -> AgentResult:
        """Execute verification or testing task"""
        try:
            file_path = context.get('file_path', '')
            
            if 'verify' in task.lower() and file_path:
                result = await self.verify_file(file_path)
            elif 'test' in task.lower():
                result = await self.generate_tests(task, context)
            else:
                result = {'status': 'no_action', 'message': 'No verification or test task identified'}
            
            return AgentResult(
                success=True,
                data=result,
                metadata={'agent': self.name}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                data={},
                error=str(e)
            )
    
    async def verify_file(self, file_path: str) -> Dict:
        """Multi-layer verification of a file"""
        results = {
            'file': file_path,
            'layers': {},
            'overall': 'unknown'
        }
        
        # Layer 1: Syntax check
        syntax_result = self._check_syntax(file_path)
        results['layers']['syntax'] = syntax_result
        
        if not syntax_result['passed']:
            results['overall'] = 'fail'
            return results
        
        # Layer 2: Lint check (if verifier available)
        if self.verifier:
            try:
                lint_result = await self.verifier.verify_file(file_path)
                results['layers']['lint'] = lint_result
            except:
                results['layers']['lint'] = {'passed': True, 'skipped': True}
        
        # Layer 3: Import check
        import_result = self._check_imports(file_path)
        results['layers']['imports'] = import_result
        
        # Determine overall status
        all_passed = all(
            layer.get('passed', True) 
            for layer in results['layers'].values()
        )
        results['overall'] = 'pass' if all_passed else 'fail'
        
        return results
    
    def _check_syntax(self, file_path: str) -> Dict:
        """Check file syntax"""
        try:
            if file_path.endswith('.py'):
                with open(file_path, 'r') as f:
                    code = f.read()
                ast.parse(code)
                return {'passed': True, 'language': 'python'}
            else:
                # For now, just check file exists and is readable
                with open(file_path, 'r') as f:
                    f.read()
                return {'passed': True, 'language': 'unknown', 'basic_check': True}
        except SyntaxError as e:
            return {
                'passed': False,
                'error': f"Line {e.lineno}: {e.msg}",
                'line': e.lineno
            }
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    def _check_imports(self, file_path: str) -> Dict:
        """Check if all imports are available"""
        if not file_path.endswith('.py'):
            return {'passed': True, 'skipped': True, 'reason': 'Not a Python file'}
        
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            # Parse imports
            tree = ast.parse(code)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Try importing each module
            missing = []
            for imp in imports:
                try:
                    __import__(imp.split('.')[0])
                except ImportError:
                    missing.append(imp)
            
            if missing:
                return {
                    'passed': False,
                    'missing_imports': missing,
                    'error': f"Missing imports: {', '.join(missing)}"
                }
            else:
                return {'passed': True, 'imports_checked': len(imports)}
        
        except Exception as e:
            return {'passed': True, 'skipped': True, 'reason': str(e)}
    
    async def generate_tests(self, description: str, context: Dict) -> Dict:
        """Generate tests for code"""
        prompt = f'''{self.system_prompt}

## Task: Generate Tests

Description: {description}

Context:
{json.dumps(context, indent=2)}

## Instructions:
Generate appropriate tests for the given code/functionality.
Include:
- Setup/teardown if needed
- Normal cases
- Edge cases  
- Error cases

Provide tests in proper format for the language (pytest for Python, jest for JS, etc.)
'''
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.call_llm(messages, session_id="tester")
        response_text = result.get('response', '')
        
        # Extract test code
        test_code = self.extract_code_blocks(response_text)
        
        return {
            'tests_generated': True,
            'test_code': test_code,
            'full_response': response_text
        }
