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
        self.current_provider = "auto"
        self.current_model = "auto"
    
    def print_banner(self):
        banner = """
╔═══════════════════════════════════════╗
║   CodeCompanion - AI Coding Assistant   ║
║   Type 'exit' to quit, 'help' for commands ║
╚═══════════════════════════════════════╝
"""
        self.console.print(banner, style="bold cyan")
        
        # Show current model status
        try:
            response = requests.get(f"{API_URL}/api/models/status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                self.current_provider = status.get('active_provider', 'unknown')
                self.current_model = status.get('active_model', 'unknown')
                
                provider_color = "green" if self.current_provider == "ollama" else "cyan"
                self.console.print(f"[{provider_color}]Provider: {self.current_provider} | Model: {self.current_model}[/{provider_color}]\n")
        except:
            pass
    
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
    
    def list_models(self):
        """List available models"""
        try:
            response = requests.get(f"{API_URL}/api/models/list", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', {})
                
                self.console.print("\n[bold]Available Models:[/bold]")
                
                if 'ollama' in models:
                    self.console.print("\n[green]Ollama (Local - FREE):[/green]")
                    for model in models['ollama']:
                        self.console.print(f"  • {model}")
                
                if 'emergent' in models:
                    self.console.print("\n[cyan]Emergent (Cloud):[/cyan]")
                    for model in models['emergent']:
                        self.console.print(f"  • {model}")
                
                current = data.get('current_provider', 'unknown')
                model_name = data.get('current_model', 'unknown')
                self.console.print(f"\n[yellow]Current: {current} ({model_name})[/yellow]")
            else:
                self.console.print(f"[red]Failed to fetch models: {response.status_code}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def switch_model(self, provider: str, model: Optional[str] = None):
        """Switch to a different provider/model"""
        try:
            response = requests.post(
                f"{API_URL}/api/models/switch",
                params={"provider": provider, "model": model} if model else {"provider": provider},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.current_provider = data.get('active_provider')
                self.current_model = data.get('active_model')
                
                provider_color = "green" if self.current_provider == "ollama" else "cyan"
                self.console.print(f"[{provider_color}]✓ Switched to {self.current_provider} ({self.current_model})[/{provider_color}]")
            else:
                error_msg = response.json().get('detail', 'Unknown error')
                self.console.print(f"[red]Failed to switch: {error_msg}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def show_status(self):
        """Show current model status"""
        try:
            response = requests.get(f"{API_URL}/api/models/status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                
                self.console.print("\n[bold]Current Status:[/bold]")
                self.console.print(f"Provider: {status.get('active_provider', 'unknown')}")
                self.console.print(f"Model: {status.get('active_model', 'unknown')}")
                self.console.print(f"Ollama Available: {'✓' if status.get('ollama_available') else '✗'}")
                self.console.print(f"Emergent Available: {'✓' if status.get('emergent_available') else '✗'}")
            else:
                self.console.print(f"[red]Failed to fetch status[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def index_workspace(self):
        """Index workspace for semantic search"""
        try:
            self.console.print("[yellow]Indexing workspace...[/yellow]")
            response = requests.post(f"{API_URL}/api/index/workspace", timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.console.print(f"[green]✓ Indexed {result.get('indexed_files', 0)} files[/green]")
                else:
                    self.console.print(f"[red]Indexing failed: {result.get('error')}[/red]")
            else:
                self.console.print(f"[red]Indexing failed: {response.status_code}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def show_index_stats(self):
        """Show indexing statistics"""
        try:
            response = requests.get(f"{API_URL}/api/index/stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                if stats.get('success'):
                    self.console.print("\n[bold]Index Statistics:[/bold]")
                    self.console.print(f"Collection: {stats.get('collection', 'unknown')}")
                    self.console.print(f"Documents: {stats.get('document_count', 0)}")
                    self.console.print(f"Workspace: {stats.get('workspace', 'unknown')}")
                else:
                    self.console.print(f"[yellow]{stats.get('error', 'Index not available')}[/yellow]")
            else:
                self.console.print(f"[red]Failed to fetch stats[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
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
- `/models` - List available AI models
- `/switch <provider> [model]` - Switch AI provider/model
- `/status` - Show current model status
- `/index` - Index workspace for semantic search
- `/indexstats` - Show indexing statistics

**Available Tools:**
- Read/write/edit files
- List directories
- Execute shell commands
- Search text in files (grep/ripgrep)
- Git operations (status, diff, log, blame)
- Semantic code search

**Examples:**
- "Read the server.py file"
- "Create a hello world Python script"
- "Show me the git status"
- "Search for authentication code"

Just ask naturally, and CodeCompanion will help you!
"""
                    self.console.print(Markdown(help_text))
                    continue
                
                elif user_input.lower() == '/models':
                    self.list_models()
                    continue
                
                elif user_input.lower().startswith('/switch'):
                    parts = user_input.split()
                    if len(parts) < 2:
                        self.console.print("[red]Usage: /switch <provider> [model][/red]")
                        self.console.print("[yellow]Example: /switch ollama deepseek-coder:6.7b[/yellow]")
                    else:
                        provider = parts[1]
                        model = parts[2] if len(parts) > 2 else None
                        self.switch_model(provider, model)
                    continue
                
                elif user_input.lower() == '/status':
                    self.show_status()
                    continue
                
                elif user_input.lower() == '/index':
                    self.index_workspace()
                    continue
                
                elif user_input.lower() == '/indexstats':
                    self.show_index_stats()
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
