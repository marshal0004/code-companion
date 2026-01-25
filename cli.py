#!/usr/bin/env python3
"""
CodeCompanion CLI - AI Coding Assistant
Enhanced CLI with model management, semantic search, and agentic capabilities
"""
import sys
import requests
import json
from typing import Optional
import os
import time

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.table import Table
    from rich.syntax import Syntax
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Installing rich for better terminal UI...")
    os.system("pip install rich")
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table

API_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')

# Recommended models for coding
RECOMMENDED_MODELS = {
    "ollama": [
        ("deepseek-coder-v2:latest", "Best overall coding model"),
        ("deepseek-coder:33b", "Large, very capable"),
        ("deepseek-coder:6.7b", "Good balance of speed/quality"),
        ("qwen2.5-coder:32b", "Excellent for complex tasks"),
        ("qwen2.5-coder:7b", "Fast, good for simple tasks"),
        ("codellama:34b", "Meta's coding model"),
        ("codellama:7b", "Lightweight option"),
        ("llama3.1:8b", "General purpose"),
    ],
    "emergent": [
        ("gpt-5.1", "OpenAI's latest"),
        ("gpt-4o", "Fast and capable"),
        ("claude-sonnet-4-20250514", "Anthropic's best"),
    ]
}


class CodeCompanionCLI:
    def __init__(self):
        self.console = Console()
        self.conversation_id: Optional[str] = None
        self.project_path = os.getcwd()
        self.current_provider = "auto"
        self.current_model = "auto"
        self.iteration_count = 0
    
    def print_banner(self):
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║     🤖 CodeCompanion - AI Coding Assistant                    ║
║     Type 'help' for commands, 'exit' to quit                  ║
╚═══════════════════════════════════════════════════════════════╝
"""
        self.console.print(banner, style="bold cyan")
        
        # Show current model status
        try:
            response = requests.get(f"{API_URL}/api/models/status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                self.current_provider = status.get('active_provider', 'unknown')
                self.current_model = status.get('active_model', 'unknown')
                
                ollama_status = "✓" if status.get('ollama_available') else "✗"
                cloud_status = "✓" if status.get('emergent_available') else "✗"
                
                provider_color = "green" if self.current_provider == "ollama" else "cyan"
                cost_info = "FREE (Local)" if self.current_provider == "ollama" else "Cloud API"
                
                self.console.print(f"[{provider_color}]🔹 Provider: {self.current_provider} | Model: {self.current_model} | {cost_info}[/{provider_color}]")
                self.console.print(f"[dim]   Ollama: {ollama_status} | Cloud: {cloud_status}[/dim]\n")
        except:
            self.console.print("[yellow]⚠ Could not connect to backend. Is it running?[/yellow]\n")
    
    def chat(self, message: str):
        """Send message and stream response with enhanced visualization"""
        try:
            response = requests.post(
                f"{API_URL}/api/chat/stream",
                json={
                    "message": message,
                    "conversation_id": self.conversation_id,
                    "project_path": self.project_path
                },
                stream=True,
                timeout=180
            )
            
            if response.status_code != 200:
                self.console.print(f"[red]Error: {response.status_code}[/red]")
                return
            
            content_buffer = ""
            tool_count = 0
            
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
                        self.console.print(data['content'], end='', style="white")
                    
                    elif data['type'] == 'planning':
                        self.console.print(f"\n[blue]📋 Planning:[/blue]")
                        self.console.print(f"[dim]{data.get('content', '')[:300]}...[/dim]")
                    
                    elif data['type'] == 'tool_call':
                        tool_count += 1
                        iteration = data.get('iteration', self.iteration_count)
                        self.console.print(f"\n\n[yellow]🔧 [{iteration}] Executing: {data['name']}[/yellow]")
                        
                        # Show args nicely
                        args = data.get('args', {})
                        if 'content' in args:
                            # Truncate content for display
                            args = {**args, 'content': args['content'][:100] + '...'}
                        self.console.print(f"[dim]   Args: {json.dumps(args, indent=2)[:200]}[/dim]")
                    
                    elif data['type'] == 'tool_result':
                        result = data['result']
                        success = data.get('success', result.get('success', False))
                        exec_time = data.get('execution_time', 0)
                        
                        if success:
                            self.console.print(f"[green]   ✓ Success ({exec_time:.2f}s)[/green]")
                            # Show preview of result
                            if 'content' in result:
                                preview = result['content'][:150].replace('\n', ' ')
                                self.console.print(f"[dim]   Preview: {preview}...[/dim]")
                            elif 'matches' in result:
                                self.console.print(f"[dim]   Found {result.get('count', 0)} matches[/dim]")
                            elif 'files' in result:
                                self.console.print(f"[dim]   Listed {result.get('count', 0)} items[/dim]")
                        else:
                            error = result.get('error', 'Unknown error')
                            self.console.print(f"[red]   ✗ Failed: {error}[/red]")
                    
                    elif data['type'] == 'verification':
                        status = data.get('status', {})
                        if status.get('success', True):
                            self.console.print(f"[green]   ✓ Verification passed[/green]")
                        else:
                            self.console.print(f"[yellow]   ⚠ Verification: {status.get('error', 'Issue detected')}[/yellow]")
                    
                    elif data['type'] == 'warning':
                        self.console.print(f"\n[yellow]⚠ {data.get('message', 'Warning')}[/yellow]")
                    
                    elif data['type'] == 'done':
                        self.conversation_id = data.get('conversation_id')
                        metrics = data.get('metrics', {})
                        if metrics:
                            iterations = metrics.get('iterations', 0)
                            tools = metrics.get('tool_calls', tool_count)
                            if iterations > 1 or tools > 0:
                                self.console.print(f"\n[dim]   📊 Iterations: {iterations} | Tools: {tools}[/dim]")
                        self.console.print("\n")
                        break
                    
                    elif data['type'] == 'error':
                        self.console.print(f"\n[red]❌ Error: {data['message']}[/red]")
                        errors = data.get('errors', [])
                        if errors:
                            for err in errors[:3]:
                                self.console.print(f"[dim]   - {err}[/dim]")
                        break
                
                except json.JSONDecodeError:
                    continue
        
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]Connection error: {e}[/red]")
            self.console.print(f"[yellow]Make sure the backend is running at {API_URL}[/yellow]")
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted[/yellow]")
    
    def list_models(self):
        """List available models with recommendations"""
        try:
            response = requests.get(f"{API_URL}/api/models/list", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', {})
                
                # Create table
                table = Table(title="Available Models", show_header=True)
                table.add_column("Provider", style="cyan")
                table.add_column("Model", style="white")
                table.add_column("Status", style="green")
                table.add_column("Cost", style="yellow")
                
                current_provider = data.get('current_provider', '')
                current_model = data.get('current_model', '')
                
                if 'ollama' in models:
                    for model in models['ollama'][:8]:
                        is_current = current_provider == 'ollama' and model == current_model
                        status = "◉ Active" if is_current else "○"
                        table.add_row("Ollama", model, status, "FREE")
                
                if 'emergent' in models:
                    for model in models['emergent']:
                        is_current = current_provider == 'emergent' and model == current_model
                        status = "◉ Active" if is_current else "○"
                        table.add_row("Emergent", model, status, "API")
                
                self.console.print(table)
                
                # Show recommendations
                self.console.print("\n[bold]💡 Recommended for Coding:[/bold]")
                self.console.print("  • [green]deepseek-coder:6.7b[/green] - Best balance (FREE)")
                self.console.print("  • [green]qwen2.5-coder:7b[/green] - Fast & capable (FREE)")
                self.console.print("  • [cyan]gpt-5.1[/cyan] - Most capable (Cloud)")
                
            else:
                self.console.print(f"[red]Failed to fetch models: {response.status_code}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def switch_model(self, provider: str, model: Optional[str] = None):
        """Switch to a different provider/model"""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                progress.add_task(description=f"Switching to {provider}...", total=None)
                
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
                cost_info = "FREE (Local)" if self.current_provider == "ollama" else "Cloud API"
                self.console.print(f"[{provider_color}]✓ Switched to {self.current_provider} ({self.current_model}) - {cost_info}[/{provider_color}]")
            else:
                error_msg = response.json().get('detail', 'Unknown error')
                self.console.print(f"[red]Failed to switch: {error_msg}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def pull_model(self, model_name: str):
        """Pull a model from Ollama"""
        try:
            self.console.print(f"[yellow]Pulling model: {model_name}[/yellow]")
            self.console.print("[dim]This may take a while for large models...[/dim]\n")
            
            # Call pull endpoint
            response = requests.post(
                f"{API_URL}/api/models/pull",
                params={"model": model_name},
                timeout=600  # 10 minute timeout for large models
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.console.print(f"[green]✓ Successfully pulled {model_name}[/green]")
                    self.console.print(f"[dim]You can now use: /switch ollama {model_name}[/dim]")
                else:
                    self.console.print(f"[red]Failed: {result.get('error')}[/red]")
            else:
                self.console.print(f"[red]Failed to pull model: {response.status_code}[/red]")
        except requests.exceptions.Timeout:
            self.console.print("[yellow]Pull is still in progress... Check Ollama directly.[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def show_status(self):
        """Show detailed current status"""
        try:
            response = requests.get(f"{API_URL}/api/models/status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                
                # Create status panel
                table = Table(show_header=False, box=None)
                table.add_column("Key", style="cyan")
                table.add_column("Value", style="white")
                
                table.add_row("Provider", status.get('active_provider', 'unknown'))
                table.add_row("Model", status.get('active_model', 'unknown'))
                table.add_row("Ollama", "✓ Available" if status.get('ollama_available') else "✗ Not available")
                table.add_row("Cloud", "✓ Available" if status.get('emergent_available') else "✗ Not available")
                table.add_row("Cost", "FREE" if status.get('active_provider') == 'ollama' else "Cloud API")
                
                self.console.print(Panel(table, title="[bold]Current Status[/bold]", border_style="cyan"))
                
            else:
                self.console.print(f"[red]Failed to fetch status[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def index_workspace(self):
        """Index workspace for semantic search"""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                task = progress.add_task(description="Indexing workspace...", total=None)
                response = requests.post(f"{API_URL}/api/index/workspace", timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.console.print(f"[green]✓ Indexed {result.get('indexed_files', 0)} files[/green]")
                    self.console.print(f"[dim]Collection: {result.get('collection', 'default')}[/dim]")
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
                    table = Table(show_header=False, box=None)
                    table.add_column("Key", style="cyan")
                    table.add_column("Value", style="white")
                    
                    table.add_row("Collection", stats.get('collection', 'unknown'))
                    table.add_row("Documents", str(stats.get('document_count', 0)))
                    table.add_row("Workspace", stats.get('workspace', 'unknown'))
                    
                    self.console.print(Panel(table, title="[bold]Index Statistics[/bold]", border_style="cyan"))
                else:
                    self.console.print(f"[yellow]{stats.get('error', 'Index not available')}[/yellow]")
            else:
                self.console.print(f"[red]Failed to fetch stats[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def show_help(self):
        """Show help with all commands"""
        help_text = """
