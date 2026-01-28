# 🚀 CodeCompanion - Code Improvements & Templates

## Recent Improvements Made

### 1. Multi-Provider LLM System
**File**: `backend/llm_client.py`

```python
# Architecture
LLMClient (Orchestrator)
  ├── OllamaClient (Local FREE inference)
  │   ├── Auto-detection of Ollama availability
  │   ├── Model pulling and listing
  │   ├── Streaming support
  │   └── 10+ coding models
  └── EmergentClient (Cloud fallback)
      ├── GPT-5.1, GPT-4o, GPT-4o-mini
      ├── Claude Sonnet 4
      └── Auto-fallback when Ollama unavailable
```

**Key Features**:
- Auto-detection: Tries Ollama first, falls back to cloud
- Model switching on-the-fly
- Streaming responses
- Tool calling support in both providers

### 2. Enhanced Tool System
**File**: `backend/tools.py`

Expanded from 6 to 13 tools:
```
File Operations (3):
  read_file    - Read with line ranges
  write_file   - Create/overwrite with auto-backup
  edit_file    - Search/replace with backup

Directory (1):
  list_directory - Recursive listing

Shell (1):
  run_command  - Safe execution

Search (2):
  search_text     - Grep/ripgrep
  semantic_search - ChromaDB vectors

Git Integration (4):
  git_status  - Repository status
  git_diff    - Show changes
  git_log     - Commit history
  git_blame   - Line-by-line attribution

Indexing (2):
  index_workspace - Index for semantic search
  index_stats     - Show index statistics
```

**Safety Features**:
- Auto-backup before file edits (timestamped in ~/.local/share/codecompanion/backups/)
- Path traversal prevention
- Command blocklist (rm -rf, sudo, etc.)
- File size limits
- Timeout enforcement

### 3. Vector Store Implementation
**File**: `backend/vector_store.py`

```python
class VectorStore:
    - ChromaDB for persistence
    - sentence-transformers (all-MiniLM-L6-v2)
    - Chunking: 512 tokens with 50 token overlap
    - Supports 15+ file types
    - Per-workspace collections
    - Incremental indexing
```

**Usage**:
```python
# Index workspace
store = VectorStore(workspace="/app")
result = store.index_workspace()

# Semantic search
results = store.search(query="authentication logic", top_k=5)
```

### 4. Context Management System
**File**: `backend/context_manager.py`

```python
class ContextManager:
    - Loads CLAUDE.md files (hierarchical)
    - Token counting with tiktoken
    - Context window optimization
    - Priority-based selection
    - History compression
```

**Context Hierarchy**:
```
~/.claude/CLAUDE.md         (Global context)
/app/CLAUDE.md              (Project context)
/app/src/CLAUDE.md          (Directory context)
README.md                   (Fallback)
```

### 5. Enhanced Agentic Loop
**File**: `backend/agent_loop.py`

```python
class AgenticLoop:
    - Multi-iteration execution (max 15)
    - Tool result observation
    - Error recovery with retries (max 3)
    - Verification after changes
    - Metrics tracking
    - State management (planning/executing/verifying)
```

**Loop Flow**:
```
1. Planning Phase
   ↓
2. LLM generates response + tool calls
   ↓
3. Execute tools and capture results
   ↓
4. Verification (if needed)
   ↓
5. Add results to context
   ↓
6. Continue loop or complete
```

### 6. Code Verification
**File**: `backend/verification.py`

```python
class CodeVerifier:
    - Python: ast.parse syntax check + ruff/flake8
    - JavaScript: Node --check
    - TypeScript: Similar to JS
    - JSON: json.loads validation
    - Test execution hooks
```

**Verification Layers**:
1. Syntax validation (immediate)
2. Lint checks (if available)
3. Type checks (if configured)
4. Test runs (if tests exist)

### 7. Enhanced System Prompt
**File**: `backend/agent_loop.py` (function `get_enhanced_system_prompt`)

Improved prompt includes:
- Detailed tool documentation with examples
- Workflow instructions (Understand → Plan → Investigate → Execute → Verify)
- Best practices
- Output format requirements
- Error handling guidelines

### 8. API Endpoints
**File**: `backend/server.py`

New endpoints:
```
POST /api/models/pull       - Pull Ollama model
GET  /api/models/list       - List all models
POST /api/models/switch     - Switch provider/model
GET  /api/models/status     - Current status
POST /api/index/workspace   - Index workspace
GET  /api/index/stats       - Index statistics
```

