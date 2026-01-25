import os
from emergentintegrations.llm.chat import LlmChat, UserMessage
from typing import List, Dict, Iterator, Optional
import json
import asyncio

class LLMClient:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY', 'sk-emergent-7C8099801D3E1A68d9')
        self.provider = "openai"
        self.model = "gpt-4o-mini"
    
    def get_system_prompt(self) -> str:
        return """You are CodeCompanion, an expert AI coding assistant. You help users with:
- Writing and editing code
- Debugging issues
- Explaining code concepts
- Refactoring and optimization
- File operations
- Shell command execution

You have access to tools for file operations, shell execution, and code search. 
Use these tools when needed to help users effectively.

When using tools:
1. read_file - Read file contents
2. write_file - Create or overwrite files
3. edit_file - Make specific edits with search/replace
4. list_directory - List directory contents
5. run_command - Execute shell commands (use cautiously)
6. search_text - Search for text in files

Be concise, accurate, and helpful. Ask clarifying questions when needed."""
    
    def get_tools_schema(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file relative to workspace root"},
                            "start_line": {"type": "integer", "description": "Optional starting line number"},
                            "end_line": {"type": "integer", "description": "Optional ending line number"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Create or overwrite a file with content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file"},
                            "content": {"type": "string", "description": "Complete file content"}
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Edit a file using search and replace",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file"},
                            "old_text": {"type": "string", "description": "Text to find (must match exactly)"},
                            "new_text": {"type": "string", "description": "Replacement text"}
                        },
                        "required": ["path", "old_text", "new_text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List contents of a directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Directory path (default: project root)"},
                            "recursive": {"type": "boolean", "description": "Include subdirectories"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Execute a shell command (use carefully)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to execute"},
                            "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"}
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_text",
                    "description": "Search for text in files",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Text to search for"},
                            "path": {"type": "string", "description": "Directory to search in"},
                            "file_pattern": {"type": "string", "description": "File pattern like '*.py'"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    async def chat_stream(self, messages: List[Dict], session_id: str = "default") -> str:
        \"\"\"Send chat message and get response (non-streaming for now)\"\"\"
        try:
            # Extract system message
            system_message = "You are CodeCompanion, an expert AI coding assistant."
            user_messages = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                elif msg['role'] == 'user':
                    user_messages.append(msg['content'])
            
            # Use last user message
            if not user_messages:
                return \"\"
            
            last_message = user_messages[-1]
            
            # Create chat instance
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=system_message
            ).with_model(self.provider, self.model)
            
            # Send message
            user_msg = UserMessage(text=last_message)
            response = await chat.send_message(user_msg)
            
            return response
            
        except Exception as e:
            raise Exception(f\"LLM error: {str(e)}\")
