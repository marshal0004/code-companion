"""Meta-Cognition Layer for CodeCompanion

Enables the system to:
- Think about its approach
- Question its assumptions
- Evaluate its confidence
- Consider alternatives
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MetaThought:
    """A meta-cognitive thought"""
    category: str          # 'assumption', 'alternative', 'risk', 'confidence'
    thought: str           # The actual thought
    action: str           # What to do about it
    priority: str         # 'high', 'medium', 'low'


class MetaCognitionLayer:
    """Enable thinking about thinking"""
    
    META_PROMPTS = {
        "assumption_check": """
## ASSUMPTION CHECK

Before proceeding, examine your assumptions:

1. What am I assuming about the codebase that I haven't verified?
2. What am I assuming about the user's intent?
3. What am I assuming will work without testing?

List each assumption and how to verify it.
""",
        
        "alternative_exploration": """
## ALTERNATIVE EXPLORATION

Consider alternative approaches:

1. What is another way to solve this?
2. What would a more experienced developer do differently?
3. Is there a simpler solution I'm overlooking?

List at least 2 alternative approaches with pros/cons.
""",
        
        "confidence_calibration": """
## CONFIDENCE CALIBRATION

Honestly assess your confidence:

1. How confident am I that this solution is correct? (0-100%)
2. What would increase my confidence?
3. What is the biggest risk if I'm wrong?

If confidence is below 70%, what additional verification is needed?
""",
        
        "risk_assessment": """
## RISK ASSESSMENT

Consider what could go wrong:

1. What existing functionality might break?
2. What edge cases haven't I considered?
3. What happens if my assumptions are wrong?
4. What's the worst case scenario?

For each risk, what mitigation is possible?
""",
        
        "progress_check": """
## PROGRESS CHECK

Evaluate current progress:

1. What have I accomplished so far?
2. Am I on track to complete the task?
3. Have I deviated from the original plan?
4. Is there a better path forward now?

If stuck, what should I try differently?
"""
    }
    
    def __init__(self):
        self.thoughts: List[MetaThought] = []
        self.confidence_history: List[float] = []
    
    def get_meta_prompt(self, prompt_type: str) -> str:
        """Get a meta-cognition prompt"""
        return self.META_PROMPTS.get(prompt_type, "")
    
    def get_all_meta_prompts(self) -> str:
        """Get all meta-prompts combined for comprehensive check"""
        return "\n\n".join(self.META_PROMPTS.values())
    
    def create_decision_framework(self, decision: str, options: List[str]) -> str:
        """Create a framework for making a decision"""
        
        framework = f"""
## DECISION FRAMEWORK

**Decision Required:** {decision}

**Options:**
"""
        for i, opt in enumerate(options, 1):
            framework += f"\n### Option {i}: {opt}\n"
            framework += """
- **Pros:**
  - [List advantages]
- **Cons:**
  - [List disadvantages]  
- **Risk Level:** [Low/Medium/High]
- **Effort Level:** [Low/Medium/High]
- **Confidence:** [0-100%]
"""
        
        framework += """
**Recommendation:** [Which option and why]
**Fallback Plan:** [What to do if the chosen option fails]
"""
        
        return framework
    
    def parse_confidence(self, response: str) -> float:
        """Parse confidence level from response"""
        import re
        
        patterns = [
            r'(\d+)%',
            r'confidence[:\s]+(\d+)',
            r'(\d+)/100',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.lower())
            if match:
                try:
                    conf = int(match.group(1))
                    if 0 <= conf <= 100:
                        self.confidence_history.append(conf / 100)
                        return conf / 100
                except:
                    pass
        
        return 0.5  # Default
    
    def should_pause_and_reconsider(self) -> tuple[bool, str]:
        """Determine if we should pause based on meta-analysis"""
        
        if len(self.confidence_history) >= 3:
            recent_avg = sum(self.confidence_history[-3:]) / 3
            if recent_avg < 0.5:
                return True, "Confidence has been consistently low. Consider asking for clarification."
        
        high_risk_thoughts = [t for t in self.thoughts if t.priority == 'high' and t.category == 'risk']
        if len(high_risk_thoughts) >= 2:
            return True, "Multiple high-priority risks identified. Proceed with extra caution."
        
        return False, "OK to proceed"
    
    def record_thought(self, category: str, thought: str, action: str, priority: str = "medium"):
        """Record a meta-thought"""
        self.thoughts.append(MetaThought(
            category=category,
            thought=thought,
            action=action,
            priority=priority
        ))
    
    def get_unresolved_thoughts(self) -> List[MetaThought]:
        """Get thoughts that need attention"""
        return [t for t in self.thoughts if t.priority in ['high', 'medium']]
    
    def create_reflection_prompt(self, task_completed: str, results: Dict) -> str:
        """Create a prompt for reflecting on completed task"""
        
        return f"""
## POST-TASK REFLECTION

**Task:** {task_completed}

**Results:** {results}

Please reflect:

1. **What went well?**
   - What approaches were effective?
   - What can be reused in the future?

2. **What could be improved?**
   - Were there any mistakes?
   - What would you do differently next time?

3. **What was learned?**
   - New patterns discovered?
   - New conventions to remember?

4. **What should be remembered?**
   - Any warnings for future tasks?
   - Any conventions to add to project memory?
"""


# Helper function for quick meta-check
def quick_meta_check(task: str) -> str:
    """Quick meta-cognition check before a task"""
    return f"""
## QUICK META-CHECK

Before implementing: "{task}"

1. ⚠️ What am I ASSUMING that could be wrong?
2. 🔍 What must I READ/VERIFY before changing anything?
3. 🎯 What is the MINIMAL change needed?
4. ✅ How will I VERIFY this works?

Answer each briefly, then proceed.
"""
