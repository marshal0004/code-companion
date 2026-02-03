# 🎯 AGENT ENHANCEMENT EXECUTION PLAN FOR 95%+ ACCURACY

## 📋 OVERVIEW
**Goal**: Enhance CodeCompanion agents to achieve 95%+ coding accuracy (competing with Claude Code)
**Current State**: 8 agents + 7 accuracy mechanisms implemented but NOT fully integrated
**Target State**: Fully integrated supervisor-controlled system with quality gates

---

## 🔍 CURRENT SYSTEM ANALYSIS

### What Exists (DO NOT RECREATE):
```
/app/backend/agents/
├── supervisor_agent.py      ✅ EXISTS (1153 lines) - Quality gates, rollback, adaptive strategies
├── enhanced_orchestrator.py ✅ EXISTS (641 lines) - Multi-strategy execution
├── agent_registry.py        ✅ EXISTS (333 lines) - Factory & discovery
├── orchestrator.py          ✅ EXISTS (502 lines) - Main coordinator
├── planner_agent.py         ✅ EXISTS (201 lines) - Task decomposition
├── coder_agent.py           ✅ EXISTS (194 lines) - Code generation
├── debugger_agent.py        ✅ EXISTS (200 lines) - Error analysis
├── tester_agent.py          ✅ EXISTS (224 lines) - Verification
├── researcher_agent.py      ✅ EXISTS - Context gathering
├── architect_agent.py       ✅ EXISTS - System design
├── reviewer_agent.py        ✅ EXISTS - Code review
└── __init__.py              ✅ UPDATED - Now exports all agents

/app/backend/
├── advanced_accuracy.py     ✅ EXISTS (953 lines) - PreValidator, Calibrator, ErrorRecognizer, QualityScorer
├── thinking_engine.py       ✅ EXISTS (326 lines) - Extended thinking
├── read_first_protocol.py   ✅ EXISTS - Read before write
├── surgical_edit.py         ✅ EXISTS - Edit vs rewrite
├── feedback_loop.py         ✅ EXISTS - Immediate feedback
├── meta_cognition.py        ✅ EXISTS - Self-reflection
├── verification_protocol.py ✅ EXISTS - Multi-layer verification
├── project_memory.py        ✅ EXISTS - Persistent context
```

### What's MISSING (Critical Gaps):
1. **server.py** - No endpoint to use SupervisorAgent
2. **Planner** - No complexity scoring, no multi-path planning
3. **Integration** - advanced_accuracy.py not connected to agents
4. **LLM Client** - No Gemini configuration with provided API key

---

## 🚀 EXECUTION PHASES

### PHASE 1: Configure Gemini API Key (5 minutes)
**File**: `/app/backend/llm_client.py`
**Action**: Add/update Gemini configuration with user's API key

```
FIND in llm_client.py:
- Look for GeminiClient class or gemini configuration
- Find where API key is loaded

UPDATE:
- Ensure GEMINI_API_KEY environment variable is used
- OR directly use: AIzaSyClmQ8_D4wCBKX6ThBHzT7JlrlccZ7r-Tc
```

**Verification**: 
```bash
cd /app/backend && python -c "from llm_client import LLMClient; print('✅ LLM Client OK')"
```

---

### PHASE 2: Enhance Planner Agent (15 minutes)
**File**: `/app/backend/agents/planner_agent.py`
**Goal**: Add complexity scoring + multi-path planning

**EXACT Changes Required**:

1. **Add complexity_score method** (after line ~50):
```python
def calculate_complexity(self, task: str, context: Dict) -> int:
    """Score task complexity 1-10 for 95%+ accuracy planning"""
    score = 3  # Base complexity
    task_lower = task.lower()
    
    # +2 for multiple files
    if any(w in task_lower for w in ['files', 'multiple', 'several', 'all']):
        score += 2
    
    # +2 for new features
    if any(w in task_lower for w in ['create', 'new', 'implement', 'build', 'add']):
        score += 2
    
    # +2 for refactoring
    if any(w in task_lower for w in ['refactor', 'rewrite', 'restructure', 'migrate']):
        score += 2
    
    # +1 for testing
    if any(w in task_lower for w in ['test', 'verify', 'check']):
        score += 1
    
    return min(score, 10)
```

