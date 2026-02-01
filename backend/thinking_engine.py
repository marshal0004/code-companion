"""Extended Thinking Engine for CodeCompanion

Forces deep reasoning BEFORE any action.
This is the #1 secret to accuracy.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ThinkingResult:
    """Result of extended thinking"""
    understanding: str          # What the request means
    current_state: str          # What exists now
    goal_state: str            # What we want to achieve
    approach: str              # How we'll do it
    risks: List[str]           # What could go wrong
    verification_plan: str     # How we'll verify success
    files_to_read: List[str]   # Files to read BEFORE acting
    files_to_modify: List[str] # Files we'll change
    confidence: float          # 0-1 confidence score


class ThinkingEngine:
    """Force structured thinking before action"""
    
    THINKING_TEMPLATE = """
## EXTENDED THINKING REQUIRED

Before taking ANY action, you MUST complete this analysis:

### 1. UNDERSTANDING CHECK
- What is the user actually asking for?
- What is the expected outcome?
- Are there any ambiguities I need to clarify?

### 2. CURRENT STATE ANALYSIS
- What files currently exist that are relevant?
- What is the current implementation (if any)?
- What dependencies exist?

### 3. GOAL STATE DEFINITION
- What should exist after I'm done?
- What behavior should change?
- What tests should pass?

### 4. APPROACH PLANNING
- What is my step-by-step approach?
- What files do I need to READ first?
- What tools will I use?
- What is the MINIMAL change needed?

### 5. RISK ASSESSMENT
- What could go wrong?
- What existing functionality might break?
- What edge cases exist?
- How will I handle failures?

### 6. VERIFICATION PLAN
- How will I verify this works?
- What tests should I run?
- What manual checks are needed?

### 7. CONFIDENCE CALIBRATION
- How confident am I? (0-100%)
- What would increase my confidence?
- Should I ask for clarification?

Output this analysis BEFORE taking any actions.
"""
    
    def __init__(self):
        self.thinking_history: List[ThinkingResult] = []
    
    def get_thinking_prompt(self, task: str, context: Dict = None) -> str:
        """Generate thinking prompt for a task"""
        context_info = ""
        if context:
            if 'workspace_root' in context:
                context_info += f"\n\nWorkspace: {context['workspace_root']}"
            if 'relevant_code' in context:
                context_info += f"\n\nRelevant Code:\n{context['relevant_code'][:500]}"
        
        return f"""
{self.THINKING_TEMPLATE}

## YOUR TASK:
{task}

{context_info}

