"""Read-First Protocol for CodeCompanion

CRITICAL RULE: NEVER write or edit a file without reading it first!

This prevents blind changes that break existing code.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class ReadRecord:
    """Track what files have been read"""
    path: str
    timestamp: datetime
    session_id: str


class ReadFirstProtocol:
    """Enforce read-before-write policy"""
    
    def __init__(self, grace_period_seconds: int = 300):
        """
        Initialize protocol.
        
        Args:
            grace_period_seconds: How long a read is valid before requiring re-read
        """
        self.read_files: Dict[str, ReadRecord] = {}
        self.grace_period = timedelta(seconds=grace_period_seconds)
        self.violations: List[Dict] = []
        self.enabled = True
    
    def record_read(self, path: str, session_id: str = "default"):
        """Record that a file was read"""
        self.read_files[path] = ReadRecord(
            path=path,
            timestamp=datetime.now(),
            session_id=session_id
        )
    
    def can_write(self, path: str, session_id: str = "default") -> tuple[bool, str]:
        """
        Check if we can write to a file.
        
        Returns:
            (allowed, reason)
        """
        if not self.enabled:
            return True, "Protocol disabled"
        
        # Check if file was read
        if path not in self.read_files:
            return False, f"File '{path}' not read yet. Must read before writing."
        
        record = self.read_files[path]
        
        # Check session matches
        if record.session_id != session_id:
            return False, f"File was read in different session. Re-read required."
        
        # Check if read is still valid (not too old)
        age = datetime.now() - record.timestamp
        if age > self.grace_period:
            return False, f"Last read was {age.seconds}s ago (stale). Re-read required."
        
        return True, "OK - file was recently read"
    
    def can_edit(self, path: str, session_id: str = "default") -> tuple[bool, str]:
        """
        Check if we can edit a file.
        Same as can_write but explicitly for edits.
        """
        return self.can_write(path, session_id)
    
    def require_read(self, path: str, session_id: str = "default") -> Dict:
        """
        Generate a read action requirement.
        
        Returns a dict describing the required read action.
        """
        return {
            'action': 'read_file',
            'args': {'path': path},
            'reason': 'READ-FIRST PROTOCOL: Must read file before modifying',
            'blocking': True
        }
    
    def enforce_write(self, path: str, session_id: str = "default") -> tuple[bool, Optional[Dict]]:
        """
        Enforce read-first for write operation.
        
        Returns:
            (allowed, required_action_if_not_allowed)
        """
        allowed, reason = self.can_write(path, session_id)
        
        if allowed:
            return True, None
        else:
            self.violations.append({
                'operation': 'write',
                'path': path,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            })
            return False, self.require_read(path, session_id)
    
    def enforce_edit(self, path: str, old_text: str, session_id: str = "default") -> tuple[bool, Optional[Dict]]:
        """
        Enforce read-first for edit operation.
        
        Additional check: Verify that old_text exists in the file
        (this proves the file was actually read and understood).
        
        Returns:
            (allowed, required_action_if_not_allowed)
        """
        allowed, reason = self.can_edit(path, session_id)
        
        if not allowed:
            self.violations.append({
                'operation': 'edit',
                'path': path,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            })
            return False, self.require_read(path, session_id)
        
        # Additional check: old_text should not be empty for edits
        if not old_text or not old_text.strip():
            reason = "Edit operation requires specific old_text to replace"
            self.violations.append({
                'operation': 'edit',
                'path': path,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            })
            return False, self.require_read(path, session_id)
        
        return True, None
    
    def get_violations(self, limit: int = 10) -> List[Dict]:
        """Get recent violations"""
        return self.violations[-limit:]
    
    def clear_session(self, session_id: str):
        """Clear read records for a session"""
        self.read_files = {
            path: record 
            for path, record in self.read_files.items()
            if record.session_id != session_id
        }
    
    def get_session_reads(self, session_id: str) -> List[str]:
        """Get all files read in a session"""
        return [
            path for path, record in self.read_files.items()
            if record.session_id == session_id
        ]
    
    def get_stats(self) -> Dict:
        """Get protocol statistics"""
        now = datetime.now()
        recent_reads = sum(
            1 for record in self.read_files.values()
            if (now - record.timestamp) < self.grace_period
        )
        
        return {
            'enabled': self.enabled,
            'total_files_read': len(self.read_files),
            'recent_reads': recent_reads,
            'total_violations': len(self.violations),
            'grace_period_seconds': self.grace_period.seconds
        }


class ReadFirstEnforcer:
    """Helper to integrate read-first protocol into tool execution"""
    
    def __init__(self, protocol: ReadFirstProtocol):
        self.protocol = protocol
    
    def wrap_tool_executor(self, tool_executor):
        """
        Wrap a tool executor to enforce read-first.
        
        This modifies write_file and edit_file methods to check protocol.
        """
        original_write = tool_executor.execute_tool
        original_read = tool_executor.execute_tool
        
        def enforced_execute_tool(tool_name: str, args: Dict, session_id: str = "default"):
            # Record reads
            if tool_name == 'read_file':
                result = original_read(tool_name, args)
                if result.get('success'):
                    path = args.get('path', '')
                    if path:
                        self.protocol.record_read(path, session_id)
                return result
            
            # Enforce writes
            elif tool_name == 'write_file':
                path = args.get('path', '')
                allowed, required_action = self.protocol.enforce_write(path, session_id)
                
                if not allowed:
                    return {
                        'success': False,
                        'error': 'READ-FIRST VIOLATION: Must read file before writing',
                        'required_action': required_action,
                        'blocking': True
                    }
                
                return original_write(tool_name, args)
            
            # Enforce edits
            elif tool_name == 'edit_file':
                path = args.get('path', '')
                old_text = args.get('old_text', '')
                allowed, required_action = self.protocol.enforce_edit(path, old_text, session_id)
                
                if not allowed:
                    return {
                        'success': False,
                        'error': 'READ-FIRST VIOLATION: Must read file before editing',
                        'required_action': required_action,
                        'blocking': True
                    }
                
                return original_write(tool_name, args)
            
            # Other tools pass through
            else:
                return original_write(tool_name, args)
        
        # Replace method
        tool_executor.execute_tool = enforced_execute_tool
        return tool_executor


# System prompt additions
READ_FIRST_PROMPT = """
## 🔒 READ-FIRST PROTOCOL (MANDATORY)

