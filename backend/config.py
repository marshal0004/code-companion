import os
from pathlib import Path

class Config:
    # LLM Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'sk-emergent-7C8099801D3E1A68d9')
    OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://api.emergent.com/v1')
    MODEL_NAME = os.environ.get('MODEL_NAME', 'gpt-4o')
    
    # Workspace Configuration
    WORKSPACE_ROOT = os.environ.get('WORKSPACE_ROOT', '/app')
    
    # Database Configuration
    DB_PATH = os.path.expanduser("~/.local/share/codecompanion/codecompanion.db")
    
    # Safety Configuration
    AUTO_APPROVE_READ = True
    AUTO_APPROVE_SEARCH = True
    REQUIRE_CONFIRM_WRITE = True
    REQUIRE_CONFIRM_SHELL = True
    MAX_FILE_SIZE = 1048576  # 1MB
    
    @classmethod
    def init_directories(cls):
        Path(cls.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
