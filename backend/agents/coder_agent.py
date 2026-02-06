"""Coder Agent

Responsible for:
- Code generation
- Code editing and refactoring
- Following project patterns
- Implementing features
"""

import json
from typing import Dict, List, Any
from .base_agent import BaseAgent, AgentResult

# PHASE 3: Import Surgical Edit System for accuracy
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from surgical_edit import SurgicalEditSystem, EditRecommendation
    SURGICAL_EDIT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Surgical edit system not available: {e}")
    SURGICAL_EDIT_AVAILABLE = False

# 95% Accuracy: Pre-execution validation
try:
    from advanced_accuracy import PreExecutionValidator
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False


class CoderAgent(BaseAgent):
    """Specialized agent for code generation and editing"""
    
    def __init__(self, llm_client, tools: Dict):
        super().__init__(llm_client, tools, name="coder")
        
        # PHASE 3: Initialize surgical edit system
        self.surgical_edit = SurgicalEditSystem() if SURGICAL_EDIT_AVAILABLE else None
        
        # 95% Accuracy: Pre-execution validator
        self.validator = PreExecutionValidator('/app') if VALIDATOR_AVAILABLE else None
    
    def _enhance_prompt_with_surgical_guidance(self, base_prompt: str) -> str:
        """Add surgical edit guidance to prompt (PHASE 3)"""
        if not self.surgical_edit:
            return base_prompt
        
        guidance = '''

🎯 SURGICAL PRECISION REQUIRED (Critical for Accuracy)

When modifying existing files, follow these rules:

1. **ALWAYS use edit_file for small changes** (< 50 lines modified)
   - Identify EXACT text to replace
   - Make minimal, targeted changes
   - Preserve surrounding code

2. **ONLY use write_file for:**
   - Brand new files that don't exist
   - Complete rewrites when > 70% of file changes
   - Files under 50 lines total

3. **Search-and-Replace Approach:**
   - Find exact text block to modify
   - Copy it precisely
   - Make minimal changes
   - Replace with new version

✅ GOOD Example (Surgical Edit):
<TOOL_CALL>{"tool": "edit_file", "args": {"path": "app.py", "old_text": "def process():\\n    return 1", "new_text": "def process():\\n    return 2"}}</TOOL_CALL>

❌ BAD Example (Avoid Rewrites):
<TOOL_CALL>{"tool": "write_file", "args": {"path": "app.py", "content": "...entire file rewritten..."}}</TOOL_CALL>

Remember: Edit, don't rewrite! This reduces errors by 50%.

'''
        return guidance + "\n" + base_prompt
    
    def _validate_action(self, action: dict) -> dict:
        """Pre-execution validation for 95%+ accuracy"""
        if not self.validator:
            return {'valid': True, 'confidence': 0.7, 'issues': []}
        
        result = self.validator.validate_action(action)
        return {
            'valid': result.valid,
            'confidence': result.confidence,
            'issues': result.issues,
            'blocking': result.blocking_issues
        }
    
    def _get_system_prompt(self) -> str:
        return '''You are a Coding Agent specialized in generating and editing code.

Your responsibilities:
1. Write clean, efficient, and maintainable code
2. Follow existing project patterns and conventions
3. Use appropriate tools (write_file, edit_file, read_file)
4. Implement features accurately
5. Handle edge cases

## Coding Guidelines:
- Read existing code before modifying
- Follow the project's style and patterns
- Add appropriate error handling
- Write clear comments for complex logic
- Use meaningful variable names
- Keep functions focused and small

## Available Tools:
- read_file: Read existing code
- write_file: Create new files
- edit_file: Modify existing files with search/replace
- list_directory: Explore project structure
- search_text: Find code patterns

## Output Format:
Provide tool calls in JSON:
```json
{
  "action": "tool_name",
  "args": {...},
  "reasoning": "Why this approach"
}
```

## Quality Standards:
- Code must be syntactically correct
- Follow language-specific best practices
- Include basic error handling
- Verify changes after implementation
'''
    
    async def execute(self, task: str, context: Dict) -> AgentResult:
        """Generate or edit code based on task"""
        try:
            # Analyze task to determine actions
            actions = await self._plan_code_actions(task, context)
            
            return AgentResult(
                success=True,
                data={'actions': actions},
                metadata={'agent': self.name}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                data={},
                error=str(e)
            )
    
    async def _plan_code_actions(self, task: str, context: Dict) -> List[Dict]:
        """Plan what coding actions to take (PHASE 3: with surgical guidance)"""
        # PHASE 3: Enhance task with surgical edit guidance
        enhanced_task = self._enhance_prompt_with_surgical_guidance(task) if self.surgical_edit else task
        
        prompt = f'''{self.system_prompt}

## Task:
{enhanced_task}

## Context:
{json.dumps(context, indent=2)}

## Instructions:
Analyze the task and determine what coding actions are needed.
Output a list of actions (tool calls) to accomplish this task.

REMEMBER: Use edit_file for modifications, write_file only for new files!

Format:
```json
[
  {{"tool": "read_file", "args": {{"path": "..."}}, "reasoning": "..."}},
  {{"tool": "write_file", "args": {{"path": "...", "content": "..."}}, "reasoning": "..."}}
]
```'''
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.call_llm(messages, session_id="coder")
        response_text = result.get('response', '')
        
        # Parse actions from response
        actions = self.parse_json_response(response_text)
        if isinstance(actions, list):
            return actions
        elif isinstance(actions, dict) and 'actions' in actions:
            return actions['actions']
        else:
            return []
    
    async def generate_code(self, description: str, language: str, context: Dict) -> str:
        """Generate code snippet"""
        prompt = f'''Generate {language} code for:
{description}

Context:
{json.dumps(context, indent=2)}

Provide ONLY the code, no explanations.
'''
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.call_llm(messages, session_id="coder_generate")
        response_text = result.get('response', '')
        
        # Extract code from response
        code_blocks = self.extract_code_blocks(response_text)
        if code_blocks:
            return code_blocks[0]['code']
        else:
            return response_text.strip()
