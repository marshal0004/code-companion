import os
import json
import re
import asyncio
from typing import List, Dict, Optional, AsyncGenerator
from enum import Enum

# Check available LLM providers
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    EMERGENT_AVAILABLE = True
except ImportError:
    EMERGENT_AVAILABLE = False


class LLMProvider(Enum):
    OLLAMA = "ollama"
    EMERGENT = "emergent"
    OPENAI = "openai"


# Recommended models for coding
RECOMMENDED_MODELS = {
    "ollama": [
        "deepseek-coder-v2:latest",
        "deepseek-coder:33b",
        "deepseek-coder:6.7b",
        "qwen2.5-coder:32b",
        "qwen2.5-coder:7b",
        "codellama:34b",
        "codellama:13b",
        "codellama:7b",
        "llama3.1:8b",
        "mistral:latest",
    ],
    "emergent": [
        "gpt-5.1",
        "gpt-4o",
        "gpt-4o-mini",
        "claude-sonnet-4-20250514",
    ]
}


def get_system_prompt_with_tools() -> str:
    return """You are CodeCompanion, an expert AI coding assistant with the ability to execute tools.

You can help users with:
- Writing and editing code
- Reading and analyzing files
- Executing shell commands
- Searching codebases
- Debugging issues
- Refactoring code
- Git operations (status, diff, log, blame)

IMPORTANT: You have access to tools. When you need to use a tool, output it in this EXACT format:

<TOOL_CALL>
{
  "tool": "tool_name",
  "args": {"arg1": "value1", "arg2": "value2"}
}
</TOOL_CALL>

Available tools:

1. **read_file** - Read contents of a file
   Args: {"path": "relative/path/to/file", "start_line": 1, "end_line": 100}
   Example: <TOOL_CALL>{"tool": "read_file", "args": {"path": "server.py"}}</TOOL_CALL>

2. **write_file** - Create or overwrite a file
   Args: {"path": "path/to/file", "content": "file content here"}
   Example: <TOOL_CALL>{"tool": "write_file", "args": {"path": "test.py", "content": "print('hello')"}}</TOOL_CALL>

3. **edit_file** - Edit specific parts of a file
   Args: {"path": "file.py", "old_text": "text to find", "new_text": "replacement"}
   Example: <TOOL_CALL>{"tool": "edit_file", "args": {"path": "app.py", "old_text": "old code", "new_text": "new code"}}</TOOL_CALL>

4. **list_directory** - List directory contents
   Args: {"path": ".", "recursive": false}
   Example: <TOOL_CALL>{"tool": "list_directory", "args": {"path": "backend"}}</TOOL_CALL>

5. **run_command** - Execute shell command
   Args: {"command": "shell command", "timeout": 30}
   Example: <TOOL_CALL>{"tool": "run_command", "args": {"command": "ls -la"}}</TOOL_CALL>

6. **search_text** - Search for text in files
   Args: {"query": "search term", "path": ".", "file_pattern": "*.py"}
   Example: <TOOL_CALL>{"tool": "search_text", "args": {"query": "def main"}}</TOOL_CALL>

7. **git_status** - Get git repository status
   Args: {}
   Example: <TOOL_CALL>{"tool": "git_status", "args": {}}</TOOL_CALL>

8. **git_diff** - Show git diff (staged or unstaged)
   Args: {"staged": false, "file": null}
   Example: <TOOL_CALL>{"tool": "git_diff", "args": {"staged": false}}</TOOL_CALL>

9. **git_log** - Show git commit history
   Args: {"count": 10, "file": null}
   Example: <TOOL_CALL>{"tool": "git_log", "args": {"count": 5}}</TOOL_CALL>

10. **git_blame** - Show git blame for a file
    Args: {"path": "file.py", "start_line": 1, "end_line": 50}
    Example: <TOOL_CALL>{"tool": "git_blame", "args": {"path": "server.py"}}</TOOL_CALL>

11. **semantic_search** - Search code semantically using embeddings
    Args: {"query": "find authentication logic", "top_k": 5}
    Example: <TOOL_CALL>{"tool": "semantic_search", "args": {"query": "database connection"}}</TOOL_CALL>

When you use a tool:
1. Output the <TOOL_CALL> block
2. Wait for the tool result
3. Use the result to continue helping the user

You can call multiple tools in sequence to accomplish complex tasks.
Be proactive - if you need information from files or need to run commands, use the tools!

IMPORTANT RULES:
- Always use tools when you need to access files, run commands, or search code
- Be concise and helpful
- Explain what you're doing before calling tools
- After getting tool results, explain what you found
- For complex tasks, break them down into steps and use multiple tools
"""


