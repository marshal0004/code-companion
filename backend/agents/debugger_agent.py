"""Debugger Agent

Responsible for:
- Error analysis and classification
- Root cause identification
- Fix generation
- Recovery strategies
"""

import json
import re
from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent, AgentResult


class ErrorType:
    """Error classification types"""
    SYNTAX = "syntax_error"
    IMPORT = "import_error" 
    RUNTIME = "runtime_error"
    LOGIC = "logic_error"
    ENVIRONMENT = "environment_error"
    UNKNOWN = "unknown_error"


class DebuggerAgent(BaseAgent):
    """Specialized agent for debugging and error fixing"""
    
    # Error pattern matching
    ERROR_PATTERNS = {
        ErrorType.SYNTAX: [
            r'SyntaxError', r'IndentationError', r'TabError',
            r'unexpected token', r'invalid syntax'
        ],
        ErrorType.IMPORT: [
            r'ImportError', r'ModuleNotFoundError', r'cannot import',
            r'No module named', r'module .* not found'
        ],
        ErrorType.RUNTIME: [
            r'TypeError', r'ValueError', r'AttributeError', r'KeyError',
            r'IndexError', r'NameError', r'ZeroDivisionError'
        ],
        ErrorType.LOGIC: [
            r'AssertionError', r'test failed', r'expected .* got',
            r'assertion failed'
        ],
        ErrorType.ENVIRONMENT: [
            r'FileNotFoundError', r'PermissionError', r'IsADirectoryError',
            r'OSError', r'permission denied'
        ]
    }
    
    # Recovery strategies per error type
    STRATEGIES = {
        ErrorType.SYNTAX: "Fix code syntax based on error message",
        ErrorType.IMPORT: "Install missing dependency or fix import path",
        ErrorType.RUNTIME: "Debug logic and fix type/value issues",
        ErrorType.LOGIC: "Analyze expected vs actual behavior and fix logic",
        ErrorType.ENVIRONMENT: "Check file paths and permissions",
        ErrorType.UNKNOWN: "General debugging approach"
    }
    
    def __init__(self, llm_client, tools: Dict):
        super().__init__(llm_client, tools, name="debugger")
    
    def _get_system_prompt(self) -> str:
        return '''You are a Debugger Agent specialized in error analysis and fixing.

Your responsibilities:
1. Classify errors into types (syntax, import, runtime, logic, environment)
2. Analyze root causes
3. Generate precise fixes
4. Suggest prevention strategies

## Error Classification:
- **Syntax Error**: Code syntax issues (indentation, missing brackets, etc.)
- **Import Error**: Missing modules or incorrect imports
- **Runtime Error**: Type errors, value errors, attribute errors at runtime
- **Logic Error**: Code runs but produces wrong results
- **Environment Error**: File system, permissions, missing files

## Analysis Process:
1. Read the error message carefully
2. Identify error type and location
3. Read relevant code context
4. Understand root cause
5. Generate minimal fix
6. Suggest verification

## Output Format:
```json
{
  "error_type": "syntax_error|import_error|runtime_error|logic_error|environment_error",
  "root_cause": "Detailed explanation",
  "fix": {
    "tool": "edit_file|write_file|run_command",
    "args": {...}
  },
  "reasoning": "Why this fix works",
  "prevention": "How to avoid this in future"
}
```

## Fix Guidelines:
- Make minimal changes
- Preserve existing functionality
- Add error handling where appropriate
- Verify fix after applying
'''
    
    async def execute(self, task: str, context: Dict) -> AgentResult:
        """Analyze error and generate fix"""
        error = context.get('error', task)
        return await self.analyze_error(error, context)
    
    async def analyze_error(self, error: str, context: Dict) -> AgentResult:
        """Analyze error and generate fix"""
        try:
            # Step 1: Classify error
            error_type = self.classify_error(error)
            strategy = self.STRATEGIES.get(error_type, self.STRATEGIES[ErrorType.UNKNOWN])
            
            # Step 2: Generate fix using LLM
            fix = await self._generate_fix(error, error_type, strategy, context)
            
            return AgentResult(
                success=True,
                data={
                    'error_type': error_type,
                    'strategy': strategy,
                    'fix': fix,
                    'classified': True
                },
                metadata={'agent': self.name, 'error_type': error_type}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                data={'error_type': ErrorType.UNKNOWN},
                error=str(e)
            )
    
    def classify_error(self, error: str) -> str:
        """Classify error by matching patterns"""
        error_lower = error.lower()
        
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error, re.IGNORECASE):
                    return error_type
        
        return ErrorType.UNKNOWN
    
    async def _generate_fix(self, error: str, error_type: str, 
                           strategy: str, context: Dict) -> Dict:
        """Generate fix using LLM"""
        prompt = f'''{self.system_prompt}

## Error:
{error}

## Error Type: {error_type}
## Strategy: {strategy}

## Context:
{json.dumps(context, indent=2)}

## Instructions:
Analyze this error and provide a fix in the JSON format specified above.
Be specific and provide exact tool calls to fix the issue.
'''
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.call_llm(messages, session_id="debugger")
        response_text = result.get('response', '')
        
        # Parse fix from response
        fix = self.parse_json_response(response_text)
        if fix:
            return fix
        else:
            return {
                'error_type': error_type,
                'root_cause': 'Unable to parse detailed analysis',
                'fix': {'tool': 'manual_review', 'args': {}},
                'reasoning': response_text[:500]
            }
    
    def extract_error_location(self, error: str) -> Optional[Dict]:
        """Extract file and line number from error"""
        # Pattern: File "path", line N
        pattern = r'File "([^"]+)", line (\d+)'
        match = re.search(pattern, error)
        if match:
            return {
                'file': match.group(1),
                'line': int(match.group(2))
            }
        return None