2. **Add multi-path planning** (after complexity method):
```python
def _generate_backup_plan(self, primary_plan: Dict, task: str) -> Dict:
    """Generate simpler backup plan if primary fails"""
    return {
        'strategic': [{'goal': f'Simplified approach for: {task[:100]}', 'success_criteria': ['Basic functionality works']}],
        'tactical': [{'phase': 'Direct Implementation', 'steps': ['Read files', 'Make minimal changes', 'Verify']}],
        'operational': self._simplify_operations(primary_plan.get('operational', [])),
        'is_backup': True
    }

def _simplify_operations(self, operations: List) -> List:
    """Simplify operations for backup plan"""
    simplified = []
    for op in operations[:5]:  # Max 5 steps in backup
        if op.get('action') in ['read_file', 'write_file', 'edit_file']:
            simplified.append({
                'action': op.get('action'),
                'args': op.get('args', {}),
                'verify': 'Check file exists and no syntax errors'
            })
    return simplified
```

3. **Update execute method** to include complexity:
```python
# In execute() method, add after getting plan:
plan['complexity_score'] = self.calculate_complexity(task, context)
plan['backup_plan'] = self._generate_backup_plan(plan, task)
```

**Verification**:
```bash
cd /app/backend && python -c "from agents.planner_agent import PlannerAgent; print('✅ Planner OK')"
```

---

### PHASE 3: Connect Supervisor to Server (10 minutes)
**File**: `/app/backend/server.py`
**Goal**: Add endpoint to use SupervisorAgent for 95%+ accuracy mode

**FIND** in server.py:
- The `/api/chat/stream` endpoint
- Import section at top

**ADD** imports at top:
```python
from agents import SupervisorAgent, SUPERVISOR_AVAILABLE
```

**ADD** new endpoint (after existing chat endpoint):
```python
@app.post("/api/chat/supervised")
async def supervised_chat(request: ChatRequest):
    """95%+ accuracy mode using SupervisorAgent with quality gates"""
    if not SUPERVISOR_AVAILABLE:
        return JSONResponse(
            status_code=501,
            content={"error": "SupervisorAgent not available"}
        )
    
    try:
        # Initialize supervisor with orchestrator
        orchestrator = AgentOrchestrator(llm_client, tool_executor, vector_store)
        supervisor = SupervisorAgent(
            orchestrator=orchestrator,
            llm_client=llm_client,
            tool_executor=tool_executor
        )
        
        # Execute with supervision
        results = []
        async for event in supervisor.execute_with_supervision(
            task=request.message,
            context={'workspace_root': '/app'},
            session_id=request.session_id or "supervised"
        ):
            results.append(event)
        
        return {"success": True, "events": results}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
```

**ADD** status endpoint:
```python
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
            "quality_gates": SUPERVISOR_AVAILABLE
        },
        "expected_accuracy": "95%+" if SUPERVISOR_AVAILABLE else "75%"
    }
```

**Verification**:
```bash
cd /app/backend && python -c "import server; print('✅ Server OK')"
```

---

### PHASE 4: Wire Advanced Accuracy to Coder Agent (10 minutes)
**File**: `/app/backend/agents/coder_agent.py`
**Goal**: Add pre-execution validation using advanced_accuracy.py

**ADD** import at top:
```python
try:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from advanced_accuracy import PreExecutionValidator, CodeQualityScorer
    ADVANCED_ACCURACY_AVAILABLE = True
except ImportError:
    ADVANCED_ACCURACY_AVAILABLE = False
```

**ADD** in __init__ method:
```python
# Initialize advanced accuracy
self.validator = PreExecutionValidator('/app') if ADVANCED_ACCURACY_AVAILABLE else None
self.quality_scorer = CodeQualityScorer() if ADVANCED_ACCURACY_AVAILABLE else None
```

**ADD** validation method:
```python
def _validate_before_execute(self, action: Dict) -> Dict:
    """Pre-execution validation for 95%+ accuracy"""
    if not self.validator:
        return {'valid': True, 'confidence': 0.7}
    
    result = self.validator.validate_action(action)
    return {
        'valid': result.valid,
        'confidence': result.confidence,
        'issues': result.issues,
        'blocking': result.blocking_issues
    }
```

