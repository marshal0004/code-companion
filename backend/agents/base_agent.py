"""Base Agent Class

Provides common functionality for all specialized agents.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AgentResult:
    """Standard result format for all agents"""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseAgent(ABC):
    """Base class for all specialized agents"""
    
    def __init__(self, llm_client, tools: Dict, name: str = "base"):
        self.llm = llm_client
        self.tools = tools
        self.name = name
        self.system_prompt = self._get_system_prompt()
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for this agent - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def execute(self, task: str, context: Dict) -> AgentResult:
        """Execute a task - must be implemented by subclasses"""
        pass
    
    def build_prompt(self, task: str, context: Dict) -> str:
        """Build prompt for this agent"""
        context_str = json.dumps(context, indent=2) if context else "No context"
        return f"{self.system_prompt}\n\n## Task:\n{task}\n\n## Context:\n{context_str}"
    
    async def call_llm(self, messages: List[Dict], session_id: str = "agent") -> Dict:
        """Call the LLM with messages"""
        try:
            result = await self.llm.chat_stream(messages, session_id)
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response': ''
            }
    
    def parse_json_response(self, text: str) -> Optional[Dict]:
        """Extract JSON from response text"""
        try:
            # Try direct parse
            return json.loads(text)
        except:
            # Try to find JSON in markdown code blocks
            import re
            json_pattern = r'```(?:json)?\s*({.*?})\s*```'
            match = re.search(json_pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass
            
            # Try to find any JSON-like structure
            json_pattern = r'{[^{}]*(?:{[^{}]*}[^{}]*)*}'
            matches = re.findall(json_pattern, text, re.DOTALL)
            for match in reversed(matches):  # Start from end
                try:
                    return json.loads(match)
                except:
                    continue
            
            return None
    
    def extract_code_blocks(self, text: str) -> List[Dict]:
        """Extract code blocks from markdown"""
        import re
        pattern = r'```(\w*)\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        return [{'language': lang or 'text', 'code': code.strip()} 
                for lang, code in matches]
