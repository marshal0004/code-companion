"""Agent System for CodeCompanion

Implements multi-agent architecture matching Claude Code:
- Orchestrator: Routes tasks to specialized agents
- Planner: Task decomposition and hierarchical planning
- Coder: Code generation and editing
- Debugger: Error analysis and fixing
- Tester: Test generation and verification
- Researcher: Context gathering and pattern search (NEW)
- Architect: System design and structure (NEW)
- Reviewer: Code review and quality assurance (NEW)
"""

from .base_agent import BaseAgent, AgentResult
from .orchestrator import AgentOrchestrator
from .planner_agent import PlannerAgent
from .coder_agent import CoderAgent
from .debugger_agent import DebuggerAgent
from .tester_agent import TesterAgent
from .researcher_agent import ResearcherAgent
from .architect_agent import ArchitectAgent
from .reviewer_agent import ReviewerAgent

__all__ = [
    'BaseAgent',
    'AgentResult',
    'AgentOrchestrator',
    'PlannerAgent',
    'CoderAgent',
    'DebuggerAgent',
    'TesterAgent',
    'ResearcherAgent',
    'ArchitectAgent',
    'ReviewerAgent'
]