def extract_tool_calls(text: str) -> List[Dict]:
    """Extract tool calls from LLM response"""
    tool_calls = []
    pattern = r'<TOOL_CALL>\s*({[^}]+})\s*</TOOL_CALL>'
    matches = re.findall(pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            tool_call = json.loads(match)
            if 'tool' in tool_call and 'args' in tool_call:
                tool_calls.append(tool_call)
        except json.JSONDecodeError:
            continue
    
    return tool_calls


def remove_tool_calls(text: str) -> str:
    """Remove tool call blocks from text"""
    pattern = r'<TOOL_CALL>.*?</TOOL_CALL>'
    return re.sub(pattern, '', text, flags=re.DOTALL).strip()


class OllamaClient:
    """Ollama local LLM client"""
    
    def __init__(self, model: str = "deepseek-coder:6.7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.client = ollama.Client(host=base_url) if OLLAMA_AVAILABLE else None
    
    def is_available(self) -> bool:
        """Check if Ollama is available and running"""
        if not OLLAMA_AVAILABLE:
            return False
        try:
            self.client.list()
            return True
        except Exception:
            return False
    
    def list_models(self) -> List[str]:
        """List available Ollama models"""
        if not self.is_available():
            return []
        try:
            response = self.client.list()
            return [m['name'] for m in response.get('models', [])]
        except Exception:
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry"""
        if not self.is_available():
            return False
        try:
            self.client.pull(model_name)
            return True
        except Exception as e:
            print(f"Failed to pull model {model_name}: {e}")
            return False
    
    async def chat(self, messages: List[Dict], system_prompt: str = None) -> Dict:
        """Send chat message to Ollama"""
        if not self.is_available():
            raise Exception("Ollama is not available")
        
        ollama_messages = []
        
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            role = msg.get('role', 'user')
            if role == 'tool':
                role = 'user'  # Ollama doesn't have tool role, use user
                content = f"Tool Result: {msg.get('content', '')}"
            else:
                content = msg.get('content', '')
            ollama_messages.append({"role": role, "content": content})
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=ollama_messages,
                options={
                    "temperature": 0.7,
                    "num_ctx": 8192,  # Context window
                }
            )
            return {
                "content": response['message']['content'],
                "model": self.model,
                "provider": "ollama"
            }
        except Exception as e:
            raise Exception(f"Ollama error: {str(e)}")
    
    async def chat_stream(self, messages: List[Dict], system_prompt: str = None) -> AsyncGenerator[str, None]:
        """Stream chat response from Ollama"""
        if not self.is_available():
            raise Exception("Ollama is not available")
        
        ollama_messages = []
        
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            role = msg.get('role', 'user')
            if role == 'tool':
                role = 'user'
                content = f"Tool Result: {msg.get('content', '')}"
            else:
                content = msg.get('content', '')
            ollama_messages.append({"role": role, "content": content})
        
        try:
            stream = self.client.chat(
                model=self.model,
                messages=ollama_messages,
                stream=True,
                options={
                    "temperature": 0.7,
                    "num_ctx": 8192,
                }
            )
            
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
        except Exception as e:
            raise Exception(f"Ollama streaming error: {str(e)}")


class EmergentClient:
    """Emergent/OpenAI cloud LLM client"""
    
    def __init__(self, model: str = "gpt-5.1"):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY', 'sk-emergent-7C8099801D3E1A68d9')
        self.model = model
        self.provider = "openai"
    
    def is_available(self) -> bool:
        """Check if Emergent API is available"""
        return EMERGENT_AVAILABLE and bool(self.api_key)
    
    async def chat(self, messages: List[Dict], system_prompt: str = None) -> Dict:
        """Send chat message to Emergent API"""
        if not self.is_available():
            raise Exception("Emergent API is not available")
        
        conversation_text = ""
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'user':
                conversation_text += f"\n\nUser: {content}"
            elif role == 'assistant':
                conversation_text += f"\n\nAssistant: {content}"
            elif role == 'tool':
                conversation_text += f"\n\nTool Result: {content}"
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id="codecompanion",
                system_message=system_prompt or get_system_prompt_with_tools()
            ).with_model(self.provider, self.model)
            
            user_msg = UserMessage(text=conversation_text.strip())
            response = await chat.send_message(user_msg)
            
            return {
                "content": response,
                "model": self.model,
                "provider": "emergent"
            }
        except Exception as e:
            raise Exception(f"Emergent API error: {str(e)}")


class LLMClient:
    """Multi-provider LLM client with automatic fallback"""
    
    def __init__(self, 
                 provider: str = "auto",
                 model: str = None,
                 ollama_url: str = "http://localhost:11434"):
        """
        Initialize LLM client.
        
        Args:
            provider: "ollama", "emergent", or "auto" (tries ollama first, falls back to emergent)
            model: Model name (provider-specific)
            ollama_url: Ollama server URL for local mode
        """
        self.preferred_provider = provider
        self.ollama_url = ollama_url
        
        # Initialize clients
        self.ollama_client = OllamaClient(
            model=model or "deepseek-coder:6.7b",
            base_url=ollama_url
        ) if OLLAMA_AVAILABLE else None
        
        self.emergent_client = EmergentClient(
            model=model or "gpt-5.1"
        ) if EMERGENT_AVAILABLE else None
        
        # Determine active provider
        self._active_provider = None
        self._active_model = model
        self._determine_provider()
    
    def _determine_provider(self):
        """Determine which provider to use based on availability"""
        if self.preferred_provider == "ollama":
            if self.ollama_client and self.ollama_client.is_available():
                self._active_provider = "ollama"
            else:
                raise Exception("Ollama requested but not available")
        elif self.preferred_provider == "emergent":
            if self.emergent_client and self.emergent_client.is_available():
                self._active_provider = "emergent"
            else:
                raise Exception("Emergent API requested but not available")
        else:  # auto
            # Try Ollama first (free), fall back to Emergent
            if self.ollama_client and self.ollama_client.is_available():
                self._active_provider = "ollama"
            elif self.emergent_client and self.emergent_client.is_available():
                self._active_provider = "emergent"
            else:
                raise Exception("No LLM provider available")
    
    @property
    def active_provider(self) -> str:
        return self._active_provider
    
    @property
    def active_model(self) -> str:
        if self._active_provider == "ollama" and self.ollama_client:
            return self.ollama_client.model
        elif self._active_provider == "emergent" and self.emergent_client:
            return self.emergent_client.model
        return "unknown"
    
    def switch_provider(self, provider: str, model: str = None):
        """Switch to a different provider/model"""
        if provider == "ollama":
            if not self.ollama_client or not self.ollama_client.is_available():
                raise Exception("Ollama is not available")
            self._active_provider = "ollama"
            if model:
                self.ollama_client.model = model
        elif provider == "emergent":
            if not self.emergent_client or not self.emergent_client.is_available():
                raise Exception("Emergent API is not available")
            self._active_provider = "emergent"
            if model:
                self.emergent_client.model = model
        else:
            raise Exception(f"Unknown provider: {provider}")
    
    def list_available_models(self) -> Dict[str, List[str]]:
        """List all available models by provider"""
        models = {}
        
        if self.ollama_client and self.ollama_client.is_available():
            local_models = self.ollama_client.list_models()
            models["ollama"] = local_models if local_models else RECOMMENDED_MODELS["ollama"]
        
        if self.emergent_client and self.emergent_client.is_available():
            models["emergent"] = RECOMMENDED_MODELS["emergent"]
        
        return models
    
    def get_status(self) -> Dict:
        """Get current LLM status"""
        return {
            "active_provider": self._active_provider,
            "active_model": self.active_model,
            "ollama_available": self.ollama_client.is_available() if self.ollama_client else False,
            "emergent_available": self.emergent_client.is_available() if self.emergent_client else False,
            "available_models": self.list_available_models()
        }
    
    async def chat_stream(self, messages: List[Dict], session_id: str = "default") -> Dict:
        """Send chat message and get response with tool calling support"""
        system_prompt = get_system_prompt_with_tools()
        
        try:
            if self._active_provider == "ollama":
                # Collect full response from stream
                full_response = ""
                async for chunk in self.ollama_client.chat_stream(messages, system_prompt):
                    full_response += chunk
                
                response_text = full_response
            else:
                # Use Emergent
                result = await self.emergent_client.chat(messages, system_prompt)
                response_text = result["content"]
            
            # Extract tool calls
            tool_calls = extract_tool_calls(response_text)
            clean_response = remove_tool_calls(response_text)
            
            return {
                "response": clean_response,
                "tool_calls": tool_calls,
                "raw_response": response_text,
                "provider": self._active_provider,
                "model": self.active_model
            }
            
        except Exception as e:
            # Try fallback if available
            if self._active_provider == "ollama" and self.emergent_client and self.emergent_client.is_available():
                print(f"Ollama failed, falling back to Emergent: {e}")
                self._active_provider = "emergent"
                return await self.chat_stream(messages, session_id)
            raise Exception(f"LLM error: {str(e)}")
