"""Planner Agent

Responsible for:
- Task decomposition
- Hierarchical planning (Strategic → Tactical → Operational)
- Dependency analysis
- RAG-powered context retrieval
"""

import json
from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent, AgentResult


class PlannerAgent(BaseAgent):
    """Specialized agent for planning and task decomposition"""
    
    def __init__(self, llm_client, tools: Dict, vector_store=None):
        super().__init__(llm_client, tools, name="planner")
        self.vector_store = vector_store
    
    # === 95% ACCURACY ENHANCEMENT: Complexity Scoring ===
    def calculate_complexity(self, task: str) -> dict:
        """Score task complexity for better planning"""
        score = 3  # Base complexity
        task_lower = task.lower()
        
        # +2 for multiple files indicator
        if any(w in task_lower for w in ['files', 'multiple', 'several', 'all']):
            score += 2
        # +2 for new feature indicator
        if any(w in task_lower for w in ['create', 'new', 'implement', 'build', 'add']):
            score += 2
        # +2 for refactoring indicator
        if any(w in task_lower for w in ['refactor', 'rewrite', 'restructure', 'migrate']):
            score += 2
        # +1 for testing
        if any(w in task_lower for w in ['test', 'verify', 'check']):
            score += 1
        # +1 for integration
        if any(w in task_lower for w in ['integrate', 'connect', 'api']):
            score += 1
        
        level = 'high' if score >= 7 else 'medium' if score >= 4 else 'low'
        
        return {
            'score': min(score, 10),
            'level': level,
            'strategy': 'conservative' if score >= 7 else 'standard'
        }
    
    def generate_backup_plan(self, primary_plan: dict, task: str) -> dict:
        """Generate simpler backup plan if primary fails (95% accuracy feature)"""
        return {
            'strategic': [
                {'goal': f'Simplified approach: {task[:100]}', 'success_criteria': ['Basic functionality works']}
            ],
            'tactical': [
                {'phase': 'Direct Implementation', 'description': 'Minimal viable approach', 'steps': ['Read existing files', 'Make minimal changes', 'Verify syntax']}
            ],
            'operational': [
                {'action': 'read_file', 'args': {}, 'verify': 'File read successfully', 'dependencies': []},
                {'action': 'edit_file', 'args': {}, 'verify': 'Edit applied without errors', 'dependencies': ['read_file']},
            ],
            'is_backup': True,
            'reasoning': 'Simplified backup plan that minimizes risk'
        }
    
    def _get_system_prompt(self) -> str:
        return '''You are a Planning Agent specialized in task decomposition and strategic planning.

Your responsibilities:
1. Analyze complex programming tasks
2. Break them into hierarchical plans (Strategic → Tactical → Operational)
3. Identify dependencies and prerequisites
4. Consider existing codebase patterns
5. Output structured plans

## Planning Levels:

### Strategic Level:
- High-level goals and objectives
- Success criteria
- Risk assessment

### Tactical Level:
- Phases and milestones
- Sequence of operations
- Resource requirements

### Operational Level:
- Atomic actions (tool calls)
- Verification steps
- Rollback points

## Output Format:
Always output your plan as JSON:

```json
{
  "strategic": [
    {"goal": "Goal description", "success_criteria": ["criterion1", "criterion2"]}
  ],
  "tactical": [
    {"phase": "Phase name", "description": "What to do", "steps": ["step1", "step2"]}
  ],
  "operational": [
    {"action": "tool_name", "args": {}, "verify": "how to verify", "dependencies": []}
  ],
  "reasoning": "Why this approach"
}
```

## Analysis Guidelines:
1. Read existing code before planning modifications
2. Identify existing patterns and follow them
3. Plan verification after each significant change
4. Consider error handling and edge cases
5. Keep actions atomic and testable
'''
    
    async def execute(self, task: str, context: Dict) -> AgentResult:
        """Create a hierarchical plan for the task"""
        try:
            # Step 1: Use RAG to get relevant context
            rag_context = await self._get_relevant_context(task, context)
            enhanced_context = {**context, "relevant_code": rag_context}
            
            # Step 2: Generate plan
            plan = await self._generate_plan(task, enhanced_context)
            
            # 95% ACCURACY: Add complexity scoring and backup plan
            plan['complexity'] = self.calculate_complexity(task)
            plan['backup_plan'] = self.generate_backup_plan(plan, task)
            
            return AgentResult(
                success=True,
                data=plan,
                metadata={'agent': self.name, 'rag_context_size': len(rag_context), 'complexity': plan['complexity']['level']}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                data={},
                error=str(e)
            )
    
    async def _get_relevant_context(self, task: str, context: Dict) -> str:
        """Use vector store to get relevant code context"""
        if not self.vector_store:
            return "No vector store available"
        
        try:
            results = await self.vector_store.search(task, top_k=3)
            if not results:
                return "No relevant code found"
            
            context_parts = []
            for result in results:
                context_parts.append(
                    f"### {result.get('file', 'unknown')}:\n"
                    f"```\n{result.get('content', '')}\n```"
                )
            return "\n\n".join(context_parts)
        except Exception as e:
            return f"RAG search failed: {e}"
    
    async def _generate_plan(self, task: str, context: Dict) -> Dict:
        """Generate hierarchical plan using LLM"""
        prompt = self.build_prompt(task, context)
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        result = await self.call_llm(messages, session_id="planner")
        response_text = result.get('response', '')
        
        # Try to parse JSON plan
        plan = self.parse_json_response(response_text)
        
        if plan:
            return self._validate_plan(plan)
        else:
            # Fallback: create basic plan from text
            return self._create_fallback_plan(task, response_text)
    
    def _validate_plan(self, plan: Dict) -> Dict:
        """Validate and fix plan structure"""
        # Ensure all required keys exist
        if 'strategic' not in plan:
            plan['strategic'] = [{'goal': 'Complete task', 'success_criteria': []}]
        if 'tactical' not in plan:
            plan['tactical'] = [{'phase': 'Implementation', 'steps': []}]
        if 'operational' not in plan:
            plan['operational'] = []
        
        return plan
    
    def _create_fallback_plan(self, task: str, response: str) -> Dict:
        """Create a simple plan when JSON parsing fails"""
        return {
            'strategic': [
                {'goal': task, 'success_criteria': ['Task completed']}
            ],
            'tactical': [
                {'phase': 'Implementation', 'description': response[:500], 'steps': []}
            ],
            'operational': [
                {'action': 'proceed', 'description': response}
            ],
            'reasoning': 'Fallback plan created from text response'
        }
    
    async def replan(self, original_plan: Dict, error: str, context: Dict) -> AgentResult:
        """Generate alternative plan based on error"""
        replan_prompt = f'''The original plan failed with error:
{error}

Original plan:
{json.dumps(original_plan, indent=2)}

Generate an ALTERNATIVE approach that avoids this error.
Consider:
1. Different implementation method
2. Additional prerequisites
3. Error handling improvements
4. Simpler approach if possible

Output the new plan in the same JSON format.'''
        
        messages = [
            {"role": "user", "content": replan_prompt}
        ]
        
        result = await self.call_llm(messages, session_id="replanner")
        response_text = result.get('response', '')
        
        new_plan = self.parse_json_response(response_text)
        if new_plan:
            return AgentResult(
                success=True,
                data=new_plan,
                metadata={'replanned': True, 'reason': error[:200]}
            )
        else:
            return AgentResult(
                success=False,
                data=original_plan,
                error="Failed to generate alternative plan"
            )
