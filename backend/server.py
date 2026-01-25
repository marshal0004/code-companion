from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import logging
import json
import asyncio
from pathlib import Path

from database import Database
from llm_client import LLMClient
from tools import ToolExecutor
from config import Config

# Initialize config
Config.init_directories()

# Create FastAPI app
app = FastAPI(title="CodeCompanion API")
api_router = APIRouter(prefix="/api")

# Initialize components
db = Database()
llm_client = LLMClient()
tool_executor = ToolExecutor()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    project_path: str = "/app"

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    message_count: int

@api_router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint with tool execution"""
    try:
        # Get or create conversation
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = db.create_conversation(request.project_path)
        
        # Add user message
        db.add_message(conversation_id, "user", request.message)
        
        # Get conversation history
        history = db.get_conversation_messages(conversation_id)
        
        # Build messages for LLM
        messages = [{"role": "system", "content": llm_client.get_system_prompt()}]
        for msg in history:
            messages.append({"role": msg['role'], "content": msg['content']})
        
        # Stream response
        async def generate():
            try:
                assistant_message = ""
                
                # Get LLM response
                response = await llm_client.chat_stream(messages, conversation_id)
                assistant_message = response
                
                # Stream the response word by word for better UX
                words = response.split()
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for streaming effect
                
                # Save assistant message
                if assistant_message:
                    db.add_message(conversation_id, "assistant", assistant_message)
                
                yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
                
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/conversations")
async def list_conversations():
    """List all conversations"""
    try:
        conversations = db.list_conversations()
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"List conversations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation messages"""
    try:
        messages = db.get_conversation_messages(conversation_id)
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "codecompanion"}

# Include router
app.include_router(api_router)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
