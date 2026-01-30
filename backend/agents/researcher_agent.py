"""Researcher Agent

Responsible for:
- Searching documentation and code patterns
- Learning from existing codebase
- Finding solutions to problems
- Gathering context for other agents
"""

import json
from typing import Dict, List, Any
from .base_agent import BaseAgent, AgentResult


class ResearcherAgent(BaseAgent):
    """Specialized agent for research and context gathering"""
    
    def __init__(self, llm_client, tools: Dict, vector_store=None):
        super().__init__(llm_client, tools, name="researcher")
        self.vector_store = vector_store
    
    def _get_system_prompt(self) -> str:
        return '''You are a Researcher Agent specialized in gathering information and context.

Your responsibilities:
1. Search existing codebase for patterns
2. Find relevant documentation
3. Identify similar implementations
4. Gather context for problem solving
5. Learn from existing code structure

## Research Methods:
- **Semantic Search**: Find relevant code by meaning
- **Pattern Matching**: Find similar implementations
- **Documentation Search**: Find relevant docs
- **Dependency Analysis**: Understand relationships

## Output Format:
```json
{
  "findings": [
    {"type": "code|doc|pattern", "source": "file/url", "content": "...", "relevance": 0.0-1.0}
  ],
  "summary": "Key insights",
  "recommendations": ["..."],
  "related_files": ["file1.py", "file2.py"]
}
```

## Research Guidelines:
1. Search before coding (avoid reinventing)
2. Find existing patterns in codebase
3. Identify reusable components
4. Note coding conventions used
5. Check for similar past solutions
'''
    
    async def execute(self, task: str, context: Dict) -> AgentResult:
        """Research a topic and gather context"""
        try:
            findings = await self._research(task, context)
            
            return AgentResult(
                success=True,
                data=findings,
                metadata={'agent': self.name, 'findings_count': len(findings.get('findings', []))}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                data={},
                error=str(e)
            )
    
    async def _research(self, query: str, context: Dict) -> Dict:
        """Perform research using available tools"""
        findings = {'findings': [], 'summary': '', 'recommendations': [], 'related_files': []}
        
        # 1. Semantic search if vector store available
        if self.vector_store:
            try:
                results = await self.vector_store.search(query, top_k=5)
                for result in results:
                    findings['findings'].append({
                        'type': 'code',
                        'source': result.get('file', 'unknown'),
                        'content': result.get('content', '')[:500],
                        'relevance': result.get('score', 0.5)
                    })
                    if result.get('file') not in findings['related_files']:
                        findings['related_files'].append(result.get('file'))
            except Exception as e:
                findings['findings'].append({
                    'type': 'error',
                    'source': 'semantic_search',
                    'content': f'Search failed: {e}'
                })
        
        # 2. Use LLM to analyze and summarize
        if findings['findings']:
            summary = await self._summarize_findings(query, findings['findings'])
            findings['summary'] = summary.get('summary', '')
            findings['recommendations'] = summary.get('recommendations', [])
        
        return findings
    
    async def _summarize_findings(self, query: str, findings: List[Dict]) -> Dict:
        """Use LLM to summarize research findings"""
        findings_text = "\n".join([
            f"- {f.get('type')}: {f.get('source')}: {f.get('content', '')[:200]}"
            for f in findings
        ])
        
        prompt = f'''Summarize these research findings for the query: {query}

Findings:
{findings_text}

Provide:
1. A brief summary of what was found
2. Recommendations for how to proceed
'''
        
        messages = [{"role": "user", "content": prompt}]
        result = await self.call_llm(messages, session_id="researcher")
        
        response_text = result.get('response', '')
        return {
            'summary': response_text[:500],
            'recommendations': []
        }
    
    async def find_patterns(self, pattern_type: str, context: Dict) -> AgentResult:
        """Find specific patterns in codebase"""
        query = f"Find {pattern_type} pattern implementations"
        return await self.execute(query, context)
    
    async def find_similar_code(self, code_snippet: str, context: Dict) -> AgentResult:
        """Find similar code in codebase"""
        query = f"Code similar to: {code_snippet[:200]}"
        return await self.execute(query, context)