### 9. Enhanced CLI
**File**: `cli.py`

New commands:
```
/models      - List all available models
/switch      - Switch provider/model
/pull        - Pull Ollama model
/status      - Show current provider/model
/index       - Index workspace
/indexstats  - Show index statistics
help         - Enhanced help
```

Features:
- Provider status display on startup
- Color-coded output (green for Ollama, cyan for cloud)
- Streaming with tool visualization
- Rich terminal UI

---

## Code Templates & Examples

### Template: Creating a CLAUDE.md File

```markdown
# Project: CodeCompanion

## Overview
AI-powered coding assistant with local LLM support.

## Architecture
- Backend: FastAPI with streaming
- Database: SQLite
- LLM: Ollama (local) + Emergent (cloud)
- Tools: File ops, shell, git, search

## Coding Conventions
- Python: PEP 8, type hints
- Async/await for I/O operations
- Tools should return Dict with 'success' key
- Log errors with logger.error()

## Common Commands
```bash
# Start backend
sudo supervisorctl restart backend

# Test CLI
python /app/cli.py

# Run tests
pytest /app/tests/
```

## Known Issues
- Ollama must be installed separately
- ChromaDB requires sentence-transformers

## Project Goals
- Zero-cost operation with Ollama
- Match Claude Code capabilities
- Better than Claude Code (local + cloud)
```

### Template: Using the Agentic Loop

```python
from backend.agent_loop import AgenticLoop
from backend.llm_client import LLMClient
from backend.tools import ToolExecutor
from backend.context_manager import ContextManager

# Initialize components
llm_client = LLMClient()
tool_executor = ToolExecutor()
context_manager = ContextManager(workspace_root="/app")

# Create agentic loop
loop = AgenticLoop(
    llm_client=llm_client,
    tool_executor=tool_executor,
    context_manager=context_manager,
    max_iterations=15,
    max_retries=3
)

# Run the loop
messages = [
    {"role": "user", "content": "Create a Python calculator module"}
]

async for event in loop.run(messages, session_id="test"):
    event_type = event['type']
    
    if event_type == 'content':
        print(event['content'], end='', flush=True)
    elif event_type == 'tool_call':
        print(f"\n[Tool: {event['name']}]")
    elif event_type == 'tool_result':
        print(f"[Result: {'✓' if event['success'] else '✗'}]")
    elif event_type == 'done':
        print(f"\n✓ Complete! Metrics: {event['metrics']}")
        break
```

### Template: Using Context Manager

```python
from backend.context_manager import ContextManager

# Initialize
context_mgr = ContextManager(workspace_root="/app", max_tokens=8192)

# Build optimized context
result = context_mgr.build_context(
    messages=conversation_history,
    system_prompt=base_system_prompt,
    relevant_files=['backend/server.py', 'backend/tools.py']
)

print(f"Total tokens: {result['total_tokens']}")
print(f"Has project context: {result['has_project_context']}")

# Use optimized context with LLM
optimized_messages = result['messages']
enhanced_system = result['system_prompt']
```

### Template: Using Vector Store

```python
from backend.vector_store import VectorStore

# Initialize
store = VectorStore(workspace="/app", collection_name="myproject")

# Index workspace
result = store.index_workspace(
    file_patterns=['*.py', '*.js', '*.ts'],
    exclude_patterns=['**/node_modules/**', '**/__pycache__/**']
)
print(f"Indexed {result['files_indexed']} files, {result['chunks_created']} chunks")

# Semantic search
results = store.search(
    query="How does authentication work?",
    top_k=5,
    min_score=0.5
)

for result in results:
    print(f"File: {result['file']}")
    print(f"Score: {result['score']:.2f}")
    print(f"Content: {result['content'][:200]}...\n")

# Get stats
stats = store.get_stats()
print(f"Total documents: {stats['count']}")
```

### Template: Using Code Verifier

```python
from backend.verification import CodeVerifier

# Initialize
verifier = CodeVerifier(workspace_root="/app")

# Verify a file
result = verifier.verify_file('backend/server.py')

if result['success']:
    print("✓ Verification passed")
    if result.get('warnings'):
        print(f"Warnings: {len(result['warnings'])}")
else:
    print("✗ Verification failed")
    for error in result.get('errors', []):
        print(f"  Line {error.get('line')}: {error.get('message')}")

# Verify Python code directly
code = '''
def hello():
    print("Hello, world!")
'''

result = verifier.verify_python(code)
print(f"Python syntax: {'✓' if result['success'] else '✗'}")

# Run tests
test_result = verifier.run_tests(test_command='pytest -v')
if test_result['success']:
    print("✓ All tests passed")
else:
    print(f"✗ Tests failed: {test_result.get('errors')}")
```

