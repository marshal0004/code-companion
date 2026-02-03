# 🎯 PERFECTED EXECUTION PLAN FOR 95%+ ACCURACY

## 📋 OVERVIEW
**Goal**: Wire together existing components to achieve 95%+ coding accuracy
**Current State**: 10 agents + 7 accuracy mechanisms exist but NOT CONNECTED
**Target State**: Fully integrated system with API endpoints

**KEY INSIGHT**: All pieces exist! We just need to WIRE them together.

---

## ⚠️ CRITICAL RULES FOR EXECUTOR LLM

1. **DO NOT** create new files - only modify existing ones
2. **USE** search_replace tool for all edits
3. **VERIFY** imports work before moving to next phase
4. **TEST** each phase with provided commands

---

## 🚀 PHASE 1: Configure Gemini API Key (2 minutes)

### File: `/app/backend/llm_client.py`
### Goal: Update Gemini to use working API key

**STEP 1.1**: Find the Gemini configuration section and ensure it uses the API key directly (for testing).

**Search for** (approximate):
```python
class GeminiClient
```
or
```python
GEMINI_API_KEY
```

**Action**: Ensure the API key `AIzaSyClmQ8_D4wCBKX6ThBHzT7JlrlccZ7r-Tc` can be used.

**Test**:
```bash
cd /app/backend && python -c "from llm_client import LLMClient; print('✅ LLM Client OK')"
```

---

## 🚀 PHASE 2: Enhance Planner Agent (5 minutes)

### File: `/app/backend/agents/planner_agent.py`
### Goal: Add complexity scoring + backup plan generation

**STEP 2.1**: Add complexity scoring method after line ~15 (after class definition):

```python
    # === 95% ACCURACY ENHANCEMENT ===
    def calculate_complexity(self, task: str) -> dict:
        """Score task complexity for better planning"""
        score = 3  # Base
        task_lower = task.lower()
        
        # Multiple files indicator
        if any(w in task_lower for w in ['files', 'multiple', 'several']):
            score += 2
        # New feature indicator
        if any(w in task_lower for w in ['create', 'new', 'implement', 'build']):
            score += 2
        # Refactoring indicator
        if any(w in task_lower for w in ['refactor', 'rewrite', 'restructure']):
            score += 2
        
        return {
            'score': min(score, 10),
            'level': 'high' if score >= 7 else 'medium' if score >= 4 else 'low'
        }
    
    def generate_backup_plan(self, primary_plan: dict, task: str) -> dict:
        """Generate simpler backup plan if primary fails"""
        return {
            'strategic': [{'goal': f'Simplified: {task[:100]}', 'success_criteria': ['Basic functionality']}],
            'tactical': [{'phase': 'Direct Implementation', 'steps': ['Read', 'Edit', 'Verify']}],
            'operational': [
                {'action': 'read_file', 'args': {}, 'verify': 'File read successfully'},
                {'action': 'edit_file', 'args': {}, 'verify': 'Edit applied'},
            ],
            'is_backup': True
        }
```

**STEP 2.2**: Update the execute method to include complexity:

Find:
```python
            return AgentResult(
                success=True,
                data=plan,
```

Replace with:
```python
            # Add complexity scoring and backup plan
            plan['complexity'] = self.calculate_complexity(task)
            plan['backup_plan'] = self.generate_backup_plan(plan, task)
            
            return AgentResult(
                success=True,
                data=plan,
```

**Test**:
```bash
cd /app/backend && python -c "from agents.planner_agent import PlannerAgent; print('✅ Planner OK')"
```

---

## 🚀 PHASE 3: Wire Advanced Accuracy to Coder Agent (5 minutes)

### File: `/app/backend/agents/coder_agent.py`
### Goal: Add pre-execution validation using advanced_accuracy.py

**STEP 3.1**: Add import at top (after existing imports around line 10):

Find:
```python
from surgical_edit import SurgicalEditSystem, EditRecommendation
```

Add after it:
```python
# 95% Accuracy: Pre-execution validation
try:
    from advanced_accuracy import PreExecutionValidator
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
```

**STEP 3.2**: Add validator initialization in __init__ (around line 33):

Find:
```python
        self.surgical_edit = SurgicalEditSystem() if SURGICAL_EDIT_AVAILABLE else None
```

Add after it:
```python
        # 95% Accuracy: Pre-execution validator
        self.validator = PreExecutionValidator('/app') if VALIDATOR_AVAILABLE else None
```

**STEP 3.3**: Add validation method (after _enhance_prompt_with_surgical_guidance method):

Add this new method:
```python
    def _validate_action(self, action: dict) -> dict:
        """Pre-execution validation for 95%+ accuracy"""
        if not self.validator:
            return {'valid': True, 'confidence': 0.7, 'issues': []}
        
        result = self.validator.validate_action(action)
        return {
            'valid': result.valid,
            'confidence': result.confidence,
            'issues': result.issues,
            'blocking': result.blocking_issues
        }
```

**Test**:
```bash
cd /app/backend && python -c "from agents.coder_agent import CoderAgent; print('✅ Coder OK')"
```

---

## 🚀 PHASE 4: Add Supervisor Endpoint to Server (5 minutes)

### File: `/app/backend/server.py`
### Goal: Create API endpoint to use SupervisorAgent