Now, complete the extended thinking analysis above BEFORE proposing any actions.
"""
    
    def parse_thinking_response(self, response: str) -> Optional[ThinkingResult]:
        """Parse LLM thinking response into structured result"""
        try:
            # Extract sections using markers
            understanding = self._extract_section(response, "UNDERSTANDING CHECK", "CURRENT STATE")
            current_state = self._extract_section(response, "CURRENT STATE", "GOAL STATE")
            goal_state = self._extract_section(response, "GOAL STATE", "APPROACH")
            approach = self._extract_section(response, "APPROACH", "RISK")
            risks_text = self._extract_section(response, "RISK ASSESSMENT", "VERIFICATION")
            verification = self._extract_section(response, "VERIFICATION", "CONFIDENCE")
            confidence_text = self._extract_section(response, "CONFIDENCE", None)
            
            # Parse risks
            risks = self._parse_list_section(risks_text)
            
            # Parse files to read
            files_to_read = self._extract_file_paths(current_state + approach)
            files_to_modify = self._extract_file_paths(approach)
            
            # Parse confidence
            confidence = self._parse_confidence(confidence_text)
            
            result = ThinkingResult(
                understanding=understanding,
                current_state=current_state,
                goal_state=goal_state,
                approach=approach,
                risks=risks,
                verification_plan=verification,
                files_to_read=files_to_read,
                files_to_modify=files_to_modify,
                confidence=confidence
            )
            
            self.thinking_history.append(result)
            return result
            
        except Exception as e:
            # If parsing fails, return None - thinking still visible in logs
            return None
    
    def _extract_section(self, text: str, start_marker: str, end_marker: Optional[str] = None) -> str:
        """Extract text between markers"""
        try:
            start_idx = text.lower().find(start_marker.lower())
            if start_idx == -1:
                return ""
            
            # Skip the marker itself
            start_idx = text.find('\n', start_idx) + 1
            
            if end_marker:
                end_idx = text.lower().find(end_marker.lower(), start_idx)
                if end_idx == -1:
                    return text[start_idx:].strip()
                return text[start_idx:end_idx].strip()
            else:
                return text[start_idx:].strip()
        except:
            return ""
    
    def _parse_list_section(self, text: str) -> List[str]:
        """Parse a bulleted/numbered list"""
        items = []
        for line in text.split('\n'):
            line = line.strip()
            # Skip section headers
            if line.startswith('#'):
                continue
            # Remove bullet/number markers
            for marker in ['-', '*', '+']:
                if line.startswith(marker):
                    line = line[1:].strip()
                    break
            # Remove number markers like "1.", "2."
            if line and line[0].isdigit() and '.' in line[:3]:
                line = line.split('.', 1)[1].strip()
            
            if line:
                items.append(line[:200])  # Limit length
        
        return items[:10]  # Limit count
    
    def _extract_file_paths(self, text: str) -> List[str]:
        """Extract file paths from text"""
        import re
        
        # Pattern for file paths
        patterns = [
            r'`([^`]+\.(py|js|ts|jsx|tsx|json|md|txt|yml|yaml))`',  # Backticked paths
            r'["\']([^"\']+\.(py|js|ts|jsx|tsx|json|md|txt|yml|yaml))["\']',  # Quoted paths
            r'\b([a-zA-Z0-9_/.-]+\.(py|js|ts|jsx|tsx|json|md|txt|yml|yaml))\b',  # Plain paths
        ]
        
        files = set()
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                file_path = match.group(1) if len(match.groups()) > 1 else match.group(0)
                # Clean up
                file_path = file_path.strip('`"\'')
                if file_path and not file_path.startswith('http'):
                    files.add(file_path)
        
        return list(files)[:20]  # Limit to 20 files
    
    def _parse_confidence(self, text: str) -> float:
        """Extract confidence percentage"""
        import re
        
        # Look for patterns like "70%", "confidence: 80", "8/10"
        patterns = [
            r'(\d+)%',
            r'confidence[:\s]+(\d+)',
            r'(\d+)/10',
            r'(\d+)/100',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                value = int(match.group(1))
                if pattern.endswith('/10'):
                    return value / 10.0
                elif pattern.endswith('/100') or pattern.endswith('%'):
                    return value / 100.0
                else:
                    # Assume percentage
                    return min(value / 100.0, 1.0)
        
        return 0.5  # Default medium confidence
    
    def should_proceed(self, thinking_result: Optional[ThinkingResult]) -> tuple[bool, str]:
        """Determine if we should proceed based on thinking"""
        if not thinking_result:
            # No thinking result, allow to proceed but warn
            return True, "No thinking result available - proceed with caution"
        
        # Check confidence
        if thinking_result.confidence < 0.3:
            return False, f"Confidence too low ({thinking_result.confidence:.0%}). Need clarification."
        
        # Check if files to read are identified
        if not thinking_result.files_to_read and thinking_result.files_to_modify:
            return False, "Must identify files to READ before modifying"
        
        # Check for high-risk items
        high_risk_keywords = ['delete', 'remove', 'drop', 'destroy', 'dangerous']
        high_risks = [r for r in thinking_result.risks 
                      if any(keyword in r.lower() for keyword in high_risk_keywords)]
        
        if len(high_risks) >= 2:
            return False, f"Multiple high-risk items identified: {high_risks}"
        
        return True, "OK to proceed"
    
    def get_next_actions(self, thinking_result: Optional[ThinkingResult]) -> List[Dict]:
        """Generate next actions based on thinking"""
        if not thinking_result:
            return []
        
        actions = []
        
        # First action: Read files
        for file_path in thinking_result.files_to_read[:5]:  # Limit to 5
            actions.append({
                'action': 'read_file',
                'args': {'path': file_path},
                'reason': 'Understand current state'
            })
        
        # Second action: Search for patterns if needed
        if 'search' in thinking_result.approach.lower() or 'find' in thinking_result.approach.lower():
            actions.append({
                'action': 'search_text',
                'args': {'query': 'TODO', 'path': '.'},
                'reason': 'Locate relevant code'
            })
        
        return actions
    
    def format_thinking_summary(self, thinking_result: Optional[ThinkingResult]) -> str:
        """Format thinking result for display"""
        if not thinking_result:
            return "[Thinking analysis not available]"
        
        summary = f"""
## 🧠 Extended Thinking Analysis

**Understanding**: {thinking_result.understanding[:200]}...

**Current State**: {thinking_result.current_state[:150]}...

**Goal**: {thinking_result.goal_state[:150]}...

**Approach**: {thinking_result.approach[:200]}...

**Risks Identified**: {len(thinking_result.risks)}
{chr(10).join([f"  - {r[:100]}" for r in thinking_result.risks[:3]])}

**Files to Read**: {', '.join(thinking_result.files_to_read[:5])}

**Confidence**: {thinking_result.confidence:.0%}

**Verification Plan**: {thinking_result.verification_plan[:150]}...
"""
        return summary


# Quick helper for integration
def think_before_action(llm_client, task: str, context: Dict = None) -> tuple[bool, str, Optional[ThinkingResult]]:
    """
    Quick function to add thinking before action.
    
    Returns:
        (should_proceed, reason, thinking_result)
    """
    engine = ThinkingEngine()
    
    # Generate thinking prompt
    prompt = engine.get_thinking_prompt(task, context)
    
    # Get LLM to think
    try:
        messages = [{"role": "user", "content": prompt}]
        # Note: This is async, you'll need to await this in async context
        # For now, return instructions
        return True, "Thinking prompt generated", None
    except Exception as e:
        return True, f"Thinking failed: {e}, proceeding anyway", None
