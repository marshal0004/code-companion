import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
import uuid
from typing import List, Dict, Optional
import os

DB_PATH = os.path.expanduser("~/.local/share/codecompanion/codecompanion.db")

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                project_path TEXT,
                title TEXT,
                created_at TEXT,
                updated_at TEXT,
                model TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tool_calls (
                id TEXT PRIMARY KEY,
                message_id TEXT,
                tool_name TEXT,
                arguments TEXT,
                result TEXT,
                status TEXT,
                created_at TEXT,
                FOREIGN KEY(message_id) REFERENCES messages(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_conversation(self, project_path: str, model: str = "gpt-4o") -> str:
        conv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO conversations (id, project_path, title, created_at, updated_at, model)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (conv_id, project_path, "New Conversation", now, now, model))
        conn.commit()
        conn.close()
        return conv_id
    
    def add_message(self, conversation_id: str, role: str, content: str) -> str:
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (id, conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (msg_id, conversation_id, role, content, now))
        
        # Update conversation timestamp
        cursor.execute('''
            UPDATE conversations SET updated_at = ? WHERE id = ?
        ''', (now, conversation_id))
        
        conn.commit()
        conn.close()
        return msg_id
    
    def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC
        ''', (conversation_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def list_conversations(self, limit: int = 20) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def add_tool_call(self, message_id: str, tool_name: str, arguments: dict, result: str = None, status: str = "completed") -> str:
        tool_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tool_calls (id, message_id, tool_name, arguments, result, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (tool_id, message_id, tool_name, json.dumps(arguments), result, status, now))
        conn.commit()
        conn.close()
        return tool_id
