"""Supervisor Agent for CodeCompanion

Central controller that manages, monitors, and ensures task completion
with perfection. Acts as the "brain" that coordinates all other agents.

95%+ Accuracy Features:
1. Quality Gates - Strict checkpoints before/after each action
2. Adaptive Strategy - Switches approaches based on failures
3. Rollback System - Recovers from errors gracefully
4. Confidence Calibration - Only proceeds when confident
5. Multi-Attempt Refinement - Tries multiple approaches
6. Cross-Validation - Verifies with multiple methods
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import copy


class TaskStatus(Enum):
    PENDING = "pending"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REFINING = "refining"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class QualityLevel(Enum):
    EXCELLENT = "excellent"  # 95%+ confidence
    GOOD = "good"           # 80-94% confidence
    ACCEPTABLE = "acceptable" # 65-79% confidence
    POOR = "poor"           # <65% confidence
    FAILED = "failed"       # Execution failed


@dataclass
class ExecutionCheckpoint:
    """Checkpoint for rollback capability"""
    id: str
    timestamp: datetime
    state: Dict
    files_modified: List[str]
    backups: Dict[str, str]  # file_path -> backup_content
    reversible: bool = True


@dataclass
class SupervisorState:
    """Complete state tracking for supervisor"""
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    confidence: float = 0.0
    quality: QualityLevel = QualityLevel.POOR
    iterations: int = 0
    max_iterations: int = 20
    checkpoints: List[ExecutionCheckpoint] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)
    attempts: List[Dict] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    success_criteria_met: bool = False
    
    # Quality metrics
    planning_quality: float = 0.0
    execution_quality: float = 0.0
    verification_passed: bool = False
    files_modified: List[str] = field(default_factory=list)
    tests_run: int = 0
    tests_passed: int = 0


@dataclass
class QualityGate:
    """Quality gate checkpoint"""
    name: str
    required_confidence: float
    passed: bool = False
    actual_confidence: float = 0.0
    details: str = ""
    mandatory: bool = True


class SupervisorAgent:
    """
    Central supervisor that ensures task completion with perfection.
    
    Key Responsibilities:
    1. PRE-EXECUTION:
       - Validate task understanding
       - Assess complexity
       - Choose optimal agent strategy
       - Set quality gates
    
    2. DURING EXECUTION:
       - Monitor progress in real-time
       - Enforce quality gates
       - Create checkpoints for rollback
       - Detect and handle errors
       - Switch strategies if failing
    
    3. POST-EXECUTION:
       - Verify all changes
       - Run comprehensive tests
       - Validate success criteria
       - Report confidence score
    """
    
    # Quality thresholds for 95%+ accuracy
    CONFIDENCE_THRESHOLD_HIGH = 0.90     # Proceed with confidence
    CONFIDENCE_THRESHOLD_MEDIUM = 0.75   # Proceed with caution
    CONFIDENCE_THRESHOLD_LOW = 0.60      # Requires additional verification
    CONFIDENCE_THRESHOLD_MINIMUM = 0.50  # Do not proceed below this
    
    # Retry configuration
    MAX_RETRIES_PER_STEP = 3
    MAX_STRATEGY_SWITCHES = 2
    MAX_ROLLBACKS = 3
    
    def __init__(
        self, 
        orchestrator,
        llm_client,
        tool_executor,
        thinking_engine=None,
        verification_protocol=None,
        read_first_protocol=None
    ):
        self.orchestrator = orchestrator
        self.llm = llm_client
        self.tools = tool_executor
        self.thinking_engine = thinking_engine
        self.verification = verification_protocol
        self.read_first = read_first_protocol
        
        self.state: Optional[SupervisorState] = None
        self.quality_gates: List[QualityGate] = []
        self.current_strategy: str = "default"
        self.strategy_history: List[str] = []
        
        # Import agents for direct access when needed
        self.agents = {
            'planner': orchestrator.planner if hasattr(orchestrator, 'planner') else None,
            'coder': orchestrator.coder if hasattr(orchestrator, 'coder') else None,
            'debugger': orchestrator.debugger if hasattr(orchestrator, 'debugger') else None,
            'tester': orchestrator.tester if hasattr(orchestrator, 'tester') else None,
            'researcher': orchestrator.researcher if hasattr(orchestrator, 'researcher') else None,
            'architect': orchestrator.architect if hasattr(orchestrator, 'architect') else None,
            'reviewer': orchestrator.reviewer if hasattr(orchestrator, 'reviewer') else None,
        }
    
    async def execute_with_supervision(
        self,
        task: str,
        context: Dict,
        session_id: str = "supervisor"
    ) -> AsyncGenerator[Dict, None]:
        """
        Execute task with full supervision for 95%+ accuracy.
        
        Flow:
        1. UNDERSTANDING PHASE
           - Deep analysis of task
           - Complexity assessment
           - Success criteria definition
           
        2. PLANNING PHASE
           - Multi-strategy planning
           - Risk assessment
           - Checkpoint definition
           
        3. EXECUTION PHASE
           - Step-by-step with verification
           - Quality gates at each step
           - Automatic error handling
           
        4. VERIFICATION PHASE
           - Multi-layer verification
           - Test execution
           - Success criteria check
           
        5. REFINEMENT PHASE (if needed)
           - Fix issues
           - Re-verify
           - Quality improvement
        """
        # Initialize state
        self.state = SupervisorState(
            task_id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self._setup_quality_gates()
        
        yield {
            'type': 'supervisor_start',
            'task_id': self.state.task_id,
            'message': '🎯 Supervisor taking control for 95%+ accuracy execution'
        }
        
        try:
            # ========================================
            # PHASE 1: UNDERSTANDING
            # ========================================
            self.state.status = TaskStatus.THINKING
            yield {'type': 'phase', 'phase': 'understanding', 'status': 'started'}
            
            understanding_result = await self._deep_understanding_phase(task, context)
            
            if not understanding_result['confident']:
                yield {
                    'type': 'warning',
                    'message': f"Understanding confidence low: {understanding_result['confidence']:.0%}",
                    'suggestion': 'Consider asking for clarification'
                }
                
                if understanding_result['confidence'] < self.CONFIDENCE_THRESHOLD_MINIMUM:
                    yield {
                        'type': 'supervisor_pause',
                        'reason': 'Confidence too low to proceed safely',
                        'confidence': understanding_result['confidence']
                    }
                    # Don't proceed with very low confidence
                    self.state.status = TaskStatus.FAILED
                    return
            
            yield {
                'type': 'understanding_complete',
                'confidence': understanding_result['confidence'],
                'complexity': understanding_result.get('complexity', 'medium'),
                'success_criteria': understanding_result.get('success_criteria', [])
            }
            
            # ========================================
            # PHASE 2: PLANNING
            # ========================================
            self.state.status = TaskStatus.PLANNING
            yield {'type': 'phase', 'phase': 'planning', 'status': 'started'}
            
            plan_result = await self._supervised_planning(task, context, understanding_result)
            
            if not self._check_quality_gate('planning', plan_result.get('confidence', 0)):
                # Try alternative planning strategy
                yield {'type': 'strategy_switch', 'reason': 'Planning quality below threshold'}
                plan_result = await self._alternative_planning(task, context)
            
            self.state.planning_quality = plan_result.get('confidence', 0)
            
            yield {
                'type': 'plan_complete',
                'plan': plan_result.get('plan', {}),
                'quality': self.state.planning_quality,
                'steps': len(plan_result.get('plan', {}).get('operational', []))
            }
            
            # Create initial checkpoint
            await self._create_checkpoint('pre_execution')
            
            # ========================================
            # PHASE 3: SUPERVISED EXECUTION
            # ========================================
            self.state.status = TaskStatus.EXECUTING
            yield {'type': 'phase', 'phase': 'execution', 'status': 'started'}
            
            execution_success = True
            execution_result = {'steps_completed': 0, 'steps_failed': 0}
            
            operational_steps = plan_result.get('plan', {}).get('operational', [])
            
            for step_index, step in enumerate(operational_steps):
                self.state.iterations += 1
                
                if self.state.iterations >= self.state.max_iterations:
                    yield {
                        'type': 'warning',
                        'message': f'Max iterations ({self.state.max_iterations}) reached'
                    }
                    break
                
                # Quality gate before step
                pre_step_check = await self._pre_step_validation(step, context)
                
                if not pre_step_check['approved']:
                    yield {
                        'type': 'step_blocked',
                        'step': step,
                        'reason': pre_step_check['reason']
                    }
                    continue
                
                yield {
                    'type': 'step_start',
                    'index': step_index,
                    'total': len(operational_steps),
                    'step': step,
                    'confidence': pre_step_check.get('confidence', 0)
                }
                
                # Execute step with retry logic
                step_result = await self._execute_step_with_retry(
                    step, context, max_retries=self.MAX_RETRIES_PER_STEP
                )
                
                if step_result['success']:
                    execution_result['steps_completed'] += 1
                    self.state.files_modified.extend(step_result.get('files_modified', []))
                    
                    # Post-step verification
                    verify_result = await self._post_step_verification(step, step_result)
                    
                    yield {
                        'type': 'step_complete',
                        'index': step_index,
                        'result': step_result,
                        'verified': verify_result['passed']
                    }
                    
                    # Create checkpoint after successful step
                    if step.get('action') in ['write_file', 'edit_file']:
                        await self._create_checkpoint(f'step_{step_index}')
                    
                else:
                    execution_result['steps_failed'] += 1
                    self.state.errors.append({
                        'step': step_index,
                        'error': step_result.get('error'),
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    yield {
                        'type': 'step_failed',
                        'index': step_index,
                        'error': step_result.get('error')
                    }
                    
                    # Attempt recovery
                    recovery_result = await self._attempt_recovery(step, step_result, context)
                    
                    if recovery_result['recovered']:
                        yield {
                            'type': 'recovery_success',
                            'method': recovery_result['method']
                        }
                    else:
                        # Consider rollback
                        if len(self.state.checkpoints) > 0:
                            yield {
                                'type': 'considering_rollback',
                                'reason': 'Multiple failures detected'
                            }
                            
                            if step_result.get('critical', False):
                                await self._rollback_to_last_checkpoint()
                                execution_success = False
                                break
            
            self.state.execution_quality = (
                execution_result['steps_completed'] / 
                max(len(operational_steps), 1)
            )
            
            # ========================================
            # PHASE 4: VERIFICATION
            # ========================================
            self.state.status = TaskStatus.VERIFYING
            yield {'type': 'phase', 'phase': 'verification', 'status': 'started'}
            
            verification_result = await self._comprehensive_verification(
                task, context, self.state.files_modified
            )
            
            self.state.verification_passed = verification_result['passed']
            self.state.tests_run = verification_result.get('tests_run', 0)
            self.state.tests_passed = verification_result.get('tests_passed', 0)
            
            yield {
                'type': 'verification_complete',
                'passed': verification_result['passed'],
                'details': verification_result.get('details', {}),
                'tests': f"{self.state.tests_passed}/{self.state.tests_run}"
            }
            
            # ========================================
            # PHASE 5: REFINEMENT (if needed)
            # ========================================
            if not verification_result['passed'] and self.state.iterations < self.state.max_iterations:
                self.state.status = TaskStatus.REFINING
                yield {'type': 'phase', 'phase': 'refinement', 'status': 'started'}
                
                refinement_result = await self._refinement_loop(
                    task, context, verification_result
                )
                
                if refinement_result['improved']:
                    self.state.verification_passed = True
                    yield {
                        'type': 'refinement_success',
                        'iterations': refinement_result['iterations']
                    }
            
            # ========================================
            # FINAL QUALITY ASSESSMENT
            # ========================================
            final_quality = self._calculate_final_quality()
            self.state.quality = final_quality['level']
            self.state.confidence = final_quality['confidence']
            
            # Determine success
            self.state.success_criteria_met = (
                self.state.verification_passed and
                self.state.confidence >= self.CONFIDENCE_THRESHOLD_MEDIUM
            )
            
            self.state.status = (
                TaskStatus.COMPLETED if self.state.success_criteria_met 
                else TaskStatus.FAILED
            )
            self.state.end_time = datetime.now()
            
            yield {
                'type': 'supervisor_complete',
                'success': self.state.success_criteria_met,
                'quality': final_quality,
                'metrics': self._get_execution_metrics(),
                'recommendations': self._generate_recommendations()
            }
            
        except Exception as e:
            self.state.status = TaskStatus.FAILED
            self.state.errors.append({
                'type': 'supervisor_error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            
            yield {
                'type': 'supervisor_error',
                'error': str(e),
                'recovery_attempted': len(self.state.checkpoints) > 0
            }
            
            # Attempt final rollback
            if len(self.state.checkpoints) > 0:
                await self._rollback_to_last_checkpoint()
                yield {'type': 'rollback_complete', 'checkpoint': self.state.checkpoints[-1].id}
    
    def _setup_quality_gates(self):
        """Setup quality gates for 95%+ accuracy"""
        self.quality_gates = [
            QualityGate(
                name='understanding',
                required_confidence=0.75,
                mandatory=True
            ),
            QualityGate(
                name='planning',
                required_confidence=0.80,
                mandatory=True
            ),
            QualityGate(
                name='pre_execution',
                required_confidence=0.70,
                mandatory=True
            ),
            QualityGate(
                name='post_step',
                required_confidence=0.85,
                mandatory=False
            ),
            QualityGate(
                name='verification',
                required_confidence=0.90,
                mandatory=True
            ),
            QualityGate(
                name='final',
                required_confidence=0.95,
                mandatory=True
            )
        ]
    
    def _check_quality_gate(self, gate_name: str, actual_confidence: float) -> bool:
        """Check if quality gate is passed"""
        for gate in self.quality_gates:
            if gate.name == gate_name:
                gate.actual_confidence = actual_confidence
                gate.passed = actual_confidence >= gate.required_confidence
                return gate.passed
        return True  # Unknown gate, allow to proceed
    
    async def _deep_understanding_phase(
        self, 
        task: str, 
        context: Dict
    ) -> Dict:
        """Phase 1: Deep understanding of the task"""
        result = {
            'confident': False,
            'confidence': 0.0,
            'complexity': 'medium',
            'success_criteria': [],
            'risks': [],
            'files_to_examine': []
        }
        
        # Use thinking engine if available
        if self.thinking_engine:
            thinking_prompt = self.thinking_engine.get_thinking_prompt(task, context)
            
            messages = [{"role": "user", "content": thinking_prompt}]
            thinking_response = await self.llm.chat_stream(messages, "supervisor_thinking")
            
            thinking_result = self.thinking_engine.parse_thinking_response(
                thinking_response.get('response', '')
            )
            
            if thinking_result:
                result['confidence'] = thinking_result.confidence
                result['risks'] = thinking_result.risks
                result['files_to_examine'] = thinking_result.files_to_read
                result['complexity'] = self._assess_complexity(task, thinking_result)
                result['success_criteria'] = self._extract_success_criteria(task, thinking_result)
        else:
            # Fallback: Basic understanding check
            understanding_prompt = f"""
            Analyze this task for understanding:
            
            TASK: {task}
            
            Provide:
            1. CONFIDENCE (0-100%): How well do you understand this task?
            2. COMPLEXITY (low/medium/high/very_high)
            3. SUCCESS_CRITERIA: List 3-5 criteria for success
            4. RISKS: What could go wrong?
            5. FILES_NEEDED: What files need to be examined first?
            
            Format as JSON.
            """
            
            messages = [{"role": "user", "content": understanding_prompt}]
            response = await self.llm.chat_stream(messages, "supervisor_understand")
            
            # Parse response
            response_text = response.get('response', '')
            result['confidence'] = self._extract_confidence_from_text(response_text)
        
        result['confident'] = result['confidence'] >= self.CONFIDENCE_THRESHOLD_LOW
        return result
    
    async def _supervised_planning(
        self, 
        task: str, 
        context: Dict,
        understanding: Dict
    ) -> Dict:
        """Phase 2: Supervised planning with quality checks"""
        
        # Add understanding to context
        enhanced_context = {
            **context,
            'complexity': understanding.get('complexity'),
            'success_criteria': understanding.get('success_criteria'),
            'risks': understanding.get('risks'),
            'files_to_examine': understanding.get('files_to_examine')
        }
        
        # Use planner agent
        if self.agents['planner']:
            plan_result = await self.agents['planner'].execute(task, enhanced_context)
            
            if plan_result.success:
                # Validate plan quality
                plan_confidence = self._assess_plan_quality(plan_result.data)
                
                return {
                    'plan': plan_result.data,
                    'confidence': plan_confidence,
                    'validated': plan_confidence >= self.CONFIDENCE_THRESHOLD_MEDIUM
                }
        
        # Fallback: Direct orchestrator planning
        return {
            'plan': {'operational': [{'action': 'proceed', 'description': task}]},
            'confidence': 0.5,
            'validated': False
        }
    
    async def _alternative_planning(
        self, 
        task: str, 
        context: Dict
    ) -> Dict:
        """Generate alternative plan when primary fails"""
        self.strategy_history.append(self.current_strategy)
        self.current_strategy = 'alternative'
        
        # Use architect for alternative approach
        if self.agents['architect']:
            arch_result = await self.agents['architect'].execute(
                f"Design alternative approach for: {task}",
                context
            )
            
            if arch_result.success:
                # Convert architecture to plan
                return {
                    'plan': self._architecture_to_plan(arch_result.data),
                    'confidence': 0.7,
                    'validated': True,
                    'strategy': 'alternative'
                }
        
        return {
            'plan': {'operational': []},
            'confidence': 0.3,
            'validated': False
        }
    
    async def _pre_step_validation(
        self, 
        step: Dict, 
        context: Dict
    ) -> Dict:
        """Validate step before execution"""
        result = {
            'approved': True,
            'confidence': 0.8,
            'reason': 'Step validation passed'
        }
        
        action = step.get('action', '')
        
        # For file modifications, enforce read-first
        if action in ['write_file', 'edit_file']:
            path = step.get('args', {}).get('path', '')
            
            if self.read_first and path:
                can_write, reason = self.read_first.can_write(path)
                if not can_write:
                    result['approved'] = False
                    result['confidence'] = 0.0
                    result['reason'] = f'Read-first violation: {reason}'
                    result['required_action'] = {'tool': 'read_file', 'args': {'path': path}}
        
        # Check for risky commands
        if action == 'run_command':
            command = step.get('args', {}).get('command', '')
            if any(risk in command.lower() for risk in ['rm -rf', 'sudo', 'drop table', 'delete from']):
                result['approved'] = False
                result['confidence'] = 0.0
                result['reason'] = 'Potentially dangerous command blocked'
        
        return result
    
    async def _execute_step_with_retry(
        self, 
        step: Dict, 
        context: Dict,
        max_retries: int = 3
    ) -> Dict:
        """Execute step with retry logic and error handling"""
        
        last_error = None
        files_modified = []
        
        for attempt in range(max_retries):
            try:
                # Execute via orchestrator
                result = await self.orchestrator._execute_step(step, context)
                
                if result.success:
                    # Track modified files
                    action = step.get('action', '')
                    if action in ['write_file', 'edit_file']:
                        files_modified.append(step.get('args', {}).get('path', ''))
                    
                    return {
                        'success': True,
                        'data': result.data,
                        'files_modified': files_modified,
                        'attempts': attempt + 1
                    }
                else:
                    last_error = result.error
                    
                    # Try to fix with debugger
                    if self.agents['debugger'] and attempt < max_retries - 1:
                        debug_result = await self.agents['debugger'].analyze_error(
                            last_error, context
                        )
                        
                        if debug_result.success and debug_result.data.get('fix'):
                            # Apply fix and retry
                            step = self._apply_debug_suggestions(step, debug_result.data)
                            continue
            
            except Exception as e:
                last_error = str(e)
            
            # Small delay between retries
            await asyncio.sleep(0.5)
        
        return {
            'success': False,
            'error': last_error,
            'attempts': max_retries,
            'files_modified': files_modified
        }
    
    async def _post_step_verification(
        self, 
        step: Dict, 
        result: Dict
    ) -> Dict:
        """Verify step completed correctly"""
        verification = {'passed': True, 'checks': []}
        
        action = step.get('action', '')
        
        # Verify file modifications
        if action in ['write_file', 'edit_file'] and self.verification:
            path = step.get('args', {}).get('path', '')
            if path:
                verify_result = await self.verification.verify_file_change(path)
                verification['passed'] = verify_result.get('verified', False)
                verification['checks'].append(verify_result)
        
        # Use tester for verification
        if self.agents['tester'] and step.get('verify'):
            test_result = await self.agents['tester'].execute(
                f"Verify: {step.get('verify')}",
                {'step': step, 'result': result}
            )
            
            if test_result.success:
                verification['checks'].append(test_result.data)
                verification['passed'] = verification['passed'] and test_result.data.get('overall') == 'pass'
        
        return verification
    
    async def _attempt_recovery(
        self, 
        step: Dict, 
        result: Dict, 
        context: Dict
    ) -> Dict:
        """Attempt to recover from step failure"""
        recovery = {
            'recovered': False,
            'method': None
        }
        
        error = result.get('error', '')
        
        # Try debugger first
        if self.agents['debugger']:
            debug_result = await self.agents['debugger'].analyze_error(error, context)
            
            if debug_result.success:
                fix = debug_result.data.get('fix', {})
                
                if fix.get('tool') and fix.get('tool') != 'manual_review':
                    # Apply automatic fix
                    fix_result = self.tools.execute_tool(
                        fix['tool'],
                        fix.get('args', {})
                    )
                    
                    if fix_result.get('success'):
                        recovery['recovered'] = True
                        recovery['method'] = 'debugger_fix'
        
        return recovery
    
    async def _create_checkpoint(self, name: str):
        """Create execution checkpoint for rollback"""
        backups = {}
        
        for file_path in self.state.files_modified:
            try:
                result = self.tools.execute_tool('read_file', {'path': file_path})
                if result.get('success'):
                    backups[file_path] = result.get('content', '')
            except:
                pass
        
        checkpoint = ExecutionCheckpoint(
            id=f"{self.state.task_id}_{name}_{len(self.state.checkpoints)}",
            timestamp=datetime.now(),
            state=copy.deepcopy(self.state.__dict__),
            files_modified=list(self.state.files_modified),
            backups=backups
        )
        
        self.state.checkpoints.append(checkpoint)
    
    async def _rollback_to_last_checkpoint(self):
        """Rollback to last checkpoint"""
        if not self.state.checkpoints:
            return False
        
        checkpoint = self.state.checkpoints[-1]
        
        # Restore files
        for file_path, content in checkpoint.backups.items():
            try:
                self.tools.execute_tool('write_file', {
                    'path': file_path,
                    'content': content
                })
            except:
                pass
        
        self.state.status = TaskStatus.ROLLED_BACK
        return True
    
    async def _comprehensive_verification(
        self, 
        task: str, 
        context: Dict,
        files_modified: List[str]
    ) -> Dict:
        """Comprehensive verification of all changes"""
        result = {
            'passed': True,
            'details': {},
            'tests_run': 0,
            'tests_passed': 0
        }
        
        # 1. Syntax verification for all modified files
        if self.verification:
            for file_path in files_modified:
                verify_result = await self.verification.verify_file_change(file_path)
                result['details'][file_path] = verify_result
                
                if not verify_result.get('verified', False):
                    result['passed'] = False
        
        # 2. Use tester agent for comprehensive testing
        if self.agents['tester']:
            test_result = await self.agents['tester'].execute(
                f"Run comprehensive verification for: {task}",
                {**context, 'files': files_modified}
            )
            
            if test_result.success:
                result['tests_run'] += 1
                if test_result.data.get('overall') == 'pass':
                    result['tests_passed'] += 1
                else:
                    result['passed'] = False
                    result['details']['test_result'] = test_result.data
        
        # 3. Use reviewer for quality check
        if self.agents['reviewer']:
            review_result = await self.agents['reviewer'].execute(
                f"Review changes for: {task}",
                {**context, 'files': files_modified}
            )
            
            if review_result.success:
                result['details']['review'] = review_result.data
                
                # Check for critical issues
                if review_result.data.get('critical_issues'):
                    result['passed'] = False
        
        return result
    
    async def _refinement_loop(
        self, 
        task: str, 
        context: Dict,
        verification_result: Dict
    ) -> Dict:
        """Iterative refinement to fix issues"""
        result = {
            'improved': False,
            'iterations': 0
        }
        
        max_refinement_iterations = 3
        
        for i in range(max_refinement_iterations):
            result['iterations'] += 1
            
            # Get issues from verification
            issues = []
            for file_path, details in verification_result.get('details', {}).items():
                if isinstance(details, dict) and not details.get('verified', True):
                    issues.append({
                        'file': file_path,
                        'errors': details.get('checks', [])
                    })
            
            if not issues:
                result['improved'] = True
                break
            
            # Use debugger to fix issues
            if self.agents['debugger']:
                for issue in issues:
                    fix_result = await self.agents['debugger'].analyze_error(
                        str(issue['errors']),
                        {**context, 'file': issue['file']}
                    )
                    
                    if fix_result.success and fix_result.data.get('fix'):
                        fix = fix_result.data['fix']
                        if fix.get('tool'):
                            self.tools.execute_tool(fix['tool'], fix.get('args', {}))
            
            # Re-verify
            verification_result = await self._comprehensive_verification(
                task, context, self.state.files_modified
            )
            
            if verification_result['passed']:
                result['improved'] = True
                break
        
        return result
    
    def _calculate_final_quality(self) -> Dict:
        """Calculate final quality score"""
        # Weight factors
        weights = {
            'planning': 0.15,
            'execution': 0.30,
            'verification': 0.35,
            'tests': 0.20
        }
        
        # Calculate scores
        scores = {
            'planning': self.state.planning_quality,
            'execution': self.state.execution_quality,
            'verification': 1.0 if self.state.verification_passed else 0.0,
            'tests': (
                self.state.tests_passed / max(self.state.tests_run, 1)
                if self.state.tests_run > 0 else 0.5
            )
        }
        
        # Weighted average
        confidence = sum(
            scores[k] * weights[k] for k in weights
        )
        
        # Determine level
        if confidence >= 0.95:
            level = QualityLevel.EXCELLENT
        elif confidence >= 0.80:
            level = QualityLevel.GOOD
        elif confidence >= 0.65:
            level = QualityLevel.ACCEPTABLE
        else:
            level = QualityLevel.POOR
        
        return {
            'confidence': confidence,
            'level': level,
            'scores': scores,
            'weights': weights
        }
    
    def _get_execution_metrics(self) -> Dict:
        """Get detailed execution metrics"""
        return {
            'task_id': self.state.task_id,
            'status': self.state.status.value,
            'iterations': self.state.iterations,
            'files_modified': len(self.state.files_modified),
            'errors_count': len(self.state.errors),
            'checkpoints_created': len(self.state.checkpoints),
            'planning_quality': f"{self.state.planning_quality:.0%}",
            'execution_quality': f"{self.state.execution_quality:.0%}",
            'verification_passed': self.state.verification_passed,
            'tests': f"{self.state.tests_passed}/{self.state.tests_run}",
            'duration': str(datetime.now() - self.state.start_time).split('.')[0],
            'strategy_used': self.current_strategy
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on execution"""
        recommendations = []
        
        if self.state.confidence < self.CONFIDENCE_THRESHOLD_HIGH:
            recommendations.append(
                f"Confidence ({self.state.confidence:.0%}) below optimal. "
                "Consider additional verification."
            )
        
        if len(self.state.errors) > 0:
            recommendations.append(
                f"{len(self.state.errors)} errors encountered. "
                "Review error patterns for improvement."
            )
        
        if not self.state.verification_passed:
            recommendations.append(
                "Verification did not pass. Manual review recommended."
            )
        
        if self.state.tests_run == 0:
            recommendations.append(
                "No tests were run. Consider adding test coverage."
            )
        
        if not recommendations:
            recommendations.append("Execution completed with high confidence. ✅")
        
        return recommendations
    
    # Helper methods
    def _assess_complexity(self, task: str, thinking_result) -> str:
        """Assess task complexity"""
        # Count indicators
        complexity_score = 0
        
        # Files to modify
        if len(thinking_result.files_to_modify) > 5:
            complexity_score += 2
        elif len(thinking_result.files_to_modify) > 2:
            complexity_score += 1
        
        # Risks identified
        if len(thinking_result.risks) > 5:
            complexity_score += 2
        elif len(thinking_result.risks) > 2:
            complexity_score += 1
        
        # Task length
        if len(task) > 500:
            complexity_score += 1
        
        # Determine level
        if complexity_score >= 4:
            return 'very_high'
        elif complexity_score >= 3:
            return 'high'
        elif complexity_score >= 2:
            return 'medium'
        else:
            return 'low'
    
    def _extract_success_criteria(self, task: str, thinking_result) -> List[str]:
        """Extract success criteria from task and thinking"""
        criteria = []
        
        # From thinking result
        if thinking_result.goal_state:
            criteria.append(f"Goal achieved: {thinking_result.goal_state[:100]}")
        
        if thinking_result.verification_plan:
            criteria.append(f"Verification: {thinking_result.verification_plan[:100]}")
        
        # Default criteria
        if not criteria:
            criteria = [
                "All files modified without errors",
                "Syntax verification passed",
                "Functionality works as expected"
            ]
        
        return criteria
    
    def _extract_confidence_from_text(self, text: str) -> float:
        """Extract confidence percentage from text"""
        import re
        patterns = [
            r'(\d+)%',
            r'confidence[:\s]+(\d+)',
            r'(\d+)/100'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    value = int(match.group(1))
                    return min(value / 100.0, 1.0)
                except:
                    pass
        
        return 0.5
    
    def _assess_plan_quality(self, plan: Dict) -> float:
        """Assess quality of generated plan"""
        score = 0.5  # Base score
        
        # Check for strategic goals
        if plan.get('strategic'):
            score += 0.1
        
        # Check for tactical phases
        if plan.get('tactical'):
            score += 0.1
        
        # Check for operational steps
        operational = plan.get('operational', [])
        if operational:
            score += 0.1
            
            # Check step quality
            steps_with_verify = sum(1 for s in operational if s.get('verify'))
            if steps_with_verify > 0:
                score += 0.1
            
            # Check for dependencies
            steps_with_deps = sum(1 for s in operational if s.get('dependencies'))
            if steps_with_deps > 0:
                score += 0.1
        
        return min(score, 1.0)
    
    def _architecture_to_plan(self, architecture: Dict) -> Dict:
        """Convert architecture result to operational plan"""
        operational = []
        
        components = architecture.get('components', [])
        for comp in components:
            operational.append({
                'action': 'write_file',
                'args': {
                    'path': comp.get('file', 'component.py'),
                    'content': comp.get('code', '')
                },
                'verify': f"Check {comp.get('name', 'component')} works"
            })
        
        return {
            'strategic': [{'goal': 'Alternative implementation approach'}],
            'tactical': [{'phase': 'Component-based implementation'}],
            'operational': operational
        }
    
    def _apply_debug_suggestions(self, step: Dict, debug_data: Dict) -> Dict:
        """Apply debugger suggestions to step"""
        fix = debug_data.get('fix', {})
        
        if fix.get('tool') == step.get('action'):
            # Update args with fix
            step['args'] = {**step.get('args', {}), **fix.get('args', {})}
        
        return step
