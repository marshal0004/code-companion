"""Enhanced Agentic Loop for CodeCompanion

Implements:
- Multi-level planning (Strategic → Tactical → Operational)
- Dynamic replanning on errors
- Self-correction with retries
- Verification loops
- Iteration tracking
"""

import json
import asyncio
import re
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from tools import ToolExecutor
from context_manager import ContextManager, PlanningContext

# Try to import orchestrator if available
try:
    from agents.orchestrator import AgentOrchestrator
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False


class LoopState(Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REPLANNING = "replanning"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class LoopMetrics:
    """Track loop execution metrics"""
    iterations: int = 0
    tool_calls: int = 0
    tool_failures: int = 0
    replans: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)
    
    def add_error(self, error: str):
        self.errors.append(error[:500])  # Limit error length
        if len(self.errors) > 10:
            self.errors = self.errors[-10:]  # Keep last 10


@dataclass
class ToolResult:
    """Result from tool execution"""
    tool_name: str
    success: bool
    result: Dict
    execution_time: float = 0.0


class AgenticLoop:
    """Enhanced agentic loop with planning and verification"""
    
    def __init__(self, 
                 llm_client,
                 tool_executor: ToolExecutor,
                 context_manager: ContextManager,
                 max_iterations: int = 15,
                 max_retries: int = 3):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.context_manager = context_manager
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        
        self.state = LoopState.PLANNING
        self.metrics = LoopMetrics()
        self.planning_context = PlanningContext()
    
    async def run(self, 
                  messages: List[Dict],
                  session_id: str = "default") -> AsyncGenerator[Dict, None]:
        """Run the agentic loop
        
        Yields events:
        - {'type': 'planning', 'plan': [...]}
        - {'type': 'thinking', 'content': '...'}
        - {'type': 'content', 'content': '...'}
        - {'type': 'tool_call', 'name': '...', 'args': {...}}
        - {'type': 'tool_result', 'name': '...', 'result': {...}}
        - {'type': 'verification', 'status': '...'}
        - {'type': 'done', 'metrics': {...}}
        - {'type': 'error', 'message': '...'}
        """
        self.state = LoopState.PLANNING
        self.metrics = LoopMetrics()
        
        conversation_messages = messages.copy()
        consecutive_failures = 0
        
        while self.metrics.iterations < self.max_iterations:
            self.metrics.iterations += 1
            
            try:
                # Get LLM response
                result = await self.llm_client.chat_stream(conversation_messages, session_id)
                response_text = result.get('response', '')
                tool_calls = result.get('tool_calls', [])
                raw_response = result.get('raw_response', response_text)
                
                # Yield thinking/planning if detected
                if self._is_planning_response(response_text):
                    yield {'type': 'planning', 'content': response_text}
                
                # Stream response content
                if response_text:
                    yield {'type': 'content', 'content': response_text}
                
                # If no tool calls, we're done
                if not tool_calls:
                    self.state = LoopState.COMPLETE
                    yield {
                        'type': 'done',
                        'response': response_text,
                        'metrics': self._get_metrics_dict()
                    }
                    break
                
                # Execute tool calls
                self.state = LoopState.EXECUTING
                tool_results = []
                
                for tool_call in tool_calls:
                    tool_name = tool_call.get('tool', '')
                    tool_args = tool_call.get('args', {})
                    
                    self.metrics.tool_calls += 1
                    
                    # Notify about tool execution
                    yield {
                        'type': 'tool_call',
                        'name': tool_name,
                        'args': tool_args,
                        'iteration': self.metrics.iterations
                    }
                    
                    # Execute tool
                    start_time = asyncio.get_event_loop().time()
                    result = self.tool_executor.execute_tool(tool_name, tool_args)
                    execution_time = asyncio.get_event_loop().time() - start_time
                    
                    tool_result = ToolResult(
                        tool_name=tool_name,
                        success=result.get('success', False),
                        result=result,
                        execution_time=execution_time
                    )
                    tool_results.append(tool_result)
                    
                    # Track failures
                    if not tool_result.success:
                        self.metrics.tool_failures += 1
                        self.metrics.add_error(f"{tool_name}: {result.get('error', 'Unknown error')}")
                    
                    # Yield tool result
                    yield {
                        'type': 'tool_result',
                        'name': tool_name,
                        'result': result,
                        'success': tool_result.success,
                        'execution_time': execution_time
                    }
                
                # Check if verification needed (after file modifications)
                if self._needs_verification(tool_calls):
                    self.state = LoopState.VERIFYING
                    verification = await self._verify_changes(tool_calls, tool_results)
                    yield {'type': 'verification', 'status': verification}
                    
                    if not verification.get('success', True):
                        # Add verification error to context
                        conversation_messages.append({
                            'role': 'user',
                            'content': f"Verification failed: {verification.get('error', 'Unknown error')}. Please fix the issue."
                        })
                        consecutive_failures += 1
                        self.metrics.replans += 1
                        continue
                
                # Add tool results to conversation
                conversation_messages.append({
                    'role': 'assistant',
                    'content': raw_response
                })
                
                tool_results_text = "\n".join([
                    f"Tool '{tr.tool_name}' result: {json.dumps(tr.result)}"
                    for tr in tool_results
                ])
                conversation_messages.append({
                    'role': 'tool',
                    'content': tool_results_text
                })
                
                # Check for consecutive failures
                all_failed = all(not tr.success for tr in tool_results)
                if all_failed:
                    consecutive_failures += 1
                    if consecutive_failures >= self.max_retries:
                        self.state = LoopState.ERROR
                        yield {
                            'type': 'error',
                            'message': f"Too many consecutive failures ({consecutive_failures})",
                            'errors': self.metrics.errors
                        }
                        break
                else:
                    consecutive_failures = 0
                
                # Small delay between iterations
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.metrics.add_error(str(e))
                consecutive_failures += 1
                
                if consecutive_failures >= self.max_retries:
                    self.state = LoopState.ERROR
                    yield {
                        'type': 'error',
                        'message': str(e),
                        'errors': self.metrics.errors
                    }
                    break
                
                # Try to recover
                yield {'type': 'warning', 'message': f"Error: {e}, retrying..."}
        
        # Max iterations reached
        if self.metrics.iterations >= self.max_iterations:
            yield {
                'type': 'warning',
                'message': f"Reached max iterations ({self.max_iterations})",
                'metrics': self._get_metrics_dict()
            }
    
    def _is_planning_response(self, text: str) -> bool:
        """Check if response contains planning"""
        planning_indicators = [
            'let me think', 'first', 'step 1', 'my plan',
            'i will', 'i\'ll', 'here\'s my approach',
            'breaking this down', 'to accomplish this'
        ]
        text_lower = text.lower()[:500]
        return any(indicator in text_lower for indicator in planning_indicators)
    
    def _needs_verification(self, tool_calls: List[Dict]) -> bool:
        """Check if tool calls need verification"""
        verification_tools = ['write_file', 'edit_file', 'run_command']
        return any(tc.get('tool') in verification_tools for tc in tool_calls)
    
    async def _verify_changes(self, tool_calls: List[Dict], results: List[ToolResult]) -> Dict:
        """Verify changes made by tools"""
        verification_results = {'success': True, 'details': []}
        
        for tc, result in zip(tool_calls, results):
            tool_name = tc.get('tool', '')
            
            if tool_name in ['write_file', 'edit_file']:
                path = tc.get('args', {}).get('path', '')
                
                # Basic verification: check file exists and is readable
                if path:
                    check_result = self.tool_executor.execute_tool('read_file', {'path': path})
                    if not check_result.get('success'):
                        verification_results['success'] = False
                        verification_results['details'].append(f"File verification failed: {path}")
                    
                    # If Python file, try syntax check
                    if path.endswith('.py'):
                        syntax_check = self._check_python_syntax(path)
                        if not syntax_check['success']:
                            verification_results['success'] = False
                            verification_results['error'] = syntax_check.get('error', 'Syntax error')
        
        return verification_results
    
    def _check_python_syntax(self, path: str) -> Dict:
        """Check Python file syntax"""
        try:
            import ast
            full_path = self.tool_executor.sanitize_path(path)
            with open(full_path, 'r') as f:
                code = f.read()
            ast.parse(code)
            return {'success': True}
        except SyntaxError as e:
            return {'success': False, 'error': f"Line {e.lineno}: {e.msg}"}
        except Exception as e:
            return {'success': True}  # Don't fail on other errors
    
    def _get_metrics_dict(self) -> Dict:
        """Get metrics as dictionary"""
        return {
            'iterations': self.metrics.iterations,
            'tool_calls': self.metrics.tool_calls,
            'tool_failures': self.metrics.tool_failures,
            'replans': self.metrics.replans,
            'errors': self.metrics.errors[:5],
            'state': self.state.value
        }