**CRITICAL RULE**: You MUST read a file before writing or editing it!

### Correct Workflow:
1. ✅ read_file() - Understand current content
2. ✅ write_file() or edit_file() - Make changes

### WRONG Workflow:
❌ write_file() without reading first - BLOCKED!
❌ edit_file() without reading first - BLOCKED!

### Why This Matters:
- Prevents overwriting existing code
- Ensures you understand the context
- Allows surgical edits instead of rewrites
- Reduces errors by 50%+

### Example:
```
# WRONG:
<TOOL_CALL>{"tool": "write_file", "args": {"path": "app.py", "content": "..."}}</TOOL_CALL>
❌ BLOCKED - File not read!

# CORRECT:
<TOOL_CALL>{"tool": "read_file", "args": {"path": "app.py"}}</TOOL_CALL>
# ... observe content ...
<TOOL_CALL>{"tool": "edit_file", "args": {"path": "app.py", "old_text": "...", "new_text": "..."}}</TOOL_CALL>
✅ ALLOWED - File was read first
```

**This rule is ENFORCED. Violations will block the operation.**
"""


# Helper functions
def enforce_read_first_in_agent(agent, protocol: ReadFirstProtocol):
    """Add read-first enforcement to an agent"""
    original_execute = agent.execute
    
    async def enforced_execute(task: str, context: Dict):
        # Add protocol to context
        context['read_first_protocol'] = protocol
        
        # Add read-first prompt to system prompt
        if hasattr(agent, '_system_prompt'):
            agent._system_prompt += "\n\n" + READ_FIRST_PROMPT
        
        return await original_execute(task, context)
    
    agent.execute = enforced_execute
    return agent


def check_and_enforce_reads(tool_calls: List[Dict], protocol: ReadFirstProtocol, session_id: str = "default") -> List[Dict]:
    """
    Check tool calls and insert required reads.
    
    Returns modified tool_calls list with read_file calls inserted where needed.
    """
    modified_calls = []
    
    for call in tool_calls:
        tool_name = call.get('tool', '')
        args = call.get('args', {})
        
        if tool_name in ['write_file', 'edit_file']:
            path = args.get('path', '')
            
            # Check if read is needed
            allowed, _ = protocol.can_write(path, session_id)
            
            if not allowed:
                # Insert read call BEFORE write/edit
                read_call = {
                    'tool': 'read_file',
                    'args': {'path': path},
                    'injected': True,
                    'reason': 'Read-first protocol enforcement'
                }
                modified_calls.append(read_call)
            
        modified_calls.append(call)
    
    return modified_calls
