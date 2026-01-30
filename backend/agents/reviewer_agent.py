"""Reviewer Agent

Responsible for:
- Code review
- Best practices enforcement
- Quality checks
- Improvement suggestions
"""

import json
from typing import Dict, List, Any
from .base_agent import BaseAgent, AgentResult


class ReviewerAgent(BaseAgent):
    """Specialized agent for code review and quality"""
    
    def __init__(self, llm_client, tools: Dict):
        super().__init__(llm_client, tools, name="reviewer")
    
    def _get_system_prompt(self) -> str:
        return '''You are a Reviewer Agent specialized in code review and quality assurance.

Your responsibilities:
1. Review code for correctness
2. Check adherence to best practices
3. Identify potential bugs
4. Suggest improvements
5. Ensure code quality standards

## Review Criteria:
- **Correctness**: Does code do what it should?
- **Readability**: Is code easy to understand?
- **Maintainability**: Is code easy to modify?
- **Performance**: Are there obvious inefficiencies?
- **Security**: Are there security issues?
- **Testing**: Is code testable?

## Review Levels:
1. **Syntax**: Basic correctness
2. **Logic**: Algorithm correctness
3. **Style**: Coding conventions
4. **Design**: Architecture quality
5. **Security**: Vulnerability check

## Output Format:
```json
{
  "review": {
    "overall_score": 1-10,
    "verdict": "approve|request_changes|comment",
    "issues": [
      {"severity": "critical|major|minor|suggestion", "line": 0, "message": "...", "fix": "..."}
    ],
    "improvements": ["..."],
    "positive": ["Things done well"]
  }
}
```

## Review Guidelines:
1. Be constructive, not critical
2. Explain WHY something is an issue
3. Provide concrete fix suggestions
4. Acknowledge good code
5. Focus on important issues first
'''
    
    async def execute(self, task: str, context: Dict) -> AgentResult:
        """Review code"""
        try:
            review = await self._review_code(task, context)
            
            return AgentResult(
                success=True,
                data=review,
                metadata={'agent': self.name}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                data={},
                error=str(e)
            )
    
    async def _review_code(self, task: str, context: Dict) -> Dict:
        """Perform code review using LLM"""
        code = context.get('code', '')
        file_path = context.get('file_path', '')
        
        prompt = f'''{self.system_prompt}

## Task:
{task}

## Code to Review:
File: {file_path}
```
{code[:5000]}
```

## Instructions:
Review this code thoroughly.
Output review in the JSON format specified above.
'''
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.call_llm(messages, session_id="reviewer")
        response_text = result.get('response', '')
        
        # Try to parse JSON review
        review = self.parse_json_response(response_text)
        if review:
            return review
        else:
            return {
                'review': {
                    'overall_score': 5,
                    'verdict': 'comment',
                    'issues': [],
                    'improvements': [],
                    'raw_response': response_text[:500]
                }
            }
    
    async def review_file(self, file_path: str, context: Dict) -> AgentResult:
        """Review a specific file"""
        # Read file first
        try:
            with open(file_path, 'r') as f:
                code = f.read()
        except:
            code = ''
        
        return await self.execute(
            f"Review code in {file_path}",
            {**context, 'code': code, 'file_path': file_path}
        )
    
    async def review_changes(self, diff: str, context: Dict) -> AgentResult:
        """Review code changes (diff)"""
        return await self.execute(
            "Review these code changes",
            {**context, 'code': diff, 'file_path': 'diff'}
        )