## 🔧 Commands

### Model Management
- `/models` - List available AI models
- `/switch <provider> [model]` - Switch AI provider/model
  - Example: `/switch ollama deepseek-coder:6.7b`
  - Example: `/switch emergent gpt-5.1`
- `/pull <model>` - Pull model from Ollama registry
  - Example: `/pull deepseek-coder:6.7b`
- `/status` - Show current model status

### Search & Index
- `/index` - Index workspace for semantic search
- `/indexstats` - Show indexing statistics

### Session
- `clear` - Start a new conversation
- `exit` - Quit the application

## 🛠️ Available Tools (Used Automatically)

| Tool | Description |
|------|-------------|
| read_file | Read file contents |
| write_file | Create/overwrite files |
| edit_file | Search/replace editing |
| list_directory | List directory contents |
| run_command | Execute shell commands |
| search_text | Text search (grep) |
| semantic_search | AI-powered code search |
| git_status | Repository status |
| git_diff | Show changes |
| git_log | Commit history |
| git_blame | Line-by-line history |

## 💡 Examples

```
"Read the server.py file and explain it"
"Create a hello world Python script"
"Show me the git status"
"Search for authentication code"
"Find all TODO comments in the codebase"
"Explain how the database connection works"
```

## 💰 Cost

| Provider | Cost |
|----------|------|
| Ollama (Local) | **FREE** |
| Emergent (Cloud) | API credits |

