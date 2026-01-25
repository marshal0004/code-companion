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
                tool_calls_buffer = []
                current_tool_call = None
                
                stream = llm_client.chat_stream(messages)
                
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    
                    delta = chunk.choices[0].delta
                    
                    # Handle content streaming
                    if delta.content:
                        assistant_message += delta.content
                        yield f"data: {json.dumps({'type': 'content', 'content': delta.content})}\n\n"
                    
                    # Handle tool calls
                    if delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            if tool_call.function:
                                # Start of new tool call
                                if tool_call.function.name:
                                    current_tool_call = {
                                        "id": tool_call.id or "",
                                        "name": tool_call.function.name,
                                        "arguments": ""
                                    }
                                    tool_calls_buffer.append(current_tool_call)
                                
                                # Accumulate arguments
                                if tool_call.function.arguments and current_tool_call:
                                    current_tool_call["arguments"] += tool_call.function.arguments
                    
                    # Check if stream finished
                    if chunk.choices[0].finish_reason == "tool_calls":
                        # Execute tools
                        for tool_call in tool_calls_buffer:
                            try:
                                args = json.loads(tool_call["arguments"])
                                yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_call['name'], 'args': args})}\n\n"
                                
                                result = tool_executor.execute_tool(tool_call["name"], args)
                                
                                yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_call['name'], 'result': result})}\n\n"
                                
                                # Add tool result to messages and continue conversation
                                messages.append({
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [{
                                        "id": tool_call["id"],
                                        "type": "function",
                                        "function": {
                                            "name": tool_call["name"],
                                            "arguments": tool_call["arguments"]
                                        }
                                    }]
                                })
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "content": json.dumps(result)
                                })
                            except Exception as e:
                                logger.error(f"Tool execution error: {e}")
                                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                        
                        # Continue conversation with tool results
                        stream = llm_client.chat_stream(messages)
                        tool_calls_buffer = []
                        current_tool_call = None
                        assistant_message = ""
                        continue
                    
                    if chunk.choices[0].finish_reason == "stop":
                        break
                
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
