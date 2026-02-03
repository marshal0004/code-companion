"""Agent Registry and Factory

Central registry for all agents in CodeCompanion.
Provides factory methods and agent discovery.
"""

from typing import Dict, List, Optional, Type
from dataclasses import dataclass

# Import all agents
from .base_agent import BaseAgent, AgentResult
from .planner_agent import PlannerAgent
from .coder_agent import CoderAgent
from .debugger_agent import DebuggerAgent
from .tester_agent import TesterAgent
from .researcher_agent import ResearcherAgent
from .architect_agent import ArchitectAgent
from .reviewer_agent import ReviewerAgent
from .orchestrator import AgentOrchestrator

# Import new agents
try:
    from .supervisor_agent import SupervisorAgent
    SUPERVISOR_AVAILABLE = True
except ImportError:
    SUPERVISOR_AVAILABLE = False

try:
    from .enhanced_orchestrator import EnhancedOrchestrator
    ENHANCED_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ENHANCED_ORCHESTRATOR_AVAILABLE = False


@dataclass
class AgentInfo:
    """Information about an agent"""
    name: str
    agent_class: Type
    description: str
    capabilities: List[str]
    dependencies: List[str]
    priority: int  # Higher = more important


# Agent Registry
AGENT_REGISTRY: Dict[str, AgentInfo] = {
    'supervisor': AgentInfo(
        name='SupervisorAgent',
        agent_class=SupervisorAgent if SUPERVISOR_AVAILABLE else None,
        description='Central supervisor that ensures 95%+ accuracy through quality gates, rollback, and adaptive strategies',
        capabilities=[
            'Quality gate enforcement',
            'Rollback on failure',
            'Adaptive strategy switching',
            'Confidence calibration',
            'Multi-attempt refinement',
            'Cross-validation'
        ],
        dependencies=['orchestrator', 'thinking_engine', 'verification_protocol'],
        priority=100
    ),
    'orchestrator': AgentInfo(
        name='AgentOrchestrator',
        agent_class=AgentOrchestrator,
        description='Main coordinator that routes tasks to specialized sub-agents',
        capabilities=[
            'Task routing',
            'Multi-agent coordination',
            'Plan execution',
            'Error handling',
            'Replanning'
        ],
        dependencies=['planner', 'coder', 'debugger', 'tester'],
        priority=90
    ),
    'enhanced_orchestrator': AgentInfo(
        name='EnhancedOrchestrator',
        agent_class=EnhancedOrchestrator if ENHANCED_ORCHESTRATOR_AVAILABLE else None,
        description='Advanced orchestrator with adaptive strategies and cross-validation',
        capabilities=[
            'Adaptive strategy selection',
            'Conservative execution mode',
            'Exploratory execution mode',
            'Iterative execution mode',
            'Cross-validation',
            'Strategy learning'
        ],
        dependencies=['orchestrator'],
        priority=95
    ),
    'planner': AgentInfo(
        name='PlannerAgent',
        agent_class=PlannerAgent,
        description='Task decomposition and hierarchical planning',
        capabilities=[
            'Strategic planning',
            'Tactical planning',
            'Operational planning',
            'RAG-powered context',
            'Dynamic replanning'
        ],
        dependencies=[],
        priority=80
    ),
    'coder': AgentInfo(
        name='CoderAgent',
        agent_class=CoderAgent,
        description='Code generation and editing with surgical precision',
        capabilities=[
            'Code generation',
            'Surgical edits',
            'Pattern following',
            'Multi-language support'
        ],
        dependencies=['surgical_edit'],
        priority=85
    ),
    'debugger': AgentInfo(
        name='DebuggerAgent',
        agent_class=DebuggerAgent,
        description='Error analysis, classification, and fix generation',
        capabilities=[
            'Error classification (5 types)',
            'Root cause analysis',
            'Fix generation',
            'Recovery strategies'
        ],
        dependencies=[],
        priority=75
    ),
    'tester': AgentInfo(
        name='TesterAgent',
        agent_class=TesterAgent,
        description='Code verification and test generation',
        capabilities=[
            'Syntax checking',
            'Import verification',
            'Lint checking',
            'Test generation',
            'Multi-layer verification'
        ],
        dependencies=['verification'],
        priority=70
    ),
    'researcher': AgentInfo(
        name='ResearcherAgent',
        agent_class=ResearcherAgent,
        description='Context gathering and pattern search',
        capabilities=[
            'Codebase search',
            'Semantic search',
            'Pattern discovery',
            'Context gathering'
        ],
        dependencies=['vector_store'],
        priority=60
    ),
    'architect': AgentInfo(
        name='ArchitectAgent',
        agent_class=ArchitectAgent,
        description='System design and structure',
        capabilities=[
            'Architecture design',
            'Component structure',
            'API design',
            'System planning'
        ],
        dependencies=[],
        priority=65
    ),
    'reviewer': AgentInfo(
        name='ReviewerAgent',
        agent_class=ReviewerAgent,
        description='Code review and quality assurance',
        capabilities=[
            'Code review',
            'Best practices check',
            'Quality scoring',
            'Improvement suggestions'
        ],
        dependencies=[],
        priority=55
    )
}


