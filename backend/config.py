import os
from pathlib import Path
from typing import Dict, Any
import json


class Config:
    # LLM Configuration
    EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', 'sk-emergent-7C8099801D3E1A68d9')
    
    # Ollama Configuration (Local LLM)
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_DEFAULT_MODEL = os.environ.get('OLLAMA_DEFAULT_MODEL', 'deepseek-coder:6.7b')
    
    # Cloud Model Configuration
    CLOUD_DEFAULT_MODEL = os.environ.get('CLOUD_DEFAULT_MODEL', 'gpt-5.1')
    
    # Provider Mode: "auto", "ollama", "emergent"
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'auto')
    
    # Workspace Configuration
    WORKSPACE_ROOT = os.environ.get('WORKSPACE_ROOT', '/app')
    
    # Database Configuration
    DB_PATH = os.path.expanduser("~/.local/share/codecompanion/codecompanion.db")
    
    # Backup Configuration
    BACKUP_DIR = os.path.expanduser("~/.local/share/codecompanion/backups")
    BACKUP_RETENTION_DAYS = 30
    MAX_BACKUPS_PER_FILE = 100
    
    # Safety Configuration
    AUTO_APPROVE_READ = True
    AUTO_APPROVE_SEARCH = True
    REQUIRE_CONFIRM_WRITE = True
    REQUIRE_CONFIRM_SHELL = True
    MAX_FILE_SIZE = 1048576  # 1MB
    COMMAND_TIMEOUT = 30
    
    # Context Configuration
    MAX_CONTEXT_TOKENS = 8192
    SYSTEM_PROMPT_RESERVE = 2000
    
    # Config file path
    CONFIG_FILE = os.path.expanduser("~/.config/codecompanion/config.json")
    
    @classmethod
    def init_directories(cls):
        """Create necessary directories"""
        Path(cls.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.BACKUP_DIR).mkdir(parents=True, exist_ok=True)
        Path(cls.CONFIG_FILE).parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load_user_config(cls) -> Dict[str, Any]:
        """Load user configuration from file"""
        if Path(cls.CONFIG_FILE).exists():
            try:
                with open(cls.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    @classmethod
    def save_user_config(cls, config: Dict[str, Any]):
        """Save user configuration to file"""
        cls.init_directories()
        with open(cls.CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    
    @classmethod
    def get_llm_settings(cls) -> Dict[str, Any]:
        """Get current LLM settings"""
        user_config = cls.load_user_config()
        return {
            "provider": user_config.get("llm_provider", cls.LLM_PROVIDER),
            "ollama_model": user_config.get("ollama_model", cls.OLLAMA_DEFAULT_MODEL),
            "cloud_model": user_config.get("cloud_model", cls.CLOUD_DEFAULT_MODEL),
            "ollama_url": user_config.get("ollama_url", cls.OLLAMA_BASE_URL),
        }
    
    @classmethod
    def set_llm_settings(cls, provider: str = None, model: str = None, ollama_url: str = None):
        """Update LLM settings"""
        config = cls.load_user_config()
        
        if provider:
            config["llm_provider"] = provider
        if model:
            if provider == "ollama":
                config["ollama_model"] = model
            else:
                config["cloud_model"] = model
        if ollama_url:
            config["ollama_url"] = ollama_url
        
        cls.save_user_config(config)