---

## Integration Example: Complete Chat Flow

```python
import asyncio
from backend.llm_client import LLMClient
from backend.tools import ToolExecutor
from backend.context_manager import ContextManager
from backend.verification import CodeVerifier
from backend.agent_loop import AgenticLoop

async def chat_with_tools(user_message: str):
    # Initialize all components
    llm = LLMClient()
    tools = ToolExecutor()
    context = ContextManager(workspace_root="/app")
    verifier = CodeVerifier(workspace_root="/app")
    
    # Create agentic loop
    loop = AgenticLoop(
        llm_client=llm,
        tool_executor=tools,
        context_manager=context,
        max_iterations=15,
        max_retries=3
    )
    
    # Prepare messages
    messages = [{"role": "user", "content": user_message}]
    
    # Run loop
    print(f"User: {user_message}\n")
    print("Assistant: ", end='', flush=True)
    
    async for event in loop.run(messages, session_id="demo"):
        if event['type'] == 'content':
            print(event['content'], end='', flush=True)
        elif event['type'] == 'tool_call':
            print(f"\n\n[Executing {event['name']}...]")
        elif event['type'] == 'tool_result':
            status = '✓' if event['success'] else '✗'
            print(f"[{status}]\n", end='', flush=True)
        elif event['type'] == 'verification':
            status = event['status']
            if status['success']:
                print("\n[✓ Verification passed]\n")
            else:
                print(f"\n[✗ Verification failed: {status.get('error')}]\n")
        elif event['type'] == 'done':
            metrics = event.get('metrics', {})
            print(f"\n\n✓ Complete! ")
            print(f"  Iterations: {metrics.get('iterations', 0)}")
            print(f"  Tool calls: {metrics.get('tool_calls', 0)}")
            print(f"  Failures: {metrics.get('tool_failures', 0)}")
            break
        elif event['type'] == 'error':
            print(f"\n\n✗ Error: {event['message']}")
            break

# Run it
if __name__ == "__main__":
    asyncio.run(chat_with_tools("Create a simple Python calculator module"))
```

---

## Performance Optimizations

### 1. Context Window Management
- Use sliding window for conversation history
- Prioritize recent messages over old ones
- Compress or summarize distant history
- Token counting to stay within limits

### 2. Tool Execution
- Parallel tool execution where possible
- Timeout enforcement (default 30s)
- Result caching for expensive operations
- Lazy loading of file contents

### 3. Vector Search
- Incremental indexing (don't re-index unchanged files)
- Chunk size optimization (512 tokens)
- Top-k limiting (default 5 results)
- Score threshold filtering

### 4. Verification
- Fast syntax checks first (ast.parse)
- Skip lint for non-critical changes
- Cache verification results
- Parallel verification when possible

---

## Best Practices

### For Users
1. Create CLAUDE.md in your project root
2. Index workspace before semantic search
3. Use /status to check current provider
4. Switch to Ollama for privacy
5. Use cloud as fallback for better accuracy

### For Developers
1. Always handle tool execution errors
2. Verify file changes immediately
3. Use context manager for large conversations
4. Implement retries with exponential backoff
5. Log everything for debugging
6. Keep tool responses concise
7. Use streaming for better UX
8. Test with both Ollama and cloud

---

## Debugging Tips

### Check Backend Status
```bash
sudo supervisorctl status backend
tail -f /var/log/supervisor/backend.*.log
```

### Test API Directly
```bash
curl http://localhost:8001/api/health
curl http://localhost:8001/api/models/status
```

### Check Ollama
```bash
ollama list
ollama ps
curl http://localhost:11434/api/tags
```

### Test Tools Directly
```python
from backend.tools import ToolExecutor
tools = ToolExecutor()

result = tools.execute_tool('read_file', {'path': 'test.py'})
print(result)
```

### Debug Context
```python
from backend.context_manager import ContextManager
ctx = ContextManager()
print(ctx.get_project_context())
print(ctx.get_workspace_summary())
```