Use `/switch ollama` for FREE local inference!
"""
        self.console.print(Markdown(help_text))
    
    def run(self):
        """Main CLI loop"""
        self.print_banner()
        
        while True:
            try:
                # Get user input with prompt
                provider_indicator = "🟢" if self.current_provider == "ollama" else "🔵"
                self.console.print(f"\n{provider_indicator} [bold cyan]You:[/bold cyan] ", end="")
                user_input = input().strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() == 'exit':
                    self.console.print("[green]Goodbye! 👋[/green]")
                    break
                
                elif user_input.lower() == 'clear':
                    self.conversation_id = None
                    self.console.print("[green]✓ Conversation cleared[/green]")
                    continue
                
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue
                
                elif user_input.lower() == '/models':
                    self.list_models()
                    continue
                
                elif user_input.lower().startswith('/switch'):
                    parts = user_input.split()
                    if len(parts) < 2:
                        self.console.print("[red]Usage: /switch <provider> [model][/red]")
                        self.console.print("[dim]Example: /switch ollama deepseek-coder:6.7b[/dim]")
                    else:
                        provider = parts[1]
                        model = parts[2] if len(parts) > 2 else None
                        self.switch_model(provider, model)
                    continue
                
                elif user_input.lower().startswith('/pull'):
                    parts = user_input.split()
                    if len(parts) < 2:
                        self.console.print("[red]Usage: /pull <model_name>[/red]")
                        self.console.print("[dim]Example: /pull deepseek-coder:6.7b[/dim]")
                        self.console.print("\n[bold]Recommended models:[/bold]")
                        for model, desc in RECOMMENDED_MODELS["ollama"][:5]:
                            self.console.print(f"  • {model} - {desc}")
                    else:
                        model = parts[1]
                        self.pull_model(model)
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
                self.console.print("\n[bold green]🤖 Assistant:[/bold green]\n")
                self.chat(user_input)
            
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except EOFError:
                break


if __name__ == "__main__":
    cli = CodeCompanionCLI()
    cli.run()