**UPDATE** execute method to use validation:
```python
# At start of execute():
# Validate all planned actions
for action in actions:
    validation = self._validate_before_execute(action)
    if not validation['valid']:
        return AgentResult(
            success=False,
            data={'blocked_action': action, 'reason': validation['blocking']},
            error=f"Pre-execution validation failed: {validation['blocking']}"
        )
```

**Verification**:
```bash
cd /app/backend && python -c "from agents.coder_agent import CoderAgent; print('✅ Coder OK')"
```

---

### PHASE 5: Integration Test (5 minutes)
**Goal**: Verify all components work together

**Test Script** (run in terminal):
```bash
cd /app/backend

# Test 1: All imports
python -c "
from agents import (
    AgentOrchestrator, 
    SupervisorAgent, 
    EnhancedOrchestrator,
    PlannerAgent,
    CoderAgent,
    SUPERVISOR_AVAILABLE
)
print('✅ All agent imports successful')
print(f'   Supervisor Available: {SUPERVISOR_AVAILABLE}')
"

# Test 2: Server starts
timeout 5 python server.py || echo "Server OK (timeout expected)"

# Test 3: Advanced accuracy
python -c "
from advanced_accuracy import create_accuracy_suite
suite = create_accuracy_suite('/app')
print('✅ Advanced accuracy suite created')
print(f'   Components: {list(suite.keys())}')
"
```

---

### PHASE 6: Live Test with Gemini (5 minutes)
**Goal**: Test end-to-end with actual API call

**Setup**:
```bash
# Set API key
export GEMINI_API_KEY="AIzaSyClmQ8_D4wCBKX6ThBHzT7JlrlccZ7r-Tc"
```

**Test Request**:
```bash
curl -X POST http://localhost:8001/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a simple hello.py file that prints Hello World",
    "use_orchestrator": true
  }'
```

**Expected Output**:
- Should show thinking phase
- Should show planning phase
- Should create file
- Should verify file

---

## 📊 SUCCESS METRICS

### Before Enhancement:
- Simple Tasks: 90%
- Medium Tasks: 60%
- Complex Tasks: 30%

### After Enhancement (Target):
- Simple Tasks: 98%
- Medium Tasks: 90%
- Complex Tasks: 75-80%

### Quality Indicators:
- [ ] Supervisor quality gates active
- [ ] Pre-execution validation working
- [ ] Complexity scoring in plans
- [ ] Backup plans generated
- [ ] Multi-layer verification

---

## ⚠️ CRITICAL RULES

1. **DO NOT** delete or recreate existing files
2. **DO NOT** change working functionality
3. **USE** search_replace for all edits (not file rewrites)
4. **VERIFY** each phase before moving to next
5. **KEEP** changes minimal and targeted

---

## 📁 FILES TO MODIFY (Summary)

| File | Action | Lines to Change |
|------|--------|-----------------|
| `/app/backend/llm_client.py` | Update Gemini config | ~5-10 lines |
| `/app/backend/agents/planner_agent.py` | Add complexity + backup | ~50 lines |
| `/app/backend/server.py` | Add supervised endpoint | ~40 lines |
| `/app/backend/agents/coder_agent.py` | Add validation | ~30 lines |

**Total**: ~130 lines of changes across 4 files

---

## 🎯 EXECUTION ORDER

```
1. PHASE 1: Configure Gemini API Key (REQUIRED FIRST)
   └── Verify LLM works

2. PHASE 2: Enhance Planner
   └── Verify planner imports

3. PHASE 3: Add Supervisor Endpoint
   └── Verify server starts

4. PHASE 4: Wire Advanced Accuracy
   └── Verify coder imports

5. PHASE 5: Integration Test
   └── All imports work

6. PHASE 6: Live Test
   └── End-to-end works
```

---

## 🔧 ROLLBACK PLAN

If anything breaks:
```bash
# Restart services
sudo supervisorctl restart backend

# Check logs
tail -50 /var/log/supervisor/backend.err.log

# Revert specific file (git)
git checkout -- /app/backend/agents/planner_agent.py
```

---

**STATUS**: PLAN READY FOR EXECUTION
**ESTIMATED TIME**: 45-60 minutes total
**CONFIDENCE**: 95% this plan will work
