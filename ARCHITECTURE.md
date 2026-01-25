# CodeCompanion Architecture Document

## Project Overview
Local AI coding assistant with streaming chat, file operations, shell execution, and code search.

## System Components

### 1. Backend (FastAPI)
- **server.py**: Main FastAPI app with SSE streaming
- **database.py**: SQLite with conversation/message storage
- **tools.py**: Tool execution engine (file ops, shell, search)
- **llm_client.py**: OpenAI client via Emergent LLM key
- **config.py**: Configuration management

### 2. CLI (Python)
- **cli.py**: Terminal interface with streaming display

### 3. Database Schema
```sql
CREATE TABLE conversations (
  id TEXT PRIMARY KEY,
  project_path TEXT,
  title TEXT,
  created_at DATETIME,
  model TEXT
);

CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT,
  role TEXT,
  content TEXT,
  created_at DATETIME,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id)
);

CREATE TABLE tool_calls (
  id TEXT PRIMARY KEY,
  message_id TEXT,
  tool_name TEXT,
  arguments TEXT,
  result TEXT,
  status TEXT,
  FOREIGN KEY(message_id) REFERENCES messages(id)
);
```

### 4. API Endpoints
- POST /api/chat/stream - Streaming chat with tool execution
- GET /api/conversations - List all conversations
- GET /api/conversations/{id} - Get conversation history
- POST /api/tools/execute - Execute tool directly

### 5. Tools Available
1. **read_file** - Read file contents
2. **write_file** - Create/overwrite file
3. **edit_file** - Search/replace edits
4. **list_directory** - List dir contents
5. **run_command** - Execute shell commands
6. **search_text** - Grep/ripgrep search

### 6. Safety Features
- Path traversal prevention
- Command blocklist (rm -rf, sudo, etc.)
- User approval for dangerous operations
- File backups before edits

### 7. Context Management
- 128K token context window
- Priority: system prompt > current message > recent history > project context
- Automatic truncation with summarization

### 8. Technology Stack
- Backend: FastAPI, SQLite, OpenAI (via Emergent)
- CLI: Python with rich/prompt_toolkit
- Storage: ~/.local/share/codecompanion/

## Implementation Status
- [PENDING] Phase 1: Database & config
- [PENDING] Phase 2: LLM client & streaming
- [PENDING] Phase 3: Tool system
- [PENDING] Phase 4: CLI interface
- [PENDING] Phase 5: Testing

## Next Steps
1. Setup database schema
2. Implement OpenAI streaming client
3. Build tool execution engine
4. Create CLI with real-time display
5. Add safety checks
6. Test end-to-end

## Environment Variables
```
OPENAI_API_KEY=sk-emergent-7C8099801D3E1A68d9
OPENAI_BASE_URL=https://api.emergent.com/v1
DB_PATH=~/.local/share/codecompanion/codecompanion.db
WORKSPACE_ROOT=/app
```
