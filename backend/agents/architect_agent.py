"""Architect Agent

Responsible for:
- System design and architecture
- Project structure planning
- Component design
- Interface definitions
"""

import json
from typing import Dict, List, Any
from .base_agent import BaseAgent, AgentResult


class ArchitectAgent(BaseAgent):
    """Specialized agent for system design and architecture"""
    
    def __init__(self, llm_client, tools: Dict):
        super().__init__(llm_client, tools, name="architect")
    
    def _get_system_prompt(self) -> str:
        return '''You are an Architect Agent specialized in system design and project structure.

Your responsibilities:
1. Design system architecture
2. Plan project structure
3. Define component interfaces
4. Identify patterns and best practices
5. Create scalable designs

## Architecture Principles:
- **Separation of Concerns**: Each module has single responsibility
- **Loose Coupling**: Minimize dependencies between modules
- **High Cohesion**: Related code stays together
- **SOLID Principles**: Follow design best practices
- **DRY**: Don\'t repeat yourself

## Design Outputs:
- Project structure recommendations
- Component diagrams (text-based)
- Interface definitions
- Data flow descriptions
- Technology recommendations

## Output Format:
```json
{
  "architecture": {
    "type": "monolithic|microservices|modular",
    "components": [
      {"name": "...", "responsibility": "...", "interfaces": [...]}
    ],
    "data_flow": "Description of data flow",
    "patterns_used": ["pattern1", "pattern2"]
  },
  "structure": {
    "directories": [
      {"path": "src/", "purpose": "..."}
    ],
    "files": [
      {"path": "src/main.py", "purpose": "..."}
    ]
  },
  "recommendations": ["..."],
  "risks": ["..."]
}
```

## Guidelines:
1. Analyze requirements thoroughly
2. Consider scalability from start
3. Follow language/framework conventions
4. Plan for testing and maintenance
5. Document design decisions
'''
    
    async def execute(self, task: str, context: Dict) -> AgentResult:
        """Design architecture for task"""
        try:
            design = await self._create_design(task, context)
            
            return AgentResult(
                success=True,
                data=design,
                metadata={'agent': self.name}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                data={},
                error=str(e)
            )
    
    async def _create_design(self, task: str, context: Dict) -> Dict:
        """Create architecture design using LLM"""
        prompt = f'''{self.system_prompt}

## Task:
{task}

## Context:
{json.dumps(context, indent=2)}

## Instructions:
Create an architecture design for this task.
Consider existing code structure if provided.
Output in the JSON format specified above.
'''
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.call_llm(messages, session_id="architect")
        response_text = result.get('response', '')
        
        # Try to parse JSON design
        design = self.parse_json_response(response_text)
        if design:
            return design
        else:
            return {
                'architecture': {'type': 'unknown', 'description': response_text[:500]},
                'structure': {},
                'recommendations': [],
                'raw_response': response_text
            }
    
    async def analyze_structure(self, context: Dict) -> AgentResult:
        """Analyze existing project structure"""
        return await self.execute("Analyze current project structure and suggest improvements", context)
    
    async def design_component(self, component_desc: str, context: Dict) -> AgentResult:
        """Design a specific component"""
        return await self.execute(f"Design component: {component_desc}", context)
