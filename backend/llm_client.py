import os
import json
import re
import asyncio
from typing import List, Dict, Optional, AsyncGenerator
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check available LLM providers
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    EMERGENT_AVAILABLE = True
except ImportError:
    EMERGENT_AVAILABLE = False


class LLMProvider(Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"
    EMERGENT = "emergent"


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
    "gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro",
    ],
    "emergent": [
        "gpt-5.1",
        "gpt-4o",
        "gpt-4o-mini",
        "claude-sonnet-4-20250514",
    ]
}


def get_system_prompt_with_tools() -> str:
    """Get enhanced system prompt for CodeCompanion"""
    return '''You are CodeCompanion, an expert AI coding assistant with tool execution capabilities.

## CAPABILITIES
You can help with:
- Writing, editing, and analyzing code
- Reading and modifying files
- Executing shell commands safely
- Searching codebases (text + semantic)
- Git operations (status, diff, log, blame)
- Debugging and troubleshooting

## TOOL USAGE

When you need to interact with the system, use this EXACT format:

<TOOL_CALL>
{"tool": "tool_name", "args": {"arg1": "value1"}}
</TOOL_CALL>

### Available Tools:

1. **read_file** - Read file contents
   Args: {"path": "file.py", "start_line": 1, "end_line": 100}
   Example: <TOOL_CALL>{"tool": "read_file", "args": {"path": "server.py"}}</TOOL_CALL>

2. **write_file** - Create or overwrite file (auto-backup created)
   Args: {"path": "file.py", "content": "code here"}
   Example: <TOOL_CALL>{"tool": "write_file", "args": {"path": "test.py", "content": "print('hello')"}}</TOOL_CALL>

3. **edit_file** - Surgical edit using search/replace (auto-backup created)
   Args: {"path": "file.py", "old_text": "old code", "new_text": "new code"}
   Example: <TOOL_CALL>{"tool": "edit_file", "args": {"path": "app.py", "old_text": "x = 1", "new_text": "x = 2"}}</TOOL_CALL>

4. **list_directory** - List files and folders
   Args: {"path": ".", "recursive": true, "max_depth": 3}
   Example: <TOOL_CALL>{"tool": "list_directory", "args": {"path": "backend", "recursive": true}}</TOOL_CALL>

5. **run_command** - Execute shell command safely
   Args: {"command": "shell command", "timeout": 30}
   Example: <TOOL_CALL>{"tool": "run_command", "args": {"command": "ls -la"}}</TOOL_CALL>

6. **search_text** - Search in files using grep/ripgrep
   Args: {"query": "search term", "path": ".", "file_pattern": "*.py"}
   Example: <TOOL_CALL>{"tool": "search_text", "args": {"query": "def main"}}</TOOL_CALL>

7. **git_status** - Get repository status
   Args: {}
   Example: <TOOL_CALL>{"tool": "git_status", "args": {}}</TOOL_CALL>

8. **git_diff** - Show changes
   Args: {"staged": false, "file": null}
   Example: <TOOL_CALL>{"tool": "git_diff", "args": {"staged": false}}</TOOL_CALL>

9. **git_log** - Commit history
   Args: {"count": 10, "file": null}
   Example: <TOOL_CALL>{"tool": "git_log", "args": {"count": 10}}</TOOL_CALL>

10. **git_blame** - Line-by-line history
    Args: {"path": "file.py", "start_line": 1, "end_line": 50}
    Example: <TOOL_CALL>{"tool": "git_blame", "args": {"path": "server.py"}}</TOOL_CALL>

11. **semantic_search** - AI-powered semantic search
    Args: {"query": "find authentication logic", "top_k": 5}
    Example: <TOOL_CALL>{"tool": "semantic_search", "args": {"query": "database connection"}}</TOOL_CALL>

12. **index_workspace** - Index code for semantic search
    Args: {}
    Example: <TOOL_CALL>{"tool": "index_workspace", "args": {}}</TOOL_CALL>

## WORKFLOW

1. **Understand** - Read the request carefully
2. **Plan** - Break complex tasks into steps (think step by step)
3. **Investigate** - Use tools to gather information FIRST
4. **Execute** - Implement the solution
5. **Verify** - Check the results work correctly

## BEST PRACTICES

- ALWAYS read files before editing them
- Use edit_file for small changes, write_file for new/complete rewrites
- Test commands before running destructive operations
- Explain what you're doing before taking actions
- After tool execution, analyze results and continue or fix issues
- If something fails, try alternative approaches (max 3 retries)
- Keep responses concise but informative
- For complex tasks, work iteratively with verification

## IMPORTANT RULES

- Use tools proactively when you need information
- Always check tool results and handle errors gracefully
- If a tool fails, explain the error and try an alternative
- For file modifications, the old_text must match EXACTLY
- Verify your changes work before completing
- Be helpful, accurate, and efficient
'''


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
    
    def pull_model(self, model_name: str, progress_callback=None) -> Dict:
        """Pull a model from Ollama registry with progress tracking"""
        if not self.is_available():
            return {"success": False, "error": "Ollama is not available"}
        try:
            # Use streaming pull for progress
            stream = self.client.pull(model_name, stream=True)
            
            last_status = ""
            for chunk in stream:
                if chunk.get('status') != last_status:
                    last_status = chunk.get('status', '')
                    if progress_callback:
                        progress_callback(chunk)
            
            return {"success": True, "model": model_name, "message": f"Successfully pulled {model_name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
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


class GeminiClient:
    """Google Gemini LLM client - FREE TIER FRIENDLY"""
    
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.api_key = os.environ.get('GEMINI_API_KEY', '')
        self.model = model
        self._initialized = False
        self._model_instance = None
        
        if self.api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self._initialized = True
            except Exception as e:
                print(f"Gemini initialization error: {e}")
    
    def is_available(self) -> bool:
        """Check if Gemini API is available"""
        return GEMINI_AVAILABLE and bool(self.api_key) and self._initialized
    
    def _get_model(self):
        """Get or create model instance"""
        if self._model_instance is None or self._model_instance.model_name != f"models/{self.model}":
            self._model_instance = genai.GenerativeModel(
                model_name=self.model,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                }
            )
        return self._model_instance
    
    async def chat(self, messages: List[Dict], system_prompt: str = None) -> Dict:
        """Send chat message to Gemini"""
        if not self.is_available():
            raise Exception("Gemini API is not available")
        
        try:
            model = self._get_model()
            
            # Build conversation history
            history = []
            for msg in messages[:-1]:  # All except last message
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                
                if role == 'user':
                    history.append({"role": "user", "parts": [content]})
                elif role == 'assistant':
                    history.append({"role": "model", "parts": [content]})
                elif role == 'tool':
                    history.append({"role": "user", "parts": [f"Tool Result: {content}"]})
            
            # Get last message
            last_msg = messages[-1] if messages else {"content": ""}
            last_content = last_msg.get('content', '')
            
            # Start chat with system prompt
            full_prompt = ""
            if system_prompt:
                full_prompt = f"System Instructions: {system_prompt}\n\n"
            full_prompt += last_content
            
            # Create chat session
            chat = model.start_chat(history=history)
            
            # Send message
            response = await asyncio.to_thread(chat.send_message, full_prompt)
            
            return {
                "content": response.text,
                "model": self.model,
                "provider": "gemini"
            }
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    async def chat_stream(self, messages: List[Dict], system_prompt: str = None) -> AsyncGenerator[str, None]:
        """Stream chat response from Gemini"""
        if not self.is_available():
            raise Exception("Gemini API is not available")
        
        try:
            model = self._get_model()
            
            # Build conversation history
            history = []
            for msg in messages[:-1]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                
                if role == 'user':
                    history.append({"role": "user", "parts": [content]})
                elif role == 'assistant':
                    history.append({"role": "model", "parts": [content]})
                elif role == 'tool':
                    history.append({"role": "user", "parts": [f"Tool Result: {content}"]})
            
            # Get last message
            last_msg = messages[-1] if messages else {"content": ""}
            last_content = last_msg.get('content', '')
            
            # Build full prompt
            full_prompt = ""
            if system_prompt:
                full_prompt = f"System Instructions: {system_prompt}\n\n"
            full_prompt += last_content
            
            # Create chat and stream response
            chat = model.start_chat(history=history)
            response = chat.send_message(full_prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            raise Exception(f"Gemini streaming error: {str(e)}")


class EmergentClient:
    """Emergent/OpenAI cloud LLM client"""
    
    def __init__(self, model: str = "gpt-5.1"):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY', '')
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
    """Multi-provider LLM client with automatic fallback
    
    Priority order:
    1. Gemini (FREE cloud, user's API key)
    2. Ollama (FREE local)
    3. Emergent (cloud, budget limited)
    """
    
    def __init__(self, 
                 provider: str = "auto",
                 model: str = None,
                 ollama_url: str = "http://localhost:11434"):
        """
        Initialize LLM client.
        
        Args:
            provider: "ollama", "gemini", "emergent", or "auto" (tries best available)
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
        
        self.gemini_client = GeminiClient(
            model=model or "gemini-2.0-flash"
        ) if GEMINI_AVAILABLE else None
        
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
        elif self.preferred_provider == "gemini":
            if self.gemini_client and self.gemini_client.is_available():
                self._active_provider = "gemini"
            else:
                raise Exception("Gemini API requested but not available")
        elif self.preferred_provider == "emergent":
            if self.emergent_client and self.emergent_client.is_available():
                self._active_provider = "emergent"
            else:
                raise Exception("Emergent API requested but not available")
        else:  # auto - prioritize FREE options
            # 1. Try Gemini first (FREE cloud API with user's key)
            if self.gemini_client and self.gemini_client.is_available():
                self._active_provider = "gemini"
            # 2. Try Ollama (FREE local)
            elif self.ollama_client and self.ollama_client.is_available():
                self._active_provider = "ollama"
            # 3. Fall back to Emergent (has budget limits)
            elif self.emergent_client and self.emergent_client.is_available():
                self._active_provider = "emergent"
            else:
                raise Exception("No LLM provider available. Please set GEMINI_API_KEY or install Ollama.")
    
    @property
    def active_provider(self) -> str:
        return self._active_provider
    
    @property
    def active_model(self) -> str:
        if self._active_provider == "ollama" and self.ollama_client:
            return self.ollama_client.model
        elif self._active_provider == "gemini" and self.gemini_client:
            return self.gemini_client.model
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
        elif provider == "gemini":
            if not self.gemini_client or not self.gemini_client.is_available():
                raise Exception("Gemini API is not available")
            self._active_provider = "gemini"
            if model:
                self.gemini_client.model = model
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
        
        if self.gemini_client and self.gemini_client.is_available():
            models["gemini"] = RECOMMENDED_MODELS["gemini"]
        
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
            "gemini_available": self.gemini_client.is_available() if self.gemini_client else False,
            "ollama_available": self.ollama_client.is_available() if self.ollama_client else False,
            "emergent_available": self.emergent_client.is_available() if self.emergent_client else False,
            "available_models": self.list_available_models()
        }
    
    async def chat_stream(self, messages: List[Dict], session_id: str = "default") -> Dict:
        """Send chat message and get response with tool calling support"""
        system_prompt = get_system_prompt_with_tools()
        
        try:
            if self._active_provider == "gemini":
                # Use Gemini (FREE)
                full_response = ""
                async for chunk in self.gemini_client.chat_stream(messages, system_prompt):
                    full_response += chunk
                response_text = full_response
                
            elif self._active_provider == "ollama":
                # Collect full response from Ollama stream
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
            # Try fallback ONLY between FREE providers (Gemini <-> Ollama)
            # NEVER automatically fall back to Emergent (has budget limits)
            error_msg = str(e)
            
            # If Gemini fails, try Ollama (both are FREE)
            if self._active_provider == "gemini" and self.ollama_client and self.ollama_client.is_available():
                print(f"⚠️ Gemini failed, falling back to Ollama (FREE): {e}")
                self._active_provider = "ollama"
                return await self.chat_stream(messages, session_id)
            
            # If Ollama fails, try Gemini (both are FREE)
            elif self._active_provider == "ollama" and self.gemini_client and self.gemini_client.is_available():
                print(f"⚠️ Ollama failed, falling back to Gemini (FREE): {e}")
                self._active_provider = "gemini"
                return await self.chat_stream(messages, session_id)
            
            # DO NOT fall back to Emergent automatically - user must explicitly choose it
            # This prevents wasting budget on API calls
            raise Exception(f"LLM error (NO AUTO-FALLBACK TO EMERGENT): {error_msg}. Use '/switch emergent' to explicitly use paid API.")