class AgentFactory:
    """
    Factory for creating and managing agents.
    """
    
    def __init__(self, llm_client, tools: Dict, vector_store=None, verifier=None):
        self.llm = llm_client
        self.tools = tools
        self.vector_store = vector_store
        self.verifier = verifier
        self._instances: Dict[str, BaseAgent] = {}
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Get or create agent by name.
        """
        if name in self._instances:
            return self._instances[name]
        
        if name not in AGENT_REGISTRY:
            return None
        
        info = AGENT_REGISTRY[name]
        if info.agent_class is None:
            return None
        
        # Create instance based on agent type
        if name == 'supervisor':
            orchestrator = self.get_agent('orchestrator')
            if orchestrator:
                instance = SupervisorAgent(
                    orchestrator=orchestrator,
                    llm_client=self.llm,
                    tool_executor=self.tools.get('executor') or self.tools
                )
        elif name == 'orchestrator':
            instance = AgentOrchestrator(
                self.llm, self.tools, self.vector_store, self.verifier
            )
        elif name == 'enhanced_orchestrator':
            instance = EnhancedOrchestrator(
                self.llm, self.tools, self.vector_store, self.verifier
            )
        elif name == 'planner':
            instance = PlannerAgent(self.llm, self.tools, self.vector_store)
        elif name == 'coder':
            instance = CoderAgent(self.llm, self.tools)
        elif name == 'debugger':
            instance = DebuggerAgent(self.llm, self.tools)
        elif name == 'tester':
            instance = TesterAgent(self.llm, self.tools, self.verifier)
        elif name == 'researcher':
            instance = ResearcherAgent(self.llm, self.tools, self.vector_store)
        elif name == 'architect':
            instance = ArchitectAgent(self.llm, self.tools)
        elif name == 'reviewer':
            instance = ReviewerAgent(self.llm, self.tools)
        else:
            return None
        
        self._instances[name] = instance
        return instance
    
    def get_all_agents(self) -> Dict[str, BaseAgent]:
        """
        Get all available agents.
        """
        agents = {}
        for name in AGENT_REGISTRY:
            agent = self.get_agent(name)
            if agent:
                agents[name] = agent
        return agents
    
    def get_agent_info(self, name: str) -> Optional[AgentInfo]:
        """
        Get information about an agent.
        """
        return AGENT_REGISTRY.get(name)
    
    def list_agents(self) -> List[Dict]:
        """
        List all registered agents with their info.
        """
        return [
            {
                'name': info.name,
                'description': info.description,
                'capabilities': info.capabilities,
                'available': info.agent_class is not None,
                'priority': info.priority
            }
            for info in sorted(
                AGENT_REGISTRY.values(),
                key=lambda x: x.priority,
                reverse=True
            )
        ]
    
    def get_agents_for_task(self, task_type: str) -> List[str]:
        """
        Get recommended agents for a task type.
        """
        task_agent_map = {
            'coding': ['supervisor', 'orchestrator', 'coder', 'tester'],
            'debugging': ['debugger', 'tester', 'coder'],
            'testing': ['tester', 'reviewer'],
            'planning': ['planner', 'architect'],
            'review': ['reviewer', 'tester'],
            'research': ['researcher', 'architect'],
            'architecture': ['architect', 'planner', 'reviewer']
        }
        
        return task_agent_map.get(task_type, ['orchestrator'])


# Convenience function
def create_full_agent_system(
    llm_client,
    tools: Dict,
    vector_store=None,
    verifier=None,
    use_supervisor: bool = True
) -> Dict:
    """
    Create complete agent system with all agents.
    
    Returns dict with:
    - factory: AgentFactory instance
    - supervisor: SupervisorAgent (if available and requested)
    - orchestrator: AgentOrchestrator
    - agents: Dict of all agents
    """
    factory = AgentFactory(llm_client, tools, vector_store, verifier)
    
    result = {
        'factory': factory,
        'orchestrator': factory.get_agent('orchestrator'),
        'agents': factory.get_all_agents()
    }
    
    if use_supervisor and SUPERVISOR_AVAILABLE:
        result['supervisor'] = factory.get_agent('supervisor')
    
    return result
