# 🎯 CodeCompanion → Claude Code Level Implementation Plan
## Filling the Critical Gaps - Detailed Execution Guide

**Created**: January 2025
**Status**: IN PROGRESS
**Goal**: Transform CodeCompanion from 40% to 95%+ Claude Code parity

---

## 📊 CURRENT STATUS

### What We Have ✅
- Multi-Provider LLM (Gemini + Ollama + Emergent)
- 13 Tools (file, shell, git, search)
- Basic agentic loop (single iteration style)
- Vector Store with ChromaDB
- Basic verification (Python syntax only)
- CLI with model switching

### What's Missing ❌ (From agenticcodingsystemstilllacks.md)
1. **NO SUB-AGENT ARCHITECTURE** - Single monolithic agent
2. **NO PLANNING PHASE** - Agent jumps to execution
3. **NO DYNAMIC REPLANNING** - Just retry, no strategy change
4. **NO MULTI-STEP DECOMPOSITION** - Complex tasks as single step
5. **NO MULTI-LAYER VERIFICATION** - Only basic syntax
6. **NO ERROR ANALYSIS/CLASSIFICATION** - Generic error handling
7. **NO RAG FOR PLANNING** - Semantic search not used for context

---

## 🏗️ IMPLEMENTATION PHASES

### PHASE 1: SUB-AGENT ARCHITECTURE (P0 - CRITICAL)
**Goal**: Create specialized agents that the orchestrator delegates to

#### Files to Create:
```
backend/agents/
├── __init__.py              # Agent exports
├── base_agent.py            # Base class for all agents
├── orchestrator.py          # Main orchestrator (routes tasks)
├── planner_agent.py         # Task decomposition & planning
├── coder_agent.py           # Code generation & editing
├── debugger_agent.py        # Error analysis & fixing
└── tester_agent.py          # Test generation & execution
```

#### Implementation Steps:

**Step 1.1: Create BaseAgent class**
```python
# base_agent.py
class BaseAgent:
    def __init__(self, llm_client, tools):
        self.llm = llm_client
        self.tools = tools
        self.name = "base"
        self.system_prompt = ""
    
    async def execute(self, task: str, context: dict) -> dict:
        """Execute a task - override in subclasses"""
        raise NotImplementedError
    
    def get_prompt(self, task: str, context: dict) -> str:
        """Build prompt for this agent"""
        return f"{self.system_prompt}\n\nTask: {task}\nContext: {context}"
```

**Step 1.2: Create PlannerAgent**
```python
# planner_agent.py
class PlannerAgent(BaseAgent):
    """Decomposes complex tasks into steps"""
    
    system_prompt = '''You are a Planning Agent. Your job is to:
    1. Analyze complex tasks
    2. Break them into strategic goals
    3. Create tactical phases
    4. Output operational steps
    
    Output format:
    <PLAN>
    {"strategic": ["goal1", "goal2"], 
     "tactical": [{"phase": "name", "steps": [...]}],
     "operational": ["step1", "step2", ...]}
    </PLAN>
    '''
    
    async def create_plan(self, task, context):
        # Use RAG to search codebase first
        relevant_code = await self.search_codebase(task)
        enhanced_context = {**context, "relevant_code": relevant_code}
        
        # Generate plan
        response = await self.llm.chat([
            {"role": "user", "content": f"Create a plan for: {task}"}
        ])
        
        return self.parse_plan(response)
```

**Step 1.3: Create DebuggerAgent**
```python
# debugger_agent.py
class DebuggerAgent(BaseAgent):
    """Analyzes and fixes errors"""
    
    ERROR_TYPES = {
        "syntax": "Syntax Error - Fix code syntax",
        "runtime": "Runtime Error - Debug logic",
        "logic": "Logic Error - Compare expected vs actual",
        "integration": "Integration Error - Check interfaces",
        "environment": "Environment Error - Install deps"
    }
    
    async def analyze_error(self, error, context):
        error_type = self.classify_error(error)
        strategy = self.ERROR_TYPES[error_type]
        fix = await self.generate_fix(error, error_type, context)
        return {"type": error_type, "strategy": strategy, "fix": fix}
```