class EnhancedAgenticLoop(AgenticLoop):
    """Enhanced agentic loop with multi-agent orchestration support"""
    
    def __init__(self, 
                 llm_client,
                 tool_executor: ToolExecutor,
                 context_manager: ContextManager,
                 vector_store=None,
                 verifier=None,
                 use_orchestrator: bool = True,
                 max_iterations: int = 15,
                 max_retries: int = 3):
        super().__init__(llm_client, tool_executor, context_manager, max_iterations, max_retries)
        self.use_orchestrator = use_orchestrator and ORCHESTRATOR_AVAILABLE
        self.vector_store = vector_store
        self.verifier = verifier
        self.orchestrator = None
        
        if self.use_orchestrator:
            try:
                # Initialize orchestrator with sub-agents
                tools_dict = {
                    'read_file': tool_executor,
                    'write_file': tool_executor,
                    'edit_file': tool_executor,
                    'list_directory': tool_executor,
                    'run_command': tool_executor,
                    'search_text': tool_executor,
                    'git_status': tool_executor,
                    'git_diff': tool_executor,
                    'git_log': tool_executor,
                    'git_blame': tool_executor,
                    'semantic_search': tool_executor,
                    'index_workspace': tool_executor,
                    'index_stats': tool_executor,
                }
                self.orchestrator = AgentOrchestrator(
                    llm_client,
                    tools_dict,
                    vector_store=vector_store,
                    verifier=verifier
                )
            except Exception as e:
                print(f"Failed to initialize orchestrator: {e}")
                self.use_orchestrator = False
    
    async def run(self, 
                  messages: List[Dict],
                  session_id: str = "default",
                  use_agents: bool = None) -> AsyncGenerator[Dict, None]:
        """
        Run the agentic loop, optionally using multi-agent orchestration.
        
        Args:
            messages: Conversation messages
            session_id: Session identifier
            use_agents: Override to force agent/no-agent mode
        
        Yields: Events from execution
        """
        # Determine if we should use orchestrator
        should_use_agents = use_agents if use_agents is not None else self.use_orchestrator
        
        if should_use_agents and self.orchestrator:
            # Use multi-agent orchestration for complex tasks
            yield {'type': 'mode', 'mode': 'multi_agent'}
            
            # Extract user task from messages
            user_messages = [m for m in messages if m.get('role') == 'user']
            if not user_messages:
                yield {'type': 'error', 'message': 'No user message found'}
                return
            
            task = user_messages[-1].get('content', '')
            
            # Build context
            context = {
                'messages': messages,
                'session_id': session_id,
                'workspace_root': self.tool_executor.workspace_root,
                'history': messages[:-1] if len(messages) > 1 else []
            }
            
            # Run orchestrator
            async for event in self.orchestrator.execute(task, context, session_id):
                # Transform orchestrator events to loop events
                event_type = event.get('type')
                
                if event_type == 'phase':
                    yield {'type': 'thinking', 'content': f"[{event.get('phase', '')} phase]"}
                elif event_type == 'plan':
                    plan = event.get('plan', {})
                    # Format plan for display
                    plan_text = self._format_plan(plan)
                    yield {'type': 'planning', 'content': plan_text}
                elif event_type == 'step':
                    if event.get('status') == 'started':
                        step = event.get('step', {})
                        yield {'type': 'thinking', 'content': f"Executing: {step.get('action', 'unknown')}"}
                elif event_type == 'tool_call':
                    yield event  # Pass through
                elif event_type == 'tool_result':
                    yield event  # Pass through
                elif event_type == 'verification':
                    result = event.get('result', {})
                    yield {'type': 'content', 'content': f"[Verification: {result.get('overall', 'unknown')}]"}
                elif event_type == 'debug_analysis':
                    analysis = event.get('analysis', {})
                    yield {'type': 'content', 'content': f"[Debug: {analysis.get('error_type', 'analyzing')}]"}
                elif event_type == 'replan':
                    yield {'type': 'thinking', 'content': '[Replanning with alternative approach]'}
                elif event_type == 'done':
                    result = event.get('result', {})
                    summary = f"Task completed: {result.get('completed_steps', 0)} steps completed"
                    if result.get('failed_steps', 0) > 0:
                        summary += f", {result['failed_steps']} failed"
                    yield {'type': 'content', 'content': summary}
                    yield event
                elif event_type == 'error':
                    yield event
                else:
                    yield event
        else:
            # Use basic loop (existing implementation)
            yield {'type': 'mode', 'mode': 'basic'}
            async for event in super().run(messages, session_id):
                yield event
    
    def _format_plan(self, plan: Dict) -> str:
        """Format plan for display"""
        parts = []
        
        # Strategic level
        strategic = plan.get('strategic', [])
        if strategic:
            parts.append("## Strategic Goals:")
            for i, goal in enumerate(strategic, 1):
                if isinstance(goal, dict):
                    parts.append(f"{i}. {goal.get('goal', 'Unknown goal')}")
                else:
                    parts.append(f"{i}. {goal}")
        
        # Tactical level
        tactical = plan.get('tactical', [])
        if tactical:
            parts.append("\n## Tactical Phases:")
            for i, phase in enumerate(tactical, 1):
                if isinstance(phase, dict):
                    parts.append(f"{i}. {phase.get('phase', 'Unknown phase')}")
                else:
                    parts.append(f"{i}. {phase}")
        
        # Operational level (just count)
        operational = plan.get('operational', [])
        if operational:
            parts.append(f"\n## Operational Steps: {len(operational)} actions planned")
        
        return "\n".join(parts) if parts else "Plan created"


