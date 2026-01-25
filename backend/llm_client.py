import os
from emergentintegrations.llm.chat import LlmChat, UserMessage
from typing import List, Dict, Optional
import json
import re

class LLMClient:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY', 'sk-emergent-7C8099801D3E1A68d9')
        self.provider = "openai"
        self.model = "gpt-5.1"
    
    def get_system_prompt_with_tools(self) -> str:
        return """You are CodeCompanion, an expert AI coding assistant with the ability to execute tools.

You can help users with:
- Writing and editing code
- Reading and analyzing files
- Executing shell commands
- Searching codebases
- Debugging issues
- Refactoring code

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
"""
    
    def extract_tool_calls(self, text: str) -> List[Dict]:
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
    
    def remove_tool_calls(self, text: str) -> str:
        """Remove tool call blocks from text"""
        pattern = r'<TOOL_CALL>.*?</TOOL_CALL>'
        return re.sub(pattern, '', text, flags=re.DOTALL).strip()
    
    async def chat_stream(self, messages: List[Dict], session_id: str = "default") -> Dict:
        """Send chat message and get response with tool calling support"""
        try:
            # Extract system message and build conversation
            system_message = self.get_system_prompt_with_tools()
            conversation_text = ""
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                elif msg['role'] == 'user':
                    conversation_text += f"\n\nUser: {msg['content']}"
                elif msg['role'] == 'assistant':
                    conversation_text += f"\n\nAssistant: {msg['content']}"
                elif msg['role'] == 'tool':
                    # Add tool results to conversation
                    conversation_text += f"\n\nTool Result: {msg['content']}"
            
            # Get last user message
            user_messages = [m['content'] for m in messages if m['role'] == 'user']
            if not user_messages:
                return {"response": "", "tool_calls": []}
            
            # Create chat with context
            full_message = conversation_text.strip()
            if not full_message:
                full_message = user_messages[-1]
            
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=system_message
            ).with_model(self.provider, self.model)
            
            # Send message
            user_msg = UserMessage(text=full_message)
            response = await chat.send_message(user_msg)
            
            # Extract tool calls
            tool_calls = self.extract_tool_calls(response)
            
            # Remove tool call blocks from response
            clean_response = self.remove_tool_calls(response)
            
            return {
                "response": clean_response,
                "tool_calls": tool_calls,
                "raw_response": response
            }
            
        except Exception as e:
            raise Exception(f"LLM error: {str(e)}")