**Step 1.4: Create Orchestrator**
```python
# orchestrator.py
class AgentOrchestrator:
    """Routes tasks to appropriate sub-agents"""
    
    def __init__(self, llm_client, tools):
        self.planner = PlannerAgent(llm_client, tools)
        self.coder = CoderAgent(llm_client, tools)
        self.debugger = DebuggerAgent(llm_client, tools)
        self.tester = TesterAgent(llm_client, tools)
    
    async def execute(self, task, context):
        # 1. Always plan first
        plan = await self.planner.create_plan(task, context)
        
        # 2. Execute each step
        for step in plan["operational"]:
            result = await self.execute_step(step, context)
            
            # 3. If error, call debugger
            if not result["success"]:
                fix = await self.debugger.analyze_error(result["error"], context)
                result = await self.apply_fix(fix)
            
            # 4. Verify after code changes
            if step.get("type") == "code_change":
                await self.tester.verify(step["file"])
        
        return {"success": True, "plan": plan}
```

---

### PHASE 2: HIERARCHICAL PLANNING SYSTEM (P0 - CRITICAL)
**Goal**: Implement 3-level planning like Claude Code

#### Implementation:

**Step 2.1: Strategic Planning**
- High-level goal identification
- Dependency analysis
- Success criteria definition

**Step 2.2: Tactical Planning**
- Break goals into phases
- Sequence phases correctly
- Identify phase dependencies

**Step 2.3: Operational Planning**
- Convert phases to atomic tool calls
- Add verification steps
- Include rollback points

```python
class HierarchicalPlanner:
    async def create_plan(self, task, context):
        # Level 1: Strategic
        strategic = await self.strategic_plan(task)
        
        # Level 2: Tactical  
        tactical = []
        for goal in strategic:
            phases = await self.tactical_plan(goal)
            tactical.extend(phases)
        
        # Level 3: Operational
        operational = []
        for phase in tactical:
            steps = await self.operational_plan(phase)
            operational.extend(steps)
        
        return {
            "strategic": strategic,
            "tactical": tactical,
            "operational": operational
        }
```

---

### PHASE 3: DYNAMIC REPLANNING SYSTEM (P0 - CRITICAL)
**Goal**: Adapt plan when things go wrong

#### Implementation:

**Step 3.1: Error Classification**
```python
class ErrorClassifier:
    CATEGORIES = {
        "syntax_error": ["SyntaxError", "IndentationError"],
        "import_error": ["ImportError", "ModuleNotFoundError"],
        "runtime_error": ["TypeError", "ValueError", "AttributeError"],
        "logic_error": ["AssertionError", "test failed"],
        "environment_error": ["FileNotFoundError", "PermissionError"]
    }
    
    def classify(self, error):
        for category, patterns in self.CATEGORIES.items():
            for pattern in patterns:
                if pattern in str(error):
                    return category
        return "unknown_error"
```

**Step 3.2: Replan Strategy**
```python
class Replanner:
    async def replan(self, current_plan, error, context):
        error_type = self.classify_error(error)
        
        if error_type == "import_error":
            # Insert install step before current
            return self.insert_install_step(current_plan, error)
        
        elif error_type == "syntax_error":
            # Retry with more context
            return self.retry_with_context(current_plan, error)
        
        elif error_type == "logic_error":
            # Try alternative approach
            return self.generate_alternative(current_plan, error)
        
        else:
            # Ask for clarification
            return self.ask_clarification(current_plan, error)
```

---

### PHASE 4: MULTI-LAYER VERIFICATION (P1 - HIGH)
**Goal**: Verify code at multiple levels

#### Enhancement to verification.py:

```python
class EnhancedVerifier:
    async def verify(self, file_path):
        results = []
        
        # Layer 1: Syntax (existing)
        results.append(await self.check_syntax(file_path))
        if not results[-1]["success"]:
            return {"success": False, "layer": "syntax", "results": results}
        
        # Layer 2: Lint (ruff/eslint)
        results.append(await self.run_lint(file_path))
        
        # Layer 3: Type Check (mypy/tsc)
        results.append(await self.run_type_check(file_path))
        
        # Layer 4: Unit Tests (if exist)
        results.append(await self.run_related_tests(file_path))
        
        # Layer 5: Import Check
        results.append(await self.verify_imports(file_path))
        
        return {
            "success": all(r.get("success", True) for r in results),
            "results": results
        }
```

---

### PHASE 5: RAG-POWERED CONTEXT (P2 - MEDIUM)
**Goal**: Use semantic search for better context

#### Enhancement to context_manager.py:

```python
class RAGContextManager(ContextManager):
    def __init__(self, workspace_root, vector_store):
        super().__init__(workspace_root)
        self.vector_store = vector_store
    
    async def get_relevant_context(self, task):
        # Search for relevant code
        results = await self.vector_store.search(task, top_k=5)
        
        # Format for context
        context_parts = []
        for result in results:
            context_parts.append(f"### {result['file']}:\n```\n{result['content']}\n```")
        
        return "\n\n".join(context_parts)
    
    async def build_context_with_rag(self, messages, task):
        # Get RAG context
        rag_context = await self.get_relevant_context(task)
        
        # Build enhanced context
        return {
            **super().build_context(messages, ""),
            "rag_context": rag_context
        }
```

---

## 📋 EXECUTION CHECKLIST

### Immediate Actions (This Session):
- [ ] Create backend/agents/ directory
- [ ] Implement BaseAgent class
- [ ] Implement PlannerAgent (task decomposition)
- [ ] Implement DebuggerAgent (error analysis)
- [ ] Implement AgentOrchestrator
- [ ] Update agent_loop.py to use orchestrator
- [ ] Enhance verification.py with multi-layer checks
- [ ] Update context_manager.py with RAG support
- [ ] Test with simple coding task

### Files to Create:
1. `/app/backend/agents/__init__.py`
2. `/app/backend/agents/base_agent.py`
3. `/app/backend/agents/orchestrator.py`
4. `/app/backend/agents/planner_agent.py`
5. `/app/backend/agents/coder_agent.py`
6. `/app/backend/agents/debugger_agent.py`
7. `/app/backend/agents/tester_agent.py`

### Files to Update:
1. `/app/backend/agent_loop.py` - Use new orchestrator
2. `/app/backend/verification.py` - Multi-layer verification
3. `/app/backend/context_manager.py` - RAG integration
4. `/app/backend/server.py` - Integrate new agent system

---

## 🎯 SUCCESS CRITERIA

### Before Implementation:
- Complex task success rate: ~30%
- Single agent, no planning
- Basic syntax verification only
- Generic error handling

### After Implementation:
- Complex task success rate: ~75%+
- Multi-agent with orchestration
- 3-level planning system
- Multi-layer verification
- Classified error handling with replanning
- RAG-powered context

---

## 💰 COST CONSIDERATION

**IMPORTANT**: 
- Use Ollama (FREE) for testing
- Gemini (FREE tier) for development
- DO NOT use Emergent automatically (budget)
- Rate limit Gemini calls (15 RPM free tier)

---

## 📝 NOTES FOR CONTINUATION

If this session runs out of tokens:
1. Read this file first: `/app/IMPLEMENTATION_PLAN.md`
2. Check what's been created in `/app/backend/agents/`
3. Continue from the unchecked items in the checklist
4. Test with: `python /app/cli.py` then ask "Create a simple calculator class"

**The goal is Claude Code level accuracy - NOT just feature checkbox!**
