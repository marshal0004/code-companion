"""Agent System for CodeCompanion

Implements multi-agent architecture similar to Claude Code:
- Orchestrator: Routes tasks to specialized agents
- Planner: Task decomposition and hierarchical planning
- Coder: Code generation and editing
- Debugger: Error analysis and fixing
- Tester: Test generation and verification
"""

from .base_agent import BaseAgent
from .orchestrator import AgentOrchestrator
from .planner_agent import PlannerAgent
from .coder_agent import CoderAgent
from .debugger_agent import DebuggerAgent
from .tester_agent import TesterAgent

__all__ = [
    'BaseAgent',
    'AgentOrchestrator',
    'PlannerAgent',
    'CoderAgent',
    'DebuggerAgent',
    'TesterAgent'
]
