"""Agent Orchestrator

Main coordinator that routes tasks to specialized sub-agents.
Implements the Claude Code multi-agent architecture.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime

from .base_agent import AgentResult
from .planner_agent import PlannerAgent
from .coder_agent import CoderAgent
from .debugger_agent import DebuggerAgent
from .tester_agent import TesterAgent
from .researcher_agent import ResearcherAgent
from .architect_agent import ArchitectAgent
from .reviewer_agent import ReviewerAgent


@dataclass
class ExecutionState:
    """Track execution state"""
    current_phase: str = "planning"
    plan: Dict = field(default_factory=dict)
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    replans: int = 0
    iterations: int = 0
    start_time: datetime = field(default_factory=datetime.now)


class AgentOrchestrator:
    """
    Main orchestrator that delegates tasks to specialized sub-agents.
    
    Architecture (8 agents - matching Claude Code):
    - PlannerAgent: Task decomposition and planning
    - CoderAgent: Code generation and editing
    - DebuggerAgent: Error analysis and fixing
    - TesterAgent: Verification and testing
    - ResearcherAgent: Context gathering and pattern search
    - ArchitectAgent: System design and structure
    - ReviewerAgent: Code review and quality assurance
    """
    
    def __init__(self, llm_client, tools: Dict, vector_store=None, verifier=None):
        """Initialize orchestrator with all sub-agents"""
        self.llm = llm_client
        self.tools = tools
        
        # Core agents
        self.planner = PlannerAgent(llm_client, tools, vector_store)
        self.coder = CoderAgent(llm_client, tools)
        self.debugger = DebuggerAgent(llm_client, tools)
        self.tester = TesterAgent(llm_client, tools, verifier)
        
        # Additional agents (matching Claude Code)
        self.researcher = ResearcherAgent(llm_client, tools, vector_store)
        self.architect = ArchitectAgent(llm_client, tools)
        self.reviewer = ReviewerAgent(llm_client, tools)
        
        self.state = ExecutionState()
        self.max_iterations = 15
        self.max_replans = 3
    
    async def execute(self, 
                     task: str, 
                     context: Dict,
                     session_id: str = "orchestrator") -> AsyncGenerator[Dict, None]:
        """
        Execute a task using multi-agent coordination.
        
        Flow:
        1. Planning: Planner creates hierarchical plan
        2. Execution: Execute operational steps
        3. Verification: Tester verifies changes
        4. Error Handling: Debugger analyzes and fixes errors
        5. Replanning: Planner creates alternative plan if needed
        
        Yields:
        - {'type': 'phase', 'phase': 'planning|executing|verifying|...'}
        - {'type': 'agent', 'agent': 'planner|coder|debugger|tester', 'action': '...'}
        - {'type': 'plan', 'plan': {...}}
        - {'type': 'step', 'step': {...}, 'status': 'started|completed|failed'}
        - {'type': 'tool_call', 'tool': '...', 'args': {...}}
        - {'type': 'tool_result', 'tool': '...', 'result': {...}}
        - {'type': 'verification', 'result': {...}}
        - {'type': 'error', 'error': '...', 'recovery': {...}}
        - {'type': 'replan', 'reason': '...', 'new_plan': {...}}
        - {'type': 'done', 'result': {...}}
        """
        self.state = ExecutionState()
        
        try:
            # Phase 1: Planning
            yield {'type': 'phase', 'phase': 'planning', 'agent': 'planner'}
            
            plan_result = await self.planner.execute(task, context)
            
            if not plan_result.success:
                yield {
                    'type': 'error',
                    'phase': 'planning',
                    'error': plan_result.error
                }
                return
            
            self.state.plan = plan_result.data
            yield {
                'type': 'plan',
                'plan': self.state.plan,
                'metadata': plan_result.metadata
            }
            
            # Phase 2: Execute Operational Steps
            yield {'type': 'phase', 'phase': 'executing'}
            
            operational_steps = self.state.plan.get('operational', [])
            
            for i, step in enumerate(operational_steps):
                if self.state.iterations >= self.max_iterations:
                    yield {
                        'type': 'warning',
                        'message': f'Max iterations ({self.max_iterations}) reached'
                    }
                    break
                
                self.state.iterations += 1
                
                # Execute step
                yield {
                    'type': 'step',
                    'step': step,
                    'index': i,
                    'total': len(operational_steps),
                    'status': 'started'
                }
                
                step_result = await self._execute_step(step, context)
                
                if step_result.success:
                    self.state.completed_steps.append(step.get('action', f'step_{i}'))
                    yield {
                        'type': 'step',
                        'step': step,
                        'index': i,
                        'status': 'completed',
                        'result': step_result.data
                    }
                    
                    # Verify if needed
                    if step.get('verify'):
                        verify_result = await self._verify_step(step, step_result, context)
                        yield {
                            'type': 'verification',
                            'step': step,
                            'result': verify_result.data
                        }
                        
                        if not verify_result.success:
                            # Verification failed - try to fix
                            yield {'type': 'phase', 'phase': 'debugging', 'agent': 'debugger'}
                            
                            fix_result = await self._handle_verification_failure(
                                step, verify_result, context
                            )
                            
                            if fix_result.success:
                                yield {
                                    'type': 'fix_applied',
                                    'fix': fix_result.data
                                }
                            else:
                                # Fix failed - replan
                                if self.state.replans < self.max_replans:
                                    replan_result = await self._replan(
                                        verify_result.error, context
                                    )
                                    if replan_result.success:
                                        yield {
                                            'type': 'replan',
                                            'reason': verify_result.error,
                                            'new_plan': replan_result.data
                                        }
                                        self.state.plan = replan_result.data
                                        # Restart execution with new plan
                                        operational_steps = self.state.plan.get('operational', [])
                                        continue
                                else:
                                    yield {
                                        'type': 'error',
                                        'message': 'Max replans reached',
                                        'failed_step': step
                                    }
                                    break
                else:
                    # Step execution failed
                    self.state.failed_steps.append(step.get('action', f'step_{i}'))
                    yield {
                        'type': 'step',
                        'step': step,
                        'index': i,
                        'status': 'failed',
                        'error': step_result.error
                    }
                    
                    # Try to debug and fix
                    yield {'type': 'phase', 'phase': 'debugging', 'agent': 'debugger'}
                    
                    debug_result = await self.debugger.analyze_error(
                        step_result.error, 
                        {**context, 'step': step}
                    )
                    
                    yield {
                        'type': 'debug_analysis',
                        'analysis': debug_result.data
                    }
                    
                    if debug_result.success and debug_result.data.get('fix'):
                        # Apply fix
                        fix = debug_result.data['fix']
                        fix_result = await self._apply_fix(fix, context)
                        
                        if fix_result.success:
                            yield {
                                'type': 'fix_applied',
                                'fix': debug_result.data
                            }
                            # Retry the step
                            continue
                        else:
                            # Fix failed - try replanning
                            if self.state.replans < self.max_replans:
                                replan_result = await self._replan(
                                    step_result.error, context
                                )
                                if replan_result.success:
                                    yield {
                                        'type': 'replan',
                                        'reason': step_result.error,
                                        'new_plan': replan_result.data
                                    }
                                    self.state.plan = replan_result.data
                                    operational_steps = self.state.plan.get('operational', [])
                                    break
            
            # Phase 3: Final Summary
            yield {
                'type': 'done',
                'result': {
                    'completed_steps': len(self.state.completed_steps),
                    'failed_steps': len(self.state.failed_steps),
                    'replans': self.state.replans,
                    'iterations': self.state.iterations,
                    'success': len(self.state.failed_steps) == 0
                },
                'plan': self.state.plan
            }
            
        except Exception as e:
            yield {
                'type': 'error',
                'phase': self.state.current_phase,
                'error': str(e)
            }
    
    async def _execute_step(self, step: Dict, context: Dict) -> AgentResult:
        """Execute a single operational step"""
        action = step.get('action', '')
        
        # Determine which agent should handle this
        if action in ['write_file', 'edit_file', 'read_file', 'generate_code']:
            # Coding task
            return await self.coder.execute(json.dumps(step), context)
        elif action == 'verify':
            # Testing task
            return await self.tester.execute('verify', {**context, **step})
        else:
            # Generic tool execution
            from tools import ToolExecutor
            tool_executor = ToolExecutor(workspace_root=context.get('workspace_root', '/app'))
            
            tool_name = step.get('action', '')
            tool_args = step.get('args', {})
            
            result = tool_executor.execute_tool(tool_name, tool_args)
            
            return AgentResult(
                success=result.get('success', False),
                data=result,
                error=result.get('error')
            )
    
    async def _verify_step(self, step: Dict, result: AgentResult, context: Dict) -> AgentResult:
        """Verify a step's result"""
        verify_instruction = step.get('verify', '')
        
        if not verify_instruction:
            return AgentResult(success=True, data={'skipped': True})
        
        # Use tester agent
        return await self.tester.execute(
            f"Verify: {verify_instruction}",
            {**context, 'step_result': result.data}
        )
    
    async def _handle_verification_failure(self, step: Dict, 
                                          verify_result: AgentResult,
                                          context: Dict) -> AgentResult:
        """Handle verification failure by debugging"""
        error = verify_result.error or "Verification failed"
        
        debug_result = await self.debugger.analyze_error(
            error,
            {**context, 'step': step, 'verify_result': verify_result.data}
        )
        
        if debug_result.success and debug_result.data.get('fix'):
            return await self._apply_fix(debug_result.data['fix'], context)
        
        return AgentResult(success=False, data={}, error="Could not generate fix")
    
    async def _apply_fix(self, fix: Dict, context: Dict) -> AgentResult:
        """Apply a fix suggested by debugger"""
        tool_name = fix.get('tool', '')
        tool_args = fix.get('args', {})
        
        if not tool_name or tool_name == 'manual_review':
            return AgentResult(
                success=False,
                data={},
                error="Manual review required"
            )
        
        from tools import ToolExecutor
        tool_executor = ToolExecutor(workspace_root=context.get('workspace_root', '/app'))
        
        result = tool_executor.execute_tool(tool_name, tool_args)
        
        return AgentResult(
            success=result.get('success', False),
            data=result,
            error=result.get('error')
        )
    
    async def _replan(self, error: str, context: Dict) -> AgentResult:
        """Create alternative plan"""
        self.state.replans += 1
        
        return await self.planner.replan(
            self.state.plan,
            error,
            context
        )
    
    def analyze_task_type(self, task: str) -> str:
        """Analyze what type of task this is"""
        task_lower = task.lower()
        
        if any(keyword in task_lower for keyword in ['debug', 'fix', 'error', 'issue', 'bug']):
            return 'debugging'
        elif any(keyword in task_lower for keyword in ['test', 'verify', 'check']):
            return 'testing'
        elif any(keyword in task_lower for keyword in ['architect', 'structure', 'design system']):
            return 'architecture'
        elif any(keyword in task_lower for keyword in ['review', 'check code', 'code review', 'quality']):
            return 'review'
        elif any(keyword in task_lower for keyword in ['search', 'find', 'look for', 'research', 'pattern']):
            return 'research'
        elif any(keyword in task_lower for keyword in ['plan', 'design']):
            return 'planning'
        else:
            return 'coding'
    
    async def execute_specialized(self, task: str, context: Dict, session_id: str = "orchestrator") -> AsyncGenerator[Dict, None]:
        """Execute task using specialized agents based on task type.
        
        This provides direct agent routing for specialized tasks without
        going through the full planning cycle.
        """
        task_type = self.analyze_task_type(task)
        
        yield {'type': 'task_analysis', 'task_type': task_type, 'agent': task_type}
        
        try:
            if task_type == 'debugging':
                yield {'type': 'phase', 'phase': 'debugging', 'agent': 'debugger'}
                result = await self.debugger.analyze_error(task, context)
                yield {'type': 'result', 'agent': 'debugger', 'data': result.data}
                
            elif task_type == 'testing':
                yield {'type': 'phase', 'phase': 'testing', 'agent': 'tester'}
                result = await self.tester.execute(task, context)
                yield {'type': 'result', 'agent': 'tester', 'data': result.data}
                
            elif task_type == 'architecture':
                yield {'type': 'phase', 'phase': 'architecture', 'agent': 'architect'}
                result = await self.architect.execute(task, context)
                yield {'type': 'result', 'agent': 'architect', 'data': result.data}
                
            elif task_type == 'review':
                yield {'type': 'phase', 'phase': 'review', 'agent': 'reviewer'}
                result = await self.reviewer.execute(task, context)
                yield {'type': 'result', 'agent': 'reviewer', 'data': result.data}
                
            elif task_type == 'research':
                yield {'type': 'phase', 'phase': 'research', 'agent': 'researcher'}
                result = await self.researcher.execute(task, context)
                yield {'type': 'result', 'agent': 'researcher', 'data': result.data}
                
            elif task_type == 'planning':
                yield {'type': 'phase', 'phase': 'planning', 'agent': 'planner'}
                result = await self.planner.execute(task, context)
                yield {'type': 'result', 'agent': 'planner', 'data': result.data}
                
            else:  # coding
                # For coding tasks, use full orchestration
                async for event in self.execute(task, context, session_id):
                    yield event
                return
            
            yield {'type': 'done', 'success': result.success if result else False}
            
        except Exception as e:
            yield {'type': 'error', 'error': str(e)}
    
    def get_agent_status(self) -> Dict:
        """Get status of all agents"""
        return {
            'agents': {
                'planner': {'name': 'PlannerAgent', 'status': 'ready', 'capability': 'Task decomposition and hierarchical planning'},
                'coder': {'name': 'CoderAgent', 'status': 'ready', 'capability': 'Code generation and editing'},
                'debugger': {'name': 'DebuggerAgent', 'status': 'ready', 'capability': 'Error analysis and fixing'},
                'tester': {'name': 'TesterAgent', 'status': 'ready', 'capability': 'Test generation and verification'},
                'researcher': {'name': 'ResearcherAgent', 'status': 'ready', 'capability': 'Context gathering and pattern search'},
                'architect': {'name': 'ArchitectAgent', 'status': 'ready', 'capability': 'System design and structure'},
                'reviewer': {'name': 'ReviewerAgent', 'status': 'ready', 'capability': 'Code review and quality assurance'}
            },
            'total_agents': 7,
            'orchestrator': 'ready'
        }
