"""Project Memory System for CodeCompanion

Equivalent to Claude Code's CLAUDE.md - persistent project instructions.
"""

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json


class ProjectMemory:
    """Manage persistent project instructions"""
    
    MEMORY_FILE = ".codecompanion/project_memory.md"
    LEARNED_PATTERNS_FILE = ".codecompanion/learned_patterns.json"
    
    def __init__(self, workspace_root: str):
        self.workspace = Path(workspace_root)
        self.memory_path = self.workspace / self.MEMORY_FILE
        self.patterns_path = self.workspace / self.LEARNED_PATTERNS_FILE
        
        self._ensure_memory_exists()
    
    def _ensure_memory_exists(self):
        """Create default memory if doesn't exist"""
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.memory_path.exists():
            self.memory_path.write_text(self._get_default_memory())
        
        if not self.patterns_path.exists():
            self.patterns_path.write_text(json.dumps({
                "patterns": [],
                "conventions": [],
                "warnings": []
            }, indent=2))
    
    def _get_default_memory(self) -> str:
        """Default project memory template"""
        return """# Project Memory

## Project Overview
[Auto-detected or user-provided project description]

## Technology Stack
[Auto-detected from package.json, requirements.txt, etc.]

## Coding Conventions
- [To be learned from existing code]

## Important Files
- [Key files to always consider]

## Known Issues
- [Issues encountered and how they were resolved]

## Commands
- [Common commands used in this project]

---
*This file is automatically maintained by CodeCompanion.*
*Add your own instructions below:*

## Custom Instructions

"""
    
    def get_project_memory(self) -> str:
        """Get current project memory"""
        return self.memory_path.read_text()
    
    def update_section(self, section: str, content: str):
        """Update a specific section of project memory"""
        current = self.get_project_memory()
        
        # Find and replace section
        import re
        pattern = rf"(## {section}\n)(.*?)(\n##|\n---|\Z)"
        
        def replacer(match):
            if match.group(3) == "\n##":
                return f"## {section}\n{content}\n\n##"
            else:
                return f"## {section}\n{content}\n---"
        
        updated = re.sub(pattern, replacer, current, flags=re.DOTALL)
        
        if updated == current:
            # Section doesn't exist, add it
            updated = current + f"\n## {section}\n{content}\n"
        
        self.memory_path.write_text(updated)
    
    def add_learned_pattern(self, pattern: Dict):
        """Add a learned pattern from the codebase"""
        patterns = json.loads(self.patterns_path.read_text())
        patterns["patterns"].append({
            **pattern,
            "learned_at": datetime.now().isoformat()
        })
        self.patterns_path.write_text(json.dumps(patterns, indent=2))
    
    def add_convention(self, convention: str, source_file: str = None):
        """Add a discovered coding convention"""
        patterns = json.loads(self.patterns_path.read_text())
        patterns["conventions"].append({
            "convention": convention,
            "source": source_file,
            "added_at": datetime.now().isoformat()
        })
        self.patterns_path.write_text(json.dumps(patterns, indent=2))
    
    def add_warning(self, warning: str):
        """Add a warning to remember"""
        patterns = json.loads(self.patterns_path.read_text())
        patterns["warnings"].append({
            "warning": warning,
            "added_at": datetime.now().isoformat()
        })
        self.patterns_path.write_text(json.dumps(patterns, indent=2))
    
    def get_learned_patterns(self) -> Dict:
        """Get all learned patterns"""
        return json.loads(self.patterns_path.read_text())
    
    def auto_detect_project_info(self) -> Dict:
        """Auto-detect project information from files"""
        info = {
            "name": self.workspace.name,
            "type": "unknown",
            "language": "unknown",
            "framework": None,
            "dependencies": [],
            "scripts": {}
        }
        
        # Check package.json
        pkg_json = self.workspace / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text())
                info["name"] = pkg.get("name", info["name"])
                info["type"] = "nodejs"
                info["language"] = "javascript"
                
                deps = list(pkg.get("dependencies", {}).keys())
                dev_deps = list(pkg.get("devDependencies", {}).keys())
                info["dependencies"] = deps[:10]  # Top 10
                
                if "typescript" in dev_deps or "typescript" in deps:
                    info["language"] = "typescript"
                if "react" in deps:
                    info["framework"] = "react"
                elif "vue" in deps:
                    info["framework"] = "vue"
                elif "next" in deps:
                    info["framework"] = "nextjs"
                elif "express" in deps:
                    info["framework"] = "express"
                
                info["scripts"] = pkg.get("scripts", {})
                
            except Exception:
                pass
        
        # Check for Python
        requirements = self.workspace / "requirements.txt"
        if requirements.exists():
            info["type"] = "python"
            info["language"] = "python"
            try:
                content = requirements.read_text()
                if "fastapi" in content.lower():
                    info["framework"] = "fastapi"
                elif "django" in content.lower():
                    info["framework"] = "django"
                elif "flask" in content.lower():
                    info["framework"] = "flask"
            except Exception:
                pass
        
        return info
    
    def initialize_from_project(self):
        """Initialize memory from project analysis"""
        info = self.auto_detect_project_info()
        
        # Update project overview
        overview = f"""
- **Name**: {info['name']}
- **Type**: {info['type']}
- **Language**: {info['language']}
- **Framework**: {info['framework'] or 'None detected'}
"""
        self.update_section("Project Overview", overview)
        
        # Update tech stack
        tech = f"""
- Primary Language: {info['language']}
- Framework: {info['framework'] or 'N/A'}
- Top Dependencies: {', '.join(info['dependencies'][:5]) or 'N/A'}
"""
        self.update_section("Technology Stack", tech)
        
        # Update commands
        if info.get('scripts'):
            commands = "\n".join([f"- `npm run {k}`: {v}" for k, v in list(info['scripts'].items())[:5]])
            self.update_section("Commands", commands)
    
    def get_context_for_llm(self) -> str:
        """Get formatted context for LLM"""
        memory = self.get_project_memory()
        patterns = self.get_learned_patterns()
        
        context = f"""
## PROJECT MEMORY (IMPORTANT - FOLLOW THESE INSTRUCTIONS)

{memory}

## LEARNED PATTERNS
"""
        
        if patterns.get("conventions"):
            context += "\n### Coding Conventions:\n"
            for conv in patterns["conventions"][-5:]:  # Last 5
                context += f"- {conv['convention']}\n"
        
        if patterns.get("warnings"):
            context += "\n### ⚠️ Warnings to Remember:\n"
            for warn in patterns["warnings"][-5:]:  # Last 5
                context += f"- {warn['warning']}\n"
        
        return context