def get_enhanced_system_prompt() -> str:
    """Get enhanced system prompt with detailed instructions"""
    return '''You are CodeCompanion, an expert AI coding assistant with tool execution capabilities.

## CAPABILITIES
You can help with:
- Writing, editing, and analyzing code
- Reading and modifying files
- Executing shell commands safely
- Searching codebases (text + semantic)
- Git operations (status, diff, log, blame)
- Debugging and troubleshooting

## TOOL USAGE

When you need to interact with the system, use this EXACT format:

<TOOL_CALL>
{"tool": "tool_name", "args": {"arg1": "value1"}}
</TOOL_CALL>

### Available Tools:

1. **read_file** - Read file contents
   ```
   <TOOL_CALL>{"tool": "read_file", "args": {"path": "file.py", "start_line": 1, "end_line": 100}}</TOOL_CALL>
   ```

2. **write_file** - Create or overwrite file
   ```
   <TOOL_CALL>{"tool": "write_file", "args": {"path": "file.py", "content": "code here"}}</TOOL_CALL>
   ```

3. **edit_file** - Surgical edit (search/replace)
   ```
   <TOOL_CALL>{"tool": "edit_file", "args": {"path": "file.py", "old_text": "old code", "new_text": "new code"}}</TOOL_CALL>
   ```

4. **list_directory** - List files
   ```
   <TOOL_CALL>{"tool": "list_directory", "args": {"path": ".", "recursive": true}}</TOOL_CALL>
   ```

5. **run_command** - Execute shell command
   ```
   <TOOL_CALL>{"tool": "run_command", "args": {"command": "ls -la", "timeout": 30}}</TOOL_CALL>
   ```

6. **search_text** - Search in files
   ```
   <TOOL_CALL>{"tool": "search_text", "args": {"query": "def main", "path": ".", "file_pattern": "*.py"}}</TOOL_CALL>
   ```

7. **git_status** - Repository status
   ```
   <TOOL_CALL>{"tool": "git_status", "args": {}}</TOOL_CALL>
   ```

8. **git_diff** - Show changes
   ```
   <TOOL_CALL>{"tool": "git_diff", "args": {"staged": false, "file": null}}</TOOL_CALL>
   ```

9. **git_log** - Commit history
   ```
   <TOOL_CALL>{"tool": "git_log", "args": {"count": 10}}</TOOL_CALL>
   ```

10. **git_blame** - Line-by-line history
    ```
    <TOOL_CALL>{"tool": "git_blame", "args": {"path": "file.py"}}</TOOL_CALL>
    ```

11. **semantic_search** - AI-powered search
    ```
    <TOOL_CALL>{"tool": "semantic_search", "args": {"query": "authentication logic", "top_k": 5}}</TOOL_CALL>
    ```

## WORKFLOW

1. **Understand** - Read the request carefully
2. **Plan** - Break complex tasks into steps
3. **Investigate** - Use tools to gather information
4. **Execute** - Implement the solution
5. **Verify** - Check the results work correctly

## BEST PRACTICES

- Always read files before editing them
- Use edit_file for small changes, write_file for new/complete rewrites
- Test commands before running destructive operations
- Explain what you\'re doing before taking actions
- After tool execution, analyze results and continue or fix issues
- If something fails, try alternative approaches
- Keep responses concise but informative

## IMPORTANT RULES

- Use tools proactively when needed
- Always check tool results and handle errors
- For complex tasks, work iteratively
- Verify your changes work before completing
- Be helpful, accurate, and efficient
'''
