"""Context Management System for CodeCompanion

Handles:
- CLAUDE.md file loading (project context)
- Token counting and budget management
- Context window optimization
- Priority-based context selection
"""

import os
import tiktoken
from pathlib import Path
from typing import Dict, List, Optional, Any
import json


class ContextManager:
    """Manages context for LLM interactions"""
    
    def __init__(self, workspace_root: str = "/app", max_tokens: int = 8192):
        self.workspace_root = Path(workspace_root)
        self.max_tokens = max_tokens
        self.system_reserve = 2000  # Reserved for system prompt
        self.history_reserve = 4000  # For conversation history
        self.file_reserve = 2000    # For file contents
        
        # Try to load tiktoken encoder
        try:
            self.encoder = tiktoken.encoding_for_model("gpt-4")
        except:
            self.encoder = None
        
        # Project context from CLAUDE.md files
        self.project_context = ""
        self._load_project_context()
    
    def _load_project_context(self):
        """Load context from CLAUDE.md files (hierarchical)"""
        context_parts = []
        
        # Check for CLAUDE.md files in order of priority
        claude_files = [
            self.workspace_root / "CLAUDE.md",
            self.workspace_root / ".claude" / "CLAUDE.md",
            Path.home() / ".claude" / "CLAUDE.md",
        ]
        
        for claude_file in claude_files:
            if claude_file.exists():
                try:
                    with open(claude_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():
                            context_parts.append(f"### Context from {claude_file.name}:\n{content}")
                except:
                    continue
        
        # Also check for README.md as fallback
        readme = self.workspace_root / "README.md"
        if readme.exists() and not context_parts:
            try:
                with open(readme, 'r', encoding='utf-8') as f:
                    content = f.read()[:2000]  # Limit README content
                    context_parts.append(f"### Project README:\n{content}")
            except:
                pass
        
        self.project_context = "\n\n".join(context_parts)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.encoder:
            return len(self.encoder.encode(text))
        # Rough estimate: ~4 chars per token
        return len(text) // 4
    
    def get_project_context(self) -> str:
        """Get project-specific context"""
        return self.project_context
    
    def reload_context(self):
        """Reload project context (call after changes)"""
        self._load_project_context()
    
    def optimize_history(self, messages: List[Dict], max_tokens: int = None) -> List[Dict]:
        """Optimize conversation history to fit within token budget"""
        if max_tokens is None:
            max_tokens = self.history_reserve
        
        optimized = []
        total_tokens = 0
        
        # Process messages in reverse (keep recent messages)
        for msg in reversed(messages):
            msg_tokens = self.count_tokens(msg.get('content', ''))
            
            if total_tokens + msg_tokens > max_tokens:
                # Truncate or skip if too long
                if len(optimized) == 0:
                    # Must include at least the last message
                    truncated = msg['content'][:max_tokens * 3]  # Rough truncation
                    optimized.insert(0, {**msg, 'content': truncated + '...[truncated]'})
                break
            
            optimized.insert(0, msg)
            total_tokens += msg_tokens
        
        return optimized
    
    def get_file_context(self, file_paths: List[str], max_tokens: int = None) -> str:
        """Get context from relevant files"""
        if max_tokens is None:
            max_tokens = self.file_reserve
        
        context_parts = []
        total_tokens = 0
        
        for path in file_paths:
            try:
                full_path = self.workspace_root / path
                if full_path.exists() and full_path.is_file():
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    tokens = self.count_tokens(content)
                    if total_tokens + tokens > max_tokens:
                        # Truncate content
                        remaining = max_tokens - total_tokens
                        content = content[:remaining * 3] + "\n...[truncated]"
                        tokens = remaining
                    
                    context_parts.append(f"### File: {path}\n```\n{content}\n```")
                    total_tokens += tokens
                    
                    if total_tokens >= max_tokens:
                        break
            except:
                continue
        
        return "\n\n".join(context_parts)
    
    def build_context(self, 
                     messages: List[Dict],
                     system_prompt: str,
                     relevant_files: List[str] = None) -> Dict[str, Any]:
        """Build optimized context for LLM
        
        Returns:
            Dict with 'system_prompt', 'messages', 'total_tokens'
        """
        # Start with system prompt
        enhanced_system = system_prompt
        
        # Add project context if available
        if self.project_context:
            enhanced_system += f"\n\n## Project Context\n{self.project_context}"
        
        system_tokens = self.count_tokens(enhanced_system)
        
        # Calculate remaining budget
        remaining = self.max_tokens - system_tokens
        history_budget = int(remaining * 0.7)  # 70% for history
        file_budget = int(remaining * 0.3)     # 30% for files
        
        # Optimize history
        optimized_messages = self.optimize_history(messages, history_budget)
        
        # Add file context if provided
        if relevant_files:
            file_context = self.get_file_context(relevant_files, file_budget)
            if file_context:
                enhanced_system += f"\n\n## Relevant Files\n{file_context}"
        
        total_tokens = (
            self.count_tokens(enhanced_system) +
            sum(self.count_tokens(m.get('content', '')) for m in optimized_messages)
        )
        
        return {
            'system_prompt': enhanced_system,
            'messages': optimized_messages,
            'total_tokens': total_tokens,
            'has_project_context': bool(self.project_context)
        }
    
    def get_workspace_summary(self) -> str:
        """Get a summary of the workspace structure"""
        summary_parts = []
        
        # Count files by type
        file_counts = {}
        for ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.md', '.json']:
            count = len(list(self.workspace_root.rglob(f'*{ext}')))
            if count > 0:
                file_counts[ext] = count
        
        if file_counts:
            summary_parts.append("File types: " + ", ".join(f"{ext}:{count}" for ext, count in file_counts.items()))
        
        # List top-level directories
        dirs = [d.name for d in self.workspace_root.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if dirs:
            summary_parts.append("Directories: " + ", ".join(dirs[:10]))
        
        return "\n".join(summary_parts)


class PlanningContext:
    """Context for multi-level planning"""
    
    def __init__(self):
        self.strategic_plan: List[str] = []
        self.tactical_plan: List[Dict] = []
        self.current_phase: int = 0
        self.completed_steps: List[str] = []
        self.failed_steps: List[Dict] = []
    
    def set_strategic_plan(self, steps: List[str]):
        """Set high-level strategic plan"""
        self.strategic_plan = steps
        self.current_phase = 0
    
    def add_tactical_step(self, step: Dict):
        """Add tactical step"""
        self.tactical_plan.append(step)
    
    def mark_complete(self, step: str):
        """Mark a step as complete"""
        self.completed_steps.append(step)
    
    def mark_failed(self, step: str, error: str):
        """Mark a step as failed"""
        self.failed_steps.append({'step': step, 'error': error})
    
    def get_progress(self) -> Dict:
        """Get current progress"""
        return {
            'strategic_plan': self.strategic_plan,
            'current_phase': self.current_phase,
            'completed': len(self.completed_steps),
            'failed': len(self.failed_steps),
            'completed_steps': self.completed_steps,
            'failed_steps': self.failed_steps
        }
    
    def to_prompt(self) -> str:
        """Convert planning context to prompt format"""
        parts = []
        
        if self.strategic_plan:
            parts.append("Strategic Plan:")
            for i, step in enumerate(self.strategic_plan):
                status = "✓" if step in self.completed_steps else "○"
                parts.append(f"  {status} {i+1}. {step}")
        
        if self.failed_steps:
            parts.append("\nFailed Steps (need retry):")
            for fail in self.failed_steps[-3:]:  # Last 3 failures
                parts.append(f"  ✗ {fail['step']}: {fail['error'][:100]}")
        
        return "\n".join(parts)
