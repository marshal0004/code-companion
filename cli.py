#!/usr/bin/env python3
import sys
import requests
import json
from typing import Optional
import os

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.live import Live
    from rich.spinner import Spinner
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Installing rich for better terminal UI...")
    os.system("pip install rich")
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

API_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')

class CodeCompanionCLI:
    def __init__(self):
        self.console = Console()
        self.conversation_id: Optional[str] = None
        self.project_path = os.getcwd()
    
    def print_banner(self):
        banner = """
╔═══════════════════════════════════════╗
║   CodeCompanion - AI Coding Assistant   ║
║   Type 'exit' to quit, 'clear' to reset ║
╚═══════════════════════════════════════╝
"""
        self.console.print(banner, style="bold cyan")
    
    def chat(self, message: str):
        """Send message and stream response"""
        try:
            response = requests.post(
                f"{API_URL}/api/chat/stream",
                json={
                    "message": message,
                    "conversation_id": self.conversation_id,
                    "project_path": self.project_path
                },
                stream=True,
                timeout=120
            )
            
            if response.status_code != 200:
                self.console.print(f"[red]Error: {response.status_code}[/red]")
                return
            
            content_buffer = ""
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                line = line.decode('utf-8')
                if not line.startswith('data: '):
                    continue
                
                try:
                    data = json.loads(line[6:])
                    
                    if data['type'] == 'content':
                        content_buffer += data['content']
                        # Print character by character for streaming effect
                        self.console.print(data['content'], end='', style="white")
                    
                    elif data['type'] == 'tool_call':
                        self.console.print(f"\n\n[yellow]🔧 Executing tool: {data['name']}[/yellow]")
                        self.console.print(f"[dim]Arguments: {json.dumps(data['args'], indent=2)}[/dim]")
                    
                    elif data['type'] == 'tool_result':
                        result = data['result']
                        if result.get('success'):
                            self.console.print(f"[green]✓ Tool completed successfully[/green]")
                            if 'content' in result:
                                # Show first 200 chars of file content
                                preview = result['content'][:200]
                                self.console.print(f"[dim]{preview}...[/dim]")
                        else:
                            self.console.print(f"[red]✗ Tool failed: {result.get('error')}[/red]")
                    
                    elif data['type'] == 'done':
                        self.conversation_id = data['conversation_id']
                        self.console.print("\n")
                        break
                    
                    elif data['type'] == 'error':
                        self.console.print(f"\n[red]Error: {data['message']}[/red]")
                        break
                
                except json.JSONDecodeError:
                    continue
        
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]Connection error: {e}[/red]")
            self.console.print("[yellow]Make sure the backend is running at {API_URL}[/yellow]")
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted[/yellow]")
    
    def run(self):
        """Main CLI loop"""
        self.print_banner()
        
        while True:
            try:
                # Get user input
                self.console.print("\n[bold cyan]You:[/bold cyan] ", end="")
                user_input = input().strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() == 'exit':
                    self.console.print("[green]Goodbye![/green]")
                    break
                
                elif user_input.lower() == 'clear':
                    self.conversation_id = None
                    self.console.print("[green]Conversation cleared[/green]")
                    continue
                
                elif user_input.lower() == 'help':
                    help_text = """
**Available Commands:**
- `exit` - Quit the application
- `clear` - Start a new conversation
- `help` - Show this help message

**Available Tools:**
- Read/write/edit files
- List directories
- Execute shell commands
- Search text in files

Just ask naturally, and CodeCompanion will help you!
"""
                    self.console.print(Markdown(help_text))
                    continue
                
                # Send to chat
                self.console.print("\n[bold green]Assistant:[/bold green]\n")
                self.chat(user_input)
            
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except EOFError:
                break

if __name__ == "__main__":
    cli = CodeCompanionCLI()
    cli.run()
