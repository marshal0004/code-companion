# 🚀 CodeCompanion - FREE Claude Code Clone

**A fully functional AI coding assistant that works 100% FREE with Ollama!**

## ✨ What Makes This Special?

### 🆓 Zero Cost with Ollama
- Run powerful coding models **completely FREE** on your local machine
- No API keys, no subscriptions, no usage limits
- Works offline - no internet required!

### 🔄 Multi-Provider Support
- **Ollama** (Local, FREE): DeepSeek-Coder, Qwen2.5-Coder, CodeLlama, and more
- **Cloud Fallback**: Emergent API (GPT-5.1, GPT-4o, Claude Sonnet 4)
- **Auto-Fallback**: Tries local first, falls back to cloud if unavailable
- **Model Switching**: Change models on-the-fly with a single command

### 🛠️ 13 Powerful Tools
All the tools you need for coding assistance:
- **File Operations**: read, write, edit with auto-backup
- **Shell Execution**: Run commands safely
- **Code Search**: Text search + semantic vector search
- **Git Integration**: status, diff, log, blame
- **Workspace Indexing**: ChromaDB embeddings for semantic search

### 🎯 Claude Code Equivalent Features
| Feature | Claude Code | CodeCompanion | Cost |
|---------|-------------|---------------|------|
| Chat Interface | ✓ | ✓ | FREE |
| File Operations | ✓ | ✓ | FREE |
| Shell Execution | ✓ | ✓ | FREE |
| Code Search | ✓ | ✓ | FREE |
| Git Tools | ✓ | ✓ | FREE |
| Semantic Search | ✓ | ✓ | FREE |
| Local LLM | ✗ | ✓ | **FREE!** |
| Multi-Model | ✗ | ✓ | **FREE!** |
| **Monthly Cost** | **$20-100+** | **$0** | **100% FREE** |

---

## 🚀 Quick Start

### Option 1: Use with Ollama (Recommended - FREE!)

#### Step 1: Install Ollama
```bash
# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

#### Step 2: Pull a Coding Model
```bash
# Recommended: DeepSeek Coder 6.7B (fast, good quality, 8GB RAM)
ollama pull deepseek-coder:6.7b

# Or try others:
ollama pull deepseek-coder:33b          # Best quality, needs 24GB RAM
ollama pull qwen2.5-coder:7b            # Alternative, 8GB RAM
ollama pull codellama:13b               # Meta's model, 12GB RAM
```

#### Step 3: Start Ollama Server
```bash
ollama serve
```

#### Step 4: Start CodeCompanion
```bash
cd /app
python cli.py
```

#### Step 5: Switch to Ollama
```
/switch ollama deepseek-coder:6.7b
```

Now you're running 100% FREE locally! 🎉

---

### Option 2: Use with Cloud (Emergent API)

If you don't have Ollama installed, CodeCompanion automatically uses the cloud:

```bash
cd /app
python cli.py
```

It will use the Emergent LLM key (gpt-5.1) as fallback.

---

## 📖 CLI Commands

### Model Management
```bash
/models          # List all available models
/switch <provider> [model]  # Switch provider/model
/status          # Show current model status
```

**Examples:**
```bash
/models                                    # Show available models
/switch ollama deepseek-coder:6.7b        # Use local model
/switch emergent gpt-4o                   # Use cloud model
/status                                    # Check current setup
```

### Semantic Search
```bash
/index           # Index workspace for semantic search
/indexstats      # Show indexing statistics
```

**Examples:**
```bash
/index           # Index all code files in workspace
/indexstats      # See how many files indexed
```

### Chat Commands
```bash
help             # Show help
clear            # Clear conversation
exit             # Quit
```

---

## 💬 Example Usage

### 1. Switch to Local FREE Model
```
You: /switch ollama deepseek-coder:6.7b
✓ Switched to ollama (deepseek-coder:6.7b)
```

### 2. Ask for Help
```
You: Create a FastAPI endpoint for user authentication