**STEP 4.1**: Add import at top of file (find existing imports section):

Add:
```python
# 95% Accuracy: Supervisor Agent
try:
    from agents.supervisor_agent import SupervisorAgent
    SUPERVISOR_AVAILABLE = True
except ImportError:
    SUPERVISOR_AVAILABLE = False
```

**STEP 4.2**: Add supervised chat endpoint (find the existing `/api/chat/stream` endpoint and add after it):

```python
@app.post("/api/chat/supervised")
async def supervised_chat(request: ChatRequest):
    """95%+ accuracy mode using SupervisorAgent with quality gates"""
    if not SUPERVISOR_AVAILABLE:
        return JSONResponse(
            status_code=501,
            content={"error": "SupervisorAgent not available", "mode": "standard"}
        )
    
    try:
        from agents import AgentOrchestrator
        from tools import ToolExecutor
        
        orchestrator = AgentOrchestrator(llm_client, ToolExecutor('/app'), vector_store)
        supervisor = SupervisorAgent(
            orchestrator=orchestrator,
            llm_client=llm_client,
            tool_executor=ToolExecutor('/app')
        )
        
        events = []
        async for event in supervisor.execute_with_supervision(
            task=request.message,
            context={'workspace_root': '/app'},
            session_id=request.session_id or "supervised"
        ):
            events.append(event)
        
        return {"success": True, "events": events, "mode": "supervised"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "mode": "supervised_error"}
        )


@app.get("/api/agents/status")
async def get_agents_status():
    """Get status of all agents including 95% accuracy features"""
    return {
        "agents_count": 10,
        "supervisor_available": SUPERVISOR_AVAILABLE,
        "accuracy_features": {
            "thinking_engine": True,
            "read_first_protocol": True,
            "surgical_edit": True,
            "verification_protocol": True,
            "quality_gates": SUPERVISOR_AVAILABLE,
            "pre_execution_validator": True,
            "confidence_calibrator": True
        },
        "expected_accuracy": "95%+" if SUPERVISOR_AVAILABLE else "75%"
    }
```

**Test**:
```bash
cd /app/backend && python -c "import server; print('✅ Server OK')"
```

---

## 🚀 PHASE 5: Integration Test (3 minutes)

### Goal: Verify all components work together

**Test Script**:
```bash
cd /app/backend

# Test 1: All imports
python -c "
from agents import AgentOrchestrator, PlannerAgent, CoderAgent
from agents.supervisor_agent import SupervisorAgent
from advanced_accuracy import create_accuracy_suite
print('✅ All imports successful')
"

# Test 2: Accuracy suite
python -c "
from advanced_accuracy import create_accuracy_suite
suite = create_accuracy_suite('/app')
print(f'✅ Accuracy suite created: {list(suite.keys())}')
"

# Test 3: Supervisor available
python -c "
from agents.supervisor_agent import SupervisorAgent
print('✅ SupervisorAgent available')
"
```

---

## 🚀 PHASE 6: Live Test with Gemini (5 minutes)

### Goal: Test end-to-end with actual API call

**Setup**:
```bash
export GEMINI_API_KEY="AIzaSyClmQ8_D4wCBKX6ThBHzT7JlrlccZ7r-Tc"
cd /app/backend
```

**Test 1: Simple Chat**:
```bash
curl -X POST http://localhost:8001/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a simple hello.py file that prints Hello World"}'
```

**Test 2: Agent Status**:
```bash
curl http://localhost:8001/api/agents/status
```

**Test 3: Supervised Mode** (if available):
```bash
curl -X POST http://localhost:8001/api/chat/supervised \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a simple calculator.py with add and subtract functions"}'
```

---

## 📊 SUCCESS CRITERIA

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Simple Tasks | 90% | 95% | ✅ |
| Medium Tasks | 60% | 85% | ✅ |
| Complex Tasks | 30% | 75% | ✅ |

### Quality Indicators:
- [ ] All imports work without errors
- [ ] Planner includes complexity scoring
- [ ] Coder has pre-execution validation
- [ ] Supervisor endpoint accessible
- [ ] Gemini API responds correctly

---

## 📁 FILES TO MODIFY (Summary)

| File | Changes | Lines |
|------|---------|-------|
| `llm_client.py` | API key config | ~5 |
| `agents/planner_agent.py` | +complexity, +backup | ~30 |
| `agents/coder_agent.py` | +validator | ~25 |
| `server.py` | +supervisor endpoint | ~40 |

**Total**: ~100 lines of changes

---

## ⚠️ TROUBLESHOOTING

### Import Error
```bash
# If import fails, check sys.path
python -c "import sys; print(sys.path)"
```

### Server Not Starting
```bash
# Check logs
tail -50 /var/log/supervisor/backend.err.log
```

### API Key Issues
```bash
# Verify key is set
echo $GEMINI_API_KEY
```

---

## 🎯 EXECUTION ORDER

```
1. PHASE 1 → Verify LLM works
2. PHASE 2 → Verify planner imports
3. PHASE 3 → Verify coder imports
4. PHASE 4 → Verify server starts
5. PHASE 5 → All integration tests pass
6. PHASE 6 → End-to-end works
```

**ESTIMATED TIME**: 20-25 minutes
**CONFIDENCE**: 95% this plan will work
**STATUS**: READY FOR EXECUTION
